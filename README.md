# CAPM Analysis Dashboard

Interactive dashboard for analyzing Cost of Equity using the Capital Asset Pricing Model (CAPM) for Indian IT/ITES companies.

## Features

- **Automated Data Pipeline**: Automatically downloads stock prices, calculates rolling beta, and computes CAPM metrics
- **Interactive Visualizations**: 6 comprehensive charts with real-time filtering
- **Company Analysis**: Infosys, Zensar Technologies, and Coforge
- **Time Period**: 2012-2025 (based on available NIFTY 50 data)

## Installation

1. Install required packages:
```bash
pip install -r requirements.txt
```

2. Ensure the risk-free rate data file exists:
```
data/risk_free_rate.csv
```

## Usage

### Run the Dashboard

Simply execute:
```bash
python visualize.py
```

This will:
1. Run the CAPM pipeline to generate fresh data
2. Load the calculated metrics
3. Start the dashboard server at http://127.0.0.1:8050

### Run Pipeline Only

To generate data without starting the dashboard:
```bash
python src/capm_pipeline.py
```

## Dashboard Features

### Interactive Filters
- **Company Selection**: Choose one or more companies to analyze
- **Time Period**: Adjust the year range using the slider

### Visualizations

1. **Cost of Equity (CAPM)**: Annual cost of equity calculated using CAPM formula
2. **Beta (60-Month Rolling)**: Stock volatility relative to market
3. **Risk-Free Rate**: Annual average 10-Year G-Sec yields
4. **Market Return**: NIFTY 50 annual returns
5. **Equity Risk Premium**: Market return minus risk-free rate
6. **Stock Prices**: Historical adjusted closing prices for all companies

## Project Structure

```
project/
├── data/
│   └── risk_free_rate.csv          # Monthly government bond yields
├── output/
│   ├── raw_data.xlsx               # Raw monthly data (auto-generated)
│   └── capm_master_dataset.xlsx    # Final CAPM calculations (auto-generated)
├── src/
│   ├── capm_pipeline.py            # Data pipeline implementation
│   └── config.py                   # Configuration constants
├── visualize.py                    # Dashboard application
├── requirements.txt                # Python dependencies
└── README.md                       # This file
```

## Data Sources

- **Stock Prices**: Yahoo Finance (yfinance)
- **Market Benchmark**: NIFTY 50 (^NSEI)
- **Risk-Free Rate**: Indian 10-Year Government Security Yields (manual CSV)

## Technical Details

### CAPM Formula
```
Cost of Equity = Risk-Free Rate + Beta × (Market Return - Risk-Free Rate)
```

### Beta Calculation
- 60-month rolling window
- Calculated using pandas rolling covariance and variance
- No regression libraries used

### Data Limitations
- NIFTY 50 data from Yahoo Finance starts September 2007
- First valid beta available: September 2012
- Analysis period: 2012-2025 (14 years)

## Requirements

- Python 3.8+
- pandas >= 2.0.0
- numpy >= 1.24.0
- yfinance >= 0.2.28
- openpyxl >= 3.1.0
- dash >= 2.14.0
- plotly >= 5.18.0

## Troubleshooting

### Dashboard won't start
- Ensure all packages are installed: `pip install -r requirements.txt`
- Check if port 8050 is available
- Verify data files exist in the output folder

### Missing data for 2010-2011
- This is expected due to NIFTY 50 data availability
- 60-month rolling beta requires data from 2005
- NIFTY data only available from September 2007
