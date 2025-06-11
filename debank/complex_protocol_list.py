import requests
import os
from dotenv import load_dotenv
import time
import json
from datetime import datetime
from debank.chain_balance import get_all_chain_balances
from debank.spot_balance import get_all_token_balances

# Load environment variables
load_dotenv()

def verify_networks_file():
    """
    Verifies that active_networks.json has been written correctly
    Returns True if the file exists and contains valid data
    """
    try:
        with open('debank/data/active_networks.json', 'r') as f:
            data = json.load(f)
            return bool(data and "networks" in data)
    except (json.JSONDecodeError, FileNotFoundError):
        return False

def get_protocol_values(address, chain_id="eth"):
    """
    Retrieves protocol IDs and their values from DeBank Pro API
    
    Args:
        address (str): User's address
        chain_id (str): Chain ID (eth, base)
    
    Returns:
        dict: Dictionary containing:
            - address: The address that was queried
            - protocols: Dictionary with protocol IDs as keys and their values as dictionaries containing:
                - name: Protocol name
                - site_url: Protocol site URL
                - tvl: Protocol TVL
                - value: Total value in USD
                - timestamp: When the data was last updated by DeBank (in human readable format)
                - chain_id: The network the protocol is on
            - network_totals: Dictionary with total value per network and cross-network total
    """
    # Get API key from environment variables
    access_key = os.getenv('DEBANK_ACCESS_KEY')
    if not access_key:
        raise ValueError("DeBank API key is not defined in .env file. Make sure you have created a .env file with DEBANK_ACCESS_KEY=your_key")

    # Pro API URL
    url = "https://pro-openapi.debank.com/v1/user/complex_protocol_list"
    
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
        print(f"\nFetching protocols for {chain_id.upper()}")
        # Make GET request with parameters
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
        # Check if request was successful
        response.raise_for_status()
        
        # Get JSON data and extract protocol IDs and values
        protocols = response.json()
        print(f"Found {len(protocols)} protocols on {chain_id.upper()}")
        
        protocol_values = {}
        network_totals = {
            "eth_usd": 0,
            "base_usd": 0,
            "total_usd": 0
        }
        
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
            
            protocol_values[protocol_id] = {
                "name": protocol.get("name", ""),
                "site_url": protocol.get("site_url", ""),
                "tvl": protocol.get("tvl", 0),
                "value": total_value,
                "timestamp": human_timestamp,
                "chain_id": chain_id
            }
            
            # Add to network totals
            network_totals[f"{chain_id}_usd"] += total_value
            network_totals["total_usd"] += total_value
            print(f"Protocol ID: {protocol_id}")
        
        return {
            "address": address,
            "protocols": protocol_values,
            "network_totals": network_totals
        }
    
    except requests.exceptions.RequestException as e:
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
    Retrieves all protocol values for a given address.
    """
    # First, update active_networks.json using chain_balance
    from debank.chain_balance import get_all_chain_balances
    get_all_chain_balances(address)
    
    # Vérifier que le fichier a été écrit correctement
    if not verify_networks_file():
        print("Warning: Could not verify active_networks.json was written correctly")
        return None
    
    # Read active networks from active_networks.json
    with open('debank/data/active_networks.json', 'r') as f:
        networks_data = json.load(f)
        active_networks = list(networks_data["networks"].keys())
    
    print(f"\nNetworks with funds found: {', '.join(active_networks)}")
    
    # Get spot values using spot_balance.py
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
    
    # Get protocol values for active chains
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
    
    # Create the final result
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
    
    # Save the result to a JSON file
    with open('debank/data/portfolio_cache.json', 'w') as f:
        json.dump(final_result, f, indent=2)
    print("\nResults saved to debank/data/portfolio_cache.json")
    
    return final_result

if __name__ == "__main__":
    print("\nStarting protocol analysis...")
    
    # Ethereum address to check
    address = "0xc6835323372a4393b90bcc227c58e82d45ce4b7d"
    print(f"Analyzing address: {address}")
    
    # Get all protocol values
    final_result = get_all_protocol_values(address)
    
    if final_result:
        # Print the final dictionary
        print("\nFinal result:")
        print(json.dumps(final_result, indent=2))
    
    print("\nAnalysis complete!") 