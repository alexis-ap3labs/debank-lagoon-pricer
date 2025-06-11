import os
from web3 import Web3
import json

def get_vault_supply():
    # Initialize Web3 connection with Base RPC
    RPC_URL = "https://mainnet.base.org"
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    
    # Check connection
    if not w3.is_connected():
        raise Exception("Unable to connect to Base RPC")
    
    # Load configuration to get vault address
    with open('config.json', 'r') as f:
        config = json.load(f)
    vault_address = config['vault_address']
    
    # Convert address to checksum format
    vault_address = Web3.to_checksum_address(vault_address)
    
    # Minimal ABI for totalSupply function
    vault_abi = [
        {
            "constant": True,
            "inputs": [],
            "name": "totalSupply",
            "outputs": [{"name": "", "type": "uint256"}],
            "type": "function"
        }
    ]
    
    # Create contract
    vault_contract = w3.eth.contract(address=vault_address, abi=vault_abi)
    
    try:
        # Call totalSupply
        total_supply = vault_contract.functions.totalSupply().call()
        print(f"Raw total supply: {total_supply}")
        
        # Convert to decimal number (divide by 1e18)
        formatted_supply = total_supply / 1e18
        print(f"Formatted total supply: {formatted_supply}")
        
        return formatted_supply
    except Exception as e:
        print(f"Error calling totalSupply: {str(e)}")
        raise

def update_nav_with_share_price():
    try:
        # Read portfolio_processed.json file
        with open('nav/data/portfolio_processed.json', 'r') as f:
            portfolio = json.load(f)
        
        # Get supply
        total_supply = get_vault_supply()
        
        # Calculate share price (NAV / supply)
        nav_usd = portfolio['nav']['usd']
        share_price_usd = nav_usd / total_supply
        
        # Update nav section with share price
        portfolio['nav']['share_price_usd'] = share_price_usd
        portfolio['nav']['total_supply'] = total_supply
        
        # Save updated file
        with open('nav/data/portfolio_processed.json', 'w') as f:
            json.dump(portfolio, f, indent=2)
        
        print(f"Share price: ${share_price_usd:.6f}")
        print(f"Total supply: {total_supply:.2f}")
    except Exception as e:
        print(f"Error updating NAV: {str(e)}")
        raise

if __name__ == "__main__":
    update_nav_with_share_price() 