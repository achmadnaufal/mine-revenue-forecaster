"""Tests for mine revenue forecasting."""
import pytest
from forecast_engine import MineRevenueForecaster


class TestRevenueForecasting:
    """Test revenue forecasting methods."""
    
    def test_revenue_metrics(self):
        """Test revenue metric calculation."""
        production = [1000, 1200, 1100]
        price = 50  # per tonne
        cost = 30   # per tonne
        
        result = MineRevenueForecaster.calculate_revenue_metrics(
            production, price, cost
        )
        
        assert result['total_production_tonnes'] == 3300
        assert result['gross_revenue'] == 165000
        assert result['margin_percentage'] == 40.0
    
    def test_forecast_trend(self):
        """Test trend forecasting."""
        historical = [100, 120, 140, 160]
        forecast = MineRevenueForecaster.forecast_simple_trend(historical, periods_ahead=3)
        
        assert len(forecast) == 3
        assert all(v > 0 for v in forecast)
    
    def test_scenario_analysis(self):
        """Test scenario analysis."""
        result = MineRevenueForecaster.scenario_analysis(
            base_case_revenue=1000000,
            price_volatility_pct=20,
            production_variance_pct=15
        )
        
        assert result['base_case'] == 1000000
        assert result['bull_case'] > result['base_case']
        assert result['bear_case'] < result['base_case']
    
    def test_breakeven_production(self):
        """Test break-even calculation."""
        breakeven = MineRevenueForecaster.calculate_breakeven_production(
            fixed_costs=100000,
            variable_cost_per_tonne=25,
            price_per_tonne=50
        )
        
        assert breakeven == 4000.0
    
    def test_npv_calculation(self):
        """Test NPV calculation."""
        cash_flows = [-1000000, 200000, 250000, 300000, 350000]
        npv = MineRevenueForecaster.calculate_npv(cash_flows, discount_rate=0.10)
        
        assert isinstance(npv, float)
