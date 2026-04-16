"""TradingStrategy domain services."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from .value_objects import (
    EvaluationResult,
    MarketData,
    ValidationSeverity,
    ValidationWarning,
)

_KST = ZoneInfo("Asia/Seoul")


class StrategyValidator:
    """Validates strategy parameter consistency — no I/O."""

    def validate(
        self,
        strategy_type: str,
        entry_price_drop_pct: float | None,
        entry_rsi_below: float | None,
        take_profit_pct: float | None,
        stop_loss_pct: float | None,
        sell_ratio: float | None,
        dca_amount: float | None,
        dca_frequency_days: int | None,
        max_position: float | None,
        entry_bb_lower_touch: bool | None = None,
        entry_macd_hist_positive: bool | None = None,
        entry_disparity_below: float | None = None,
        entry_volume_surge: float | None = None,
        entry_sma_cross: int | None = None,
    ) -> list[ValidationWarning]:
        """Validate strategy params for range/conflict issues.

        Returns:
            List of ValidationWarning objects (empty = no issues).
        """
        warnings: list[ValidationWarning] = []

        if entry_price_drop_pct is not None and entry_price_drop_pct > 0:
            warnings.append(
                ValidationWarning(
                    message=(
                        f"entry_price_drop_pct={entry_price_drop_pct}이 양수입니다. "
                        "하락 진입 조건은 음수여야 합니다 (예: -5.0)."
                    )
                )
            )

        if entry_rsi_below is not None and not (0 < entry_rsi_below < 100):
            warnings.append(
                ValidationWarning(
                    message=(f"entry_rsi_below={entry_rsi_below}이 유효 범위(0~100)를 벗어납니다.")
                )
            )

        if (
            take_profit_pct is not None
            and stop_loss_pct is not None
            and stop_loss_pct >= take_profit_pct
        ):
            warnings.append(
                ValidationWarning(
                    message=(
                        f"stop_loss_pct({stop_loss_pct}) ≥ take_profit_pct({take_profit_pct}): "
                        "손절가가 익절가보다 크거나 같습니다. 두 조건이 동시에 발동될 수 있습니다."
                    ),
                    severity=ValidationSeverity.ERROR,
                )
            )

        if (
            entry_price_drop_pct is not None
            and take_profit_pct is not None
            and stop_loss_pct is not None
            and abs(stop_loss_pct) < abs(entry_price_drop_pct)
        ):
            warnings.append(
                ValidationWarning(
                    message=(
                        f"stop_loss_pct({stop_loss_pct})의 절대값이 "
                        f"entry_price_drop_pct({entry_price_drop_pct})보다 작습니다. "
                        "진입 조건이 충족되자마자 손절이 발동될 수 있습니다."
                    )
                )
            )

        if sell_ratio is not None and not (0 < sell_ratio <= 1):
            warnings.append(
                ValidationWarning(
                    message=(f"sell_ratio={sell_ratio}이 유효 범위(0 초과 ~ 1 이하)를 벗어납니다."),
                    severity=ValidationSeverity.ERROR,
                )
            )

        if dca_frequency_days is not None and dca_frequency_days <= 0:
            warnings.append(
                ValidationWarning(
                    message=f"dca_frequency_days={dca_frequency_days}는 양수여야 합니다.",
                    severity=ValidationSeverity.ERROR,
                )
            )

        if dca_amount is not None and max_position is not None and dca_amount > max_position:
            warnings.append(
                ValidationWarning(
                    message=(
                        f"dca_amount({dca_amount}) > max_position({max_position}): "
                        "첫 번째 DCA 매수만으로 포지션 한도를 초과합니다."
                    ),
                    severity=ValidationSeverity.ERROR,
                )
            )

        if strategy_type == "dca" and dca_amount is None:
            warnings.append(
                ValidationWarning(
                    message="DCA 전략인데 dca_amount가 설정되지 않았습니다.",
                    severity=ValidationSeverity.ERROR,
                )
            )

        if strategy_type == "dca" and dca_frequency_days is None:
            warnings.append(
                ValidationWarning(
                    message="DCA 전략인데 dca_frequency_days가 설정되지 않았습니다.",
                    severity=ValidationSeverity.ERROR,
                )
            )

        if entry_disparity_below is not None and entry_disparity_below > 0:
            warnings.append(
                ValidationWarning(
                    message=(
                        f"entry_disparity_below={entry_disparity_below}이 양수입니다. "
                        "이격도 과매도 조건은 음수여야 합니다 (예: -5.0)."
                    )
                )
            )

        if entry_volume_surge is not None and entry_volume_surge <= 1.0:
            warnings.append(
                ValidationWarning(
                    message=(
                        f"entry_volume_surge={entry_volume_surge}이 1.0 이하입니다. "
                        "거래량 급등 조건은 1.0 초과여야 합니다 (예: 2.0 = 평균의 2배)."
                    )
                )
            )

        if entry_sma_cross is not None and entry_sma_cross not in (20, 60):
            warnings.append(
                ValidationWarning(
                    message=(
                        f"entry_sma_cross={entry_sma_cross}은 지원하지 않는 기간입니다. "
                        "20 또는 60을 사용하세요."
                    ),
                    severity=ValidationSeverity.ERROR,
                )
            )

        all_entry_conditions = [
            entry_price_drop_pct,
            entry_rsi_below,
            entry_bb_lower_touch,
            entry_macd_hist_positive,
            entry_disparity_below,
            entry_volume_surge,
            entry_sma_cross,
        ]
        if strategy_type != "dca" and all(c is None for c in all_entry_conditions):
            warnings.append(
                ValidationWarning(
                    message=(
                        "진입 조건이 하나도 설정되지 않았습니다. "
                        "최소 하나의 entry 조건을 설정하세요."
                    ),
                    severity=ValidationSeverity.ERROR,
                )
            )

        return warnings


class StrategyEvaluator:
    """Evaluates strategy entry/exit conditions — no I/O.

    Caller (tools.py) fetches market data and injects it via MarketData.
    """

    def evaluate(
        self,
        strategy: dict,
        market_data: MarketData,
        current_holding: dict | None,
    ) -> EvaluationResult:
        """Evaluate entry/exit conditions against injected market data.

        Args:
            strategy: strategy dict from DB (id, ticker, entry_price_drop_pct, etc.)
            market_data: pre-fetched market data (current_price, high_30d, rsi_14)
            current_holding: holding dict from DB, or None if not held

        Returns:
            EvaluationResult with entry_triggered, exit_triggered, and per-condition details.
        """
        current_price = market_data.current_price
        entry_triggered = False
        exit_triggered = False
        conditions: dict = {}

        # entry_price_drop_pct: 30일 고점 대비 하락률
        if strategy.get("entry_price_drop_pct") is not None and market_data.high_30d is not None:
            high_30d = market_data.high_30d
            drop_pct = (current_price - high_30d) / high_30d * 100
            threshold = strategy["entry_price_drop_pct"]
            triggered = drop_pct <= threshold
            conditions["entry_price_drop"] = {
                "reference_30d_high": round(high_30d, 4),
                "current_drop_pct": round(drop_pct, 2),
                "threshold_pct": threshold,
                "triggered": triggered,
            }
            if triggered:
                entry_triggered = True

        # entry_rsi_below: 14일 RSI
        if strategy.get("entry_rsi_below") is not None and market_data.rsi_14 is not None:
            rsi = market_data.rsi_14
            threshold = strategy["entry_rsi_below"]
            triggered = rsi <= threshold
            conditions["entry_rsi"] = {
                "current_rsi": round(rsi, 1),
                "threshold": threshold,
                "triggered": triggered,
            }
            if triggered:
                entry_triggered = True

        # take_profit_pct / stop_loss_pct: 보유 평균단가 기준
        holding_avg_price: float | None = None
        current_pnl_pct: float | None = None
        note: str | None = None

        if current_holding:
            avg_price = current_holding["avg_price"]
            pnl_pct = (current_price - avg_price) / avg_price * 100
            holding_avg_price = avg_price
            current_pnl_pct = round(pnl_pct, 2)

            if strategy.get("take_profit_pct") is not None:
                tp = strategy["take_profit_pct"]
                triggered = pnl_pct >= tp
                conditions["take_profit"] = {
                    "current_pnl_pct": round(pnl_pct, 2),
                    "threshold_pct": tp,
                    "triggered": triggered,
                }
                if triggered:
                    exit_triggered = True

            if strategy.get("stop_loss_pct") is not None:
                sl = strategy["stop_loss_pct"]
                triggered = pnl_pct <= sl
                conditions["stop_loss"] = {
                    "current_pnl_pct": round(pnl_pct, 2),
                    "threshold_pct": sl,
                    "triggered": triggered,
                }
                if triggered:
                    exit_triggered = True
        else:
            holding_avg_price = None
            note = "No holding found; take_profit/stop_loss not evaluated"

        # entry_bb_lower_touch: 볼린저 하단 이탈
        if strategy.get("entry_bb_lower_touch") and market_data.bb_lower is not None:
            triggered = current_price <= market_data.bb_lower
            conditions["entry_bb_lower_touch"] = {
                "current_price": round(current_price, 4),
                "bb_lower": round(market_data.bb_lower, 4),
                "triggered": triggered,
            }
            if triggered:
                entry_triggered = True

        # entry_macd_hist_positive: MACD 히스토그램 양전환
        if strategy.get("entry_macd_hist_positive") and market_data.macd_hist is not None:
            triggered = market_data.macd_hist > 0
            conditions["entry_macd_hist_positive"] = {
                "macd_hist": round(market_data.macd_hist, 6),
                "triggered": triggered,
            }
            if triggered:
                entry_triggered = True

        # entry_disparity_below: 이격도 임계값 이하
        if (
            strategy.get("entry_disparity_below") is not None
            and market_data.disparity_20 is not None
        ):
            threshold = strategy["entry_disparity_below"]
            triggered = market_data.disparity_20 <= threshold
            conditions["entry_disparity_below"] = {
                "current_disparity_pct": round(market_data.disparity_20, 2),
                "threshold_pct": threshold,
                "triggered": triggered,
            }
            if triggered:
                entry_triggered = True

        # entry_volume_surge: 거래량 비율 임계값 초과
        if (
            strategy.get("entry_volume_surge") is not None
            and market_data.volume_ratio_20 is not None
        ):
            threshold = strategy["entry_volume_surge"]
            triggered = market_data.volume_ratio_20 >= threshold
            conditions["entry_volume_surge"] = {
                "current_volume_ratio": round(market_data.volume_ratio_20, 2),
                "threshold": threshold,
                "triggered": triggered,
            }
            if triggered:
                entry_triggered = True

        # entry_sma_cross: 현재가가 SMA(N) 위 (골든크로스 간소화)
        if strategy.get("entry_sma_cross") is not None:
            period = strategy["entry_sma_cross"]
            sma_val = market_data.sma_20 if period == 20 else market_data.sma_60
            if sma_val is not None:
                triggered = current_price > sma_val
                conditions["entry_sma_cross"] = {
                    "current_price": round(current_price, 4),
                    f"sma_{period}": round(sma_val, 4),
                    "triggered": triggered,
                }
                if triggered:
                    entry_triggered = True

        # signal_score: 발동된 진입 조건 수 / 전체 활성 진입 조건 수
        entry_conds = [v for k, v in conditions.items() if k.startswith("entry_")]
        if entry_conds:
            triggered_count = sum(1 for c in entry_conds if c["triggered"])
            signal_score: float | None = triggered_count / len(entry_conds)
        else:
            signal_score = None

        # 보유 없이 exit_triggered가 발동되지 않도록 방어
        if current_holding is None:
            exit_triggered = False

        return EvaluationResult(
            ticker=market_data.ticker,
            current_price=round(current_price, 4),
            entry_triggered=entry_triggered,
            exit_triggered=exit_triggered,
            conditions=conditions,
            signal_score=round(signal_score, 4) if signal_score is not None else None,
            holding_avg_price=holding_avg_price,
            current_pnl_pct=current_pnl_pct,
            note=note,
        )


class DcaScheduleChecker:
    """Checks whether a DCA strategy is due for its next buy — no I/O."""

    def is_due(
        self,
        strategy: dict,
        now: datetime | None = None,
    ) -> dict:
        """Check if a DCA strategy is due for its next scheduled buy.

        Args:
            strategy: strategy dict from DB
            now: current time (defaults to KST now; injectable for testing)

        Returns:
            dict with is_due, reason, days_since_last, dca_frequency_days
        """
        freq = strategy.get("dca_frequency_days")
        if not freq:
            return {
                "is_due": False,
                "reason": "Not a DCA strategy (dca_frequency_days not set)",
            }

        last = strategy.get("last_triggered_at")
        if last is None:
            return {
                "is_due": True,
                "reason": "Never triggered before",
                "days_since_last": None,
                "dca_frequency_days": freq,
            }

        if isinstance(last, str):
            last = datetime.fromisoformat(last)

        if last.tzinfo is None:
            last = last.replace(tzinfo=_KST)

        if now is None:
            now = datetime.now(_KST)
        elif now.tzinfo is None:
            now = now.replace(tzinfo=_KST)

        days_since = (now - last).total_seconds() / 86400
        is_due = days_since >= freq
        reason = f"{days_since:.1f} days since last trigger (frequency: {freq} days)"

        return {
            "is_due": is_due,
            "reason": reason,
            "days_since_last": round(days_since, 2),
            "dca_frequency_days": freq,
        }
