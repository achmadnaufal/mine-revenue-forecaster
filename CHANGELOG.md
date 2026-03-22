# Changelog - Mine Revenue Forecaster

## [1.6.0] - 2026-03-22

### Added
- **Hedging Strategy Optimizer** (`src/hedging_strategy_optimizer.py`) — coal price forward-cover analysis
  - `HedgeScenario` and `HedgeResult` dataclasses for structured scenario specification
  - `evaluate()` — calculates blended revenue, hedge P&L, EBIT, and EBIT margin for a single hedge scenario
  - `compare_scenarios()` — batch evaluation of multiple coverage strategies, sorted by EBIT
  - `scan_hedge_ratios()` — sweeps 0%–100% coverage in configurable steps to generate EBIT curve
  - `breakeven_spot_price()` — calculates the spot price level below which hedging adds net value
  - `hedge_value_at_risk()` — parametric VaR reduction estimate from hedging (95%/99% confidence levels)
  - Full input validation: production volume, hedge ratio bounds, price positivity, cost non-negativity
- **Unit tests** — 27 tests in `tests/test_hedging_strategy_optimizer.py` covering all public methods and error paths

### References
- Hull (2018) Options, Futures, and Other Derivatives, 10th Ed.
- ICE Futures Newcastle Coal contract specifications
- APBI Price Risk Management Guidelines

## [1.5.0] - 2026-03-18

### Added
- **Cost Structure Analyzer** (`src/cost_structure_analyzer.py`) — mine cost disaggregation and AISC analysis
  - `CostComponent` and `ProductionScenario` dataclasses with full input validation
  - C1 cash cost calculation with strip-ratio premium adjustment (±5% per unit vs SR=5 baseline)
  - All-In Sustaining Cost (AISC) = C1 + royalty + sustaining capex
  - Break-even coal price solver accounting for royalty as % of revenue
  - Annual EBITDA approximation for project economics
  - `cost_breakdown()`: full cost waterfall with benchmark positioning (vs industry AISC median)
  - `strip_ratio_sensitivity()`: AISC and margin across a range of strip ratios
  - Indonesian royalty rate catalogue (IUP Small/Medium/Large, PKP2B, IUPK)
- **Unit tests** — 29 tests in `tests/test_cost_structure_analyzer.py` covering C1, AISC, BEP, sensitivity, and catalogue validation

### References
- World Coal Association (2021) coal cost benchmarking
- Indonesian ESDM HPB royalty formula
- Wood Mackenzie Coal Cost Curve methodology

## [1.4.0] - 2026-03-15

### Added
- **Monte Carlo Revenue Simulation** — `monte_carlo_revenue_simulation()`: Models revenue uncertainty via log-normal price sampling; returns P10/P90 range, VaR@95%, probability-of-profit, and price distribution statistics
- **Unit Tests** — 8 new tests in `tests/test_monte_carlo.py` covering simulation correctness, edge cases, profitability scenarios, and reproducibility
- **README** — Added Monte Carlo simulation usage example

### Improved
- Added `seed` parameter for reproducible Monte Carlo runs
- Docstrings updated with `Raises` and `Example` sections

## [1.3.0] - 2026-03-10

### Added

- **Forecast Engine**: New `forecast_engine.py` with MineRevenueForecaster class
  - `calculate_revenue_metrics()`: Revenue and margin calculation
  - `forecast_simple_trend()`: Linear trend forecasting
  - `scenario_analysis()`: Bull/base/bear case scenarios
  - `calculate_breakeven_production()`: Break-even analysis
  - `calculate_npv()`: Net present value calculation
- **Test Suite**: 5 new tests for forecasting methods
- **Financial Analysis**: NPV and break-even tools for investment decisions

## [1.2.0] - 2026-02-15

### Added

- Revenue projection templates
- Basic forecasting

## [1.1.0] - 2026-01-15

### Added

- Initial mining revenue module

## [1.0.0] - 2025-12-01

### Added

- Initial forecasting framework
