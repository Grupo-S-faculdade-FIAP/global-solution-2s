import sys
from datetime import datetime, timezone
from pathlib import Path

import boto3
from playwright.sync_api import sync_playwright

_SRC = Path(__file__).resolve().parents[2]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from app.core.config import settings

# URL do Windy + camada satélite INFRA+
gondorTown = "https://www.windy.com/pt/-Sat%C3%A9lite-satellite?satellite,6.868,-10.667,9,p:cams"
saoPaulo = "https://www.windy.com/pt/-Sat%C3%A9lite-satellite?satellite,-24.104,-46.633,8,p:cams"
URL = gondorTown

def capture():
    ts = datetime.now(timezone.utc)
    filename = f"satellite_data_{ts.strftime('%Y%m%d_%H%M')}.jpg"
    s3_key = f"satellite-data/{ts.strftime('%Y/%m/%d/%H')}/{filename}"

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.goto(URL, wait_until="load", timeout=90000)
        page.locator("#map-container").wait_for(state="visible", timeout=30000)

        page.wait_for_timeout(10000)
        
        page.evaluate("""
            document.querySelectorAll(".switch__item.svelte-ngn3sj")[2].click();
            document.querySelectorAll('#plugin-radar-plus, #logo-wrapper, .rhpane, #search, .webcams-thumbnail')
                .forEach(el => el.style.display = 'none')
        """)
        
        page.screenshot(path=filename, full_page=False)
        browser.close()

    if not settings.S3_BUCKET_IMAGES:
        print("ERRO: defina S3_BUCKET_IMAGES no .env", file=sys.stderr)
        sys.exit(1)

    s3 = boto3.client("s3", region_name=settings.AWS_REGION)
    try:
        s3.upload_file(
            filename,
            settings.S3_BUCKET_IMAGES,
            s3_key,
            ExtraArgs={"ContentType": "image/jpeg"},
        )
    except Exception as exc:
        print(f"ERRO upload: {exc}", file=sys.stderr)
        sys.exit(1)

    Path(filename).unlink()
    print(f"OK: s3://{settings.S3_BUCKET_IMAGES}/{s3_key}")

if __name__ == "__main__":
    capture()