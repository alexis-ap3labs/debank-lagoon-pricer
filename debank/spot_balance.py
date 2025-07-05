"""
Spot Balance Module for DeBank API Integration

This module provides functionality to retrieve and analyze spot token balances
for cryptocurrency addresses across different blockchain networks. It focuses
on native tokens and simple token holdings (excluding complex protocol positions).

Key Features:
- Retrieve spot token balances for specific chains
- Calculate total USD values for spot holdings
- Aggregate spot balances across multiple networks
- Integrate with active networks configuration
- Add timestamps for data tracking

Dependencies:
- requests: For HTTP API calls to DeBank
- python-dotenv: For environment variable management
- datetime: For timestamp handling
- json: For data serialization/deserialization
"""

import requests
import os
from dotenv import load_dotenv
import json
from datetime import datetime

# Load environment variables from .env file
load_dotenv()

def get_active_networks():
    """
    Retrieves the list of active networks from active_networks.json
    
    This function reads the previously generated active networks file to determine
    which blockchain networks have funds for the analyzed address.
    
    Returns:
        list: List of chain IDs (e.g., ["eth", "base"]) where the address has funds
        
    Example:
        >>> networks = get_active_networks()
        >>> print(f"Active networks: {networks}")
    """
    try:
        with open('debank/data/active_networks.json', 'r') as f:
            data = json.load(f)
            return list(data.get('networks', {}).keys())
    except Exception as e:
        print(f"Error reading active_networks.json: {e}")
        return []

def get_token_list(address, chain_id="eth"):
    """
    Retrieves the list of spot tokens for a given address on a specific chain
    
    This function fetches all spot token holdings (excluding protocol positions)
    for the specified address on the given blockchain network. It includes
    native tokens and simple token transfers.
    
    Args:
        address (str): The cryptocurrency address to query (e.g., "0x1234...")
        chain_id (str): The blockchain network identifier (e.g., "eth", "base", "bsc")
    
    Returns:
        tuple: (total_value, raw_data) where:
            - total_value (float): Total USD value of all spot tokens on the chain
            - raw_data (list): Raw token data from DeBank API with added timestamp
            
    Raises:
        ValueError: If DeBank API key is not configured in environment variables
        
    Example:
        >>> total_value, tokens = get_token_list("0x1234...", "eth")
        >>> print(f"Total spot value on Ethereum: ${total_value:,.2f}")
    """
    # Get API key from environment variables
    access_key = os.getenv('DEBANK_ACCESS_KEY')
    if not access_key:
        raise ValueError("DeBank API key is not defined in .env file")

    # DeBank Pro API endpoint for token list
    url = "https://pro-openapi.debank.com/v1/user/token_list"
    
    # Request parameters for the API call
    params = {
        "id": address,
        "chain_id": chain_id,
        "is_all": "false"  # Only get spot tokens, exclude protocol tokens
    }
    
    # Headers required for DeBank Pro API authentication
    headers = {
        "accept": "application/json",
        "AccessKey": access_key
    }
    
    try:
        # Make GET request with parameters and timeout
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
        # Check if request was successful (status code 200)
        response.raise_for_status()
        
        # Parse JSON response from DeBank API
        data = response.json()
        
        # If no data is returned, return 0 and empty list
        if data is None:
            return 0, []
        
        # Add timestamp to each token's data for tracking
        timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
        for token in data:
            token['timestamp'] = timestamp
        
        # Calculate total USD value by multiplying amount by price for each token
        total_value = sum(token.get("amount", 0) * token.get("price", 0) for token in data)
        
        return total_value, data
    
    except requests.exceptions.RequestException as e:
        # Handle network errors, timeouts, and API errors
        print(f"Error during API request for chain {chain_id}: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Error details: {e.response.text}")
        return 0, []

def get_all_token_balances(address):
    """
    Retrieves total spot balances for a given address on all active chains
    
    This is the main function that orchestrates the complete spot balance analysis.
    It reads the list of active networks and fetches spot token balances for each
    network where the address has funds.
    
    Args:
        address (str): The cryptocurrency address to analyze
        
    Returns:
        dict: Complete spot balance analysis containing:
            - address: The address that was queried
            - network_totals: Dictionary with total value per network and total
            - raw_data: Dictionary with raw API data per network
            
    Example:
        >>> spot_data = get_all_token_balances("0x1234...")
        >>> print(f"Total spot value: ${spot_data['network_totals']['total_usd']:,.2f}")
    """
    # Get list of active networks from the previously generated file
    active_networks = get_active_networks()
    
    # Return empty result if no active networks found
    if not active_networks:
        return {
            "address": address,
            "network_totals": {
                "eth_usd": 0,
                "base_usd": 0,
                "total_usd": 0
            },
            "raw_data": {}
        }
    
    # Initialize network totals and raw data storage
    network_totals = {
        "eth_usd": 0,
        "base_usd": 0,
        "total_usd": 0
    }
    
    raw_data = {}
    
    # Get token lists for each active chain
    for chain_id in active_networks:
        chain_total, chain_data = get_token_list(address, chain_id=chain_id)
        network_totals[f"{chain_id}_usd"] = chain_total
        network_totals["total_usd"] += chain_total
        raw_data[chain_id] = chain_data
    
    # Create the final comprehensive result
    final_result = {
        "address": address,
        "network_totals": network_totals,
        "raw_data": raw_data
    }
    
    return final_result

if __name__ == "__main__":
    """
    Main execution block for testing the spot balance functionality
    
    This block runs when the script is executed directly (not imported as a module).
    It demonstrates how to use the get_all_token_balances function with a sample address.
    """
    # Ethereum address to check (example address)
    address = "0xc6835323372a4393b90bcc227c58e82d45ce4b7d"
    
    # Get all token balances for the address
    all_balances = get_all_token_balances(address)
    
    # Print the complete dictionary with nice formatting
    print(json.dumps(all_balances, indent=4)) 