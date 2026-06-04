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

Saída:
    - Local:  data/nasa_captures/{regiao}_{YYYYMMDD_HHMM}.png
    - S3:     s3://{S3_BUCKET_IMAGES}/nasa-satellite/{ano}/{mes}/{dia}/{arquivo}
              (apenas se S3_BUCKET_IMAGES estiver configurado no .env)
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
    try:
        page.evaluate("""
            ['#timeline-footer','#app-sidebar','#toolbar','.ol-control',
             '#wv-logo','.notification-banner','.tour-overlay','#data-panel']
            .forEach(s => document.querySelectorAll(s)
                .forEach(el => el.style.display = 'none'));
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

    logger.info("✓ Salvo local: %s (%d KB)", destino.name, destino.stat().st_size // 1024)
    return destino


def upload_s3(caminho: Path, data: str) -> str | None:
    """
    Faz upload para S3 se S3_BUCKET_IMAGES estiver configurado.

    Returns:
        s3_key se enviou, None se bucket não configurado.
    """
    bucket = settings.S3_BUCKET_IMAGES
    if not bucket or bucket == "input-images":
        logger.debug("S3 não configurado — pulando upload de %s", caminho.name)
        return None

    dt       = datetime.strptime(data, "%Y-%m-%d")
    s3_key   = f"nasa-satellite/{dt.year}/{dt.month:02d}/{dt.day:02d}/{caminho.name}"

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


def capturar_todas(data: str | None = None) -> list[dict]:
    """Captura todas as regiões para uma data."""
    if data is None:
        data = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    resultados = []
    for regiao in REGIOES:
        try:
            caminho  = capturar_regiao(regiao, data)
            s3_key   = upload_s3(caminho, data)
            resultados.append({
                "regiao":    regiao["nome"],
                "arquivo":   caminho.name,
                "caminho":   str(caminho),
                "s3_key":    s3_key,
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
            # Pula se já existe localmente
            existente = list(CAPTURES_DIR.glob(f"{regiao['nome']}_*.png"))
            if any(data.replace("-", "") in f.name for f in existente):
                print(f"    [SKIP] {regiao['nome']}")
                continue
            try:
                caminho = capturar_regiao(regiao, data)
                upload_s3(caminho, data)
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
    args = parser.parse_args()

    if args.historico:
        capturar_historico(dias=args.dias)
    else:
        resultados = capturar_todas(data=args.data)
        ok = sum(1 for r in resultados if r["status"] == "ok")
        print(f"\n✓ {ok}/{len(resultados)} regiões capturadas → {CAPTURES_DIR}")
