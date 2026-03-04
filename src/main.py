"""
Revenue forecasting model for coal mining operations.

Provides coal mine revenue projection with price sensitivity, volume scenarios,
operating cost modeling, and break-even analysis.

Author: github.com/achmadnaufal
"""
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional, Dict, Any, List


class RevenueForecaster:
    """
    Coal mine revenue forecasting model.

    Calculates revenue projections, operating margins, and break-even
    analysis across price and volume scenarios.

    Args:
        config: Optional dict with keys:
            - royalty_rate: Government royalty as fraction of revenue (default 0.13)
            - transport_usd_t: Port/logistics cost per tonne (default 8.0)
            - mining_cost_usd_t: Cash mining cost per tonne (default 22.0)

    Example:
        >>> fc = RevenueForecaster(config={"royalty_rate": 0.13})
        >>> df = fc.load_data("data/production_plan.csv")
        >>> result = fc.forecast_revenue(df, price_usd_t=85.0)
        >>> print(result["annual_net_revenue_usd"])
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.royalty_rate = self.config.get("royalty_rate", 0.13)
        self.transport_usd_t = self.config.get("transport_usd_t", 8.0)
        self.mining_cost_usd_t = self.config.get("mining_cost_usd_t", 22.0)

    def load_data(self, filepath: str) -> pd.DataFrame:
        """
        Load production plan data from CSV or Excel.

        Args:
            filepath: Path to file. Expected columns: month, volume_mt,
                      calorific_value, price_usd_t (optional).

        Returns:
            DataFrame with production schedule.

        Raises:
            FileNotFoundError: If file does not exist.
        """
        p = Path(filepath)
        if not p.exists():
            raise FileNotFoundError(f"Data file not found: {filepath}")
        if p.suffix in (".xlsx", ".xls"):
            return pd.read_excel(filepath)
        return pd.read_csv(filepath)

    def validate(self, df: pd.DataFrame) -> bool:
        """
        Validate production plan data.

        Args:
            df: DataFrame to validate.

        Returns:
            True if valid.

        Raises:
            ValueError: If empty or volume is negative.
        """
        if df.empty:
            raise ValueError("Input DataFrame is empty")
        df_cols = [c.lower().strip().replace(" ", "_") for c in df.columns]
        if "volume_mt" in df_cols:
            df2 = df.copy()
            df2.columns = df_cols
            if (df2["volume_mt"] < 0).any():
                raise ValueError("volume_mt contains negative values")
        return True

    def preprocess(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardize column names and fill missing values."""
        df = df.copy()
        df.dropna(how="all", inplace=True)
        df.columns = [c.lower().strip().replace(" ", "_") for c in df.columns]
        num_cols = df.select_dtypes(include="number").columns
        for col in num_cols:
            if df[col].isnull().any():
                df[col].fillna(df[col].median(), inplace=True)
        return df

    def forecast_revenue(
        self,
        df: pd.DataFrame,
        price_usd_t: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Calculate revenue, cost, and margin for a production plan.

        Revenue = volume × price
        Royalty = revenue × royalty_rate
        Total cost = volume × (mining_cost + transport)
        Net revenue = revenue - royalty - total_cost

        Args:
            df: Production plan DataFrame with at minimum volume_mt.
            price_usd_t: Coal price in USD/tonne. Uses df column if None.

        Returns:
            Dict with:
                - total_volume_mt: Total production in metric tonnes
                - gross_revenue_usd: Revenue before deductions
                - royalty_usd: Government royalty
                - total_opex_usd: Operating cost (mining + transport)
                - net_revenue_usd: Net revenue after royalty and opex
                - ebitda_margin_pct: Net revenue / gross revenue %
                - price_used_usd_t: Price per tonne applied

        Raises:
            ValueError: If volume_mt column missing.
        """
        df = self.preprocess(df)
        if "volume_mt" not in df.columns:
            raise ValueError("Column 'volume_mt' required for revenue forecast")

        if price_usd_t is None:
            if "price_usd_t" in df.columns:
                price_usd_t = float(df["price_usd_t"].mean())
            else:
                raise ValueError("price_usd_t must be provided or present in data")

        if price_usd_t <= 0:
            raise ValueError(f"price_usd_t must be positive, got {price_usd_t}")

        total_volume = float(df["volume_mt"].sum())
        gross_revenue = total_volume * price_usd_t
        royalty = gross_revenue * self.royalty_rate
        opex = total_volume * (self.mining_cost_usd_t + self.transport_usd_t)
        net_revenue = gross_revenue - royalty - opex
        margin = (net_revenue / gross_revenue * 100) if gross_revenue > 0 else 0

        return {
            "total_volume_mt": round(total_volume, 1),
            "price_used_usd_t": round(price_usd_t, 2),
            "gross_revenue_usd": round(gross_revenue, 2),
            "royalty_usd": round(royalty, 2),
            "total_opex_usd": round(opex, 2),
            "net_revenue_usd": round(net_revenue, 2),
            "ebitda_margin_pct": round(margin, 2),
            "break_even_price_usd_t": round(
                (opex / total_volume) / (1 - self.royalty_rate), 2
            ) if total_volume > 0 else None,
        }

    def price_sensitivity(
        self,
        df: pd.DataFrame,
        price_range: Optional[List[float]] = None,
    ) -> pd.DataFrame:
        """
        Run revenue forecast across a range of coal prices.

        Args:
            df: Production plan DataFrame.
            price_range: List of prices to test. Defaults to [50, 60, 70, 80, 90, 100, 110, 120].

        Returns:
            DataFrame with revenue metrics per price scenario.
        """
        if price_range is None:
            price_range = [50, 60, 70, 80, 90, 100, 110, 120]

        rows = []
        for price in price_range:
            try:
                result = self.forecast_revenue(df, price_usd_t=float(price))
                rows.append({
                    "price_usd_t": price,
                    "gross_revenue_usd": result["gross_revenue_usd"],
                    "net_revenue_usd": result["net_revenue_usd"],
                    "ebitda_margin_pct": result["ebitda_margin_pct"],
                    "break_even_price_usd_t": result.get("break_even_price_usd_t"),
                    "profitable": result["net_revenue_usd"] > 0,
                })
            except Exception as e:
                rows.append({"price_usd_t": price, "error": str(e)})
        return pd.DataFrame(rows)

    def analyze(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Run descriptive analysis and return summary metrics."""
        df = self.preprocess(df)
        result = {
            "total_records": len(df),
            "columns": list(df.columns),
            "missing_pct": (df.isnull().sum() / len(df) * 100).round(1).to_dict(),
        }
        numeric_df = df.select_dtypes(include="number")
        if not numeric_df.empty:
            result["summary_stats"] = numeric_df.describe().round(3).to_dict()
            result["totals"] = numeric_df.sum().round(2).to_dict()
            result["means"] = numeric_df.mean().round(3).to_dict()
        return result

    def run(self, filepath: str) -> Dict[str, Any]:
        """Full pipeline: load → validate → analyze."""
        df = self.load_data(filepath)
        self.validate(df)
        return self.analyze(df)

    def to_dataframe(self, result: Dict) -> pd.DataFrame:
        """Convert result dict to flat DataFrame."""
        rows = []
        for k, v in result.items():
            if isinstance(v, dict):
                for kk, vv in v.items():
                    rows.append({"metric": f"{k}.{kk}", "value": vv})
            else:
                rows.append({"metric": k, "value": v})
        return pd.DataFrame(rows)
