# mine-revenue-forecaster

**Domain:** Coal Mining

## Features
- Add commodity price volatility modeling
- Comprehensive documentation and examples

## Getting Started

### Installation
```bash
pip install -r requirements.txt
```

### Quick Example
```python
# See examples/ directory for complete examples
```

## Configuration
Detailed configuration options in `config/` directory.

## Testing
```bash
pytest tests/ -v
```

## Edge Cases Handled
- Null/empty input validation
- Boundary condition testing
- Type safety checks

## Contributing
See CONTRIBUTING.md for guidelines.

## License
MIT


## Usage Examples

### Monte Carlo Revenue Simulation

```python
from src.main import MineRevenueForecaster

forecaster = MineRevenueForecaster(
    royalty_rate=0.13,
    mining_cost_usd_t=35.0,
    transport_usd_t=15.0,
)

sim = forecaster.monte_carlo_revenue_simulation(
    production_mt=1_200_000,
    base_price_usd_t=90.0,
    price_volatility_pct=18.0,
    n_simulations=5000,
)

print(f"Expected revenue: ${sim['mean_revenue_usd']:,.0f}")
print(f"P10 (downside):   ${sim['p10_revenue_usd']:,.0f}")
print(f"P90 (upside):     ${sim['p90_revenue_usd']:,.0f}")
print(f"Prob. profitable: {sim['prob_profitable_pct']:.1f}%")
print(f"Break-even price: ${sim['break_even_price_usd_t']:.2f}/t")
```

Refer to the `tests/` directory for comprehensive example implementations.
