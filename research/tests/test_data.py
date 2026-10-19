"""KRX·DART 수집기와 수정주가·유니버스 계산 테스트 (네트워크 없음)."""

from datetime import date

import httpx
import pandas as pd
import pytest

from research.data.dart import map_corp_codes, parse_common_dps
from research.data.index import normalize_index_rows
from research.data.krx import KOSPI_STOCKS, KrxClient, KrxError, to_number
from research.data.prices import add_adjustment, adjusted_window, normalize_stock_rows
from research.universe import build_universe, members_on, quarter_end_dates


def _krx_row(day: str, code: str, close: str, change: str, **kw) -> dict:
    row = {
        "BAS_DD": day,
        "ISU_CD": code,
        "ISU_NM": kw.get("name", f"종목{code}"),
        "TDD_OPNPRC": kw.get("open", close),
        "TDD_HGPRC": kw.get("high", close),
        "TDD_LWPRC": kw.get("low", close),
        "TDD_CLSPRC": close,
        "CMPPREVDD_PRC": change,
        "ACC_TRDVOL": kw.get("volume", "1000"),
        "MKTCAP": kw.get("mktcap", "1000000"),
        "LIST_SHRS": kw.get("shares", "100"),
    }
    return row


class TestToNumber:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [("1,234", 1234.0), ("-500", -500.0), ("", None), ("-", None), (None, None)],
    )
    def test_parses_krx_strings(self, raw, expected):
        assert to_number(raw) == expected


class TestKrxClient:
    def _client(self, tmp_path, handler) -> KrxClient:
        http = httpx.Client(
            base_url="https://example.test/", transport=httpx.MockTransport(handler)
        )
        return KrxClient("key", cache_dir=tmp_path, http=http)

    def test_sends_auth_header_and_caches(self, tmp_path):
        seen = []

        def handler(request: httpx.Request) -> httpx.Response:
            seen.append(request)
            return httpx.Response(
                200, json={"OutBlock_1": [_krx_row("20200102", "005930", "1", "0")]}
            )

        client = self._client(tmp_path, handler)
        first = client.fetch_day(KOSPI_STOCKS, date(2020, 1, 2))
        second = client.fetch_day(KOSPI_STOCKS, date(2020, 1, 2))
        assert len(seen) == 1
        assert seen[0].headers["AUTH_KEY"] == "key"
        assert seen[0].url.params["basDd"] == "20200102"
        pd.testing.assert_frame_equal(first, second)

    def test_unauthorized_explains_service_approval(self, tmp_path):
        client = self._client(tmp_path, lambda r: httpx.Response(401))
        with pytest.raises(KrxError, match="이용신청"):
            client.fetch_day(KOSPI_STOCKS, date(2020, 1, 2))

    def test_old_empty_day_is_cached_as_holiday(self, tmp_path):
        calls = []

        def handler(request: httpx.Request) -> httpx.Response:
            calls.append(request)
            return httpx.Response(200, json={"OutBlock_1": []})

        client = self._client(tmp_path, handler)
        client.fetch_day(KOSPI_STOCKS, date(2020, 1, 1))
        client.fetch_day(KOSPI_STOCKS, date(2020, 1, 1))
        assert len(calls) == 1

    def test_call_limit_stops_fetching(self, tmp_path):
        http = httpx.Client(
            base_url="https://example.test/",
            transport=httpx.MockTransport(lambda r: httpx.Response(200, json={})),
        )
        client = KrxClient("key", cache_dir=tmp_path, http=http, call_limit=0)
        with pytest.raises(KrxError, match="한도"):
            client.fetch_day(KOSPI_STOCKS, date(2020, 1, 2))


class TestAdjustment:
    def _panel(self) -> pd.DataFrame:
        # 4일차에 50:1 액면분할 — 기준가 = 2,600,000/50 = 52,000
        rows = [
            _krx_row("20180502", "005930", "2,500,000", "0"),
            _krx_row("20180503", "005930", "2,600,000", "100,000"),
            _krx_row("20180504", "005930", "51,900", "-100"),
            _krx_row("20180508", "005930", "52,900", "1,000"),
        ]
        return add_adjustment(normalize_stock_rows(pd.DataFrame(rows)))

    def test_detects_split_factor(self):
        panel = self._panel()
        assert panel["factor"].tolist() == pytest.approx([1.0, 1.0, 0.02, 1.0])

    def test_adj_ratio_excludes_same_day_event(self):
        assert self._panel()["adj_ratio"].tolist() == pytest.approx([0.02, 0.02, 1.0, 1.0])

    def test_adjusted_window_keeps_decision_day_price(self):
        panel = self._panel()
        before_split = adjusted_window(panel.iloc[:2])
        assert before_split["close"].tolist() == pytest.approx([2_500_000, 2_600_000])
        after_split = adjusted_window(panel)
        assert after_split["close"].tolist() == pytest.approx([50_000, 52_000, 51_900, 52_900])
        assert after_split["volume"].iloc[0] == pytest.approx(1000 / 0.02)

    def test_small_rounding_is_not_an_event(self):
        rows = [
            _krx_row("20200102", "000001", "10,000", "0"),
            _krx_row("20200103", "000001", "10,100", "105"),  # 기준가 9,995 → 0.05% 차이
        ]
        panel = add_adjustment(normalize_stock_rows(pd.DataFrame(rows)))
        assert panel["factor"].tolist() == [1.0, 1.0]

    def test_no_trade_price_becomes_missing(self):
        rows = [_krx_row("20200102", "000001", "", "0", open="0")]
        panel = normalize_stock_rows(pd.DataFrame(rows))
        assert panel["close"].isna().all()
        assert panel["open"].isna().all()

    def test_standard_code_is_shortened(self):
        rows = [_krx_row("20200102", "KR7005930003", "100", "0")]
        assert normalize_stock_rows(pd.DataFrame(rows))["code"].iloc[0] == "005930"


class TestUniverse:
    def _panel(self) -> pd.DataFrame:
        days = pd.bdate_range("2020-01-01", "2020-07-10")
        rows = []
        for i, day in enumerate(days):
            bas = f"{day:%Y%m%d}"
            rows += [
                _krx_row(bas, "000010", "100", "0", mktcap="300"),
                _krx_row(bas, "000020", "100", "0", mktcap="200"),
                _krx_row(bas, "000025", "100", "0", mktcap="900"),  # 우선주
                _krx_row(bas, "000030", "100", "0", mktcap="999", name="하나스팩"),
            ]
            if i >= 100:  # 늦게 상장해 이력 부족
                rows.append(_krx_row(bas, "000040", "100", "0", mktcap="5000"))
        return add_adjustment(normalize_stock_rows(pd.DataFrame(rows)))

    def test_quarter_end_dates(self):
        days = pd.bdate_range("2020-01-01", "2020-07-10")
        assert [d.strftime("%m-%d") for d in quarter_end_dates(days)] == [
            "03-31",
            "06-30",
            "07-10",
        ]

    def test_top_n_excludes_preferred_spac_and_short_history(self):
        cfg = {
            "top_n_by_market_cap": 1,
            "min_history_bars": 60,
            "exclude": {"preferred_shares": True, "name_contains": ["스팩"]},
        }
        universe = build_universe(self._panel(), cfg)
        first = universe[universe["rebalance_date"] == "2020-03-31"]
        assert first["code"].tolist() == ["000010"]

    def test_members_apply_from_next_day(self):
        cfg = {"top_n_by_market_cap": 2, "min_history_bars": 1, "exclude": {}}
        universe = build_universe(self._panel(), cfg)
        assert members_on(universe, pd.Timestamp("2020-03-31")).empty
        assert len(members_on(universe, pd.Timestamp("2020-04-01"))) == 2


def test_normalize_index_rows_picks_named_index():
    raw = pd.DataFrame(
        [
            {"BAS_DD": "20200103", "IDX_NM": "코스피 200", "CLSPRC_IDX": "290.5"},
            {"BAS_DD": "20200102", "IDX_NM": "코스피 200", "CLSPRC_IDX": "289.1"},
            {"BAS_DD": "20200102", "IDX_NM": "코스피", "CLSPRC_IDX": "2,175.5"},
        ]
    )
    series = normalize_index_rows(raw, "코스피 200")
    assert series.tolist() == [289.1, 290.5]


def test_parse_common_dps():
    rows = [
        {"se": "주당액면가액(원)", "thstrm": "100"},
        {"se": "주당 현금배당금(원)", "stock_knd": "우선주", "thstrm": "1,417"},
        {"se": "주당 현금배당금(원)", "stock_knd": "보통주", "thstrm": "1,416", "frmtrm": "-"},
    ]
    assert parse_common_dps(rows, "thstrm") == 1416.0
    assert parse_common_dps(rows, "frmtrm") is None


def test_map_corp_codes_falls_back_to_unique_name():
    corp = pd.DataFrame(
        {
            "corp_code": ["001", "002", "003", "004"],
            "corp_name": ["삼성전자", "폐지회사", "중복", "중복"],
            "stock_code": ["005930", "", "", ""],
        }
    )
    stocks = pd.DataFrame(
        {"code": ["005930", "999990", "888880"], "name": ["x", "폐지회사", "중복"]}
    )
    assert map_corp_codes(stocks, corp) == {"005930": "001", "999990": "002"}
