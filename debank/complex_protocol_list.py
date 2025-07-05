"""
Complex Protocol List Module for DeBank API Integration

This module provides functionality to retrieve and analyze complex protocol positions
for cryptocurrency addresses across different blockchain networks. It handles the
aggregation of protocol data, spot balances, and network totals.

Key Features:
- Retrieve protocol positions and values from DeBank Pro API
- Aggregate data across multiple blockchain networks
- Calculate network-specific and total portfolio values
- Integrate with chain balance and spot balance modules
- Generate comprehensive portfolio analysis reports

Dependencies:
- requests: For HTTP API calls to DeBank
- python-dotenv: For environment variable management
- datetime: For timestamp handling
- debank.chain_balance: For chain balance integration
- debank.spot_balance: For spot balance integration
"""

import requests
import os
from dotenv import load_dotenv
import time
import json
from datetime import datetime
from debank.chain_balance import get_all_chain_balances
from debank.spot_balance import get_all_token_balances

# Load environment variables from .env file
load_dotenv()

def verify_networks_file():
    """
    Verifies that active_networks.json has been written correctly with valid data structure
    
    This function performs a basic integrity check to ensure the active networks file
    was written successfully and contains the expected data structure.
    
    Returns:
        bool: True if file exists and contains valid data structure, False otherwise
    """
    try:
        with open('debank/data/active_networks.json', 'r') as f:
            data = json.load(f)
            return bool(data and "networks" in data)
    except (json.JSONDecodeError, FileNotFoundError):
        return False

def get_protocol_values(address, chain_id="eth"):
    """
    Retrieves protocol IDs and their values from DeBank Pro API for a specific chain
    
    This function fetches detailed protocol information including positions, values,
    and metadata for all protocols where the address has active positions on the
    specified blockchain network.
    
    Args:
        address (str): The cryptocurrency address to query (e.g., "0x1234...")
        chain_id (str): The blockchain network identifier (e.g., "eth", "base", "bsc")
    
    Returns:
        dict: Dictionary containing:
            - address: The address that was queried
            - protocols: Dictionary with protocol IDs as keys and their values as dictionaries containing:
                - name: Protocol name
                - site_url: Protocol site URL
                - tvl: Protocol TVL (Total Value Locked)
                - value: Total value in USD
                - timestamp: When the data was last updated by DeBank (in human readable format)
                - chain_id: The network the protocol is on
            - network_totals: Dictionary with total value per network and cross-network total
            
    Raises:
        ValueError: If DeBank API key is not configured in environment variables
        
    Example:
        >>> result = get_protocol_values("0x1234...", "eth")
        >>> print(f"Found {len(result['protocols'])} protocols on Ethereum")
    """
    # Get API key from environment variables
    access_key = os.getenv('DEBANK_ACCESS_KEY')
    if not access_key:
        raise ValueError("DeBank API key is not defined in .env file. Make sure you have created a .env file with DEBANK_ACCESS_KEY=your_key")

    # DeBank Pro API endpoint for complex protocol list
    url = "https://pro-openapi.debank.com/v1/user/complex_protocol_list"
    
    # Request parameters for the API call
    params = {
        "id": address,
        "chain_id": chain_id
    }
    
    # Headers required for DeBank Pro API authentication
    headers = {
        "accept": "application/json",
        "AccessKey": access_key
    }
    
    try:
        print(f"\nFetching protocols for {chain_id.upper()}")
        # Make GET request with parameters and timeout
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
        # Check if request was successful (status code 200)
        response.raise_for_status()
        
        # Parse JSON response and extract protocol IDs and values
        protocols = response.json()
        print(f"Found {len(protocols)} protocols on {chain_id.upper()}")
        
        # Initialize storage for protocol values and network totals
        protocol_values = {}
        network_totals = {
            "eth_usd": 0,
            "base_usd": 0,
            "total_usd": 0
        }
        
        # Process each protocol and calculate its total value
        for protocol in protocols:
            protocol_id = protocol.get("id")
            total_value = 0
            latest_update = 0
            
            # Sum up all position values for this protocol and get the latest update time
            for item in protocol.get("portfolio_item_list", []):
                total_value += item.get("stats", {}).get("net_usd_value", 0)
                # Get the update_at timestamp from the item
                item_update = item.get("update_at", 0)
                if item_update > latest_update:
                    latest_update = item_update
            
            # Convert the DeBank timestamp to human readable format
            human_timestamp = datetime.utcfromtimestamp(latest_update).strftime('%Y-%m-%d %H:%M:%S UTC')
            
            # Store protocol information
            protocol_values[protocol_id] = {
                "name": protocol.get("name", ""),
                "site_url": protocol.get("site_url", ""),
                "tvl": protocol.get("tvl", 0),
                "value": total_value,
                "timestamp": human_timestamp,
                "chain_id": chain_id
            }
            
            # Add to network totals for aggregation
            network_totals[f"{chain_id}_usd"] += total_value
            network_totals["total_usd"] += total_value
            print(f"Protocol ID: {protocol_id}")
        
        return {
            "address": address,
            "protocols": protocol_values,
            "network_totals": network_totals
        }
    
    except requests.exceptions.RequestException as e:
        # Handle API errors and provide fallback response
        print(f"Error during API request for {chain_id}: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Error details: {e.response.text}")
        return {
            "address": address,
            "protocols": {},
            "network_totals": {
                "eth_usd": 0,
                "base_usd": 0,
                "total_usd": 0
            }
        }

def get_all_protocol_values(address):
    """
    Retrieves all protocol values for a given address across all active networks
    
    This is the main function that orchestrates the complete protocol analysis.
    It integrates data from multiple sources:
    1. Chain balance analysis to identify active networks
    2. Protocol position analysis for each active network
    3. Spot balance analysis for comprehensive portfolio view
    
    Args:
        address (str): The cryptocurrency address to analyze
        
    Returns:
        dict: Complete portfolio analysis containing:
            - address: The address that was queried
            - script_execution_time: When the analysis was performed
            - network_totals: Aggregated values per network and total
            - protocols: All protocol positions across all networks
            - spot: Spot token balances and totals
            
    Example:
        >>> portfolio = get_all_protocol_values("0x1234...")
        >>> print(f"Total portfolio value: ${portfolio['network_totals']['total_usd']:,.2f}")
    """
    # First, update active_networks.json using chain_balance module
    from debank.chain_balance import get_all_chain_balances
    get_all_chain_balances(address)
    
    # Verify that the active networks file was written correctly
    if not verify_networks_file():
        print("Warning: Could not verify active_networks.json was written correctly")
        return None
    
    # Read active networks from the generated file
    with open('debank/data/active_networks.json', 'r') as f:
        networks_data = json.load(f)
        active_networks = list(networks_data["networks"].keys())
    
    print(f"\nNetworks with funds found: {', '.join(active_networks)}")
    
    # Get spot values using spot_balance module for comprehensive analysis
    print("\nFetching spot balances...")
    spot_data = get_all_token_balances(address)
    
    # Initialize default spot totals if spot_data is None
    spot_totals = {
        "eth_usd": 0,
        "base_usd": 0,
        "total_usd": 0
    }
    spot_tokens = {}
    
    if spot_data:
        spot_totals = spot_data.get("network_totals", spot_totals)
        spot_tokens = spot_data.get("raw_data", {})
    
    # Initialize storage for all protocols and network totals
    all_protocols = {}
    network_totals = {
        "eth_usd": 0,
        "base_usd": 0,
        "total_usd": 0
    }
    
    # Get protocols for each active chain
    for chain_id in active_networks:
        chain_values = get_protocol_values(address, chain_id=chain_id)
        all_protocols.update(chain_values["protocols"])
        
        # Update network totals with protocol values
        network_totals[f"{chain_id}_usd"] = chain_values["network_totals"][f"{chain_id}_usd"]
        network_totals["total_usd"] += chain_values["network_totals"][f"{chain_id}_usd"]
    
    # Create the final comprehensive result
    final_result = {
        "address": address,
        "script_execution_time": datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'),
        "network_totals": {
            "eth_usd": network_totals["eth_usd"] + spot_totals["eth_usd"],
            "base_usd": network_totals["base_usd"] + spot_totals["base_usd"],
            "total_usd": network_totals["total_usd"] + spot_totals["total_usd"]
        },
        "protocols": all_protocols,
        "spot": {
            "totals": spot_totals,
            "tokens": spot_tokens
        }
    }
    
    # Save the complete analysis to portfolio_cache.json
    output_file = 'debank/data/portfolio_cache.json'
    with open(output_file, 'w') as f:
        json.dump(final_result, f, indent=2)
    print(f"\nResults saved to {output_file}")
    
    return final_result

if __name__ == "__main__":
    """
    Main execution block for testing the complex protocol list functionality
    
    This block runs when the script is executed directly (not imported as a module).
    It demonstrates how to use the get_all_protocol_values function with a sample address.
    """
    # Ethereum address to check (example address)
    address = "0xc6835323372a4393b90bcc227c58e82d45ce4b7d"
    
    # Get all protocol values for the address
    all_values = get_all_protocol_values(address)
    
    # Print the complete dictionary with nice formatting
    print(json.dumps(all_values, indent=4)) 