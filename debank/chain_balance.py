"""
Chain Balance Module for DeBank API Integration

This module provides functionality to retrieve and manage chain balances for cryptocurrency addresses.
It interacts with the DeBank Pro API to fetch balance information across different blockchain networks.

Key Features:
- Retrieve total balance for a specific chain
- Get balances for all chains where an address has been used
- Update and manage active networks configuration
- Verify file integrity and data consistency

Dependencies:
- requests: For HTTP API calls to DeBank
- python-dotenv: For environment variable management
- json: For data serialization/deserialization
- datetime: For timestamp handling
"""

import requests
import os
from dotenv import load_dotenv
import json
from datetime import datetime, timezone
import time

# Load environment variables from .env file
load_dotenv()

def get_chain_balance(address, chain_id):
    """
    Retrieves the total balance of an address on a specific chain
    
    This function makes a direct API call to DeBank Pro to get the total USD value
    of all assets held by the specified address on the given blockchain network.
    
    Args:
        address (str): The cryptocurrency address to query (e.g., "0x1234...")
        chain_id (str): The blockchain network identifier (e.g., "eth", "base", "bsc")
    
    Returns:
        float: Total USD value of all assets on the specified chain, or 0 if error
        
    Raises:
        ValueError: If DeBank API key is not configured in environment variables
        
    Example:
        >>> balance = get_chain_balance("0x1234...", "eth")
        >>> print(f"Ethereum balance: ${balance:,.2f}")
    """
    # Get API key from environment variables
    access_key = os.getenv('DEBANK_ACCESS_KEY')
    if not access_key:
        raise ValueError("DeBank API key is not defined in .env file")

    # DeBank Pro API endpoint for chain balance
    url = "https://pro-openapi.debank.com/v1/user/chain_balance"
    
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
        # Make GET request with parameters and timeout
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
        # Check if request was successful (status code 200)
        response.raise_for_status()
        
        # Parse JSON response from DeBank API
        data = response.json()
        
        # Return the USD value, defaulting to 0 if not found
        return data.get("usd_value", 0)
    
    except requests.exceptions.RequestException as e:
        # Handle network errors, timeouts, and API errors
        print(f"Error during API request for chain {chain_id}: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Error details: {e.response.text}")
        return 0

def update_networks_config(chain_balances, script_timestamp):
    """
    Updates the active_networks.json file with the latest chain balances.
    
    This function creates or updates a JSON file that stores the current state
    of all active networks and their balances for the analyzed address.
    
    Args:
        chain_balances (dict): Dictionary containing chain balances with structure:
            {
                "chain_id": {
                    "balance": float,
                    "name": str,
                    "logo_url": str
                }
            }
        script_timestamp (str): Timestamp of when the script was executed
    """
    # Create the data directory if it doesn't exist
    os.makedirs('debank/data', exist_ok=True)
    
    # Save the chain balances to active_networks.json with proper formatting
    with open('debank/data/active_networks.json', 'w') as f:
        json.dump({
            "script_execution_time": script_timestamp,
            "networks": chain_balances
        }, f, indent=2)

def verify_file_written(filepath):
    """
    Verifies that the file has been written correctly with valid data structure
    
    This function performs a basic integrity check to ensure the JSON file
    was written successfully and contains the expected data structure.
    
    Args:
        filepath (str): Path to the file to verify
        
    Returns:
        bool: True if file exists and contains valid data structure, False otherwise
    """
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
            # Check if data exists and has the expected "networks" key
            return bool(data and "networks" in data)
    except (json.JSONDecodeError, FileNotFoundError):
        return False

def get_all_chain_balances(address, script_timestamp=None):
    """
    Retrieves balances for all chains where the address has been used
    
    This is the main function that orchestrates the complete chain balance analysis.
    It first fetches the list of all chains where the address has activity,
    then retrieves the balance for each chain, and finally aggregates the results.
    
    Args:
        address (str): The cryptocurrency address to analyze
        script_timestamp (str, optional): Custom timestamp for script execution time.
            If None, current UTC time will be used.
    
    Returns:
        dict: Complete analysis result containing:
            - address: The address that was queried
            - script_execution_time: When the script was run
            - chain_balances: Dictionary with balance details for each chain
            - total_balance: Sum of all balances across all chains
            - error: Error message if the analysis failed
            
    Raises:
        ValueError: If DeBank API key is not configured
        
    Example:
        >>> result = get_all_chain_balances("0x1234...")
        >>> print(f"Total balance: ${result['total_balance']:,.2f}")
    """
    # Get API key from environment variables
    access_key = os.getenv('DEBANK_ACCESS_KEY')
    if not access_key:
        raise ValueError("DeBank API key is not defined in .env file")

    # DeBank Pro API endpoint for getting list of used chains
    url = "https://pro-openapi.debank.com/v1/user/used_chain_list"
    
    # Request parameters for the API call
    params = {
        "id": address
    }
    
    # Headers required for DeBank Pro API authentication
    headers = {
        "accept": "application/json",
        "AccessKey": access_key
    }
    
    try:
        # Get list of all chains where the address has been used
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        chains_data = response.json()
        
        # Initialize results storage
        chain_balances = {}
        total_balance = 0
        
        # Process each chain and get its balance
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
        
        # Update networks configuration file
        update_networks_config(chain_balances, script_timestamp)
        
        # Verify that the file was written correctly
        if not verify_file_written('debank/data/active_networks.json'):
            print("Warning: Could not verify active_networks.json was written correctly")
        
        # Create the final result structure
        final_result = {
            "address": address,
            "script_execution_time": script_timestamp,
            "chain_balances": chain_balances,
            "total_balance": total_balance
        }
        
        return final_result
    
    except requests.exceptions.RequestException as e:
        # Handle API errors and provide fallback response
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
    """
    Main execution block for testing the chain balance functionality
    
    This block runs when the script is executed directly (not imported as a module).
    It demonstrates how to use the get_all_chain_balances function with a sample address.
    """
    # Ethereum address to check (example address)
    address = "0xc6835323372a4393b90bcc227c58e82d45ce4b7d"
    
    # Get all chain balances for the address
    balances = get_all_chain_balances(address)
    
    # Print the complete dictionary with nice formatting
    print(json.dumps(balances, indent=4)) 