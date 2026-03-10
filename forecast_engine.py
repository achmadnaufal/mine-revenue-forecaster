"""
Mining revenue forecasting engine.

Provides time series forecasting, scenario analysis, and revenue projections.
"""

from typing import Dict, List, Tuple, Optional
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


class MineRevenueForecaster:
    """Forecast mining revenue based on historical data and commodity prices."""
    
    @staticmethod
    def calculate_revenue_metrics(
        production_tonnes: List[float],
        price_per_tonne: float,
        operating_cost_per_tonne: float
    ) -> Dict:
        """
        Calculate revenue and margin metrics.
        
        Args:
            production_tonnes: List of production volumes
            price_per_tonne: Average price per tonne
            operating_cost_per_tonne: Operating cost per tonne
            
        Returns:
            Dictionary with revenue metrics
        """
        total_production = sum(production_tonnes)
        gross_revenue = total_production * price_per_tonne
        operating_costs = total_production * operating_cost_per_tonne
        net_revenue = gross_revenue - operating_costs
        
        margin_pct = (net_revenue / gross_revenue * 100) if gross_revenue > 0 else 0
        
        return {
            "total_production_tonnes": int(total_production),
            "gross_revenue": round(gross_revenue, 2),
            "operating_costs": round(operating_costs, 2),
            "net_revenue": round(net_revenue, 2),
            "margin_percentage": round(margin_pct, 2),
        }
    
    @staticmethod
    def forecast_simple_trend(
        historical_values: List[float],
        periods_ahead: int = 12
    ) -> List[float]:
        """
        Simple linear trend forecast.
        
        Args:
            historical_values: Historical data points
            periods_ahead: Number of periods to forecast
            
        Returns:
            List of forecasted values
        """
        if len(historical_values) < 2:
            return [historical_values[-1]] * periods_ahead
        
        x = np.arange(len(historical_values))
        y = np.array(historical_values)
        
        # Linear regression
        coeffs = np.polyfit(x, y, 1)
        poly = np.poly1d(coeffs)
        
        # Forecast
        future_x = np.arange(len(historical_values), len(historical_values) + periods_ahead)
        forecast = [max(poly(x), 0) for x in future_x]  # Ensure non-negative
        
        return [round(v, 2) for v in forecast]
    
    @staticmethod
    def scenario_analysis(
        base_case_revenue: float,
        price_volatility_pct: float = 20,
        production_variance_pct: float = 15
    ) -> Dict:
        """
        Perform scenario analysis with price and production variations.
        
        Args:
            base_case_revenue: Base case revenue projection
            price_volatility_pct: Price volatility assumption
            production_variance_pct: Production variance assumption
            
        Returns:
            Dictionary with bull, base, and bear scenarios
        """
        price_upside = base_case_revenue * (1 + price_volatility_pct / 100)
        price_downside = base_case_revenue * (1 - price_volatility_pct / 100)
        
        prod_upside = base_case_revenue * (1 + production_variance_pct / 100)
        prod_downside = base_case_revenue * (1 - production_variance_pct / 100)
        
        bull_case = (price_upside + prod_upside) / 2
        bear_case = (price_downside + prod_downside) / 2
        
        return {
            "bear_case": round(bear_case, 2),
            "base_case": round(base_case_revenue, 2),
            "bull_case": round(bull_case, 2),
            "upside_pct": round((bull_case - base_case_revenue) / base_case_revenue * 100, 2),
            "downside_pct": round((bear_case - base_case_revenue) / base_case_revenue * 100, 2),
        }
    
    @staticmethod
    def calculate_breakeven_production(
        fixed_costs: float,
        variable_cost_per_tonne: float,
        price_per_tonne: float
    ) -> float:
        """
        Calculate break-even production level.
        
        Args:
            fixed_costs: Total fixed costs
            variable_cost_per_tonne: Variable cost per unit
            price_per_tonne: Revenue per unit
            
        Returns:
            Break-even production in tonnes
        """
        if price_per_tonne <= variable_cost_per_tonne:
            return float('inf')
        
        contribution_margin = price_per_tonne - variable_cost_per_tonne
        breakeven = fixed_costs / contribution_margin
        
        return round(breakeven, 0)
    
    @staticmethod
    def calculate_npv(
        cash_flows: List[float],
        discount_rate: float = 0.10
    ) -> float:
        """
        Calculate Net Present Value of cash flows.
        
        Args:
            cash_flows: List of cash flows (initial investment, then annual flows)
            discount_rate: Annual discount rate (e.g., 0.10 for 10%)
            
        Returns:
            NPV value
        """
        npv = 0
        for i, cf in enumerate(cash_flows):
            npv += cf / ((1 + discount_rate) ** i)
        
        return round(npv, 2)
