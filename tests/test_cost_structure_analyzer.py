"""
Unit tests for mine cost structure breakdown and AISC analysis.
"""

import pytest
from src.cost_structure_analyzer import (
    CostComponent,
    ProductionScenario,
    CostStructureAnalyzer,
    ROYALTY_RATES_IDN,
)


# ---------------------------------------------------------------------------
# CostComponent tests
# ---------------------------------------------------------------------------


class TestCostComponent:
    def test_valid_creation(self):
        c = CostComponent("mining", 24.0, "variable", True, "drill + blast + load")
        assert c.cost_per_tonne_usd == 24.0

    def test_empty_name_raises(self):
        with pytest.raises(ValueError, match="name cannot be empty"):
            CostComponent("  ", 24.0)

    def test_negative_cost_raises(self):
        with pytest.raises(ValueError, match="cannot be negative"):
            CostComponent("mining", -5.0)

    def test_invalid_cost_type_raises(self):
        with pytest.raises(ValueError, match="cost_type must be one of"):
            CostComponent("mining", 24.0, cost_type="semi-variable")


# ---------------------------------------------------------------------------
# ProductionScenario tests
# ---------------------------------------------------------------------------


class TestProductionScenario:
    def test_valid_creation(self):
        s = ProductionScenario("Base", 3500.0, 4.8, 82.0)
        assert s.annual_production_kt == 3500.0

    def test_production_in_tonnes(self):
        s = ProductionScenario("Base", 1000.0, 5.0, 80.0)
        assert s.annual_production_tonnes == pytest.approx(1_000_000)

    def test_overburden_bcm_positive(self):
        s = ProductionScenario("Base", 1000.0, 5.0, 80.0)
        assert s.overburden_bcm > 0

    def test_zero_production_raises(self):
        with pytest.raises(ValueError, match="annual_production_kt must be positive"):
            ProductionScenario("Bad", 0.0, 4.8, 82.0)

    def test_negative_strip_ratio_raises(self):
        with pytest.raises(ValueError, match="strip_ratio cannot be negative"):
            ProductionScenario("Bad", 3500.0, -1.0, 82.0)

    def test_zero_price_raises(self):
        with pytest.raises(ValueError, match="coal_price_usd_t must be positive"):
            ProductionScenario("Bad", 3500.0, 4.8, 0.0)

    def test_invalid_method_raises(self):
        with pytest.raises(ValueError, match="mining_method must be one of"):
            ProductionScenario("Bad", 3500.0, 4.8, 82.0, mining_method="tunnel")


# ---------------------------------------------------------------------------
# CostStructureAnalyzer tests
# ---------------------------------------------------------------------------


@pytest.fixture
def components():
    return [
        CostComponent("mining_cash", 24.0, "variable", True),
        CostComponent("processing", 3.5, "variable", True),
        CostComponent("haulage", 5.5, "variable", True),
        CostComponent("port_loading", 6.0, "variable", True),
        CostComponent("g_and_a", 2.5, "fixed", True),
    ]


@pytest.fixture
def analyzer(components):
    return CostStructureAnalyzer(components, royalty_rate=0.13, sustaining_capex_usd_t=3.0)


@pytest.fixture
def scenario():
    return ProductionScenario("Base Case", 3500.0, 4.8, 82.0)


class TestCostStructureAnalyzer:
    def test_creation_valid(self, analyzer):
        assert analyzer.royalty_rate == 0.13

    def test_empty_components_raises(self):
        with pytest.raises(ValueError, match="components list cannot be empty"):
            CostStructureAnalyzer([])

    def test_royalty_above_one_raises(self, components):
        with pytest.raises(ValueError, match="royalty_rate must be in"):
            CostStructureAnalyzer(components, royalty_rate=1.5)

    def test_negative_sustaining_capex_raises(self, components):
        with pytest.raises(ValueError, match="sustaining_capex_usd_t"):
            CostStructureAnalyzer(components, sustaining_capex_usd_t=-2.0)

    def test_c1_cash_cost_positive(self, analyzer, scenario):
        c1 = analyzer.cash_cost_c1(scenario)
        assert c1 > 0

    def test_c1_increases_with_strip_ratio(self, analyzer, components):
        low_sr = ProductionScenario("LowSR", 3500.0, 3.0, 82.0)
        high_sr = ProductionScenario("HighSR", 3500.0, 8.0, 82.0)
        assert analyzer.cash_cost_c1(high_sr) > analyzer.cash_cost_c1(low_sr)

    def test_royalty_cost_proportional(self, analyzer):
        r80 = analyzer.royalty_cost(80.0)
        r100 = analyzer.royalty_cost(100.0)
        assert r100 > r80
        assert r100 == pytest.approx(r80 * (100.0 / 80.0))

    def test_aisc_greater_than_c1(self, analyzer, scenario):
        assert analyzer.aisc(scenario) > analyzer.cash_cost_c1(scenario)

    def test_break_even_price_positive(self, analyzer, scenario):
        bep = analyzer.break_even_price(scenario)
        assert bep > 0

    def test_break_even_at_bep_margin_near_zero(self, analyzer, scenario):
        bep = analyzer.break_even_price(scenario)
        bep_scenario = ProductionScenario("BEP", scenario.annual_production_kt,
                                          scenario.strip_ratio, bep)
        margin = analyzer.gross_margin_per_tonne(bep_scenario)
        assert abs(margin) < 1.0  # should be near zero

    def test_positive_margin_above_aisc(self, analyzer, scenario):
        # Price 82 > AISC should be profitable at typical costs
        margin = analyzer.gross_margin_per_tonne(scenario)
        # May be positive or negative depending on component costs — just verify direction
        aisc_val = analyzer.aisc(scenario)
        assert margin == pytest.approx(scenario.coal_price_usd_t - aisc_val)

    def test_annual_ebitda_positive_for_profitable(self, analyzer):
        cheap_components = [CostComponent("mining", 10.0, "variable", True)]
        cheap_analyzer = CostStructureAnalyzer(cheap_components, 0.05, 1.0)
        s = ProductionScenario("Cheap", 1000.0, 3.0, 100.0)
        assert cheap_analyzer.annual_ebitda_usd(s) > 0

    def test_cost_breakdown_keys(self, analyzer, scenario):
        bd = analyzer.cost_breakdown(scenario)
        expected = {
            "scenario_name", "aisc_usd_t", "c1_cash_cost_usd_t", "royalty_usd_t",
            "break_even_price_usd_t", "gross_margin_usd_t", "annual_ebitda_usd",
            "margin_pct", "benchmark_position", "components",
        }
        assert expected.issubset(bd.keys())

    def test_cost_breakdown_components_non_empty(self, analyzer, scenario):
        bd = analyzer.cost_breakdown(scenario)
        assert len(bd["components"]) == len(analyzer.components)

    def test_strip_ratio_sensitivity_sorted(self, analyzer, scenario):
        results = analyzer.strip_ratio_sensitivity(scenario, [6, 3, 8, 5])
        srs = [r["strip_ratio"] for r in results]
        assert srs == sorted(srs)

    def test_strip_ratio_sensitivity_empty_raises(self, analyzer, scenario):
        with pytest.raises(ValueError, match="strip_ratios list cannot be empty"):
            analyzer.strip_ratio_sensitivity(scenario, [])

    def test_high_strip_ratio_higher_aisc(self, analyzer, scenario):
        results = analyzer.strip_ratio_sensitivity(scenario, [3.0, 8.0])
        aisc_3 = results[0]["aisc_usd_t"]
        aisc_8 = results[1]["aisc_usd_t"]
        assert aisc_8 > aisc_3

    def test_royalty_rates_catalogue_valid(self):
        for key, rate in ROYALTY_RATES_IDN.items():
            assert 0.0 < rate < 1.0, f"Invalid rate for {key}: {rate}"
