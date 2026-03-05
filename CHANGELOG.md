# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

## [1.3.0] - 2026-03-05
### Added
- `quarterly_projection()`: distributes production plan into quarterly P&L projections
- `scenario_comparison()`: side-by-side revenue comparison across bear/base/bull price scenarios
- 10 new unit tests covering quarterly projection and scenario comparison
### Improved
- README updated with scenario comparison table and quarterly projection usage

## [1.2.0] - 2026-03-04
### Added
- `forecast_revenue()`: gross revenue, royalty, opex, net revenue, EBITDA margin, break-even price
- `price_sensitivity()`: revenue projections across configurable price range
- Configurable royalty rate, mining cost, and transport cost via constructor
- 14 unit tests covering revenue math, edge cases, and price sensitivity
- Sample data: 12-month production plan with CV and strip ratio
### Fixed
- `validate()` checks for negative volumes
- `forecast_revenue()` raises clear errors for missing price or volume columns
## [1.1.0] - 2026-03-02
### Added
- Add multi-commodity revenue modeling and scenario planning
- Improved unit test coverage
- Enhanced documentation with realistic examples
