"""
GOES Pipeline — Etapa 0: Download em massa via NASA GIBS WMS API
================================================================
Substitui a captura Playwright (lenta, ~20s/img) por requisições HTTP diretas
ao serviço GIBS da NASA, que expõe a mesma camada GOES-East IR C13 do Worldview.

Resultado: data/nasa_captures/*.png
  - 9 regiões × 180 dias × 3 horários UTC = ~4860 imagens
  - Download paralelo (20 workers) → ~15–25 min

API usada: NASA GIBS WMS 1.3.0
  https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi
  Documentação: https://wiki.earthdata.nasa.gov/display/GIBS

Execute a partir do root do projeto:
    python scripts/goes_pipeline/00_download_gibs.py
    python scripts/goes_pipeline/00_download_gibs.py --dias 180 --workers 20
    python scripts/goes_pipeline/00_download_gibs.py --limpar  # apaga capturas antigas antes
"""

from __future__ import annotations

import argparse
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

PROJECT_ROOT  = Path(__file__).resolve().parents[2]
CAPTURES_DIR  = PROJECT_ROOT / "data" / "nasa_captures"
CAPTURES_DIR.mkdir(parents=True, exist_ok=True)

GIBS_WMS = "https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi"
LAYER    = "GOES-East_ABI_Band13_Clean_Infrared"
IMG_W    = 1024
IMG_H    = 1024

# Horários UTC capturados por dia — diversidade temporal (madrugada, manhã e tarde BR)
HORARIOS_UTC = ["00:00:00", "12:00:00", "21:00:00"]

# Regiões: west, south, east, north (EPSG:4326)
# Para WMS 1.3.0, BBOX = south,west,north,east
REGIOES = [
    {"nome": "nasa_americas",       "w": -120, "s": -60, "e": 20,  "n": 35},
    {"nome": "nasa_brasil",         "w": -75,  "s": -35, "e": -28, "n": 8},
    {"nome": "nasa_brasil_sudeste", "w": -55,  "s": -26, "e": -38, "n": -18},
    {"nome": "nasa_nordeste",       "w": -45,  "s": -15, "e": -34, "n": 0},
    {"nome": "nasa_norte",          "w": -70,  "s": -5,  "e": -48, "n": 5},
    {"nome": "nasa_sul",            "w": -56,  "s": -34, "e": -48, "n": -26},
    {"nome": "nasa_argentina",      "w": -70,  "s": -55, "e": -50, "n": -30},
    {"nome": "nasa_colombia",       "w": -80,  "s": 0,   "e": -60, "n": 15},
    {"nome": "nasa_peru_bolivia",   "w": -80,  "s": -20, "e": -60, "n": -5},
]

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "global-solutions-gs2/1.0 (FIAP dataset)"})


def _wms_url(regiao: dict, data: str, hora: str) -> str:
    s, w, n, e = regiao["s"], regiao["w"], regiao["n"], regiao["e"]
    return (
        f"{GIBS_WMS}"
        f"?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap"
        f"&BBOX={s},{w},{n},{e}"
        f"&CRS=EPSG:4326"
        f"&WIDTH={IMG_W}&HEIGHT={IMG_H}"
        f"&LAYERS={LAYER}"
        f"&STYLES=&FORMAT=image/png"
        f"&TIME={data}T{hora}Z"
    )


def _filename(regiao: dict, data: str, hora: str) -> str:
    hora_tag = hora.replace(":", "")[:4]
    data_tag = data.replace("-", "")
    return f"{regiao['nome']}_{data_tag}_{hora_tag}.png"


def _download_one(regiao: dict, data: str, hora: str, timeout: int = 30) -> dict:
    fname   = _filename(regiao, data, hora)
    dest    = CAPTURES_DIR / fname

    if dest.exists() and dest.stat().st_size > 5_000:
        return {"status": "skip", "file": fname}

    url = _wms_url(regiao, data, hora)
    try:
        r = SESSION.get(url, timeout=timeout)
        r.raise_for_status()

        content_type = r.headers.get("Content-Type", "")
        if "image" not in content_type:
            return {"status": "erro", "file": fname,
                    "erro": f"Content-Type inesperado: {content_type}"}

        if len(r.content) < 5_000:
            return {"status": "vazio", "file": fname}

        dest.write_bytes(r.content)
        return {"status": "ok", "file": fname, "bytes": len(r.content)}

    except Exception as exc:
        return {"status": "erro", "file": fname, "erro": str(exc)}


def _build_tarefas(dias: int) -> list[tuple[dict, str, str]]:
    hoje  = datetime.now(timezone.utc).date()
    tarefas = []
    for d in range(1, dias + 1):
        data = (hoje - timedelta(days=d)).isoformat()
        for regiao in REGIOES:
            for hora in HORARIOS_UTC:
                tarefas.append((regiao, data, hora))
    return tarefas


def download(dias: int = 90, workers: int = 8, limpar: bool = False) -> None:
    if limpar:
        removidos = 0
        for f in CAPTURES_DIR.glob("*.png"):
            f.unlink()
            removidos += 1
        print(f"🗑️  Removidas {removidos} imagens antigas de {CAPTURES_DIR}\n")

    tarefas  = _build_tarefas(dias)
    total    = len(tarefas)
    n_reg    = len(REGIOES)
    n_hor    = len(HORARIOS_UTC)

    print(f"{'='*65}")
    print(f"  NASA GIBS WMS — download em massa")
    print(f"  Regiões   : {n_reg}")
    print(f"  Dias      : {dias}")
    print(f"  Horários  : {n_hor} por dia ({', '.join(HORARIOS_UTC)})")
    print(f"  Total     : {total} requisições")
    print(f"  Workers   : {workers} paralelos")
    print(f"  Destino   : {CAPTURES_DIR}")
    print(f"{'='*65}\n")

    ok = skip = vazio = erro = 0
    t0 = time.time()

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futuros = {pool.submit(_download_one, r, d, h): (r, d, h)
                   for r, d, h in tarefas}

        for i, fut in enumerate(as_completed(futuros), 1):
            res = fut.result()
            s   = res["status"]

            if s == "ok":
                ok += 1
                icon = "✓"
            elif s == "skip":
                skip += 1
                icon = "~"
            elif s == "vazio":
                vazio += 1
                icon = "∅"
            else:
                erro += 1
                icon = "✗"

            if i % 50 == 0 or s == "erro":
                elapsed = time.time() - t0
                rate    = i / elapsed if elapsed > 0 else 0
                eta     = (total - i) / rate if rate > 0 else 0
                print(f"  [{i:>5}/{total}] {icon} {res['file']:<55} "
                      f"| ok={ok} skip={skip} vazio={vazio} erro={erro} "
                      f"| {rate:.1f}/s ETA {eta/60:.1f}min")
                if s == "erro":
                    print(f"         → {res.get('erro', '?')}")

    elapsed = time.time() - t0
    total_png = sum(1 for _ in CAPTURES_DIR.glob("*.png"))

    print(f"\n{'='*65}")
    print(f"  ✅ Download concluído em {elapsed/60:.1f} min")
    print(f"  ok={ok}  skip={skip}  vazio={vazio}  erro={erro}")
    print(f"  PNGs em {CAPTURES_DIR}: {total_png}")
    print(f"\n  Próximo passo:")
    print(f"    python scripts/goes_pipeline/04_nasa_to_yolo.py --clean")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Download em massa NASA GIBS WMS → data/nasa_captures/",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--dias",    type=int, default=180,
                        help="Quantos dias para trás baixar")
    parser.add_argument("--workers", type=int, default=8,
                        help="Downloads paralelos")
    parser.add_argument("--limpar",  action="store_true",
                        help="Apagar imagens existentes antes de baixar")
    args = parser.parse_args()
    download(dias=args.dias, workers=args.workers, limpar=args.limpar)
