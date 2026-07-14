"""
CAPM Pipeline for Indian IT/ITES Companies.

This module implements a complete data pipeline to prepare annual datasets
required to compute the Cost of Equity using the Capital Asset Pricing Model (CAPM).
"""

import pandas as pd
import numpy as np
import yfinance as yf
from pathlib import Path
from typing import Dict, Tuple
import warnings

from config import (
    DOWNLOAD_START_DATE,
    DOWNLOAD_END_DATE,
    ANALYSIS_START_YEAR,
    ANALYSIS_END_YEAR,
    ROLLING_WINDOW,
    COMPANIES,
    MARKET_TICKER,
    MARKET_NAME,
    RISK_FREE_FILE,
    OUTPUT_FOLDER,
    RAW_OUTPUT_FILE,
    MASTER_OUTPUT_FILE,
    DECIMAL_PLACES,
    YFINANCE_INTERVAL,
    YFINANCE_AUTO_ADJUST
)

warnings.filterwarnings('ignore')


def download_prices() -> Dict[str, pd.DataFrame]:
    """
    Download monthly adjusted closing prices for all companies and market index.
    
    Returns:
        Dict[str, pd.DataFrame]: Dictionary mapping ticker symbols to DataFrames
            containing Date index and Adjusted_Close column.
    
    Raises:
        ValueError: If download fails or returns empty data.
    """
    print("Step 1: Downloading monthly adjusted prices...")
    
    # Combine all tickers
    all_tickers = list(COMPANIES.values()) + [MARKET_TICKER]
    
    prices_dict = {}
    
    for ticker in all_tickers:
        print(f"  Downloading {ticker}...")
        try:
            data = yf.download(
                ticker,
                start=DOWNLOAD_START_DATE,
                end=DOWNLOAD_END_DATE,
                interval=YFINANCE_INTERVAL,
                auto_adjust=YFINANCE_AUTO_ADJUST,
                progress=False
            )
            
            if data.empty:
                raise ValueError(f"No data downloaded for {ticker}")
            
            # Extract adjusted close prices
            if 'Close' in data.columns:
                # Handle both single and multi-column DataFrames
                close_data = data['Close']
                if isinstance(close_data, pd.DataFrame):
                    close_data = close_data.iloc[:, 0]
                
                df = pd.DataFrame({
                    'Date': data.index,
                    'Adjusted_Close': close_data.values
                })
            else:
                raise ValueError(f"Close price not found for {ticker}")
            
            df['Date'] = pd.to_datetime(df['Date'])
            df = df.set_index('Date').sort_index()
            
            # Remove duplicates
            df = df[~df.index.duplicated(keep='first')]
            
            prices_dict[ticker] = df
            print(f"    Downloaded {len(df)} records")
            
        except Exception as e:
            raise ValueError(f"Failed to download {ticker}: {str(e)}")
    
    print("  Download complete.\n")
    return prices_dict


def compute_monthly_returns(prices_dict: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
    """
    Compute monthly percentage returns for all securities.
    
    Args:
        prices_dict: Dictionary mapping tickers to price DataFrames.
    
    Returns:
        Dict[str, pd.DataFrame]: Dictionary mapping tickers to DataFrames
            containing Date, Adjusted_Close, and Monthly_Return columns.
    """
    print("Step 2: Computing monthly percentage returns...")
    
    returns_dict = {}
    
    for ticker, df in prices_dict.items():
        df_copy = df.copy()
        
        # Calculate percentage returns
        df_copy['Monthly_Return'] = df_copy['Adjusted_Close'].pct_change()
        
        returns_dict[ticker] = df_copy
        
        valid_returns = df_copy['Monthly_Return'].dropna()
        print(f"  {ticker}: {len(valid_returns)} monthly returns computed")
    
    print("  Monthly returns computation complete.\n")
    return returns_dict


def compute_rolling_beta(
    returns_dict: Dict[str, pd.DataFrame],
    market_ticker: str
) -> Dict[str, pd.DataFrame]:
    """
    Compute 60-month rolling beta for each company against the market.
    
    Args:
        returns_dict: Dictionary mapping tickers to returns DataFrames.
        market_ticker: Ticker symbol for the market benchmark.
    
    Returns:
        Dict[str, pd.DataFrame]: Dictionary mapping company tickers to DataFrames
            containing Date, Monthly_Return, and Rolling_Beta columns.
    """
    print("Step 3: Computing 60-month rolling beta...")
    
    market_returns = returns_dict[market_ticker]['Monthly_Return']
    beta_dict = {}
    
    for company_name, ticker in COMPANIES.items():
        stock_returns = returns_dict[ticker]['Monthly_Return']
        
        # Align the series
        aligned_data = pd.DataFrame({
            'Stock': stock_returns,
            'Market': market_returns
        }).dropna()
        
        # Compute rolling covariance and variance
        rolling_cov = aligned_data['Stock'].rolling(window=ROLLING_WINDOW).cov(aligned_data['Market'])
        rolling_var = aligned_data['Market'].rolling(window=ROLLING_WINDOW).var()
        
        # Calculate beta
        rolling_beta = rolling_cov / rolling_var
        
        # Create result DataFrame
        df_beta = returns_dict[ticker].copy()
        df_beta['Rolling_Beta'] = rolling_beta
        
        beta_dict[ticker] = df_beta
        
        valid_betas = rolling_beta.dropna()
        print(f"  {company_name} ({ticker}): {len(valid_betas)} beta values computed")
    
    print("  Rolling beta computation complete.\n")
    return beta_dict


def prepare_annual_beta(beta_dict: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Extract annual beta values (preferring December) for analysis period.
    
    Args:
        beta_dict: Dictionary mapping tickers to DataFrames with rolling beta.
    
    Returns:
        pd.DataFrame: DataFrame with columns Year, Company, Ticker, Beta.
    """
    print("Step 4: Preparing annual beta values...")
    
    annual_beta_list = []
    
    for company_name, ticker in COMPANIES.items():
        df = beta_dict[ticker].copy()
        
        # Extract year first
        df['Year'] = df.index.year
        
        # Filter to analysis period BEFORE dropping NaN
        # This ensures we check all years in the range
        df = df[(df['Year'] >= ANALYSIS_START_YEAR) & (df['Year'] <= ANALYSIS_END_YEAR)]
        
        # Now drop NaN values
        df = df.dropna(subset=['Rolling_Beta'])
        
        # Group by year and take the last available beta (prefer December)
        annual_beta = df.groupby('Year')['Rolling_Beta'].last().reset_index()
        annual_beta.columns = ['Year', 'Beta']
        annual_beta['Company'] = company_name
        annual_beta['Ticker'] = ticker
        
        annual_beta_list.append(annual_beta)
        print(f"  {company_name}: {len(annual_beta)} annual beta values")
    
    # Combine all companies
    annual_beta_df = pd.concat(annual_beta_list, ignore_index=True)
    annual_beta_df = annual_beta_df[['Year', 'Company', 'Ticker', 'Beta']]
    
    print("  Annual beta preparation complete.\n")
    return annual_beta_df


def compute_annual_market_return(returns_dict: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Compute annual market returns using year-end prices.
    
    Args:
        returns_dict: Dictionary mapping tickers to returns DataFrames.
    
    Returns:
        pd.DataFrame: DataFrame with columns Year, Market_Return.
    """
    print("Step 5: Computing annual market returns...")
    
    market_df = returns_dict[MARKET_TICKER].copy()
    
    # Extract year
    market_df['Year'] = market_df.index.year
    
    # Get year-end prices (last available price for each year)
    year_end_prices = market_df.groupby('Year')['Adjusted_Close'].last()
    
    # Compute annual returns
    annual_returns = year_end_prices.pct_change()
    
    # Create DataFrame
    market_return_df = pd.DataFrame({
        'Year': annual_returns.index,
        'Market_Return': annual_returns.values
    })
    
    # Filter to analysis period (need previous year for first return)
    market_return_df = market_return_df[
        (market_return_df['Year'] >= ANALYSIS_START_YEAR) & 
        (market_return_df['Year'] <= ANALYSIS_END_YEAR)
    ]
    
    print(f"  Computed {len(market_return_df)} annual market returns")
    print("  Annual market return computation complete.\n")
    return market_return_df


def compute_annual_stock_returns(returns_dict: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Compute annual stock returns using year-end prices for all companies.
    
    Args:
        returns_dict: Dictionary mapping tickers to returns DataFrames.
    
    Returns:
        pd.DataFrame: DataFrame with columns Year, Company, Ticker, Annual_Stock_Return.
    """
    print("Step 6: Computing annual stock returns...")
    
    annual_stock_returns_list = []
    
    for company_name, ticker in COMPANIES.items():
        df = returns_dict[ticker].copy()
        
        # Extract year
        df['Year'] = df.index.year
        
        # Get year-end prices
        year_end_prices = df.groupby('Year')['Adjusted_Close'].last()
        
        # Compute annual returns
        annual_returns = year_end_prices.pct_change()
        
        # Create DataFrame
        stock_return_df = pd.DataFrame({
            'Year': annual_returns.index,
            'Annual_Stock_Return': annual_returns.values
        })
        
        # Filter to analysis period
        stock_return_df = stock_return_df[
            (stock_return_df['Year'] >= ANALYSIS_START_YEAR) & 
            (stock_return_df['Year'] <= ANALYSIS_END_YEAR)
        ]
        
        stock_return_df['Company'] = company_name
        stock_return_df['Ticker'] = ticker
        
        annual_stock_returns_list.append(stock_return_df)
        print(f"  {company_name}: {len(stock_return_df)} annual returns")
    
    # Combine all companies
    annual_stock_returns_df = pd.concat(annual_stock_returns_list, ignore_index=True)
    annual_stock_returns_df = annual_stock_returns_df[
        ['Year', 'Company', 'Ticker', 'Annual_Stock_Return']
    ]
    
    print("  Annual stock returns computation complete.\n")
    return annual_stock_returns_df


def load_risk_free_rate() -> pd.DataFrame:
    """
    Load monthly risk-free rate data from CSV and compute annual averages.
    
    The CSV file contains monthly Indian 10-Year Government Security Yields.
    This function loads the monthly data, parses dates, and calculates the
    annual average yield for each year in the analysis period.
    
    Returns:
        pd.DataFrame: DataFrame with columns Year, Risk_Free_Rate (annual average).
    
    Raises:
        FileNotFoundError: If risk_free_rate.csv does not exist.
        ValueError: If required columns are missing or data is invalid.
    """
    print("Step 7: Loading monthly risk-free rate data...")
    
    # Check if file exists
    if not RISK_FREE_FILE.exists():
        raise FileNotFoundError(
            f"Risk-free rate file not found: {RISK_FREE_FILE}\n"
            f"Please ensure 'risk_free_rate.csv' exists in the 'data' folder."
        )
    
    # Load CSV
    try:
        rf_df = pd.read_csv(RISK_FREE_FILE)
    except Exception as e:
        raise ValueError(f"Failed to read risk-free rate file: {str(e)}")
    
    # Validate required columns
    required_columns = ['Year', 'Risk_Free_Rate']
    missing_columns = [col for col in required_columns if col not in rf_df.columns]
    
    if missing_columns:
        raise ValueError(
            f"Missing required columns in risk-free rate file: {missing_columns}\n"
            f"Expected columns: {required_columns}\n"
            f"Found columns: {list(rf_df.columns)}"
        )
    
    # Parse the date column (format: MM-DD-YYYY)
    try:
        rf_df['Date'] = pd.to_datetime(rf_df['Year'], format='%m-%d-%Y')
    except Exception as e:
        raise ValueError(
            f"Failed to parse 'Year' column as date (expected format: MM-DD-YYYY): {str(e)}"
        )
    
    # Validate numeric values for Risk_Free_Rate
    if not pd.api.types.is_numeric_dtype(rf_df['Risk_Free_Rate']):
        raise ValueError("'Risk_Free_Rate' column must contain numeric values")
    
    # Convert percentage to decimal (e.g., 7.95 -> 0.0795)
    rf_df['Risk_Free_Rate'] = rf_df['Risk_Free_Rate'] / 100.0
    
    # Extract year from date
    rf_df['Year'] = rf_df['Date'].dt.year
    
    # Calculate annual average risk-free rate
    annual_rf = rf_df.groupby('Year')['Risk_Free_Rate'].mean().reset_index()
    annual_rf.columns = ['Year', 'Risk_Free_Rate']
    
    # Filter to analysis period
    annual_rf = annual_rf[
        (annual_rf['Year'] >= ANALYSIS_START_YEAR) & 
        (annual_rf['Year'] <= ANALYSIS_END_YEAR)
    ].copy()
    
    # Validate required years are present
    required_years = set(range(ANALYSIS_START_YEAR, ANALYSIS_END_YEAR + 1))
    available_years = set(annual_rf['Year'].astype(int))
    missing_years = required_years - available_years
    
    if missing_years:
        raise ValueError(
            f"Missing required years in risk-free rate data: {sorted(missing_years)}\n"
            f"Required years: {ANALYSIS_START_YEAR}-{ANALYSIS_END_YEAR}"
        )
    
    # Sort by year
    annual_rf = annual_rf.sort_values('Year').reset_index(drop=True)
    
    print(f"  Loaded monthly data and computed {len(annual_rf)} annual average yields")
    print("  Risk-free rate data loaded and validated.\n")
    return annual_rf


def compute_capm(
    annual_beta_df: pd.DataFrame,
    market_return_df: pd.DataFrame,
    risk_free_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Compute Equity Risk Premium and Cost of Equity using CAPM.
    
    Args:
        annual_beta_df: DataFrame with Year, Company, Ticker, Beta.
        market_return_df: DataFrame with Year, Market_Return.
        risk_free_df: DataFrame with Year, Risk_Free_Rate.
    
    Returns:
        pd.DataFrame: DataFrame with Year, Company, Ticker, Beta,
            Market_Return, Risk_Free_Rate, Equity_Risk_Premium, Cost_of_Equity.
    """
    print("Step 8: Computing CAPM (Cost of Equity)...")
    
    # Merge beta with market returns
    capm_df = annual_beta_df.merge(market_return_df, on='Year', how='left')
    
    # Merge with risk-free rate
    capm_df = capm_df.merge(risk_free_df, on='Year', how='left')
    
    # Compute Equity Risk Premium
    capm_df['Equity_Risk_Premium'] = capm_df['Market_Return'] - capm_df['Risk_Free_Rate']
    
    # Compute Cost of Equity: Rf + Beta * (Rm - Rf)
    capm_df['Cost_of_Equity'] = (
        capm_df['Risk_Free_Rate'] + 
        capm_df['Beta'] * capm_df['Equity_Risk_Premium']
    )
    
    # Validate no missing values
    missing_cols = capm_df.columns[capm_df.isnull().any()].tolist()
    if missing_cols:
        raise ValueError(
            f"Missing values detected in CAPM computation for columns: {missing_cols}\n"
            f"Please check input data integrity."
        )
    
    print(f"  Computed CAPM for {len(capm_df)} company-year observations")
    print("  CAPM computation complete.\n")
    return capm_df


def build_master_dataframe(
    capm_df: pd.DataFrame,
    annual_stock_returns_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Build the final tidy master annual dataframe.
    
    Args:
        capm_df: DataFrame with CAPM calculations.
        annual_stock_returns_df: DataFrame with annual stock returns.
    
    Returns:
        pd.DataFrame: Master dataframe with all annual metrics, sorted by Year and Company.
    """
    print("Step 9: Building master annual dataframe...")
    
    # Merge CAPM with stock returns
    master_df = capm_df.merge(
        annual_stock_returns_df[['Year', 'Company', 'Annual_Stock_Return']],
        on=['Year', 'Company'],
        how='left'
    )
    
    # Reorder columns
    master_df = master_df[[
        'Year',
        'Company',
        'Ticker',
        'Annual_Stock_Return',
        'Market_Return',
        'Risk_Free_Rate',
        'Equity_Risk_Premium',
        'Beta',
        'Cost_of_Equity'
    ]]
    
    # Round numeric columns
    numeric_columns = [
        'Annual_Stock_Return',
        'Market_Return',
        'Beta',
        'Equity_Risk_Premium',
        'Cost_of_Equity'
    ]
    
    for col in numeric_columns:
        master_df[col] = master_df[col].round(DECIMAL_PLACES)
    
    # Sort by Year and Company
    master_df = master_df.sort_values(['Year', 'Company']).reset_index(drop=True)
    
    # Validate expected row count
    expected_rows = len(COMPANIES) * (ANALYSIS_END_YEAR - ANALYSIS_START_YEAR + 1)
    actual_rows = len(master_df)
    
    if actual_rows != expected_rows:
        print(f"  WARNING: Expected {expected_rows} rows, got {actual_rows} rows")
    else:
        print(f"  Master dataframe created with {actual_rows} rows (as expected)")
    
    print("  Master dataframe build complete.\n")
    return master_df


def export_raw_data(
    returns_dict: Dict[str, pd.DataFrame],
    risk_free_df: pd.DataFrame
) -> None:
    """
    Export raw monthly data to Excel workbook with multiple sheets.
    
    Args:
        returns_dict: Dictionary mapping tickers to returns DataFrames.
        risk_free_df: DataFrame with annual average risk-free rate data.
    """
    print("Step 10: Exporting raw data workbook...")
    
    # Ensure output directory exists
    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
    
    # Load original monthly risk-free rate for export
    try:
        rf_monthly = pd.read_csv(RISK_FREE_FILE)
        rf_monthly['Date'] = pd.to_datetime(rf_monthly['Year'], format='%m-%d-%Y')
        rf_monthly['Risk_Free_Rate_Percent'] = rf_monthly['Risk_Free_Rate']
        rf_monthly = rf_monthly[['Date', 'Risk_Free_Rate_Percent']].sort_values('Date')
    except Exception as e:
        print(f"  Warning: Could not load monthly risk-free data: {str(e)}")
        rf_monthly = None
    
    with pd.ExcelWriter(RAW_OUTPUT_FILE, engine='openpyxl') as writer:
        # Export each company's monthly data
        for company_name, ticker in COMPANIES.items():
            df = returns_dict[ticker].copy()
            df = df.reset_index()
            df = df[['Date', 'Adjusted_Close', 'Monthly_Return']]
            
            # Sort chronologically
            df = df.sort_values('Date')
            
            # Remove duplicates
            df = df.drop_duplicates(subset=['Date'], keep='first')
            
            sheet_name = f"{company_name}_Monthly"
            df.to_excel(writer, sheet_name=sheet_name, index=False)
            print(f"  Exported sheet: {sheet_name} ({len(df)} rows)")
        
        # Export NIFTY50 monthly data
        nifty_df = returns_dict[MARKET_TICKER].copy()
        nifty_df = nifty_df.reset_index()
        nifty_df = nifty_df[['Date', 'Adjusted_Close', 'Monthly_Return']]
        nifty_df = nifty_df.sort_values('Date')
        nifty_df = nifty_df.drop_duplicates(subset=['Date'], keep='first')
        
        nifty_df.to_excel(writer, sheet_name='NIFTY50_Monthly', index=False)
        print(f"  Exported sheet: NIFTY50_Monthly ({len(nifty_df)} rows)")
        
        # Export monthly risk-free rate (original data)
        if rf_monthly is not None:
            rf_monthly.to_excel(writer, sheet_name='Risk_Free_Rate_Monthly', index=False)
            print(f"  Exported sheet: Risk_Free_Rate_Monthly ({len(rf_monthly)} rows)")
        
        # Export annual average risk-free rate
        risk_free_df.to_excel(writer, sheet_name='Risk_Free_Rate_Annual', index=False)
        print(f"  Exported sheet: Risk_Free_Rate_Annual ({len(risk_free_df)} rows)")
    
    print(f"  Raw data workbook saved: {RAW_OUTPUT_FILE}\n")


def export_master_dataset(master_df: pd.DataFrame) -> None:
    """
    Export final master dataset to Excel workbook.
    
    Args:
        master_df: Master dataframe with all annual CAPM calculations.
    """
    print("Step 11: Exporting master dataset workbook...")
    
    # Ensure output directory exists
    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
    
    with pd.ExcelWriter(MASTER_OUTPUT_FILE, engine='openpyxl') as writer:
        master_df.to_excel(writer, sheet_name='CAPM_Master', index=False)
    
    print(f"  Master dataset saved: {MASTER_OUTPUT_FILE}")
    print(f"  Total rows: {len(master_df)}\n")


def main() -> None:
    """
    Main execution function for the CAPM pipeline.
    
    Orchestrates the complete data pipeline from download to export.
    """
    print("=" * 80)
    print("CAPM PIPELINE - Indian IT/ITES Companies")
    print("=" * 80)
    print()
    
    try:
        # Step 1: Download prices
        prices_dict = download_prices()
        
        # Step 2: Compute monthly returns
        returns_dict = compute_monthly_returns(prices_dict)
        
        # Step 3: Compute rolling beta
        beta_dict = compute_rolling_beta(returns_dict, MARKET_TICKER)
        
        # Step 4: Prepare annual beta
        annual_beta_df = prepare_annual_beta(beta_dict)
        
        # Step 5: Compute annual market return
        market_return_df = compute_annual_market_return(returns_dict)
        
        # Step 6: Compute annual stock returns
        annual_stock_returns_df = compute_annual_stock_returns(returns_dict)
        
        # Step 7: Load risk-free rate
        risk_free_df = load_risk_free_rate()
        
        # Step 8: Compute CAPM
        capm_df = compute_capm(annual_beta_df, market_return_df, risk_free_df)
        
        # Step 9: Build master dataframe
        master_df = build_master_dataframe(capm_df, annual_stock_returns_df)
        
        # Step 10: Export raw data
        export_raw_data(returns_dict, risk_free_df)
        
        # Step 11: Export master dataset
        export_master_dataset(master_df)
        
        print("=" * 80)
        print("PIPELINE EXECUTION COMPLETE")
        print("=" * 80)
        print()
        print("Generated files:")
        print(f"  1. {RAW_OUTPUT_FILE}")
        print(f"  2. {MASTER_OUTPUT_FILE}")
        print()
        print("Master dataset summary:")
        print(f"  Companies: {len(COMPANIES)}")
        print(f"  Years: {ANALYSIS_START_YEAR}-{ANALYSIS_END_YEAR}")
        print(f"  Total observations: {len(master_df)}")
        print()
        
    except Exception as e:
        print()
        print("=" * 80)
        print("PIPELINE EXECUTION FAILED")
        print("=" * 80)
        print(f"Error: {str(e)}")
        print()
        raise


if __name__ == "__main__":
    main()
