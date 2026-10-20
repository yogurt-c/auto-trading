"""백테스트 데이터 수집 — 캐시가 있으면 건너뛰므로 중단 후 다시 실행하면 이어서 받는다.

.venv/bin/python scripts/fetch_data.py krx     # KRX 일별 원본 (약 8,500회, 한도 10,000/일)
.venv/bin/python scripts/fetch_data.py panel   # 종목 패널·수정계수·유니버스·지수 생성
.venv/bin/python scripts/fetch_data.py dart    # 유니버스 종목의 공시·배당 (DART)
.venv/bin/python scripts/fetch_data.py bench   # KODEX 200 (yfinance)
"""

from __future__ import annotations

import argparse
import os
from datetime import date

import pandas as pd
from dotenv import load_dotenv

from research import config
from research.data.dart import DartClient, map_corp_codes
from research.data.index import load_kodex200, normalize_index_rows
from research.data.krx import KOSPI_INDEX, KOSPI_STOCKS, KrxClient
from research.data.prices import add_adjustment, normalize_stock_rows
from research.paths import DATA_DIR, RESEARCH_DIR
from research.universe import build_universe

PANEL_PATH = DATA_DIR / "panel.parquet"
UNIVERSE_PATH = DATA_DIR / "universe.parquet"
INDEX_PATH = DATA_DIR / "kospi200.parquet"


def _range() -> tuple[date, date]:
    periods = config.load("periods")
    return config.to_date(periods["data_start"]), config.to_date(periods["test"]["end"])


def fetch_krx() -> None:
    start, end = _range()
    client = KrxClient(os.environ.get("KRX_AUTH_KEY", ""))
    for service in (KOSPI_STOCKS, KOSPI_INDEX):
        calls = client.fetch_range(service, start, end)
        print(f"{service}: 신규 호출 {calls}회 (누적 {client.calls})")


def build_panel() -> None:
    start, end = _range()
    client = KrxClient(os.environ.get("KRX_AUTH_KEY", "unused-for-cache-read"))
    panel = add_adjustment(normalize_stock_rows(client.load_range(KOSPI_STOCKS, start, end)))
    panel.to_parquet(PANEL_PATH, index=False)

    universe = build_universe(panel, config.load("universe"))
    universe.to_parquet(UNIVERSE_PATH, index=False)

    index_name = config.load("strategy")["regime_filter"]["index"]
    kospi200 = normalize_index_rows(client.load_range(KOSPI_INDEX, start, end), index_name)
    kospi200.to_frame("close").to_parquet(INDEX_PATH)

    events = panel[panel["factor"] != 1.0]
    print(f"패널 {len(panel):,}행, 종목 {panel['code'].nunique():,}개, 조정 이벤트 {len(events)}건")
    print(
        f"유니버스 리밸런싱 {universe['rebalance_date'].nunique()}회, 고유 종목 "
        f"{universe['code'].nunique()}개"
    )
    print(f"{index_name} {len(kospi200)}일")


def fetch_dart() -> None:
    start, end = _range()
    client = DartClient(os.environ.get("DART_API_KEY", ""))
    corp = client.corp_codes()
    panel = pd.read_parquet(PANEL_PATH, columns=["code", "name"])
    panel = panel.drop_duplicates("code", keep="last")
    codes = pd.read_parquet(UNIVERSE_PATH)["code"].unique()

    mapping = map_corp_codes(panel[panel["code"].isin(codes)], corp)
    missing = sorted(set(codes) - set(mapping))
    if missing:
        print(f"corp_code 매핑 실패 {len(missing)}개 (공시·배당 없음으로 처리): {missing}")

    years = range(start.year, end.year + 1)
    for corp_code in mapping.values():
        client.disclosures(corp_code, f"{start:%Y%m%d}", f"{end:%Y%m%d}")
        client.annual_dividends(corp_code, years)
    pd.Series(mapping, name="corp_code").rename_axis("code").to_frame().to_parquet(
        DATA_DIR / "dart" / "code_map.parquet"
    )
    print(f"DART 종목 {len(mapping)}개, 호출 {client.calls}회")


def main() -> None:
    load_dotenv(RESEARCH_DIR / ".env")
    stages = {"krx": fetch_krx, "panel": build_panel, "dart": fetch_dart, "bench": fetch_bench}
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=list(stages))
    stages[parser.parse_args().stage]()


def fetch_bench() -> None:
    start, end = _range()
    df = load_kodex200(f"{start}", f"{end}")
    print(f"KODEX 200 {len(df)}일 ({df.index.min():%Y-%m-%d} ~ {df.index.max():%Y-%m-%d})")


if __name__ == "__main__":
    main()
