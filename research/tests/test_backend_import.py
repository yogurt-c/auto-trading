"""research가 backend 도메인 코드를 설치된 패키지로 import할 수 있는지 확인."""

from app.domain.trading_strategy.services import StrategyEvaluator


def test_backend_domain_importable():
    assert StrategyEvaluator().evaluate is not None
