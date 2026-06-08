"""
INMET — cliente para estações automáticas e BDMEP (dados históricos).

Fontes:
  - Catálogo: https://apitempo.inmet.gov.br/estacoes/T
  - BDMEP ZIP anual: https://portal.inmet.gov.br/uploads/dadoshistoricos/{year}.zip
"""

from __future__ import annotations

import io
import logging
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

from app.services.external_api_rate_limit import acquire_external_api_slot

logger = logging.getLogger(__name__)

BDMEP_ZIP_URL = "https://portal.inmet.gov.br/uploads/dadoshistoricos/{year}.zip"
STATIONS_URL = "https://apitempo.inmet.gov.br/estacoes/T"

# Estações operantes alinhadas às capitais do MVP
DEFAULT_TRAINING_STATIONS: list[dict[str, str]] = [
    {"code": "A701", "city": "São Paulo", "uf": "SP"},
    {"code": "A636", "city": "Rio de Janeiro", "uf": "RJ"},
    {"code": "A001", "city": "Brasília", "uf": "DF"},
    {"code": "A801", "city": "Porto Alegre", "uf": "RS"},
    {"code": "A201", "city": "Belém", "uf": "PA"},
]

# Índices fixos do CSV horário BDMEP (após cabeçalho de metadados)
_COL_DATA = 0
_COL_HORA = 1
_COL_PRECIP = 2
_COL_TEMP = 7
_COL_UMID = 15
_COL_VENTO_MS = 18

_NULL_MARKERS = frozenset({"", "-", "null", "NULL", "9999", "-9999"})


@dataclass(frozen=True)
class InmetHourlyRecord:
    timestamp: str
    station_code: str
    city: str
    uf: str
    temperatura: float
    umidade: float
    precipitacao: float
    vento_kmh: float

    def as_features(self) -> list[float]:
        return [self.temperatura, self.umidade, self.precipitacao, self.vento_kmh]


def _parse_br_number(raw: str) -> float | None:
    text = (raw or "").strip()
    if text in _NULL_MARKERS:
        return None
    text = text.replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def _parse_hora(hora_raw: str) -> str:
    """'0000 UTC' -> '00:00'."""
    digits = re.sub(r"\D", "", hora_raw)[:4]
    if len(digits) < 4:
        return "00:00"
    return f"{digits[:2]}:{digits[2:4]}"


def parse_bdmep_csv(
    content: str,
    *,
    station_code: str,
    city: str,
    uf: str,
) -> list[InmetHourlyRecord]:
    """Parseia um CSV horário BDMEP (latin-1, separador ';')."""
    lines = content.splitlines()
    data_start = 0
    for i, line in enumerate(lines):
        if line.startswith("Data;Hora"):
            data_start = i + 1
            break

    records: list[InmetHourlyRecord] = []
    for line in lines[data_start:]:
        if not line.strip():
            continue
        parts = line.split(";")
        if len(parts) < 19:
            continue

        temp = _parse_br_number(parts[_COL_TEMP])
        umid = _parse_br_number(parts[_COL_UMID])
        precip = _parse_br_number(parts[_COL_PRECIP])
        vento_ms = _parse_br_number(parts[_COL_VENTO_MS])
        if temp is None or umid is None or precip is None or vento_ms is None:
            continue

        date_raw = parts[_COL_DATA].strip()
        hora = _parse_hora(parts[_COL_HORA])
        date_norm = date_raw.replace("/", "-")
        ts = f"{date_norm}T{hora}:00"

        records.append(
            InmetHourlyRecord(
                timestamp=ts,
                station_code=station_code,
                city=city,
                uf=uf,
                temperatura=temp,
                umidade=umid,
                precipitacao=max(0.0, precip),
                vento_kmh=round(vento_ms * 3.6, 2),
            )
        )
    return records


class InmetClient:
    def __init__(self, session: requests.Session | None = None) -> None:
        self.session = session or requests.Session()
        self.session.headers.setdefault("User-Agent", "global-solutions/1.0")

    def list_stations(self) -> list[dict[str, Any]]:
        acquire_external_api_slot("inmet")
        resp = self.session.get(STATIONS_URL, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, list):
            raise ValueError("Resposta inesperada do catálogo INMET")
        return data

    def fetch_bdmep_year(
        self,
        year: int,
        station_codes: list[str] | None = None,
    ) -> dict[str, str]:
        """Baixa ZIP BDMEP do ano e retorna {code: csv_text} para estações filtradas."""
        codes = set(station_codes or [s["code"] for s in DEFAULT_TRAINING_STATIONS])
        url = BDMEP_ZIP_URL.format(year=year)
        logger.info("INMET BDMEP: baixando %s", url)
        acquire_external_api_slot("inmet-bdmep")
        resp = self.session.get(url, timeout=600)
        resp.raise_for_status()

        out: dict[str, str] = {}
        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            for name in zf.namelist():
                if not name.upper().endswith(".CSV"):
                    continue
                matched = next((c for c in codes if f"_{c}_" in name.upper() or f"_{c}." in name.upper()), None)
                if not matched:
                    continue
                out[matched] = zf.read(name).decode("latin-1", errors="replace")
                logger.info("INMET BDMEP: extraído %s (%s)", matched, name)
        return out

    def load_training_records(
        self,
        years: list[int] | None = None,
        stations: list[dict[str, str]] | None = None,
    ) -> list[InmetHourlyRecord]:
        station_list = stations or DEFAULT_TRAINING_STATIONS
        meta = {s["code"]: s for s in station_list}
        years = years or [2024]
        all_records: list[InmetHourlyRecord] = []

        for year in years:
            files = self.fetch_bdmep_year(year, list(meta.keys()))
            for code, csv_text in files.items():
                info = meta[code]
                parsed = parse_bdmep_csv(
                    csv_text,
                    station_code=code,
                    city=info["city"],
                    uf=info["uf"],
                )
                all_records.extend(parsed)
                logger.info("INMET %s %s: %d registros horários", year, code, len(parsed))

        if not all_records:
            raise ValueError("INMET BDMEP não retornou registros para as estações configuradas")
        return all_records

    @staticmethod
    def load_cache_csv(path: Path) -> list[InmetHourlyRecord]:
        import csv

        if not path.exists():
            raise FileNotFoundError(path)
        records: list[InmetHourlyRecord] = []
        with path.open(encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                records.append(
                    InmetHourlyRecord(
                        timestamp=row["timestamp"],
                        station_code=row["station_code"],
                        city=row["city"],
                        uf=row["uf"],
                        temperatura=float(row["temperatura"]),
                        umidade=float(row["umidade"]),
                        precipitacao=float(row["precipitacao"]),
                        vento_kmh=float(row["vento_kmh"]),
                    )
                )
        return records

    @staticmethod
    def save_cache_csv(path: Path, records: list[InmetHourlyRecord]) -> None:
        import csv

        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "timestamp", "station_code", "city", "uf",
                    "temperatura", "umidade", "precipitacao", "vento_kmh",
                ],
            )
            writer.writeheader()
            for rec in records:
                writer.writerow({
                    "timestamp": rec.timestamp,
                    "station_code": rec.station_code,
                    "city": rec.city,
                    "uf": rec.uf,
                    "temperatura": rec.temperatura,
                    "umidade": rec.umidade,
                    "precipitacao": rec.precipitacao,
                    "vento_kmh": rec.vento_kmh,
                })
