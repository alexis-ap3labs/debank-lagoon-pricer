"""
Protocol Details Module for DeBank API Integration

This module provides functionality to retrieve detailed information about specific
protocol positions for cryptocurrency addresses. It builds upon the complex protocol
list analysis to fetch granular details about each protocol position.

Key Features:
- Retrieve detailed protocol information from DeBank Pro API
- Convert Unix timestamps to human-readable UTC format
- Aggregate protocol details across multiple networks
- Generate comprehensive portfolio analysis reports
- Integrate with portfolio cache for complete analysis

Dependencies:
- requests: For HTTP API calls to DeBank
- python-dotenv: For environment variable management
- datetime: For timestamp conversion and handling
- json: For data serialization/deserialization
- debank.complex_protocol_list: For initial protocol analysis
"""

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
    Verifies that portfolio_cache.json has been written correctly with valid data structure
    
    This function performs a basic integrity check to ensure the portfolio cache file
    was written successfully and contains the expected data structure with protocols.
    
    Returns:
        bool: True if file exists and contains valid data structure, False otherwise
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
    
    This utility function converts DeBank's Unix timestamp format to a human-readable
    UTC datetime string for better data presentation and analysis.
    
    Args:
        timestamp (float): Unix timestamp from DeBank API
        
    Returns:
        str: UTC datetime string in format 'YYYY-MM-DD HH:MM:SS UTC'
        
    Example:
        >>> convert_timestamp_to_utc(1640995200)
        '2022-01-01 00:00:00 UTC'
    """
    return datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S UTC')

def get_protocol_details(address, protocol_id, chain_id):
    """
    Retrieves detailed information about a specific protocol for a user.
    
    This function makes a direct API call to DeBank Pro to get comprehensive
    information about a specific protocol position, including all portfolio items,
    token details, and position statistics.
    
    Args:
        address (str): The cryptocurrency address to query (e.g., "0x1234...")
        protocol_id (str): Protocol identifier (e.g., "convex", "equilibria", "aave")
        chain_id (str): The blockchain network identifier (e.g., "eth", "base", "bsc")
    
    Returns:
        dict: Dictionary containing detailed protocol information including:
            - id: Protocol identifier
            - name: Protocol name
            - site_url: Protocol website URL
            - logo_url: Protocol logo URL
            - portfolio_item_list: List of user positions in the protocol
            - tvl: Total Value Locked in the protocol
            - has_supported_portfolio: Whether portfolio is supported
            
    Raises:
        ValueError: If DeBank API key is not configured in environment variables
        
    Example:
        >>> details = get_protocol_details("0x1234...", "convex", "eth")
        >>> print(f"Protocol: {details['name']}")
    """
    # Get API key from environment variables
    access_key = os.getenv('DEBANK_ACCESS_KEY')
    if not access_key:
        raise ValueError("DeBank API key is not defined in .env file")

    # DeBank Pro API endpoint for protocol details
    url = "https://pro-openapi.debank.com/v1/user/protocol"
    
    # Request parameters for the API call
    params = {
        "id": address,
        "protocol_id": protocol_id,
        "chain_id": chain_id
    }
    
    # Headers required for DeBank Pro API authentication
    headers = {
        "accept": "application/json",
        "AccessKey": access_key
    }
    
    try:
        # Send GET request with parameters and timeout
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
        # Check if request was successful (status code 200)
        response.raise_for_status()
        
        # Parse JSON response from DeBank API
        data = response.json()
        
        # Convert update_at timestamps to UTC format for better readability
        if "portfolio_item_list" in data:
            for item in data["portfolio_item_list"]:
                if "update_at" in item:
                    item["update_at"] = convert_timestamp_to_utc(item["update_at"])
        
        return data
    
    except requests.exceptions.RequestException as e:
        # Handle network errors, timeouts, and API errors
        print(f"Error during API request for protocol {protocol_id} on {chain_id}: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Error details: {e.response.text}")
        return {}

def get_all_protocol_details(address):
    """
    Retrieves detailed information about all protocols for a given address.
    
    This is the main function that orchestrates the complete protocol details analysis.
    It integrates with the complex protocol list module to get a comprehensive view
    of all protocol positions and their detailed information.
    
    Args:
        address (str): The cryptocurrency address to analyze
        
    Returns:
        dict: Complete protocol analysis containing:
            - address: The analyzed address
            - script_execution_time: Timestamp of when the analysis was performed
            - network_totals: Dictionary with total values per network and total
            - protocols: Dictionary with detailed protocol information for each protocol
            - spot: Dictionary containing spot token information from portfolio cache
            
    Example:
        >>> analysis = get_all_protocol_details("0x1234...")
        >>> print(f"Total protocols found: {len(analysis['protocols'])}")
    """
    # First, update portfolio_cache.json using complex protocol list module
    get_all_protocol_values(address)
    
    # Verify that the portfolio cache file was written correctly
    if not verify_portfolio_cache():
        print("Warning: Could not verify portfolio_cache.json was written correctly")
        return None
    
    # Read the analysis data from the portfolio cache
    with open('debank/data/portfolio_cache.json', 'r') as f:
        analysis_data = json.load(f)
    
    # Get script execution timestamp for tracking
    script_timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
    
    # Initialize network totals dynamically from spot data
    network_totals = {
        "total_usd": analysis_data["spot"]["totals"]["total_usd"]
    }
    
    # Add network-specific totals from spot data
    for network in analysis_data["spot"]["tokens"].keys():
        network_totals[f"{network}_usd"] = analysis_data["spot"]["totals"][f"{network}_usd"]
    
    # Initialize storage for protocol details
    protocol_details = {}
    
    # Process each protocol from the analysis data
    for protocol_id, protocol_info in analysis_data["protocols"].items():
        chain_id = protocol_info["chain_id"]
        # Get detailed information for this specific protocol
        details = get_protocol_details(address, protocol_id, chain_id=chain_id)
        if details:
            details["chain_id"] = chain_id
            protocol_details[protocol_id] = details
            # Add protocol values to network totals
            for item in details.get("portfolio_item_list", []):
                network_totals[f"{chain_id}_usd"] += item.get("stats", {}).get("net_usd_value", 0)
                network_totals["total_usd"] += item.get("stats", {}).get("net_usd_value", 0)
    
    # Create the final comprehensive result
    final_result = {
        "address": address,
        "script_execution_time": script_timestamp,
        "network_totals": network_totals,
        "protocols": protocol_details,
        "spot": analysis_data["spot"]  # Include spot data from portfolio cache
    }
    
    # Save the complete analysis to portfolio_live.json
    output_file = 'debank/data/portfolio_live.json'
    with open(output_file, 'w') as f:
        json.dump(final_result, f, indent=2)
    print(f"\nResults saved to {output_file}")
    
    return final_result

if __name__ == "__main__":
    """
    Main execution block for testing the protocol details functionality
    
    This block runs when the script is executed directly (not imported as a module).
    It demonstrates how to use the get_all_protocol_details function with a sample
    address and provides a comprehensive analysis summary.
    """
    print("\n=== Starting Protocol Details Analysis ===")
    
    # Ethereum address to check (example address)
    address = "0xc6835323372a4393b90bcc227c58e82d45ce4b7d"
    print(f"\nAnalyzing address: {address}")
    
    # Get all protocol details for the address
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
        # Display spot token summary
        spot_totals = all_details['spot']['totals']
        for network, total in spot_totals.items():
            if network != 'total_usd':
                network_name = network.replace('_usd', '').upper()
                print(f"{network_name} Spot Balance: ${total:,.2f}")
        
        print(f"Total Spot Balance: ${spot_totals['total_usd']:,.2f}")
        
        print("\n=== Analysis Complete ===")
    else:
        print("Analysis failed. Please check your configuration and try again.") 