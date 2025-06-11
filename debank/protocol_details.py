import requests
import os
import json
import time
from datetime import datetime
from dotenv import load_dotenv
from debank.complex_protocol_list import get_all_protocol_values

# Load environment variables from .env file
load_dotenv()

def verify_portfolio_cache():
    """
    Verifies that portfolio_cache.json has been written correctly
    Returns True if the file exists and contains valid data
    """
    try:
        with open('debank/data/portfolio_cache.json', 'r') as f:
            data = json.load(f)
            return bool(data and "protocols" in data)
    except (json.JSONDecodeError, FileNotFoundError):
        return False

def convert_timestamp_to_utc(timestamp):
    """
    Convert a Unix timestamp to UTC datetime string.
    
    Args:
        timestamp (float): Unix timestamp
    
    Returns:
        str: UTC datetime string in format 'YYYY-MM-DD HH:MM:SS UTC'
    """
    return datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S UTC')

def get_protocol_details(address, protocol_id, chain_id):
    """
    Retrieves detailed information about a specific protocol for a user.
    
    Args:
        address (str): User's address
        protocol_id (str): Protocol identifier (e.g., convex, equilibria)
        chain_id (str): Chain ID (e.g., eth, base)
    
    Returns:
        dict: Dictionary containing protocol details and user positions
    """
    # Get API key from environment variables
    access_key = os.getenv('DEBANK_ACCESS_KEY')
    if not access_key:
        raise ValueError("DeBank API key is not defined in .env file")

    # Configure Pro API URL
    url = "https://pro-openapi.debank.com/v1/user/protocol"
    
    # Request parameters
    params = {
        "id": address,
        "protocol_id": protocol_id,
        "chain_id": chain_id
    }
    
    # Request headers with access key
    headers = {
        "accept": "application/json",
        "AccessKey": access_key
    }
    
    try:
        # Send GET request with parameters
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
        # Check if request was successful
        response.raise_for_status()
        
        data = response.json()
        
        # Convert update_at timestamps to UTC format
        if "portfolio_item_list" in data:
            for item in data["portfolio_item_list"]:
                if "update_at" in item:
                    item["update_at"] = convert_timestamp_to_utc(item["update_at"])
        
        return data
    
    except requests.exceptions.RequestException as e:
        print(f"Error during API request for protocol {protocol_id} on {chain_id}: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Error details: {e.response.text}")
        return {}

def get_all_protocol_details(address):
    """
    Retrieves detailed information about all protocols for a given address.
    
    Args:
        address (str): The Ethereum address to analyze
        
    Returns:
        dict: A dictionary containing:
            - address: The analyzed address
            - script_execution_time: Timestamp of the analysis
            - network_totals: Dictionary with total values per network
            - protocols: Dictionary with detailed protocol information
            - spot: Dictionary containing spot token information from portfolio_cache.json
    """
    # First, update portfolio_cache.json
    get_all_protocol_values(address)
    
    # Vérifier que le fichier a été écrit correctement
    if not verify_portfolio_cache():
        print("Warning: Could not verify portfolio_cache.json was written correctly")
        return None
    
    # Read the analysis data
    with open('debank/data/portfolio_cache.json', 'r') as f:
        analysis_data = json.load(f)
    
    # Get script execution timestamp
    script_timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
    
    # Initialize network totals dynamically from spot data
    network_totals = {
        "total_usd": analysis_data["spot"]["totals"]["total_usd"]
    }
    
    # Add network-specific totals from spot data
    for network in analysis_data["spot"]["tokens"].keys():
        network_totals[f"{network}_usd"] = analysis_data["spot"]["totals"][f"{network}_usd"]
    
    # Get details for each protocol
    protocol_details = {}
    
    # Process each protocol from the analysis data
    for protocol_id, protocol_info in analysis_data["protocols"].items():
        chain_id = protocol_info["chain_id"]
        details = get_protocol_details(address, protocol_id, chain_id=chain_id)
        if details:
            details["chain_id"] = chain_id
            protocol_details[protocol_id] = details
            # Add to network total
            for item in details.get("portfolio_item_list", []):
                network_totals[f"{chain_id}_usd"] += item.get("stats", {}).get("net_usd_value", 0)
                network_totals["total_usd"] += item.get("stats", {}).get("net_usd_value", 0)
    
    # Create the final result
    final_result = {
        "address": address,
        "script_execution_time": script_timestamp,
        "network_totals": network_totals,
        "protocols": protocol_details,
        "spot": analysis_data["spot"]  # Include spot data from portfolio_cache.json
    }
    
    # Save the result to a JSON file
    output_file = 'debank/data/portfolio_live.json'
    with open(output_file, 'w') as f:
        json.dump(final_result, f, indent=2)
    print(f"\nResults saved to {output_file}")
    
    return final_result

if __name__ == "__main__":
    print("\n=== Starting Protocol Details Analysis ===")
    
    # Ethereum address to check
    address = "0xc6835323372a4393b90bcc227c58e82d45ce4b7d"
    print(f"\nAnalyzing address: {address}")
    
    # Get all protocol details
    all_details = get_all_protocol_details(address)
    
    if all_details:
        print("\n=== Analysis Summary ===")
        print(f"Address: {all_details['address']}")
        print(f"Execution Time: {all_details['script_execution_time']}")
        
        print("\n=== Network Totals ===")
        for network, total in all_details['network_totals'].items():
            if network != 'total_usd':
                network_name = network.replace('_usd', '').upper()
                print(f"\n{network_name} Network:")
                # Get spot total for this network
                spot_total = all_details['spot']['totals'][network]
                protocol_total = total - spot_total
                print(f"- Protocol Value: ${protocol_total:,.2f}")
                print(f"- Spot Balance: ${spot_total:,.2f}")
                print(f"- Total Value: ${total:,.2f}")
        
        print(f"\nTotal Value Across All Networks: ${all_details['network_totals']['total_usd']:,.2f}")
        
        print("\n=== Protocols Found ===")
        for protocol_id, details in all_details['protocols'].items():
            # Calculate protocol total value
            protocol_value = sum(item.get("stats", {}).get("net_usd_value", 0) 
                               for item in details.get("portfolio_item_list", []))
            print(f"\n{protocol_id.upper()} ({details['chain_id']}):")
            print(f"- Value: ${protocol_value:,.2f}")
        
        print("\n=== Spot Tokens Summary ===")
        for network, tokens in all_details['spot']['tokens'].items():
            print(f"\n{network.upper()} Spot Tokens:")
            network_spot_total = 0
            for token in tokens:
                token_value = float(token['amount']) * float(token['price'])
                network_spot_total += token_value
                print(f"- {token['symbol']}: ${token_value:,.2f}")
            print(f"Total Spot Value: ${network_spot_total:,.2f}")
        
        print("\n=== Analysis Complete ===") 