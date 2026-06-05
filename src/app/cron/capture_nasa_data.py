"""
capture_nasa_data.py — Captura imagens do NASA Worldview (GOES-East IR Band 13)

Mesmo dado do GOES-16 C13 usado pelo Windy, renderizado pelo NASA Worldview
sobre um mapa. Visual compatível com screenshots do Windy satélite.

Uso:
    # Captura do dia atual (todas as regiões)
    python src/app/cron/capture_nasa_data.py

    # Captura retroativa dos últimos 30 dias (monta dataset)
    python src/app/cron/capture_nasa_data.py --historico --dias 30

    # Captura uma data específica
    python src/app/cron/capture_nasa_data.py --data 2024-03-15

Saída (canônica):
    - S3:     s3://{S3_BUCKET_IMAGES}/nasa-satellite/{ano}/{mes}/{dia}/{arquivo}
    - Local:  data/nasa_captures/ apenas se NASA_KEEP_LOCAL=true (treino offline)
"""

import argparse
import logging
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

_SRC = Path(__file__).resolve().parents[2]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from app.core.config import settings
from app.services.nasa_captures import s3_has_capture

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# ── Caminhos ───────────────────────────────────────────────────────────────────
PROJECT_ROOT   = Path(__file__).resolve().parents[3]
CAPTURES_DIR   = PROJECT_ROOT / "data" / "nasa_captures"
CAPTURES_DIR.mkdir(parents=True, exist_ok=True)

# ── Configuração das regiões ───────────────────────────────────────────────────
# bbox = west,south,east,north | camada IR C13 do GOES-East
LAYER = "GOES-East_ABI_Band13_Clean_Infrared"

REGIOES = [
    {
        "nome":      "nasa_americas",
        "bbox":      "-120,-60,20,35",
        "descricao": "Américas completas — GOES-East IR C13",
    },
    {
        "nome":      "nasa_brasil",
        "bbox":      "-75,-35,-28,8",
        "descricao": "Brasil completo — GOES-East IR C13",
    },
    {
        "nome":      "nasa_brasil_sudeste",
        "bbox":      "-55,-26,-38,-18",
        "descricao": "Sudeste do Brasil (SP / RJ / MG) — GOES-East IR C13",
    },
]

VIEWPORT   = {"width": 1920, "height": 1080}
WAIT_MS    = 15_000   # ms aguardando renderização dos tiles


# ── Captura ────────────────────────────────────────────────────────────────────

def _url(bbox: str, data: str) -> str:
    return (
        f"https://worldview.earthdata.nasa.gov/"
        f"?v={bbox}&l={LAYER}&t={data}&sm=false"
    )


def _limpar_ui(page) -> None:
    """Remove chrome da UI NASA Worldview que gera bboxes fantasma no pipeline YOLO."""
    try:
        page.evaluate("""
            const selectors = [
                '#timeline-footer', '#app-sidebar', '#toolbar', '.ol-control',
                '#wv-logo', '.notification-banner', '.tour-overlay', '#data-panel',
                '#layers-sidebar', '#events-sidebar', '.layer-info', '.layer-options',
                '.date-display', '.date-selector', '.time-selector', '.timeline',
                '.timeline-axis', '.timeline-label', '.timeline-tick',
                '.wv-date-line', '.wv-date-line-layer', '#date-selector',
                '.settings-dropdown', '.settings-panel', '.layer-list-header',
                '.layer-category', '.layer-category-header', '.layer-category-content',
                '[class*="legend"]', '[class*="Legend"]', '[id*="legend"]',
                '.distro-tooltip', '.tooltip', '.modal', '.modal-backdrop',
                'header', 'footer', 'nav',
            ];
            selectors.forEach(s => {
                document.querySelectorAll(s).forEach(el => {
                    el.style.display = 'none';
                    el.style.visibility = 'hidden';
                });
            });
        """)
    except Exception:
        pass


def capturar_regiao(regiao: dict, data: str) -> Path:
    """
    Captura screenshot do NASA Worldview para uma região e data.

    Returns:
        Path do arquivo salvo localmente.
    """
    ts       = datetime.now(timezone.utc)
    filename = f"{regiao['nome']}_{ts.strftime('%Y%m%d_%H%M')}.png"
    destino  = CAPTURES_DIR / filename
    url      = _url(regiao["bbox"], data)

    logger.info("Capturando %s (%s)...", regiao["nome"], data)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
        )
        page = browser.new_context(viewport=VIEWPORT).new_page()
        try:
            page.goto(url, wait_until="networkidle", timeout=90_000)
            page.wait_for_timeout(WAIT_MS)

            # Fecha modal de boas-vindas se aparecer
            for texto in ["Skip", "No thanks", "Fechar"]:
                try:
                    page.locator(f"button:has-text('{texto}')").click(timeout=2_000)
                except Exception:
                    pass

            _limpar_ui(page)
            page.wait_for_timeout(800)
            page.screenshot(path=str(destino), full_page=False)

        except PlaywrightTimeout as e:
            logger.error("Timeout %s: %s", regiao["nome"], e)
            raise
        finally:
            browser.close()

    logger.info("✓ Captura temporária: %s (%d KB)", destino.name, destino.stat().st_size // 1024)
    return destino


def _finalize_capture(caminho: Path, data: str) -> str | None:
    """Envia para S3 e remove do disco local quando NASA_KEEP_LOCAL=false."""
    s3_key = upload_s3(caminho, data)
    if s3_key and not settings.NASA_KEEP_LOCAL:
        caminho.unlink(missing_ok=True)
        logger.info("✓ Removido do disco local: %s", caminho.name)
    elif not s3_key and not settings.NASA_KEEP_LOCAL:
        logger.warning(
            "Upload S3 falhou — %s mantido localmente até novo upload",
            caminho.name,
        )
    return s3_key


def upload_s3(caminho: Path, data: str) -> str | None:
    """
    Upload para S3 (arquivo PNG no prefixo NASA_S3_PREFIX).

    Returns:
        s3_key se enviou, None se falhou ou bucket vazio.
    """
    bucket = (settings.S3_BUCKET_IMAGES or "").strip()
    if not bucket:
        logger.warning("S3_BUCKET_IMAGES não configurado — pulando upload de %s", caminho.name)
        return None

    dt = datetime.strptime(data, "%Y-%m-%d")
    prefix = (settings.NASA_S3_PREFIX or "nasa-satellite").strip("/")
    s3_key = f"{prefix}/{dt.year}/{dt.month:02d}/{dt.day:02d}/{caminho.name}"

    try:
        s3 = boto3.client("s3", region_name=settings.AWS_REGION)
        s3.upload_file(
            str(caminho), bucket, s3_key,
            ExtraArgs={"ContentType": "image/png"},
        )
        logger.info("✓ S3: s3://%s/%s", bucket, s3_key)
        return s3_key
    except (BotoCoreError, ClientError) as e:
        logger.warning("Upload S3 falhou (continuando): %s", e)
        return None


def upload_s3_cv_jpg(caminho: Path) -> str | None:
    """
    Converte PNG → JPG e envia para screenshots/ (dispara Lambda S3 em produção).

    Returns:
        s3_key do .jpg ou None.
    """
    bucket = (settings.S3_BUCKET_IMAGES or "").strip()
    if not bucket:
        return None

    prefix = (settings.NASA_CV_S3_PREFIX or "screenshots").strip("/")
    jpg_name = caminho.stem + ".jpg"
    s3_key = f"{prefix}/{jpg_name}"

    try:
        from PIL import Image

        jpg_local = caminho.with_suffix(".jpg")
        with Image.open(caminho) as img:
            rgb = img.convert("RGB")
            rgb.save(jpg_local, format="JPEG", quality=92)

        s3 = boto3.client("s3", region_name=settings.AWS_REGION)
        s3.upload_file(
            str(jpg_local), bucket, s3_key,
            ExtraArgs={"ContentType": "image/jpeg"},
        )
        logger.info("✓ S3 CV: s3://%s/%s", bucket, s3_key)
        if jpg_local != caminho and jpg_local.exists():
            jpg_local.unlink(missing_ok=True)
        return s3_key
    except (BotoCoreError, ClientError) as e:
        logger.warning("Upload CV S3 falhou: %s", e)
        return None
    except OSError as e:
        logger.warning("Conversão PNG→JPG falhou: %s", e)
        return None


def trigger_cv_pipeline(bucket: str, s3_key: str) -> dict | None:
    """Executa pipeline YOLO localmente (dev) após upload em screenshots/."""
    try:
        from app.routers.cv import process_s3_image
        return process_s3_image(bucket=bucket, key=s3_key)
    except Exception as e:
        logger.warning("Pipeline CV local falhou: %s", e)
        return None


def capturar_todas(
    data: str | None = None,
    *,
    upload_cv_jpg: bool = False,
    trigger_cv_local: bool = False,
) -> list[dict]:
    """Captura todas as regiões para uma data."""
    if data is None:
        data = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    resultados = []
    for regiao in REGIOES:
        try:
            caminho  = capturar_regiao(regiao, data)
            s3_key   = _finalize_capture(caminho, data)
            cv_key   = upload_s3_cv_jpg(caminho) if (upload_cv_jpg or trigger_cv_local) else None
            cv_result = None
            if trigger_cv_local and cv_key and settings.S3_BUCKET_IMAGES:
                cv_result = trigger_cv_pipeline(settings.S3_BUCKET_IMAGES, cv_key)
            resultados.append({
                "regiao":    regiao["nome"],
                "arquivo":   caminho.name,
                "caminho":   str(caminho),
                "s3_key":    s3_key,
                "cv_s3_key": cv_key,
                "cv_result": cv_result,
                "data":      data,
                "status":    "ok",
                "tamanho_kb": caminho.stat().st_size // 1024,
            })
        except Exception as e:
            logger.error("Erro em %s: %s", regiao["nome"], e)
            resultados.append({
                "regiao": regiao["nome"],
                "data":   data,
                "status": "erro",
                "erro":   str(e),
            })
    return resultados


def capturar_historico(dias: int = 30) -> list[dict]:
    """
    Baixa imagens retroativas do NASA Worldview (até 90 dias).

    Ideal para montar o dataset sem esperar capturas em tempo real.
    """
    dias = min(dias, 90)
    hoje = datetime.now(timezone.utc)
    todos = []

    print(f"\nCapturando {dias} dias × {len(REGIOES)} regiões...\n")

    for d in range(dias):
        data = (hoje - timedelta(days=d + 1)).strftime("%Y-%m-%d")
        print(f"  [{d+1}/{dias}] {data}")
        for regiao in REGIOES:
            if s3_has_capture(regiao["nome"], data):
                print(f"    [SKIP] {regiao['nome']} (já no S3)")
                continue
            if settings.NASA_KEEP_LOCAL:
                existente = list(CAPTURES_DIR.glob(f"{regiao['nome']}_*.png"))
                if any(data.replace("-", "") in f.name for f in existente):
                    print(f"    [SKIP] {regiao['nome']} (local)")
                    continue
            try:
                caminho = capturar_regiao(regiao, data)
                _finalize_capture(caminho, data)
                todos.append({"data": data, "regiao": regiao["nome"], "status": "ok"})
                print(f"    ✓ {regiao['nome']}")
            except Exception as e:
                todos.append({"data": data, "regiao": regiao["nome"], "status": "erro", "erro": str(e)})
                print(f"    ✗ {regiao['nome']}: {e}")

    ok = sum(1 for r in todos if r["status"] == "ok")
    print(f"\n✓ Concluído: {ok}/{len(todos)} capturas")
    return todos


# ── CLI ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Captura imagens do NASA Worldview (GOES-East IR C13)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--data",      default=None, help="Data específica YYYY-MM-DD")
    parser.add_argument("--historico", action="store_true", help="Baixar retroativamente")
    parser.add_argument("--dias",      type=int, default=30, help="Dias para trás (--historico)")
    parser.add_argument(
        "--upload-cv-jpg",
        action="store_true",
        help="Envia JPG em screenshots/ (dispara pipeline CV na Lambda via S3)",
    )
    parser.add_argument(
        "--trigger-cv",
        action="store_true",
        help="Dev: inclui --upload-cv-jpg e roda YOLO localmente após upload",
    )
    args = parser.parse_args()

    if args.historico:
        capturar_historico(dias=args.dias)
    else:
        resultados = capturar_todas(
            data=args.data,
            upload_cv_jpg=args.upload_cv_jpg or args.trigger_cv,
            trigger_cv_local=args.trigger_cv,
        )
        ok = sum(1 for r in resultados if r["status"] == "ok")
        print(f"\n✓ {ok}/{len(resultados)} regiões capturadas → {CAPTURES_DIR}")
