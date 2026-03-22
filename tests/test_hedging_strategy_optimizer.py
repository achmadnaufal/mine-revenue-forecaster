"""
Unit tests for HedgingStrategyOptimizer.
"""

import pytest
from src.hedging_strategy_optimizer import (
    HedgingStrategyOptimizer,
    HedgeScenario,
    HedgeResult,
)


@pytest.fixture
def optimizer():
    return HedgingStrategyOptimizer()


@pytest.fixture
def falling_market_scenario():
    """Scenario where spot fell below forward; hedge was beneficial."""
    return HedgeScenario(
        scenario_name="50% Cover - Falling Market",
        production_mt=5.0,
        hedge_ratio=0.50,
        forward_price_usd_t=85.0,
        spot_price_usd_t=72.0,
        hedge_cost_usd_t=0.50,
        production_cost_usd_t=32.0,
    )


@pytest.fixture
def rising_market_scenario():
    """Scenario where spot rose above forward; unhedged would have been better."""
    return HedgeScenario(
        scenario_name="50% Cover - Rising Market",
        production_mt=5.0,
        hedge_ratio=0.50,
        forward_price_usd_t=85.0,
        spot_price_usd_t=100.0,
        hedge_cost_usd_t=0.50,
        production_cost_usd_t=32.0,
    )


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------

class TestInit:
    def test_default_cost_set(self):
        opt = HedgingStrategyOptimizer()
        assert opt._default_cost == 30.0

    def test_negative_cost_raises(self):
        with pytest.raises(ValueError):
            HedgingStrategyOptimizer(default_production_cost_usd_t=-5.0)


# ---------------------------------------------------------------------------
# evaluate — happy paths
# ---------------------------------------------------------------------------

class TestEvaluate:
    def test_returns_hedge_result(self, optimizer, falling_market_scenario):
        result = optimizer.evaluate(falling_market_scenario)
        assert isinstance(result, HedgeResult)

    def test_falling_market_hedge_gain_positive(self, optimizer, falling_market_scenario):
        result = optimizer.evaluate(falling_market_scenario)
        assert result.hedge_gain_loss_usd_m > 0

    def test_rising_market_hedge_gain_negative(self, optimizer, rising_market_scenario):
        result = optimizer.evaluate(rising_market_scenario)
        assert result.hedge_gain_loss_usd_m < 0

    def test_unhedged_equals_spot_only_revenue(self, optimizer):
        s = HedgeScenario(
            scenario_name="0% hedge",
            production_mt=4.0,
            hedge_ratio=0.0,
            forward_price_usd_t=90.0,
            spot_price_usd_t=80.0,
        )
        result = optimizer.evaluate(s)
        expected_unhedged = 4.0 * 80.0
        assert abs(result.unhedged_revenue_usd_m - expected_unhedged) < 0.01
        assert abs(result.blended_revenue_usd_m - expected_unhedged) < 0.01

    def test_fully_hedged_no_spot_exposure(self, optimizer):
        s = HedgeScenario(
            scenario_name="100% hedge",
            production_mt=3.0,
            hedge_ratio=1.0,
            forward_price_usd_t=88.0,
            spot_price_usd_t=60.0,  # large drop — doesn't matter when fully hedged
        )
        result = optimizer.evaluate(s)
        expected = 3.0 * 88.0
        assert abs(result.blended_revenue_usd_m - expected) < 0.01

    def test_ebit_positive_when_revenue_exceeds_cost(self, optimizer, falling_market_scenario):
        result = optimizer.evaluate(falling_market_scenario)
        assert result.ebit_usd_m > 0

    def test_ebit_margin_between_0_and_100(self, optimizer, falling_market_scenario):
        result = optimizer.evaluate(falling_market_scenario)
        assert 0 <= result.ebit_margin_pct <= 100

    def test_hedge_cost_reduces_net_revenue(self, optimizer):
        no_cost = HedgeScenario("no cost", 5.0, 0.5, 85.0, 80.0, hedge_cost_usd_t=0.0)
        with_cost = HedgeScenario("with cost", 5.0, 0.5, 85.0, 80.0, hedge_cost_usd_t=1.0)
        r_no = optimizer.evaluate(no_cost)
        r_with = optimizer.evaluate(with_cost)
        assert r_no.net_revenue_usd_m > r_with.net_revenue_usd_m


# ---------------------------------------------------------------------------
# evaluate — error handling
# ---------------------------------------------------------------------------

class TestEvaluateErrors:
    def test_zero_production_raises(self, optimizer):
        with pytest.raises(ValueError, match="production_mt"):
            optimizer.evaluate(HedgeScenario("X", 0.0, 0.5, 85.0, 80.0))

    def test_invalid_hedge_ratio_raises(self, optimizer):
        with pytest.raises(ValueError, match="hedge_ratio"):
            optimizer.evaluate(HedgeScenario("X", 5.0, 1.5, 85.0, 80.0))

    def test_negative_forward_price_raises(self, optimizer):
        with pytest.raises(ValueError, match="forward_price"):
            optimizer.evaluate(HedgeScenario("X", 5.0, 0.5, -10.0, 80.0))

    def test_negative_hedge_cost_raises(self, optimizer):
        with pytest.raises(ValueError, match="hedge_cost"):
            optimizer.evaluate(HedgeScenario("X", 5.0, 0.5, 85.0, 80.0, hedge_cost_usd_t=-1.0))


# ---------------------------------------------------------------------------
# compare_scenarios
# ---------------------------------------------------------------------------

class TestCompareScenarios:
    def test_returns_sorted_by_ebit(self, optimizer, falling_market_scenario, rising_market_scenario):
        results = optimizer.compare_scenarios([rising_market_scenario, falling_market_scenario])
        ebits = [r.ebit_usd_m for r in results]
        assert ebits == sorted(ebits, reverse=True)

    def test_empty_list_returns_empty(self, optimizer):
        assert optimizer.compare_scenarios([]) == []


# ---------------------------------------------------------------------------
# scan_hedge_ratios
# ---------------------------------------------------------------------------

class TestScanHedgeRatios:
    def test_returns_correct_number_of_steps(self, optimizer):
        results = optimizer.scan_hedge_ratios(
            production_mt=5.0, forward_price_usd_t=85.0, spot_price_usd_t=70.0,
            production_cost_usd_t=32.0, steps=11
        )
        assert len(results) == 11

    def test_falling_market_full_hedge_best_ebit(self, optimizer):
        results = optimizer.scan_hedge_ratios(
            production_mt=5.0, forward_price_usd_t=85.0, spot_price_usd_t=60.0,
            production_cost_usd_t=32.0
        )
        best = max(results, key=lambda r: r.ebit_usd_m)
        assert "100" in best.scenario_name  # 100% hedge wins when price drops sharply


# ---------------------------------------------------------------------------
# breakeven_spot_price
# ---------------------------------------------------------------------------

class TestBreakevenSpotPrice:
    def test_breakeven_below_forward_when_hedging_costs_exist(self, optimizer):
        be = optimizer.breakeven_spot_price(85.0, 0.5, 32.0, hedge_cost_usd_t=1.0)
        assert be < 85.0

    def test_zero_hedge_cost_breakeven_equals_forward(self, optimizer):
        be = optimizer.breakeven_spot_price(85.0, 0.5, 32.0, hedge_cost_usd_t=0.0)
        assert be == 85.0


# ---------------------------------------------------------------------------
# hedge_value_at_risk
# ---------------------------------------------------------------------------

class TestHedgeVaR:
    def test_hedging_reduces_var(self, optimizer):
        result = optimizer.hedge_value_at_risk(
            production_mt=5.0, hedge_ratio=0.5,
            forward_price_usd_t=85.0, spot_price_mean_usd_t=80.0,
            spot_price_std_usd_t=10.0, confidence_level=0.95
        )
        assert result["hedged_var_usd_m"] < result["unhedged_var_usd_m"]
        assert result["var_reduction_pct"] > 0

    def test_full_hedge_eliminates_var(self, optimizer):
        result = optimizer.hedge_value_at_risk(
            production_mt=5.0, hedge_ratio=1.0,
            forward_price_usd_t=85.0, spot_price_mean_usd_t=80.0,
            spot_price_std_usd_t=10.0
        )
        assert result["hedged_var_usd_m"] == pytest.approx(0.0)
        assert result["var_reduction_pct"] == pytest.approx(100.0)

    def test_invalid_confidence_raises(self, optimizer):
        with pytest.raises(ValueError, match="confidence_level"):
            optimizer.hedge_value_at_risk(5.0, 0.5, 85.0, 80.0, 10.0, confidence_level=0.3)
