"""
Mine cost structure breakdown and unit cost analysis module.

Disaggregates total mine cash costs into operational components and calculates
key mining economics metrics. Supports:
  - All-In Sustaining Cost (AISC) analysis
  - Strip ratio impact on unit costs
  - Mine cost curve positioning vs benchmark
  - Break-even coal price at various production rates

References:
    - World Coal Association (2021) Coal Cost Benchmarking methodology
    - Indonesian Ministry of Energy (ESDM) HPB formula for benchmark price
    - Wood Mackenzie Coal Cost Curve methodology
    - JORC Code 2012 — competent persons report cost reporting standards
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# Indonesian regulatory benchmarks (2024)
ROYALTY_RATES_IDN = {
    "IUP_small":   0.03,   # < 100,000 tpa production
    "IUP_medium":  0.05,   # 100,000 – 1,000,000 tpa
    "IUP_large":   0.07,   # > 1,000,000 tpa (sub-bituminous)
    "PKP2B":       0.13,   # Coal contracts of work (PKP2B) — standard
    "IUPK":        0.135,  # IUPK (continuation of PKP2B)
}

# Industry benchmark cost ranges (USD/tonne, FOB Kalimantan) — 2024
BENCHMARK_COSTS = {
    "mining_cash_cost":  {"low": 18, "median": 28, "high": 42},
    "processing":        {"low": 2,  "median": 4,  "high": 8},
    "haulage":           {"low": 3,  "median": 6,  "high": 12},
    "port_loading":      {"low": 4,  "median": 7,  "high": 11},
    "royalty":           {"low": 8,  "median": 12, "high": 18},
    "sustaining_capex":  {"low": 1,  "median": 3,  "high": 6},
}


@dataclass
class CostComponent:
    """
    A single operational cost component for mine cost structure analysis.

    Attributes:
        name (str): Cost category name (e.g., 'drilling_blasting')
        cost_per_tonne_usd (float): Unit cost in USD per tonne of coal produced
        cost_type (str): 'variable' (scales with production) or 'fixed' (site overhead)
        is_cash_cost (bool): True if included in cash cost (C1); False for non-cash items
        notes (str): Description or source of cost estimate

    Example:
        >>> drilling = CostComponent(
        ...     name="drilling_blasting",
        ...     cost_per_tonne_usd=3.80,
        ...     cost_type="variable",
        ...     is_cash_cost=True,
        ...     notes="Emulsion explosive + drill hire"
        ... )
    """

    name: str
    cost_per_tonne_usd: float
    cost_type: str = "variable"   # 'variable' | 'fixed'
    is_cash_cost: bool = True
    notes: str = ""

    VALID_COST_TYPES = {"variable", "fixed"}

    def __post_init__(self):
        if not self.name.strip():
            raise ValueError("name cannot be empty")
        if self.cost_per_tonne_usd < 0:
            raise ValueError(f"cost_per_tonne_usd cannot be negative for '{self.name}'")
        if self.cost_type not in self.VALID_COST_TYPES:
            raise ValueError(f"cost_type must be one of {self.VALID_COST_TYPES}")


@dataclass
class ProductionScenario:
    """
    Mine production parameters for a given scenario or period.

    Attributes:
        scenario_name (str): Label (e.g., 'FY2025 Base Case')
        annual_production_kt (float): Coal production in thousands of tonnes
        strip_ratio (float): Overburden removal ratio (BCM waste / tonne coal)
        coal_price_usd_t (float): Realised FOB coal price (USD/tonne)
        mining_method (str): Excavation method ('open_pit' or 'underground')

    Example:
        >>> scenario = ProductionScenario(
        ...     scenario_name="Base Case",
        ...     annual_production_kt=3500.0,
        ...     strip_ratio=4.8,
        ...     coal_price_usd_t=82.0,
        ... )
    """

    scenario_name: str
    annual_production_kt: float
    strip_ratio: float
    coal_price_usd_t: float
    mining_method: str = "open_pit"

    VALID_METHODS = {"open_pit", "underground"}

    def __post_init__(self):
        if not self.scenario_name.strip():
            raise ValueError("scenario_name cannot be empty")
        if self.annual_production_kt <= 0:
            raise ValueError("annual_production_kt must be positive")
        if self.strip_ratio < 0:
            raise ValueError("strip_ratio cannot be negative")
        if self.coal_price_usd_t <= 0:
            raise ValueError("coal_price_usd_t must be positive")
        if self.mining_method not in self.VALID_METHODS:
            raise ValueError(f"mining_method must be one of {self.VALID_METHODS}")

    @property
    def annual_production_tonnes(self) -> float:
        """Annual production in tonnes."""
        return self.annual_production_kt * 1000

    @property
    def overburden_bcm(self) -> float:
        """Approximate overburden volume in bank cubic metres (BCM)."""
        # Coal bulk density ≈ 1.3 t/BCM for loose coal; overburden ≈ 2.5 t/BCM
        coal_bcm = self.annual_production_tonnes / 1.3
        return coal_bcm * self.strip_ratio


class CostStructureAnalyzer:
    """
    Analyse mine cost structure and position against industry benchmarks.

    Args:
        components (List[CostComponent]): Operational cost components
        royalty_rate (float): Government royalty rate as fraction of revenue (0–1)
        sustaining_capex_usd_t (float): Sustaining capital expenditure per tonne

    Example:
        >>> components = [
        ...     CostComponent("mining", 24.0, "variable", True),
        ...     CostComponent("processing", 3.5, "variable", True),
        ...     CostComponent("haulage", 5.5, "variable", True),
        ...     CostComponent("port_loading", 6.0, "variable", True),
        ...     CostComponent("G&A", 2.5, "fixed", True),
        ... ]
        >>> analyzer = CostStructureAnalyzer(components, royalty_rate=0.13)
        >>> scenario = ProductionScenario("Base", 3500, 4.8, 82.0)
        >>> breakdown = analyzer.cost_breakdown(scenario)
        >>> print(f"AISC: ${breakdown['aisc_usd_t']:.2f}/t")
    """

    def __init__(
        self,
        components: List[CostComponent],
        royalty_rate: float = 0.13,
        sustaining_capex_usd_t: float = 3.0,
    ):
        if not components:
            raise ValueError("components list cannot be empty")
        if not 0.0 <= royalty_rate < 1.0:
            raise ValueError("royalty_rate must be in [0, 1)")
        if sustaining_capex_usd_t < 0:
            raise ValueError("sustaining_capex_usd_t cannot be negative")

        self.components = components
        self.royalty_rate = royalty_rate
        self.sustaining_capex_usd_t = sustaining_capex_usd_t

    def cash_cost_c1(self, scenario: Optional[ProductionScenario] = None) -> float:
        """
        Calculate C1 cash cost per tonne.

        C1 = all direct cash costs (mining, processing, haulage, port) EXCLUDING royalty
        and sustaining capex. Standard mining industry definition.

        Args:
            scenario: Optional scenario for strip-ratio adjustment.
                If provided, a strip ratio premium is applied to variable mining costs
                (every unit increase in strip ratio adds ~5% to variable mining costs).

        Returns:
            C1 cash cost in USD/tonne
        """
        base_c1 = sum(c.cost_per_tonne_usd for c in self.components if c.is_cash_cost)

        if scenario and scenario.strip_ratio > 0:
            # Strip ratio premium: baseline at SR=5; each 1-unit change = ±5% on variable mining
            sr_baseline = 5.0
            sr_diff = scenario.strip_ratio - sr_baseline
            variable_mining = sum(
                c.cost_per_tonne_usd for c in self.components
                if c.cost_type == "variable" and c.is_cash_cost
            )
            strip_premium = variable_mining * sr_diff * 0.05
            return max(0.0, base_c1 + strip_premium)

        return base_c1

    def royalty_cost(self, price_usd_t: float) -> float:
        """
        Royalty cost per tonne at a given coal price.

        Indonesian royalty is calculated as a percentage of the benchmark price (HPB).
        Modelled here as royalty_rate × price.

        Args:
            price_usd_t: FOB coal price in USD/tonne

        Returns:
            Royalty cost in USD/tonne
        """
        return self.royalty_rate * price_usd_t

    def aisc(self, scenario: ProductionScenario) -> float:
        """
        All-In Sustaining Cost (AISC) per tonne.

        AISC = C1 cash cost + royalty + sustaining capex

        Args:
            scenario: Production scenario (for strip ratio adjustment and price)

        Returns:
            AISC in USD/tonne
        """
        return (
            self.cash_cost_c1(scenario)
            + self.royalty_cost(scenario.coal_price_usd_t)
            + self.sustaining_capex_usd_t
        )

    def break_even_price(self, scenario: ProductionScenario) -> float:
        """
        Minimum coal price required to break even (AISC = Revenue).

        Solves: P = C1 + P × royalty_rate + sustaining_capex
        → P × (1 - royalty_rate) = C1 + sustaining_capex
        → P = (C1 + sustaining_capex) / (1 - royalty_rate)

        Args:
            scenario: Production scenario (strip ratio affects C1)

        Returns:
            Break-even FOB price in USD/tonne
        """
        c1 = self.cash_cost_c1(scenario)
        numerator = c1 + self.sustaining_capex_usd_t
        denominator = 1.0 - self.royalty_rate
        if denominator <= 0:
            raise ValueError("royalty_rate must be < 1.0 for break-even calculation")
        return numerator / denominator

    def gross_margin_per_tonne(self, scenario: ProductionScenario) -> float:
        """
        Gross margin per tonne: revenue less AISC.

        Returns:
            USD/tonne (positive = profitable, negative = loss-making)
        """
        return scenario.coal_price_usd_t - self.aisc(scenario)

    def annual_ebitda_usd(self, scenario: ProductionScenario) -> float:
        """
        Approximate annual EBITDA (earnings before interest, tax, D&A).

        EBITDA ≈ (coal_price - AISC + sustaining_capex) × annual_production_tonnes
        (Sustaining capex is added back as it's included in AISC but is capital, not P&L expense)

        Args:
            scenario: Production scenario with annual volume

        Returns:
            Annual EBITDA in USD
        """
        ebitda_per_tonne = scenario.coal_price_usd_t - self.aisc(scenario) + self.sustaining_capex_usd_t
        return ebitda_per_tonne * scenario.annual_production_tonnes

    def cost_breakdown(self, scenario: ProductionScenario) -> Dict:
        """
        Full cost breakdown with benchmark comparison.

        Args:
            scenario: Production scenario

        Returns:
            Dict with:
                - scenario_name (str)
                - components (List[Dict]): Per-component costs
                - c1_cash_cost_usd_t (float)
                - royalty_usd_t (float)
                - sustaining_capex_usd_t (float)
                - aisc_usd_t (float)
                - break_even_price_usd_t (float)
                - gross_margin_usd_t (float)
                - annual_ebitda_usd (float)
                - margin_pct (float): Gross margin as % of revenue
                - benchmark_position (str): 'below_median', 'at_median', 'above_median'

        Example:
            >>> bd = analyzer.cost_breakdown(scenario)
            >>> print(f"AISC: ${bd['aisc_usd_t']:.1f}/t | Margin: {bd['margin_pct']:.1f}%")
        """
        c1 = self.cash_cost_c1(scenario)
        royalty = self.royalty_cost(scenario.coal_price_usd_t)
        aisc_val = self.aisc(scenario)
        margin = self.gross_margin_per_tonne(scenario)
        margin_pct = (margin / scenario.coal_price_usd_t * 100) if scenario.coal_price_usd_t > 0 else 0.0

        # Benchmark positioning (vs industry AISC median ~$50/t)
        industry_aisc_median = (
            BENCHMARK_COSTS["mining_cash_cost"]["median"]
            + BENCHMARK_COSTS["processing"]["median"]
            + BENCHMARK_COSTS["haulage"]["median"]
            + BENCHMARK_COSTS["port_loading"]["median"]
            + BENCHMARK_COSTS["royalty"]["median"]
            + BENCHMARK_COSTS["sustaining_capex"]["median"]
        )
        if aisc_val < industry_aisc_median * 0.9:
            benchmark_position = "below_median (cost competitive)"
        elif aisc_val <= industry_aisc_median * 1.1:
            benchmark_position = "at_median"
        else:
            benchmark_position = "above_median (cost disadvantage)"

        return {
            "scenario_name": scenario.scenario_name,
            "strip_ratio": scenario.strip_ratio,
            "coal_price_usd_t": scenario.coal_price_usd_t,
            "annual_production_kt": scenario.annual_production_kt,
            "components": [
                {
                    "name": c.name,
                    "cost_usd_t": round(c.cost_per_tonne_usd, 2),
                    "cost_type": c.cost_type,
                    "is_cash_cost": c.is_cash_cost,
                }
                for c in self.components
            ],
            "c1_cash_cost_usd_t": round(c1, 2),
            "royalty_usd_t": round(royalty, 2),
            "sustaining_capex_usd_t": round(self.sustaining_capex_usd_t, 2),
            "aisc_usd_t": round(aisc_val, 2),
            "break_even_price_usd_t": round(self.break_even_price(scenario), 2),
            "gross_margin_usd_t": round(margin, 2),
            "annual_ebitda_usd": round(self.annual_ebitda_usd(scenario)),
            "margin_pct": round(margin_pct, 1),
            "benchmark_position": benchmark_position,
        }

    def strip_ratio_sensitivity(
        self, base_scenario: ProductionScenario, strip_ratios: List[float]
    ) -> List[Dict]:
        """
        Analyse how AISC and margin change across different strip ratios.

        Useful for mine planning decisions on waste removal scheduling.

        Args:
            base_scenario: Base case scenario (strip ratio is overridden)
            strip_ratios: List of strip ratios to evaluate

        Returns:
            List of dicts with aisc, margin, and break-even per strip ratio

        Example:
            >>> sensitivity = analyzer.strip_ratio_sensitivity(scenario, [3, 4, 5, 6, 7, 8])
        """
        if not strip_ratios:
            raise ValueError("strip_ratios list cannot be empty")

        results = []
        for sr in sorted(strip_ratios):
            import dataclasses
            test_scenario = dataclasses.replace(base_scenario, strip_ratio=sr)
            c1 = self.cash_cost_c1(test_scenario)
            aisc_val = self.aisc(test_scenario)
            margin = self.gross_margin_per_tonne(test_scenario)
            results.append(
                {
                    "strip_ratio": sr,
                    "c1_usd_t": round(c1, 2),
                    "aisc_usd_t": round(aisc_val, 2),
                    "gross_margin_usd_t": round(margin, 2),
                    "profitable": margin > 0,
                    "break_even_price_usd_t": round(self.break_even_price(test_scenario), 2),
                }
            )
        return results
