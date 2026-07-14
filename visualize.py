"""
CAPM Dashboard - Interactive Visualization

This module creates an interactive Dash dashboard to visualize CAPM analysis results
for Indian IT/ITES companies. It automatically runs the data pipeline before displaying
the dashboard.
"""

import subprocess
import sys
from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output, callback
import dash_bootstrap_components as dbc

# Project paths
PROJECT_ROOT = Path(__file__).parent
PIPELINE_SCRIPT = PROJECT_ROOT / "src" / "capm_pipeline.py"
MASTER_DATA_FILE = PROJECT_ROOT / "output" / "capm_master_dataset.xlsx"
RAW_DATA_FILE = PROJECT_ROOT / "output" / "raw_data.xlsx"

# Color palette for consistent styling
COLORS = {
    'primary': '#1f77b4',
    'secondary': '#ff7f0e',
    'success': '#2ca02c',
    'danger': '#d62728',
    'warning': '#ff9800',
    'info': '#17a2b8',
    'dark': '#2c3e50',
    'light': '#ecf0f1',
    'background': '#ffffff',
    'text': '#2c3e50',
    'Infosys': '#1f77b4',
    'Zensar': '#ff7f0e',
    'Coforge': '#2ca02c'
}


def run_pipeline():
    """
    Execute the CAPM pipeline to generate fresh data.
    
    Raises:
        RuntimeError: If pipeline execution fails.
    """
    print("=" * 80)
    print("Running CAPM Pipeline...")
    print("=" * 80)
    
    try:
        result = subprocess.run(
            [sys.executable, str(PIPELINE_SCRIPT)],
            capture_output=True,
            text=True,
            check=True
        )
        print(result.stdout)
        print("\n[SUCCESS] Pipeline completed successfully!\n")
    except subprocess.CalledProcessError as e:
        print(f"\n[ERROR] Pipeline failed with error:\n{e.stderr}")
        raise RuntimeError(f"Pipeline execution failed: {e.stderr}")


def load_data():
    """
    Load CAPM master dataset and raw stock price data.
    
    Returns:
        tuple: (master_df, stock_prices_df) containing CAPM data and stock prices.
    
    Raises:
        FileNotFoundError: If data files don't exist.
    """
    if not MASTER_DATA_FILE.exists():
        raise FileNotFoundError(
            f"Master dataset not found: {MASTER_DATA_FILE}\n"
            f"Please run the pipeline first."
        )
    
    # Load CAPM master data
    master_df = pd.read_excel(MASTER_DATA_FILE, sheet_name='CAPM_Master')
    
    # Load stock prices from raw data
    stock_prices = {}
    with pd.ExcelFile(RAW_DATA_FILE) as xls:
        for company in master_df['Company'].unique():
            sheet_name = f"{company}_Monthly"
            if sheet_name in xls.sheet_names:
                df = pd.read_excel(xls, sheet_name=sheet_name)
                df['Date'] = pd.to_datetime(df['Date'])
                df['Company'] = company
                stock_prices[company] = df
    
    # Combine all stock prices
    stock_prices_df = pd.concat(stock_prices.values(), ignore_index=True)
    
    return master_df, stock_prices_df


def create_line_chart(df, x, y, color, title, yaxis_title):
    """
    Create a styled line chart with consistent formatting.
    
    Args:
        df: DataFrame containing the data.
        x: Column name for x-axis.
        y: Column name for y-axis.
        color: Column name for color grouping.
        title: Chart title.
        yaxis_title: Y-axis label.
    
    Returns:
        plotly.graph_objects.Figure: Configured line chart.
    """
    fig = px.line(
        df,
        x=x,
        y=y,
        color=color,
        title=title,
        markers=True,
        color_discrete_map=COLORS
    )
    
    fig.update_layout(
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(color=COLORS['text'], size=12),
        title_font=dict(size=16, color=COLORS['dark']),
        xaxis=dict(
            showgrid=True,
            gridcolor='#e0e0e0',
            title_font=dict(size=14)
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor='#e0e0e0',
            title=yaxis_title,
            title_font=dict(size=14)
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        hovermode='x unified'
    )
    
    return fig


def create_dashboard(master_df, stock_prices_df):
    """
    Create and configure the Dash dashboard.
    
    Args:
        master_df: DataFrame with CAPM calculations.
        stock_prices_df: DataFrame with stock price history.
    
    Returns:
        Dash: Configured Dash application.
    """
    # Initialize Dash app with Bootstrap theme
    app = Dash(
        __name__,
        external_stylesheets=[dbc.themes.BOOTSTRAP],
        suppress_callback_exceptions=True
    )
    
    # Get available companies and years
    companies = sorted(master_df['Company'].unique())
    years = sorted([int(y) for y in master_df['Year'].unique()])
    min_year, max_year = int(min(years)), int(max(years))
    
    # Dashboard layout
    app.layout = dbc.Container([
        # Header
        dbc.Row([
            dbc.Col([
                html.H1(
                    "CAPM Analysis Dashboard",
                    className="text-center mb-2",
                    style={'color': COLORS['dark'], 'fontWeight': 'bold'}
                ),
                html.H5(
                    "Indian IT/ITES Companies - Cost of Equity Analysis",
                    className="text-center mb-4",
                    style={'color': COLORS['info']}
                )
            ])
        ]),
        
        # Filters
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.Label("Select Companies:", style={'fontWeight': 'bold'}),
                        dcc.Checklist(
                            id='company-filter',
                            options=[{'label': c, 'value': c} for c in companies],
                            value=companies,
                            inline=True,
                            style={'marginBottom': '15px'}
                        ),
                        html.Label("Select Time Period:", style={'fontWeight': 'bold'}),
                        dcc.RangeSlider(
                            id='year-filter',
                            min=int(min_year),
                            max=int(max_year),
                            value=[int(min_year), int(max_year)],
                            marks={int(year): str(year) for year in years},
                            step=1,
                            tooltip={"placement": "bottom", "always_visible": True}
                        )
                    ])
                ], className="mb-4")
            ])
        ]),
        
        # Charts Row 1: Cost of Equity (full width)
        dbc.Row([
            dbc.Col([
                dcc.Graph(id='cost-of-equity-chart')
            ], width=12)
        ], className="mb-4"),
        
        # Charts Row 2: Risk-Free Rate vs Cost of Equity and Market Return vs Cost of Equity
        dbc.Row([
            dbc.Col([
                dcc.Graph(id='rf-vs-coe-chart')
            ], width=6),
            dbc.Col([
                dcc.Graph(id='mr-vs-coe-chart')
            ], width=6)
        ], className="mb-4"),
        
        # Charts Row 3: Beta
        dbc.Row([
            dbc.Col([
                dcc.Graph(id='beta-chart')
            ], width=12)
        ], className="mb-4"),
        
        # Charts Row 4: Risk-Free Rate and Market Return
        dbc.Row([
            dbc.Col([
                dcc.Graph(id='risk-free-rate-chart')
            ], width=6),
            dbc.Col([
                dcc.Graph(id='market-return-chart')
            ], width=6)
        ], className="mb-4"),
        
        # Charts Row 5: Equity Risk Premium and Stock Prices
        dbc.Row([
            dbc.Col([
                dcc.Graph(id='equity-risk-premium-chart')
            ], width=6),
            dbc.Col([
                dcc.Graph(id='stock-prices-chart')
            ], width=6)
        ], className="mb-4"),
        
        # Charts Row 6: Beta vs Cost of Equity (with year selector)
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.Label("Select Year for Beta vs Cost of Equity:", style={'fontWeight': 'bold', 'marginBottom': '10px'}),
                        dcc.Dropdown(
                            id='beta-coe-year-filter',
                            options=[{'label': str(year), 'value': year} for year in years if year >= 2012],
                            value=max([year for year in years if year >= 2012]),
                            clearable=False,
                            style={'width': '200px'}
                        )
                    ])
                ], className="mb-3")
            ], width=12)
        ]),
        dbc.Row([
            dbc.Col([
                dcc.Graph(id='beta-vs-coe-chart')
            ], width=12)
        ], className="mb-4"),
        
        # Footer
        dbc.Row([
            dbc.Col([
                html.Hr(),
                html.P(
                    "Data Source: Yahoo Finance | Analysis Period: 2010-2025",
                    className="text-center text-muted",
                    style={'fontSize': '12px'}
                )
            ])
        ])
    ], fluid=True, style={'backgroundColor': COLORS['light'], 'padding': '20px'})
    
    # Callbacks for interactive filtering
    @app.callback(
        [
            Output('cost-of-equity-chart', 'figure'),
            Output('rf-vs-coe-chart', 'figure'),
            Output('mr-vs-coe-chart', 'figure'),
            Output('beta-chart', 'figure'),
            Output('risk-free-rate-chart', 'figure'),
            Output('market-return-chart', 'figure'),
            Output('equity-risk-premium-chart', 'figure'),
            Output('stock-prices-chart', 'figure')
        ],
        [
            Input('company-filter', 'value'),
            Input('year-filter', 'value')
        ]
    )
    def update_charts(selected_companies, year_range):
        """Update all charts based on filter selections."""
        # Filter master data
        filtered_df = master_df[
            (master_df['Company'].isin(selected_companies)) &
            (master_df['Year'] >= year_range[0]) &
            (master_df['Year'] <= year_range[1])
        ]
        
        # Filter stock prices
        filtered_prices = stock_prices_df[
            (stock_prices_df['Company'].isin(selected_companies)) &
            (stock_prices_df['Date'].dt.year >= year_range[0]) &
            (stock_prices_df['Date'].dt.year <= year_range[1])
        ]
        
        # Cost of Equity Chart
        fig_coe = create_line_chart(
            filtered_df,
            x='Year',
            y='Cost_of_Equity',
            color='Company',
            title='Cost of Equity (CAPM)',
            yaxis_title='Cost of Equity'
        )
        fig_coe.update_yaxes(tickformat='.2%')
        
        # Risk-Free Rate vs Cost of Equity Chart
        fig_rf_vs_coe = go.Figure()
        
        # Add Risk-Free Rate line (only once, same for all companies)
        if len(selected_companies) > 0:
            first_company_data = filtered_df[filtered_df['Company'] == selected_companies[0]]
            fig_rf_vs_coe.add_trace(go.Scatter(
                x=first_company_data['Year'],
                y=first_company_data['Risk_Free_Rate'],
                mode='lines+markers',
                name='Risk-Free Rate',
                line=dict(color='#808080', dash='dash', width=2),
                legendgroup='rf'
            ))
        
        # Add Cost of Equity lines for each company
        for company in selected_companies:
            company_data = filtered_df[filtered_df['Company'] == company]
            fig_rf_vs_coe.add_trace(go.Scatter(
                x=company_data['Year'],
                y=company_data['Cost_of_Equity'],
                mode='lines+markers',
                name=f'{company} - Cost of Equity',
                line=dict(color=COLORS.get(company, COLORS['primary'])),
                legendgroup=company
            ))
        
        fig_rf_vs_coe.update_layout(
            title='Risk-Free Rate vs Cost of Equity',
            plot_bgcolor='white',
            paper_bgcolor='white',
            font=dict(color=COLORS['text'], size=12),
            title_font=dict(size=16, color=COLORS['dark']),
            xaxis=dict(
                showgrid=True,
                gridcolor='#e0e0e0',
                title='Year',
                title_font=dict(size=14)
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor='#e0e0e0',
                title='Rate',
                title_font=dict(size=14),
                tickformat='.2%'
            ),
            legend=dict(
                orientation="v",
                yanchor="top",
                y=1,
                xanchor="left",
                x=1.02
            ),
            hovermode='x unified'
        )
        
        # Market Return vs Cost of Equity Chart
        fig_mr_vs_coe = go.Figure()
        
        # Add Market Return line (only once, same for all companies)
        if len(selected_companies) > 0:
            first_company_data = filtered_df[filtered_df['Company'] == selected_companies[0]]
            fig_mr_vs_coe.add_trace(go.Scatter(
                x=first_company_data['Year'],
                y=first_company_data['Market_Return'],
                mode='lines+markers',
                name='Market Return (NIFTY 50)',
                line=dict(color='#808080', dash='dash', width=2),
                legendgroup='mr'
            ))
        
        # Add Cost of Equity lines for each company
        for company in selected_companies:
            company_data = filtered_df[filtered_df['Company'] == company]
            fig_mr_vs_coe.add_trace(go.Scatter(
                x=company_data['Year'],
                y=company_data['Cost_of_Equity'],
                mode='lines+markers',
                name=f'{company} - Cost of Equity',
                line=dict(color=COLORS.get(company, COLORS['primary'])),
                legendgroup=company
            ))
        
        fig_mr_vs_coe.update_layout(
            title='Market Return vs Cost of Equity',
            plot_bgcolor='white',
            paper_bgcolor='white',
            font=dict(color=COLORS['text'], size=12),
            title_font=dict(size=16, color=COLORS['dark']),
            xaxis=dict(
                showgrid=True,
                gridcolor='#e0e0e0',
                title='Year',
                title_font=dict(size=14)
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor='#e0e0e0',
                title='Return',
                title_font=dict(size=14),
                tickformat='.2%'
            ),
            legend=dict(
                orientation="v",
                yanchor="top",
                y=1,
                xanchor="left",
                x=1.02
            ),
            hovermode='x unified'
        )
        
        # Beta Chart
        fig_beta = create_line_chart(
            filtered_df,
            x='Year',
            y='Beta',
            color='Company',
            title='Beta (60-Month Rolling)',
            yaxis_title='Beta'
        )
        
        # Risk-Free Rate Chart
        fig_rf = create_line_chart(
            filtered_df,
            x='Year',
            y='Risk_Free_Rate',
            color='Company',
            title='Risk-Free Rate (10-Year G-Sec)',
            yaxis_title='Risk-Free Rate'
        )
        fig_rf.update_yaxes(tickformat='.2%')
        
        # Market Return Chart
        fig_market = create_line_chart(
            filtered_df,
            x='Year',
            y='Market_Return',
            color='Company',
            title='Market Return (NIFTY 50)',
            yaxis_title='Market Return'
        )
        fig_market.update_yaxes(tickformat='.2%')
        
        # Equity Risk Premium Chart
        fig_erp = create_line_chart(
            filtered_df,
            x='Year',
            y='Equity_Risk_Premium',
            color='Company',
            title='Equity Risk Premium',
            yaxis_title='Equity Risk Premium'
        )
        fig_erp.update_yaxes(tickformat='.2%')
        
        # Stock Prices Chart
        fig_prices = px.line(
            filtered_prices,
            x='Date',
            y='Adjusted_Close',
            color='Company',
            title='Stock Prices (Adjusted Close)',
            markers=False,
            color_discrete_map=COLORS
        )
        
        fig_prices.update_layout(
            plot_bgcolor='white',
            paper_bgcolor='white',
            font=dict(color=COLORS['text'], size=12),
            title_font=dict(size=16, color=COLORS['dark']),
            xaxis=dict(
                showgrid=True,
                gridcolor='#e0e0e0',
                title='Date',
                title_font=dict(size=14)
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor='#e0e0e0',
                title='Price (INR)',
                title_font=dict(size=14)
            ),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            hovermode='x unified'
        )
        
        return fig_coe, fig_rf_vs_coe, fig_mr_vs_coe, fig_beta, fig_rf, fig_market, fig_erp, fig_prices
    
    # Callback for Beta vs Cost of Equity chart
    @app.callback(
        Output('beta-vs-coe-chart', 'figure'),
        [
            Input('company-filter', 'value'),
            Input('beta-coe-year-filter', 'value')
        ]
    )
    def update_beta_vs_coe_chart(selected_companies, selected_year):
        """Update Beta vs Cost of Equity chart for selected year with SML."""
        # Ensure selected_year is integer
        selected_year = int(selected_year)
        
        # Filter data for selected year and companies
        year_data = master_df[
            (master_df['Company'].isin(selected_companies)) &
            (master_df['Year'] == selected_year)
        ]
        
        # Create scatter plot
        fig = go.Figure()
        
        # Get Risk-Free Rate and Market Return for the selected year
        if not year_data.empty:
            rf = year_data['Risk_Free_Rate'].iloc[0]
            rm = year_data['Market_Return'].iloc[0]
            
            # Calculate SML line: Expected Return = Rf + Beta * (Rm - Rf)
            # Create beta range from 0 to max beta + 0.5
            max_beta = year_data['Beta'].max()
            beta_range = [0, max_beta + 0.5]
            sml_returns = [rf + beta * (rm - rf) for beta in beta_range]
            
            # Add SML line
            fig.add_trace(go.Scatter(
                x=beta_range,
                y=sml_returns,
                mode='lines',
                name='SML (Security Market Line)',
                line=dict(color='red', width=3, dash='solid'),
                hovertemplate='<b>SML</b><br>Beta: %{x:.2f}<br>Expected Return: %{y:.2%}<extra></extra>'
            ))
        
        # Add data points for each company
        for company in selected_companies:
            company_data = year_data[year_data['Company'] == company]
            if not company_data.empty:
                beta_val = company_data['Beta'].iloc[0]
                coe_val = company_data['Cost_of_Equity'].iloc[0]
                
                fig.add_trace(go.Scatter(
                    x=[beta_val],
                    y=[coe_val],
                    mode='markers+text',
                    name=company,
                    marker=dict(
                        size=20,
                        color=COLORS.get(company, COLORS['primary']),
                        line=dict(width=2, color='white')
                    ),
                    text=[company],
                    textposition='top center',
                    textfont=dict(size=14, color=COLORS['dark'], family='Arial Black'),
                    hovertemplate=f'<b>{company}</b><br>Beta: {beta_val:.4f}<br>Cost of Equity: {coe_val:.2%}<extra></extra>'
                ))
        
        fig.update_layout(
            title=f'Beta vs Cost of Equity ({selected_year})',
            plot_bgcolor='white',
            paper_bgcolor='white',
            font=dict(color=COLORS['text'], size=12),
            title_font=dict(size=16, color=COLORS['dark']),
            xaxis=dict(
                showgrid=True,
                gridcolor='#e0e0e0',
                title='Beta',
                title_font=dict(size=14),
                zeroline=True,
                zerolinecolor='#cccccc'
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor='#e0e0e0',
                title='Cost of Equity',
                title_font=dict(size=14),
                tickformat='.2%',
                zeroline=True,
                zerolinecolor='#cccccc'
            ),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            hovermode='closest',
            showlegend=True
        )
        
        return fig
    
    return app


def main():
    """
    Main execution function.
    
    Runs the pipeline, loads data, and starts the dashboard server.
    """
    try:
        # Step 1: Run the pipeline
        run_pipeline()
        
        # Step 2: Load data
        print("Loading data for dashboard...")
        master_df, stock_prices_df = load_data()
        print(f"[SUCCESS] Loaded {len(master_df)} CAPM records")
        print(f"[SUCCESS] Loaded {len(stock_prices_df)} stock price records\n")
        
        # Step 3: Create and run dashboard
        app = create_dashboard(master_df, stock_prices_df)
        
        print("=" * 80)
        print("Starting Dashboard Server...")
        print("=" * 80)
        print("\nDashboard URL: http://127.0.0.1:8050")
        print("\nPress Ctrl+C to stop the server\n")
        
        app.run(debug=True, host='127.0.0.1', port=8050)
        
    except Exception as e:
        print(f"\n[ERROR] Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
