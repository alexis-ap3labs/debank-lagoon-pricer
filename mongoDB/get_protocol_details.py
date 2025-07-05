"""
Protocol Details Orchestrator Module

This module serves as the main entry point for the complete portfolio analysis workflow.
It orchestrates the entire process from protocol analysis to MongoDB storage, providing
a comprehensive view of a cryptocurrency address's DeFi positions.

Key Features:
- Orchestrate complete portfolio analysis workflow
- Generate position keys for protocol and spot holdings
- Process multi-network portfolio data
- Integrate with NAV calculation and MongoDB storage
- Provide detailed analysis summaries

Workflow Steps:
1. Active Networks Analysis - Identify networks with funds
2. Protocol Discovery - Find all protocol positions
3. Portfolio Processing - Calculate NAV and process data
4. MongoDB Storage - Store results in database

Dependencies:
- json: For configuration and data handling
- pathlib: For file path management
- web3: For address validation and formatting
- debank.protocol_details: For protocol analysis
- nav.process_portfolio: For NAV calculation
- mongoDB.mongo_formatter: For database storage
"""

import json
import sys
from pathlib import Path
from web3 import Web3

# Add parent directory to PYTHONPATH for module imports
sys.path.append(str(Path(__file__).parent.parent))

from debank.protocol_details import get_all_protocol_details
from nav.process_portfolio import process_portfolio
from mongoDB.mongo_formatter import format_for_mongodb

def create_position_key(protocol_id, chain_id, item):
    """
    Creates a position key in the format: protocol.chain.tokenSymbol
    
    This function generates a unique identifier for each position by combining
    the protocol ID, chain ID, and token symbols. For positions with multiple
    tokens, it combines the first two token symbols with a hyphen.
    
    Args:
        protocol_id (str): The protocol identifier (e.g., "convex", "aave")
        chain_id (str): The blockchain network identifier (e.g., "eth", "base")
        item (dict): The portfolio item containing asset token information
        
    Returns:
        str: Position key in format "protocol.chain.tokenSymbol" or "protocol.chain.token1-token2"
        
    Example:
        >>> item = {"asset_token_list": [{"symbol": "USDC"}, {"symbol": "USDT"}]}
        >>> create_position_key("convex", "eth", item)
        'convex.eth.USDC-USDT'
    """
    tokens = item.get("asset_token_list", [])
    if len(tokens) >= 2:
        # For positions with multiple tokens, combine first two symbols
        token_symbols = "-".join([t.get("symbol", "") for t in tokens[:2]])
    else:
        # For single token positions, use the token symbol or "unknown"
        token_symbols = tokens[0].get("symbol", "") if tokens else "unknown"
    return f"{protocol_id}.{chain_id}.{token_symbols}"

def main():
    """
    Main function that orchestrates the complete portfolio analysis workflow
    
    This function executes the entire analysis pipeline:
    1. Reads configuration from config.json
    2. Performs protocol analysis across all networks
    3. Processes portfolio data for NAV calculation
    4. Stores results in MongoDB
    
    The function provides detailed progress updates and summary information
    at each step of the process.
    
    Configuration Requirements:
    - config.json must contain wallet_address and other required fields
    - .env file must contain MongoDB connection details
    - DeBank API key must be configured in .env
    
    Example:
        >>> main()
        === Step 1: Active Networks Analysis ===
        === Analysis Summary ===
        Address: 0x1234...
        Total Value: $320,881.99
    """
    # Path to config.json file in the parent directory
    config_path = Path(__file__).parent.parent / 'config.json'
    
    # Read configuration from config.json file
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    # Extract wallet address from configuration
    wallet_address = config.get('wallet_address')
    if not wallet_address:
        print("Error: Wallet address not found in config.json")
        return
    
    # Convert to checksum address format for consistency
    wallet_address = Web3.to_checksum_address(wallet_address)
    
    print("\n=== Step 1: Active Networks Analysis ===")
    print("This step identifies all networks where the wallet has a non-zero balance")
    print("Results will be saved in: debank/data/active_networks.json")
    
    # Call get_all_protocol_details function to perform complete analysis
    protocol_details = get_all_protocol_details(wallet_address)
    
    if protocol_details:
        # Display comprehensive analysis summary
        print("\n=== Analysis Summary ===")
        print(f"Address: {protocol_details['address']}")
        print(f"Execution Time: {protocol_details['script_execution_time']}")
        
        print("\n=== Network Totals ===")
        for network, total in protocol_details['network_totals'].items():
            if network != 'total_usd':
                network_name = network.replace('_usd', '').upper()
                print(f"\n{network_name} Network:")
                # Calculate spot and protocol totals separately
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
        
        # Initialize positions dictionary for storing all position keys and values
        positions = {}
        
        # Process protocol positions and create position keys
        for protocol_id, details in protocol_details['protocols'].items():
            chain_id = details['chain_id']
            # Create position keys for each portfolio item
            for item in details.get("portfolio_item_list", []):
                position_key = create_position_key(protocol_id, chain_id, item)
                value = item.get("stats", {}).get("net_usd_value", 0)
                if value > 0:
                    positions[position_key] = f"{value:.6f}"
            
            # Calculate and display protocol summary
            protocol_value = sum(item.get("stats", {}).get("net_usd_value", 0) 
                               for item in details.get("portfolio_item_list", []))
            print(f"\n{protocol_id.upper()} ({chain_id}):")
            print(f"- Value: ${protocol_value:,.2f}")
            print(f"- Chain: {chain_id}")
            print(f"- Site URL: {details.get('site_url', 'N/A')}")
        
        # Process spot positions and add to positions dictionary
        for network, tokens in protocol_details['spot']['tokens'].items():
            spot_total = sum(float(token['amount']) * float(token['price']) for token in tokens)
            if spot_total > 0:
                positions[f"spot.{network}"] = f"{spot_total:.6f}"
        
        # Add positions to protocol_details for later use
        protocol_details['positions'] = positions
        
        print("\n=== Step 3: Portfolio Processing ===")
        print("Processing portfolio data for NAV calculation")
        print("Results will be saved in: nav/data/portfolio_processed.json")
        # Process portfolio for NAV calculation
        process_portfolio()
        
        print("\n=== Step 4: MongoDB Storage ===")
        print("Storing processed portfolio data in MongoDB")
        print("Data will be stored in the collection specified in .env file")
        # Store data in MongoDB
        format_for_mongodb()
        
        print("\n=== Analysis Complete ===")
        print("All steps completed successfully!")
    else:
        print("Analysis failed. Please check your configuration and try again.")

if __name__ == "__main__":
    """
    Main execution block for the protocol details orchestrator
    
    This block runs when the script is executed directly (not imported as a module).
    It calls the main function to execute the complete portfolio analysis workflow.
    """
    main() 