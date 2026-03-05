# Mine Revenue Forecaster

Coal mining revenue projection model with price sensitivity and break-even analysis.

## Features
- Revenue, royalty, opex, and net margin calculation
- Break-even price computation
- Price sensitivity table across configurable price range
- Configurable royalty rate (default 13% — Indonesian PKP2B standard)
- Monthly production plan ingestion (CSV/Excel)

## Quick Start

```python
from src.main import RevenueForecaster
import pandas as pd

fc = RevenueForecaster(config={
    "royalty_rate": 0.13,
    "transport_usd_t": 8.0,
    "mining_cost_usd_t": 22.0,
})

df = pd.read_csv("sample_data/production_plan.csv")
result = fc.forecast_revenue(df, price_usd_t=87.0)

print(f"Total Volume:    {result['total_volume_mt']:,.0f} MT")
print(f"Gross Revenue:   USD {result['gross_revenue_usd']:,.0f}")
print(f"Net Revenue:     USD {result['net_revenue_usd']:,.0f}")
print(f"EBITDA Margin:   {result['ebitda_margin_pct']:.1f}%")
print(f"Break-even Price: USD {result['break_even_price_usd_t']:.2f}/t")

# Price sensitivity
sensitivity = fc.price_sensitivity(df, price_range=[60, 70, 80, 90, 100, 110])
print(sensitivity[["price_usd_t", "net_revenue_usd", "ebitda_margin_pct", "profitable"]])
```

## Running Tests
```bash
pytest tests/ -v
```

---

## [v1.3.0] Quarterly Projection & Scenario Comparison

```python
# Quarterly P&L projection
quarters = fc.quarterly_projection(prod_df, price_usd_t=85.0)
print(quarters[["quarter", "volume_mt", "gross_revenue_usd", "net_revenue_usd", "ebitda_margin_pct"]])
#   quarter  volume_mt  gross_revenue_usd  net_revenue_usd  ebitda_margin_pct
#        Q1   131250.0       11156250.0       4568812.5              40.95
#        Q2   131250.0       11156250.0       4568812.5              40.95

# Side-by-side scenario comparison
scenarios = fc.scenario_comparison(prod_df)
print(scenarios[["scenario", "price_usd_t", "net_revenue_usd", "ebitda_margin_pct", "profitable"]])
#     scenario  price_usd_t  net_revenue_usd  ebitda_margin_pct  profitable
#   Bear Case          65.0       4875000.0              18.75        True
#   Base Case          85.0      12750000.0              37.50        True
#   Bull Case         110.0      24375000.0              55.11        True
```
