"""KIS client 단위 테스트."""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.infrastructure import kis_client

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _make_response(status_code: int, json_body: dict | None = None) -> httpx.Response:
    """httpx.Response mock 생성."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_body or {}
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            f"HTTP {status_code}",
            request=MagicMock(),
            response=resp,
        )
    else:
        resp.raise_for_status.return_value = None
    return resp


def _ok_balance_response(items: list[dict] | None = None) -> httpx.Response:
    return _make_response(
        200,
        {
            "rt_cd": "0",
            "msg_cd": "70070000",
            "msg1": "정상처리 되었습니다.",
            "output1": items or [],
            "output2": {},
        },
    )


# ---------------------------------------------------------------------------
# _get_overseas_positions 재시도 테스트
# ---------------------------------------------------------------------------


class TestGetOverseasPositionsRetry:
    """500 오류 시 재시도 로직 검증."""

    @patch("app.infrastructure.kis_client.time.sleep")
    @patch("app.infrastructure.kis_client._headers", return_value={})
    @patch("app.infrastructure.kis_client._base_url", return_value="https://mock")
    @patch("app.infrastructure.kis_client.get_settings")
    @patch("httpx.get")
    def test_succeeds_on_first_attempt(
        self, mock_get, mock_settings, mock_url, mock_headers, mock_sleep
    ):
        """첫 시도에 성공하면 sleep 없이 결과 반환."""
        mock_settings.return_value = MagicMock(kis_account_no="50181833", kis_paper=True)
        mock_get.return_value = _ok_balance_response()

        result = kis_client._get_overseas_positions()

        assert result == []
        mock_get.assert_called_once()
        mock_sleep.assert_not_called()

    @patch("app.infrastructure.kis_client.time.sleep")
    @patch("app.infrastructure.kis_client._headers", return_value={})
    @patch("app.infrastructure.kis_client._base_url", return_value="https://mock")
    @patch("app.infrastructure.kis_client.get_settings")
    @patch("httpx.get")
    def test_retries_on_500_then_succeeds(
        self, mock_get, mock_settings, mock_url, mock_headers, mock_sleep
    ):
        """500 → 500 → 200 순서로 응답 시 3번째에 성공."""
        mock_settings.return_value = MagicMock(kis_account_no="50181833", kis_paper=True)
        mock_get.side_effect = [
            _make_response(500),
            _make_response(500),
            _ok_balance_response(),
        ]

        result = kis_client._get_overseas_positions()

        assert result == []
        assert mock_get.call_count == 3
        # 1초, 2초 대기
        assert mock_sleep.call_count == 2
        mock_sleep.assert_any_call(1)
        mock_sleep.assert_any_call(2)

    @patch("app.infrastructure.kis_client.time.sleep")
    @patch("app.infrastructure.kis_client._headers", return_value={})
    @patch("app.infrastructure.kis_client._base_url", return_value="https://mock")
    @patch("app.infrastructure.kis_client.get_settings")
    @patch("httpx.get")
    def test_raises_after_three_500s(
        self, mock_get, mock_settings, mock_url, mock_headers, mock_sleep
    ):
        """3회 모두 500이면 예외 전파."""
        mock_settings.return_value = MagicMock(kis_account_no="50181833", kis_paper=True)
        mock_get.return_value = _make_response(500)

        with pytest.raises(RuntimeError, match="HTTP 500"):
            kis_client._get_overseas_positions()

        assert mock_get.call_count == 3

    @patch("app.infrastructure.kis_client.time.sleep")
    @patch("app.infrastructure.kis_client._headers", return_value={})
    @patch("app.infrastructure.kis_client._base_url", return_value="https://mock")
    @patch("app.infrastructure.kis_client.get_settings")
    @patch("httpx.get")
    def test_does_not_retry_on_4xx(
        self, mock_get, mock_settings, mock_url, mock_headers, mock_sleep
    ):
        """4xx 오류는 재시도하지 않고 즉시 예외 전파."""
        mock_settings.return_value = MagicMock(kis_account_no="50181833", kis_paper=True)
        mock_get.return_value = _make_response(401)

        with pytest.raises(httpx.HTTPStatusError):
            kis_client._get_overseas_positions()

        mock_get.assert_called_once()
        mock_sleep.assert_not_called()

    @patch("app.infrastructure.kis_client.time.sleep")
    @patch("app.infrastructure.kis_client._headers", return_value={})
    @patch("app.infrastructure.kis_client._base_url", return_value="https://mock")
    @patch("app.infrastructure.kis_client.get_settings")
    @patch("httpx.get")
    def test_parses_positions_correctly(
        self, mock_get, mock_settings, mock_url, mock_headers, mock_sleep
    ):
        """output1 파싱이 올바르게 이루어지는지 확인."""
        mock_settings.return_value = MagicMock(kis_account_no="50181833", kis_paper=True)
        mock_get.return_value = _ok_balance_response(
            items=[
                {
                    "ovrs_pdno": "AAPL",
                    "ovrs_cblc_qty": "10",
                    "pchs_avg_pric": "150.00",
                    "now_pric2": "175.00",
                    "ovrs_stck_evlu_amt": "1750.00",
                    "frcr_evlu_pfls_amt": "250.00",
                    "evlu_pfls_rt": "16.67",
                },
                {
                    "ovrs_pdno": "TSLA",
                    "ovrs_cblc_qty": "0",  # 보유 수량 0 → 제외
                    "pchs_avg_pric": "200.00",
                    "now_pric2": "190.00",
                    "ovrs_stck_evlu_amt": "0",
                    "frcr_evlu_pfls_amt": "-10.00",
                    "evlu_pfls_rt": "-5.00",
                },
            ]
        )

        result = kis_client._get_overseas_positions()

        assert len(result) == 1
        pos = result[0]
        assert pos["ticker"] == "AAPL"
        assert pos["qty"] == 10.0
        assert pos["avg_entry_price"] == 150.0
        assert pos["current_price"] == 175.0
        assert pos["market"] == "US"
        assert pos["currency"] == "USD"
