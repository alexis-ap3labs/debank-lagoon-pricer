import requests
import os
from dotenv import load_dotenv
import json
from datetime import datetime, timezone
import time

# Load environment variables
load_dotenv()

def get_chain_balance(address, chain_id):
    """
    Retrieves the total balance of an address on a specific chain
    
    Args:
        address (str): User's address
        chain_id (str): Chain ID (eth, base, etc.)
    
    Returns:
        float: Total USD value of all assets on the chain
    """
    # Get API key from environment variables
    access_key = os.getenv('DEBANK_ACCESS_KEY')
    if not access_key:
        raise ValueError("DeBank API key is not defined in .env file")

    # Pro API URL
    url = "https://pro-openapi.debank.com/v1/user/chain_balance"
    
    # Request parameters
    params = {
        "id": address,
        "chain_id": chain_id
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
        
        # Return the USD value
        return data.get("usd_value", 0)
    
    except requests.exceptions.RequestException as e:
        print(f"Error during API request for chain {chain_id}: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Error details: {e.response.text}")
        return 0

def update_networks_config(chain_balances, script_timestamp):
    """
    Updates the active_networks.json file with the latest chain balances.
    
    Args:
        chain_balances (dict): Dictionary containing chain balances
        script_timestamp (str): Timestamp of the script execution
    """
    # Create the data directory if it doesn't exist
    os.makedirs('debank/data', exist_ok=True)
    
    # Save the chain balances to active_networks.json
    with open('debank/data/active_networks.json', 'w') as f:
        json.dump({
            "script_execution_time": script_timestamp,
            "networks": chain_balances
        }, f, indent=2)

def verify_file_written(filepath):
    """
    Verifies that the file has been written correctly
    Returns True if the file exists and contains valid data
    """
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
            return bool(data and "networks" in data)
    except (json.JSONDecodeError, FileNotFoundError):
        return False

def get_all_chain_balances(address, script_timestamp=None):
    """
    Retrieves balances for all chains where the address has been used
    
    Args:
        address (str): User's address
        script_timestamp (str, optional): Timestamp to use for the script execution time
    
    Returns:
        dict: Dictionary containing:
            - address: The address that was queried
            - script_execution_time: When the script was run
            - chain_balances: Dictionary with chain balances
            - total_balance: Total balance across all chains
    """
    # Get API key from environment variables
    access_key = os.getenv('DEBANK_ACCESS_KEY')
    if not access_key:
        raise ValueError("DeBank API key is not defined in .env file")

    # Pro API URL for used chains
    url = "https://pro-openapi.debank.com/v1/user/used_chain_list"
    
    # Request parameters
    params = {
        "id": address
    }
    
    # Headers with AccessKey
    headers = {
        "accept": "application/json",
        "AccessKey": access_key
    }
    
    try:
        # Get list of used chains
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        chains_data = response.json()
        
        # Initialize results
        chain_balances = {}
        total_balance = 0
        
        # Get balance for each chain
        for chain in chains_data:
            chain_id = chain["id"]
            balance = get_chain_balance(address, chain_id)
            if balance > 0:  # Only include chains with non-zero balance
                chain_balances[chain_id] = {
                    "balance": balance,
                    "name": chain["name"],
                    "logo_url": chain["logo_url"]
                }
                total_balance += balance
        
        # Use provided timestamp or generate new one
        if script_timestamp is None:
            script_timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
        
        # Update networks configuration
        update_networks_config(chain_balances, script_timestamp)
        
        # Vérifier que le fichier a été écrit correctement
        if not verify_file_written('debank/data/active_networks.json'):
            print("Warning: Could not verify active_networks.json was written correctly")
        
        # Create the final result
        final_result = {
            "address": address,
            "script_execution_time": script_timestamp,
            "chain_balances": chain_balances,
            "total_balance": total_balance
        }
        
        return final_result
    
    except requests.exceptions.RequestException as e:
        print(f"Error during API request: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Error details: {e.response.text}")
        return {
            "address": address,
            "script_execution_time": script_timestamp or datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'),
            "chain_balances": {},
            "total_balance": 0,
            "error": str(e)
        }

if __name__ == "__main__":
    # Ethereum address to check
    address = "0xc6835323372a4393b90bcc227c58e82d45ce4b7d"
    
    # Get all chain balances
    balances = get_all_chain_balances(address)
    
    # Print the complete dictionary with nice formatting
    print(json.dumps(balances, indent=4)) 