import json
import sys
from pathlib import Path
from web3 import Web3

# Add parent directory to PYTHONPATH
sys.path.append(str(Path(__file__).parent.parent))

from debank.protocol_details import get_all_protocol_details
from nav.process_portfolio import process_portfolio
from mongoDB.mongo_formatter import format_for_mongodb

def create_position_key(protocol_id, chain_id, item):
    """Creates a position key in the format: protocol.chain.tokenSymbol"""
    tokens = item.get("asset_token_list", [])
    if len(tokens) >= 2:
        token_symbols = "-".join([t.get("symbol", "") for t in tokens[:2]])
    else:
        token_symbols = tokens[0].get("symbol", "") if tokens else "unknown"
    return f"{protocol_id}.{chain_id}.{token_symbols}"

def main():
    # Path to config.json file
    config_path = Path(__file__).parent.parent / 'config.json'
    
    # Read config.json file
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    # Get wallet address and convert to checksum format
    wallet_address = config.get('wallet_address')
    if not wallet_address:
        print("Error: Wallet address not found in config.json")
        return
    
    # Convert to checksum address
    wallet_address = Web3.to_checksum_address(wallet_address)
    
    print("\n=== Step 1: Active Networks Analysis ===")
    print("This step identifies all networks where the wallet has a non-zero balance")
    print("Results will be saved in: debank/data/active_networks.json")
    
    # Call get_all_protocol_details function
    protocol_details = get_all_protocol_details(wallet_address)
    
    if protocol_details:
        print("\n=== Analysis Summary ===")
        print(f"Address: {protocol_details['address']}")
        print(f"Execution Time: {protocol_details['script_execution_time']}")
        
        print("\n=== Network Totals ===")
        for network, total in protocol_details['network_totals'].items():
            if network != 'total_usd':
                network_name = network.replace('_usd', '').upper()
                print(f"\n{network_name} Network:")
                spot_total = protocol_details['spot']['totals'][network]
                protocol_total = total - spot_total
                print(f"- Protocol Value: ${protocol_total:,.2f}")
                print(f"- Spot Balance: ${spot_total:,.2f}")
                print(f"- Total Value: ${total:,.2f}")
        
        print(f"\nTotal Value Across All Networks: ${protocol_details['network_totals']['total_usd']:,.2f}")
        
        print("\n=== Step 2: Protocol Discovery ===")
        print("This step identifies all protocols where the wallet has positions")
        print("Results will be saved in: debank/data/portfolio_cache.json")
        print("\nProtocols Found by Network:")
        
        # Initialize positions dictionary
        positions = {}
        
        # Process protocol positions
        for protocol_id, details in protocol_details['protocols'].items():
            chain_id = details['chain_id']
            for item in details.get("portfolio_item_list", []):
                position_key = create_position_key(protocol_id, chain_id, item)
                value = item.get("stats", {}).get("net_usd_value", 0)
                if value > 0:
                    positions[position_key] = f"{value:.6f}"
            
            protocol_value = sum(item.get("stats", {}).get("net_usd_value", 0) 
                               for item in details.get("portfolio_item_list", []))
            print(f"\n{protocol_id.upper()} ({chain_id}):")
            print(f"- Value: ${protocol_value:,.2f}")
            print(f"- Chain: {chain_id}")
            print(f"- Site URL: {details.get('site_url', 'N/A')}")
        
        # Process spot positions
        for network, tokens in protocol_details['spot']['tokens'].items():
            spot_total = sum(float(token['amount']) * float(token['price']) for token in tokens)
            if spot_total > 0:
                positions[f"spot.{network}"] = f"{spot_total:.6f}"
        
        # Add positions to protocol_details
        protocol_details['positions'] = positions
        
        print("\n=== Step 3: Portfolio Processing ===")
        print("Processing portfolio data for NAV calculation")
        print("Results will be saved in: nav/data/portfolio_processed.json")
        process_portfolio()
        
        print("\n=== Step 4: MongoDB Storage ===")
        print("Storing processed portfolio data in MongoDB")
        print("Data will be stored in the collection specified in .env file")
        format_for_mongodb()

if __name__ == "__main__":
    main() 