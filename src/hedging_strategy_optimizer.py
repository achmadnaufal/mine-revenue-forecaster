"""
Coal Price Hedging Strategy Optimizer.

Models forward-cover hedging strategies for coal mining operations to reduce
exposure to spot price volatility. Calculates optimal hedge ratios, cost-
benefit of hedging vs. unhedged exposure, and simulates P&L under hedged
and unhedged scenarios.

Relevant to Indonesian ICI (Indonesian Coal Index) and ICE Newcastle futures
contract strategies used by major Kalimantan thermal coal producers.

Methodology references:
- Hull (2018) Options, Futures, and Other Derivatives, 10th Ed.
- Harris & Shen (2006) Hedging and Value at Risk: A Semi-parametric Approach
- Indonesian Coal Mining Association (APBI) Price Risk Management Guidelines
- ICE Futures Newcastle Coal Futures Contract specifications

Author: github.com/achmadnaufal
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class HedgeScenario:
    """Input specification for a single hedging scenario.

    Attributes:
        scenario_name: Label for this hedging scenario.
        production_mt: Annual production volume (million tonnes).
        hedge_ratio: Fraction of production hedged (0.0 = unhedged, 1.0 = fully hedged).
        forward_price_usd_t: Locked-in forward/futures price (USD/tonne).
        spot_price_usd_t: Realized or assumed spot price at settlement (USD/tonne).
        hedge_cost_usd_t: Broker/margin cost per tonne hedged (USD/tonne). Default 0.
        production_cost_usd_t: All-in sustaining cost per tonne (USD/tonne).
    """

    scenario_name: str
    production_mt: float         # million tonnes
    hedge_ratio: float           # 0.0 – 1.0
    forward_price_usd_t: float   # USD/tonne
    spot_price_usd_t: float      # USD/tonne (realized)
    hedge_cost_usd_t: float = 0.0
    production_cost_usd_t: float = 30.0


@dataclass
class HedgeResult:
    """Output of a single hedging scenario evaluation.

    Attributes:
        scenario_name: Label for this scenario.
        hedged_volume_mt: Volume sold at forward price (million tonnes).
        spot_volume_mt: Volume sold at spot price (million tonnes).
        blended_revenue_usd_m: Total blended revenue (USD millions).
        unhedged_revenue_usd_m: Revenue if fully unhedged at spot (USD millions).
        hedge_gain_loss_usd_m: Revenue difference (hedged vs unhedged). Positive = gain from hedge.
        hedge_cost_total_usd_m: Total hedging cost (USD millions).
        net_revenue_usd_m: Blended revenue minus hedge cost (USD millions).
        ebit_usd_m: Net revenue minus total production cost (USD millions).
        ebit_margin_pct: EBIT as % of net revenue.
        hedge_effectiveness: Ratio of net_revenue to unhedged_revenue (higher = hedge added value).
    """

    scenario_name: str
    hedged_volume_mt: float
    spot_volume_mt: float
    blended_revenue_usd_m: float
    unhedged_revenue_usd_m: float
    hedge_gain_loss_usd_m: float
    hedge_cost_total_usd_m: float
    net_revenue_usd_m: float
    ebit_usd_m: float
    ebit_margin_pct: float
    hedge_effectiveness: float


class HedgingStrategyOptimizer:
    """Evaluates coal price hedging strategies under different market scenarios.

    Models the financial impact of forward-price hedging at different coverage
    ratios, comparing blended revenue, hedge P&L, and EBIT outcomes against
    a fully unhedged baseline.

    The optimizer can also scan across a range of hedge ratios to find the
    combination that maximises EBIT or minimises downside risk, given
    assumptions about spot price distribution.

    Args:
        default_production_cost_usd_t: Default all-in sustaining cost per tonne.
            Used when HedgeScenario does not specify ``production_cost_usd_t``.

    Example::

        optimizer = HedgingStrategyOptimizer()
        scenario = HedgeScenario(
            scenario_name="50% Forward Cover",
            production_mt=5.0,
            hedge_ratio=0.50,
            forward_price_usd_t=85.0,
            spot_price_usd_t=72.0,   # price fell; hedge was beneficial
            hedge_cost_usd_t=0.50,
            production_cost_usd_t=32.0,
        )
        result = optimizer.evaluate(scenario)
        print(f"Hedge gain/loss: USD {result.hedge_gain_loss_usd_m:.1f}M")
        print(f"EBIT margin: {result.ebit_margin_pct:.1f}%")
    """

    def __init__(self, default_production_cost_usd_t: float = 30.0) -> None:
        if default_production_cost_usd_t < 0:
            raise ValueError("default_production_cost_usd_t must be ≥ 0.")
        self._default_cost = default_production_cost_usd_t

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def evaluate(self, scenario: HedgeScenario) -> HedgeResult:
        """Evaluate financial outcomes for a single hedge scenario.

        Args:
            scenario: HedgeScenario specifying production volume, hedge ratio,
                forward price, realized spot price, hedge cost, and opex.

        Returns:
            HedgeResult with blended revenue, hedge P&L, EBIT, and effectiveness.

        Raises:
            ValueError: If scenario inputs are out of valid range.
        """
        self._validate_scenario(scenario)

        hedged_mt = scenario.production_mt * scenario.hedge_ratio
        spot_mt = scenario.production_mt * (1 - scenario.hedge_ratio)

        # Revenue components (USD millions)
        hedged_rev = hedged_mt * scenario.forward_price_usd_t   # at locked price
        spot_rev = spot_mt * scenario.spot_price_usd_t          # at market

        blended_rev = hedged_rev + spot_rev
        unhedged_rev = scenario.production_mt * scenario.spot_price_usd_t
        hedge_gain_loss = blended_rev - unhedged_rev

        hedge_cost_total = hedged_mt * scenario.hedge_cost_usd_t
        net_rev = blended_rev - hedge_cost_total

        production_cost = scenario.production_mt * scenario.production_cost_usd_t
        ebit = net_rev - production_cost

        ebit_margin = (ebit / net_rev * 100) if net_rev > 0 else 0.0
        effectiveness = (net_rev / unhedged_rev) if unhedged_rev > 0 else 1.0

        return HedgeResult(
            scenario_name=scenario.scenario_name,
            hedged_volume_mt=round(hedged_mt, 3),
            spot_volume_mt=round(spot_mt, 3),
            blended_revenue_usd_m=round(blended_rev, 2),
            unhedged_revenue_usd_m=round(unhedged_rev, 2),
            hedge_gain_loss_usd_m=round(hedge_gain_loss, 2),
            hedge_cost_total_usd_m=round(hedge_cost_total, 2),
            net_revenue_usd_m=round(net_rev, 2),
            ebit_usd_m=round(ebit, 2),
            ebit_margin_pct=round(ebit_margin, 2),
            hedge_effectiveness=round(effectiveness, 4),
        )

    def compare_scenarios(self, scenarios: List[HedgeScenario]) -> List[HedgeResult]:
        """Evaluate multiple hedge scenarios and sort by EBIT (highest first).

        Args:
            scenarios: List of HedgeScenario objects.

        Returns:
            List of HedgeResult sorted by ebit_usd_m descending.
        """
        results = [self.evaluate(s) for s in scenarios]
        return sorted(results, key=lambda r: r.ebit_usd_m, reverse=True)

    def scan_hedge_ratios(
        self,
        production_mt: float,
        forward_price_usd_t: float,
        spot_price_usd_t: float,
        production_cost_usd_t: float,
        hedge_cost_usd_t: float = 0.50,
        steps: int = 11,
    ) -> List[HedgeResult]:
        """Sweep hedge ratios from 0% to 100% and return EBIT curve.

        Useful for finding the optimal coverage ratio given a price outlook.

        Args:
            production_mt: Annual production volume (million tonnes).
            forward_price_usd_t: Forward price available in the market.
            spot_price_usd_t: Expected or realized spot price.
            production_cost_usd_t: All-in cost per tonne.
            hedge_cost_usd_t: Hedging transaction cost per hedged tonne.
            steps: Number of hedge ratio intervals (default 11 = 0%, 10%, ..., 100%).

        Returns:
            List of HedgeResult ordered by hedge_ratio ascending.

        Example::

            results = optimizer.scan_hedge_ratios(
                production_mt=5.0,
                forward_price_usd_t=85.0,
                spot_price_usd_t=70.0,   # falling market; hedge adds value
                production_cost_usd_t=32.0,
                hedge_cost_usd_t=0.50,
            )
            best = max(results, key=lambda r: r.ebit_usd_m)
            print(f"Optimal hedge ratio: {best.scenario_name}")
        """
        ratios = [i / (steps - 1) for i in range(steps)]
        scenarios = [
            HedgeScenario(
                scenario_name=f"{ratio * 100:.0f}% hedged",
                production_mt=production_mt,
                hedge_ratio=ratio,
                forward_price_usd_t=forward_price_usd_t,
                spot_price_usd_t=spot_price_usd_t,
                hedge_cost_usd_t=hedge_cost_usd_t,
                production_cost_usd_t=production_cost_usd_t,
            )
            for ratio in ratios
        ]
        return [self.evaluate(s) for s in scenarios]

    def breakeven_spot_price(
        self,
        forward_price_usd_t: float,
        hedge_ratio: float,
        production_cost_usd_t: float,
        hedge_cost_usd_t: float = 0.50,
    ) -> float:
        """Calculate the spot price at which hedging and not hedging are equivalent.

        Args:
            forward_price_usd_t: Locked forward price (USD/tonne).
            hedge_ratio: Proportion hedged (0–1).
            production_cost_usd_t: All-in sustaining cost per tonne.
            hedge_cost_usd_t: Hedging transaction cost per hedged tonne.

        Returns:
            Breakeven spot price (USD/tonne).

        Note:
            Below this price, hedging adds value. Above it, staying unhedged was better.
        """
        if not (0.0 <= hedge_ratio <= 1.0):
            raise ValueError("hedge_ratio must be in [0, 1].")

        if hedge_ratio == 0:
            return forward_price_usd_t  # irrelevant; no hedge

        # Equate hedged net revenue per tonne = unhedged net revenue per tonne
        # Hedged: ratio * forward + (1-ratio) * spot - ratio * hedge_cost = spot
        # Solve for spot:
        # ratio * forward - ratio * hedge_cost + spot - ratio * spot = spot
        # ratio * (forward - hedge_cost) = spot * ratio
        # spot = forward - hedge_cost
        # (when production cost same both sides it cancels)
        breakeven = forward_price_usd_t - hedge_cost_usd_t
        return round(breakeven, 2)

    def hedge_value_at_risk(
        self,
        production_mt: float,
        hedge_ratio: float,
        forward_price_usd_t: float,
        spot_price_mean_usd_t: float,
        spot_price_std_usd_t: float,
        confidence_level: float = 0.95,
    ) -> Dict:
        """Estimate Value-at-Risk (VaR) reduction from hedging.

        Uses a parametric (normal distribution) VaR approach.

        Args:
            production_mt: Annual production (million tonnes).
            hedge_ratio: Proportion hedged (0–1).
            forward_price_usd_t: Forward price (USD/tonne).
            spot_price_mean_usd_t: Expected spot price (USD/tonne).
            spot_price_std_usd_t: Spot price standard deviation (USD/tonne).
            confidence_level: VaR confidence (e.g., 0.95 for 95% VaR).

        Returns:
            Dict with:
                - ``unhedged_var_usd_m``: Revenue at risk without hedge.
                - ``hedged_var_usd_m``: Revenue at risk with hedge.
                - ``var_reduction_pct``: % reduction in VaR from hedging.
                - ``z_score``: Normal z-score for the confidence level used.
        """
        if not (0.5 <= confidence_level < 1.0):
            raise ValueError("confidence_level must be in [0.5, 1.0).")

        # z-score approximation for normal distribution
        # z = Φ⁻¹(confidence_level) — using linear approximation for common levels
        z_approx = {0.90: 1.282, 0.95: 1.645, 0.99: 2.326}
        z = z_approx.get(confidence_level, 1.645)
        if confidence_level not in z_approx:
            # Simple Newton-Raphson-free approximation
            z = math.sqrt(-2 * math.log(1 - confidence_level)) * 0.9  # rough

        # VaR for unhedged: entire production exposed to spot volatility
        unhedged_var = production_mt * spot_price_std_usd_t * z

        # Hedged portion has zero price risk; only spot portion has risk
        spot_fraction = 1 - hedge_ratio
        hedged_var = production_mt * spot_fraction * spot_price_std_usd_t * z

        var_reduction = (
            (unhedged_var - hedged_var) / unhedged_var * 100
            if unhedged_var > 0 else 0.0
        )

        return {
            "unhedged_var_usd_m": round(unhedged_var, 2),
            "hedged_var_usd_m": round(hedged_var, 2),
            "var_reduction_pct": round(var_reduction, 1),
            "z_score": z,
        }

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_scenario(s: HedgeScenario) -> None:
        if s.production_mt <= 0:
            raise ValueError(f"production_mt must be > 0, got {s.production_mt}.")
        if not (0.0 <= s.hedge_ratio <= 1.0):
            raise ValueError(f"hedge_ratio must be in [0, 1], got {s.hedge_ratio}.")
        if s.forward_price_usd_t <= 0:
            raise ValueError(f"forward_price_usd_t must be > 0, got {s.forward_price_usd_t}.")
        if s.spot_price_usd_t <= 0:
            raise ValueError(f"spot_price_usd_t must be > 0, got {s.spot_price_usd_t}.")
        if s.hedge_cost_usd_t < 0:
            raise ValueError(f"hedge_cost_usd_t must be ≥ 0, got {s.hedge_cost_usd_t}.")
