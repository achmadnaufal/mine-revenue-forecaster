"""
Unit tests for Monte Carlo revenue simulation.
"""
import pytest
from src.main import MineRevenueForecaster


@pytest.fixture
def forecaster():
    return MineRevenueForecaster(
        royalty_rate=0.13,
        mining_cost_usd_t=35.0,
        transport_usd_t=15.0,
    )


class TestMonteCarloSimulation:

    def test_basic_simulation_runs(self, forecaster):
        result = forecaster.monte_carlo_revenue_simulation(
            production_mt=500_000,
            base_price_usd_t=90.0,
        )
        assert "mean_revenue_usd" in result
        assert "p90_revenue_usd" in result
        assert result["n_simulations"] == 1000

    def test_p10_less_than_p90(self, forecaster):
        """P10 should always be less than P90."""
        result = forecaster.monte_carlo_revenue_simulation(
            production_mt=500_000, base_price_usd_t=90.0
        )
        assert result["p10_revenue_usd"] < result["p90_revenue_usd"]

    def test_high_price_mostly_profitable(self, forecaster):
        """Very high price → nearly 100% profitable."""
        result = forecaster.monte_carlo_revenue_simulation(
            production_mt=500_000, base_price_usd_t=200.0, price_volatility_pct=5.0
        )
        assert result["prob_profitable_pct"] > 95.0

    def test_low_price_mostly_unprofitable(self, forecaster):
        """Price well below cost → mostly unprofitable."""
        result = forecaster.monte_carlo_revenue_simulation(
            production_mt=500_000, base_price_usd_t=20.0, price_volatility_pct=5.0
        )
        assert result["prob_profitable_pct"] < 5.0

    def test_invalid_production_raises(self, forecaster):
        with pytest.raises(ValueError, match="production_mt must be positive"):
            forecaster.monte_carlo_revenue_simulation(
                production_mt=0, base_price_usd_t=90.0
            )

    def test_invalid_price_raises(self, forecaster):
        with pytest.raises(ValueError, match="base_price_usd_t must be positive"):
            forecaster.monte_carlo_revenue_simulation(
                production_mt=500_000, base_price_usd_t=-10.0
            )

    def test_reproducible_with_seed(self, forecaster):
        """Same seed → same result."""
        r1 = forecaster.monte_carlo_revenue_simulation(
            production_mt=500_000, base_price_usd_t=90.0, seed=99
        )
        r2 = forecaster.monte_carlo_revenue_simulation(
            production_mt=500_000, base_price_usd_t=90.0, seed=99
        )
        assert r1["mean_revenue_usd"] == r2["mean_revenue_usd"]

    def test_break_even_price_positive(self, forecaster):
        result = forecaster.monte_carlo_revenue_simulation(
            production_mt=500_000, base_price_usd_t=90.0
        )
        assert result["break_even_price_usd_t"] > 0
