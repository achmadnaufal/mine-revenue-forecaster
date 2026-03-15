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


    def quarterly_projection(
        self,
        df: pd.DataFrame,
        price_usd_t: Optional[float] = None,
        quarters: int = 4,
    ) -> pd.DataFrame:
        """
        Project revenue across quarters based on production plan.

        Distributes total production evenly (or uses monthly data if available)
        and computes per-quarter revenue, opex, and net revenue.

        Args:
            df: Production plan DataFrame with volume_mt (and optionally 'month' column).
            price_usd_t: Coal price USD/tonne. Uses df column or raises if missing.
            quarters: Number of quarters to project (default 4).

        Returns:
            DataFrame with quarter, volume_mt, gross_revenue_usd,
            opex_usd, net_revenue_usd, ebitda_margin_pct.
        """
        df = self.preprocess(df)
        if "volume_mt" not in df.columns:
            raise ValueError("Column 'volume_mt' required")

        if price_usd_t is None:
            if "price_usd_t" in df.columns:
                price_usd_t = float(df["price_usd_t"].mean())
            else:
                raise ValueError("price_usd_t required")

        if price_usd_t <= 0:
            raise ValueError(f"price_usd_t must be positive, got {price_usd_t}")

        total_vol = float(df["volume_mt"].sum())
        q_vol = total_vol / quarters

        rows = []
        for q in range(1, quarters + 1):
            gross = q_vol * price_usd_t
            royalty = gross * self.royalty_rate
            opex = q_vol * (self.mining_cost_usd_t + self.transport_usd_t)
            net = gross - royalty - opex
            margin = net / gross * 100 if gross > 0 else 0
            rows.append({
                "quarter": f"Q{q}",
                "volume_mt": round(q_vol, 1),
                "price_usd_t": round(price_usd_t, 2),
                "gross_revenue_usd": round(gross, 2),
                "royalty_usd": round(royalty, 2),
                "opex_usd": round(opex, 2),
                "net_revenue_usd": round(net, 2),
                "ebitda_margin_pct": round(margin, 2),
            })
        return pd.DataFrame(rows)

    def scenario_comparison(
        self,
        df: pd.DataFrame,
        scenarios: Optional[List[Dict[str, float]]] = None,
    ) -> pd.DataFrame:
        """
        Compare revenue outcomes across multiple price/cost scenarios.

        Args:
            df: Production plan DataFrame.
            scenarios: List of dicts with keys: name, price_usd_t,
                       and optionally mining_cost_usd_t, transport_usd_t, royalty_rate.
                       Defaults to base, bull, and bear case scenarios.

        Returns:
            DataFrame with one row per scenario showing key financial metrics.
        """
        if scenarios is None:
            scenarios = [
                {"name": "Bear Case", "price_usd_t": 65.0},
                {"name": "Base Case", "price_usd_t": 85.0},
                {"name": "Bull Case", "price_usd_t": 110.0},
            ]

        rows = []
        original_config = {
            "royalty_rate": self.royalty_rate,
            "transport_usd_t": self.transport_usd_t,
            "mining_cost_usd_t": self.mining_cost_usd_t,
        }
        for sc in scenarios:
            self.royalty_rate = sc.get("royalty_rate", original_config["royalty_rate"])
            self.transport_usd_t = sc.get("transport_usd_t", original_config["transport_usd_t"])
            self.mining_cost_usd_t = sc.get("mining_cost_usd_t", original_config["mining_cost_usd_t"])
            try:
                res = self.forecast_revenue(df, price_usd_t=sc.get("price_usd_t"))
                rows.append({
                    "scenario": sc.get("name", "Unnamed"),
                    "price_usd_t": res["price_used_usd_t"],
                    "net_revenue_usd": res["net_revenue_usd"],
                    "ebitda_margin_pct": res["ebitda_margin_pct"],
                    "break_even_price_usd_t": res.get("break_even_price_usd_t"),
                    "profitable": res["net_revenue_usd"] > 0,
                })
            except Exception as e:
                rows.append({"scenario": sc.get("name", "Unnamed"), "error": str(e)})
        # Restore
        self.royalty_rate = original_config["royalty_rate"]
        self.transport_usd_t = original_config["transport_usd_t"]
        self.mining_cost_usd_t = original_config["mining_cost_usd_t"]
        return pd.DataFrame(rows)

    def monte_carlo_revenue_simulation(
        self,
        production_mt: float,
        base_price_usd_t: float,
        price_volatility_pct: float = 15.0,
        n_simulations: int = 1000,
        seed: Optional[int] = 42,
    ) -> dict:
        """
        Run Monte Carlo simulation to model revenue uncertainty.

        Simulates revenue distribution by sampling coal price from a
        log-normal distribution parameterized by volatility.

        Args:
            production_mt: Annual production in metric tonnes
            base_price_usd_t: Expected/mean coal price (USD/tonne)
            price_volatility_pct: Annualised price volatility as % of mean, default 15%
            n_simulations: Number of Monte Carlo iterations, default 1000
            seed: Random seed for reproducibility, default 42

        Returns:
            Dict with revenue statistics:
                - mean_revenue_usd, median_revenue_usd, std_revenue_usd
                - p10_revenue_usd, p90_revenue_usd (10th/90th percentiles)
                - var_95_usd (Value at Risk at 95% confidence)
                - prob_profitable_pct
                - price_distribution: {mean, std, min, max}

        Raises:
            ValueError: If production_mt or base_price_usd_t <= 0

        Example:
            >>> forecaster = MineRevenueForecaster(royalty_rate=0.13)
            >>> sim = forecaster.monte_carlo_revenue_simulation(
            ...     production_mt=500_000,
            ...     base_price_usd_t=90.0,
            ...     price_volatility_pct=20.0,
            ... )
            >>> print(f"P90 revenue: ${sim['p90_revenue_usd']:,.0f}")
        """
        if production_mt <= 0:
            raise ValueError("production_mt must be positive")
        if base_price_usd_t <= 0:
            raise ValueError("base_price_usd_t must be positive")
        if not (0 < price_volatility_pct < 200):
            raise ValueError("price_volatility_pct must be between 0 and 200")
        if n_simulations < 10:
            raise ValueError("n_simulations must be at least 10")

        rng = np.random.default_rng(seed)

        # Log-normal price simulation
        sigma = price_volatility_pct / 100.0
        mu = np.log(base_price_usd_t) - 0.5 * sigma ** 2
        simulated_prices = rng.lognormal(mean=mu, sigma=sigma, size=n_simulations)

        # Revenue per simulation
        total_cost_per_t = self.mining_cost_usd_t + self.transport_usd_t
        revenues = []
        for price in simulated_prices:
            gross = production_mt * price
            royalty = gross * self.royalty_rate
            cost = production_mt * total_cost_per_t
            net = gross - royalty - cost
            revenues.append(net)

        revenues_arr = np.array(revenues)
        break_even_price = total_cost_per_t / (1 - self.royalty_rate)

        return {
            "mean_revenue_usd": round(float(revenues_arr.mean()), 0),
            "median_revenue_usd": round(float(np.median(revenues_arr)), 0),
            "std_revenue_usd": round(float(revenues_arr.std()), 0),
            "p10_revenue_usd": round(float(np.percentile(revenues_arr, 10)), 0),
            "p90_revenue_usd": round(float(np.percentile(revenues_arr, 90)), 0),
            "var_95_usd": round(float(np.percentile(revenues_arr, 5)), 0),
            "prob_profitable_pct": round(float((revenues_arr > 0).mean() * 100), 1),
            "n_simulations": n_simulations,
            "break_even_price_usd_t": round(break_even_price, 2),
            "price_distribution": {
                "mean_usd_t": round(float(simulated_prices.mean()), 2),
                "std_usd_t": round(float(simulated_prices.std()), 2),
                "min_usd_t": round(float(simulated_prices.min()), 2),
                "max_usd_t": round(float(simulated_prices.max()), 2),
            },
        }
