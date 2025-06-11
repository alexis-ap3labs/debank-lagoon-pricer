import requests
import os
from dotenv import load_dotenv
import json
from datetime import datetime

# Load environment variables
load_dotenv()

def get_active_networks():
    """
    Retrieves the list of active networks from active_networks.json
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
    
    Args:
        address (str): User's address
        chain_id (str): Chain ID (eth, base)
    
    Returns:
        tuple: (total_value, raw_data) where:
            - total_value (float): Total USD value of spot tokens
            - raw_data (list): Raw token data from DeBank API with added timestamp
    """
    # Get API key from environment variables
    access_key = os.getenv('DEBANK_ACCESS_KEY')
    if not access_key:
        raise ValueError("DeBank API key is not defined in .env file")

    # Pro API URL
    url = "https://pro-openapi.debank.com/v1/user/token_list"
    
    # Request parameters
    params = {
        "id": address,
        "chain_id": chain_id,
        "is_all": "false"  # Only get spot tokens, no protocol tokens
    }
    
    # Headers with AccessKey
    headers = {
        "accept": "application/json",
        "AccessKey": access_key
    }
    
    try:
        # Make GET request with parameters
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
        # Check if request was successful
        response.raise_for_status()
        
        # Get JSON data
        data = response.json()
        
        # If no data is returned, return 0 and empty list
        if data is None:
            return 0, []
        
        # Add timestamp to each token's data
        timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
        for token in data:
            token['timestamp'] = timestamp
        
        # Calculate total USD value
        total_value = sum(token.get("amount", 0) * token.get("price", 0) for token in data)
        
        return total_value, data
    
    except requests.exceptions.RequestException as e:
        print(f"Error during API request for chain {chain_id}: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Error details: {e.response.text}")
        return 0, []

def get_all_token_balances(address):
    """
    Retrieves total spot balances for a given address on active chains from active_networks.json
    
    Args:
        address (str): User's address
    
    Returns:
        dict: Dictionary containing:
            - address: The address that was queried
            - network_totals: Dictionary with total value per network and total
            - raw_data: Dictionary with raw API data per network
    """
    # Get list of active networks from active_networks.json
    active_networks = get_active_networks()
    
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
    
    # Initialize network totals and raw data
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
    
    # Create the final result
    final_result = {
        "address": address,
        "network_totals": network_totals,
        "raw_data": raw_data
    }
    
    return final_result

if __name__ == "__main__":
    # Ethereum address to check
    address = "0xc6835323372a4393b90bcc227c58e82d45ce4b7d"
    
    # Get all token balances
    all_balances = get_all_token_balances(address)
    
    # Print the complete dictionary with nice formatting
    print(json.dumps(all_balances, indent=4)) 