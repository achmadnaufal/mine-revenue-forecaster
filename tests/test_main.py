"""Unit tests for RevenueForecaster."""
import pytest
import pandas as pd
import sys
sys.path.insert(0, "/Users/johndoe/projects/mine-revenue-forecaster")
from src.main import RevenueForecaster


@pytest.fixture
def prod_df():
    return pd.DataFrame({
        "month": ["2026-01", "2026-02", "2026-03", "2026-04"],
        "volume_mt": [120000, 135000, 128000, 142000],
        "calorific_value": [6000, 5950, 6050, 6000],
    })


@pytest.fixture
def fc():
    return RevenueForecaster(config={"royalty_rate": 0.13, "transport_usd_t": 8.0, "mining_cost_usd_t": 22.0})


class TestValidation:
    def test_empty_df_raises(self, fc):
        with pytest.raises(ValueError, match="empty"):
            fc.validate(pd.DataFrame())

    def test_negative_volume_raises(self, fc):
        df = pd.DataFrame({"volume_mt": [-100, 200]})
        with pytest.raises(ValueError, match="negative"):
            fc.validate(df)

    def test_valid_data_passes(self, fc, prod_df):
        assert fc.validate(prod_df) is True


class TestForecastRevenue:
    def test_required_keys_present(self, fc, prod_df):
        result = fc.forecast_revenue(prod_df, price_usd_t=85.0)
        assert "gross_revenue_usd" in result
        assert "net_revenue_usd" in result
        assert "ebitda_margin_pct" in result
        assert "break_even_price_usd_t" in result

    def test_revenue_calculation_correct(self, fc, prod_df):
        total_vol = prod_df["volume_mt"].sum()
        price = 85.0
        expected_gross = total_vol * price
        result = fc.forecast_revenue(prod_df, price_usd_t=price)
        assert abs(result["gross_revenue_usd"] - expected_gross) < 0.01

    def test_net_revenue_less_than_gross(self, fc, prod_df):
        result = fc.forecast_revenue(prod_df, price_usd_t=85.0)
        assert result["net_revenue_usd"] < result["gross_revenue_usd"]

    def test_zero_price_raises(self, fc, prod_df):
        with pytest.raises(ValueError):
            fc.forecast_revenue(prod_df, price_usd_t=0)

    def test_negative_price_raises(self, fc, prod_df):
        with pytest.raises(ValueError):
            fc.forecast_revenue(prod_df, price_usd_t=-10)

    def test_missing_volume_col_raises(self, fc):
        df = pd.DataFrame({"month": ["2026-01"], "price_usd_t": [80]})
        with pytest.raises(ValueError, match="volume_mt"):
            fc.forecast_revenue(df, price_usd_t=80)

    def test_break_even_below_market_price(self, fc, prod_df):
        result = fc.forecast_revenue(prod_df, price_usd_t=85.0)
        assert result["break_even_price_usd_t"] < 85.0

    def test_price_from_column(self, fc):
        df = pd.DataFrame({"volume_mt": [100000, 120000], "price_usd_t": [80.0, 80.0]})
        result = fc.forecast_revenue(df)
        assert result["price_used_usd_t"] == 80.0


class TestPriceSensitivity:
    def test_returns_dataframe(self, fc, prod_df):
        result = fc.price_sensitivity(prod_df)
        assert isinstance(result, pd.DataFrame)

    def test_correct_number_of_scenarios(self, fc, prod_df):
        prices = [60, 80, 100]
        result = fc.price_sensitivity(prod_df, price_range=prices)
        assert len(result) == 3

    def test_higher_price_higher_revenue(self, fc, prod_df):
        result = fc.price_sensitivity(prod_df, price_range=[70, 100])
        rev_70 = result[result["price_usd_t"] == 70]["net_revenue_usd"].values[0]
        rev_100 = result[result["price_usd_t"] == 100]["net_revenue_usd"].values[0]
        assert rev_100 > rev_70
