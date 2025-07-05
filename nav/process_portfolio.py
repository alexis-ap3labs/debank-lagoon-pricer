"""
Portfolio Processing Module for NAV Calculation

This module processes portfolio data to calculate Net Asset Value (NAV) and related
metrics for a DeFi vault. It integrates price data, vault supply information, and
portfolio analysis to generate comprehensive NAV calculations.

Key Features:
- Calculate NAV in both USD and underlying asset (e.g., USDC)
- Compute share price based on total supply
- Integrate real-time price data from CoinGecko
- Read vault supply from blockchain
- Generate processed portfolio data with NAV metrics

NAV Calculation Process:
1. Load portfolio data from DeBank analysis
2. Fetch current price of underlying asset
3. Calculate NAV in underlying asset units
4. Read total vault supply from blockchain
5. Compute share price and other metrics
6. Generate comprehensive portfolio document

Dependencies:
- json: For configuration and data handling
- datetime: For timestamp management
- price_fetcher: For real-time price data
- supply_reader: For vault supply information
"""

import json
from datetime import datetime
import os
from .price_fetcher import PriceFetcher
from .supply_reader import get_vault_supply, update_nav_with_share_price

def process_portfolio():
    """
    Process portfolio data and calculate NAV metrics
    
    This function orchestrates the complete NAV calculation process by:
    1. Loading configuration and portfolio data
    2. Fetching current price of the underlying asset
    3. Calculating NAV in both USD and underlying asset units
    4. Reading total vault supply from the blockchain
    5. Computing share price and other metrics
    6. Generating a comprehensive processed portfolio document
    
    Configuration Requirements:
    - config.json must contain vault_address and asset information
    - debank/data/portfolio_live.json must exist with portfolio data
    
    Output:
    - Creates nav/data/portfolio_processed.json with NAV calculations
    - Displays NAV metrics in console
    
    Example:
        >>> process_portfolio()
        Processed portfolio saved to nav/data/portfolio_processed.json
        NAV in USDC: 320923.713117
        Share price: $1.036112
        Total supply: 309698.31
    """
    # Load configuration from config.json
    with open('config.json', 'r') as f:
        config = json.load(f)
    
    # Load portfolio data from DeBank analysis
    with open('debank/data/portfolio_live.json', 'r') as f:
        portfolio = json.load(f)
    
    # Initialize PriceFetcher and get underlying asset price
    price_fetcher = PriceFetcher()
    underlying_price = price_fetcher.get_price(config['asset']['coingecko_id'])
    
    # Calculate NAV in underlying asset (e.g., USDC)
    total_usd = portfolio['network_totals']['total_usd']
    nav_in_underlying = round(total_usd / underlying_price, 6)
    
    # Get vault supply from blockchain
    total_supply = get_vault_supply()
    
    # Calculate share price (NAV / total supply)
    share_price_usd = total_usd / total_supply
    
    # Create new document while preserving original structure
    processed_data = {
        "address": portfolio['address'],
        "vault_address": config['vault_address'],
        "script_execution_time": portfolio['script_execution_time'],
        "underlying_asset": {
            "ticker": config['asset']['ticker'],
            "coingecko_id": config['asset']['coingecko_id'],
            "price_usd": underlying_price
        },
        "nav": {
            "usd": total_usd,
            config['asset']['ticker'].lower(): nav_in_underlying,
            "share_price_usd": share_price_usd,
            "total_supply": total_supply
        },
        "network_totals": portfolio['network_totals'],
        "protocols": portfolio['protocols'],
        "spot": portfolio['spot']
    }
    
    # Save processed portfolio data to file
    output_file = 'nav/data/portfolio_processed.json'
    with open(output_file, 'w') as f:
        json.dump(processed_data, f, indent=2)
    
    # Display NAV calculation results
    print(f"Processed portfolio saved to {output_file}")
    print(f"NAV in {config['asset']['ticker']}: {nav_in_underlying:.6f}")
    print(f"Share price: ${share_price_usd:.6f}")
    print(f"Total supply: {total_supply:.2f}")

if __name__ == "__main__":
    """
    Main execution block for portfolio processing
    
    This block runs when the script is executed directly (not imported as a module).
    It calls the process_portfolio function to calculate NAV and generate processed data.
    """
    process_portfolio() 