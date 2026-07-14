"""
Configuration file for CAPM Pipeline.

This module contains all configurable constants used throughout the project.
"""

from pathlib import Path

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent

# Date ranges
DOWNLOAD_START_DATE = "2005-01-01"
DOWNLOAD_END_DATE = "2026-01-31"
ANALYSIS_START_YEAR = 2010
ANALYSIS_END_YEAR = 2025

# Rolling window for beta calculation (in months)
ROLLING_WINDOW = 60

# Companies configuration
COMPANIES = {
    "Infosys": "INFY.NS",
    "Zensar": "ZENSARTECH.NS",
    "Coforge": "COFORGE.NS"
}

# Market benchmark
MARKET_TICKER = "^NSEI"
MARKET_NAME = "NIFTY50"

# File paths
DATA_FOLDER = PROJECT_ROOT / "data"
OUTPUT_FOLDER = PROJECT_ROOT / "output"
RISK_FREE_FILE = DATA_FOLDER / "risk_free_rate.csv"
RAW_OUTPUT_FILE = OUTPUT_FOLDER / "raw_data.xlsx"
MASTER_OUTPUT_FILE = OUTPUT_FOLDER / "capm_master_dataset.xlsx"

# Rounding precision
DECIMAL_PLACES = 6

# yfinance download settings
YFINANCE_INTERVAL = "1mo"
YFINANCE_AUTO_ADJUST = True
