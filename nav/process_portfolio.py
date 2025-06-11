import json
from datetime import datetime
import os
from .price_fetcher import PriceFetcher
from .supply_reader import get_vault_supply, update_nav_with_share_price

def process_portfolio():
    # Load configuration
    with open('config.json', 'r') as f:
        config = json.load(f)
    
    # Load portfolio
    with open('debank/data/portfolio_live.json', 'r') as f:
        portfolio = json.load(f)
    
    # Initialize PriceFetcher and get underlying asset price
    price_fetcher = PriceFetcher()
    underlying_price = price_fetcher.get_price(config['asset']['coingecko_id'])
    
    # Calculate NAV in underlying asset
    total_usd = portfolio['network_totals']['total_usd']
    nav_in_underlying = round(total_usd / underlying_price, 6)
    
    # Get vault supply
    total_supply = get_vault_supply()
    
    # Calculate share price
    share_price_usd = total_usd / total_supply
    
    # Create new document while keeping original structure
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
    
    # Save new document
    output_file = 'nav/data/portfolio_processed.json'
    with open(output_file, 'w') as f:
        json.dump(processed_data, f, indent=2)
    
    print(f"Processed portfolio saved to {output_file}")
    print(f"NAV in {config['asset']['ticker']}: {nav_in_underlying:.6f}")
    print(f"Share price: ${share_price_usd:.6f}")
    print(f"Total supply: {total_supply:.2f}")

if __name__ == "__main__":
    process_portfolio() 