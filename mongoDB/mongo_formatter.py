"""
MongoDB Formatter Module for Portfolio Data Storage

This module provides functionality to format and store portfolio analysis data in MongoDB.
It handles data transformation, type conversion, and database operations for the
complete portfolio analysis results.

Key Features:
- Extract and format position data from portfolio analysis
- Convert data types for MongoDB compatibility
- Store comprehensive portfolio data in MongoDB
- Generate position summaries with proper formatting
- Handle database connection and error management

Data Structure:
- Portfolio metadata (address, vault, timestamp)
- NAV calculations (USD, underlying asset, share price)
- Position breakdowns (protocol and spot positions)
- Network totals and protocol details
- Spot token information

Dependencies:
- pymongo: For MongoDB database operations
- python-dotenv: For environment variable management
- web3: For address validation and formatting
- pathlib: For file path management
- debank.protocol_details: For protocol analysis
- nav.process_portfolio: For NAV calculation
"""

import json
from datetime import datetime
from pathlib import Path
from pymongo import MongoClient
from dotenv import load_dotenv
import os
from decimal import Decimal
from web3 import Web3

# Add parent directory to PYTHONPATH for module imports
import sys
sys.path.append(str(Path(__file__).parent.parent))

from debank.protocol_details import get_all_protocol_details
from nav.process_portfolio import process_portfolio

def extract_positions(portfolio_data):
    """
    Extract positions from protocols and spot balances with proper formatting
    
    This function processes the portfolio data to extract all positions (both protocol
    and spot) and formats them into a standardized structure for MongoDB storage.
    Positions are sorted by value in descending order for easy analysis.
    
    Args:
        portfolio_data (dict): Complete portfolio data containing protocols and spot information
        
    Returns:
        dict: Dictionary of positions sorted by value in descending order with format:
            {
                "protocol.chain.token": "value",
                "spot.chain": "value"
            }
            
    Example:
        >>> positions = extract_positions(portfolio_data)
        >>> print(f"Largest position: {list(positions.keys())[0]}")
        'convex.eth.USDC-USDT'
    """
    positions = {}
    
    # Process protocol positions from all protocols
    for protocol_id, protocol in portfolio_data['protocols'].items():
        chain = protocol['chain']
        for item in protocol.get('portfolio_item_list', []):
            # Extract token symbol from description or supply tokens
            token_symbol = ""
            detail = item.get('detail', {})
            
            # Try to get symbol from description first (most reliable)
            if 'description' in detail:
                token_symbol = detail['description']
            # If no description, use all supply tokens
            elif 'supply_token_list' in detail and detail['supply_token_list']:
                supply_tokens = detail['supply_token_list']
                # Combine all token symbols for multi-token positions
                token_symbol = ''.join(token.get('symbol', '') for token in supply_tokens)
            
            # Skip positions without valid token symbols
            if not token_symbol:
                continue
            
            # Create position key and add value if positive
            position_key = f"{protocol_id}.{chain}.{token_symbol}"
            value = item.get('stats', {}).get('net_usd_value', 0)
            if value > 0:
                positions[position_key] = value  # Store as float for sorting
    
    # Process spot positions from all networks
    for chain, tokens in portfolio_data['spot']['tokens'].items():
        # Calculate total spot value for each chain
        spot_total = sum(float(token['amount']) * float(token['price']) for token in tokens)
        if spot_total > 0:
            positions[f"spot.{chain}"] = spot_total  # Store as float for sorting
    
    # Sort positions by value in descending order and convert to formatted strings
    sorted_positions = {
        k: f"{v:.6f}" 
        for k, v in sorted(positions.items(), key=lambda x: x[1], reverse=True)
    }
    
    return sorted_positions

def convert_to_mongo_compatible(value):
    """
    Convert values to MongoDB compatible types
    
    This function recursively converts data types to ensure compatibility with MongoDB.
    It handles nested dictionaries and lists, converting numeric types to float
    for consistent storage.
    
    Args:
        value: The value to convert (can be any type)
        
    Returns:
        MongoDB compatible value with proper type conversion
        
    Example:
        >>> convert_to_mongo_compatible({"amount": 100, "price": 1.5})
        {"amount": 100.0, "price": 1.5}
    """
    if isinstance(value, (int, float)):
        # Convert to float for MongoDB compatibility
        return float(value)
    elif isinstance(value, dict):
        # Recursively convert dictionary values
        return {k: convert_to_mongo_compatible(v) for k, v in value.items()}
    elif isinstance(value, list):
        # Recursively convert list items
        return [convert_to_mongo_compatible(item) for item in value]
    return value

def format_for_mongodb():
    """
    Format portfolio data for MongoDB storage
    
    This is the main function that orchestrates the complete data formatting and
    storage process. It performs the following steps:
    1. Loads configuration and environment variables
    2. Retrieves protocol details and processes portfolio
    3. Extracts and formats position data
    4. Converts data types for MongoDB compatibility
    5. Stores data in MongoDB and saves to local file
    
    Configuration Requirements:
    - .env file must contain MONGO_URI and COLLECTION_NAME
    - config.json must contain database_name and wallet_address
    - DeBank API key must be configured in .env
    
    Returns:
        bool: True if successful, False if error occurred
        
    Raises:
        ValueError: If required configuration is missing
        
    Example:
        >>> success = format_for_mongodb()
        >>> print(f"Storage successful: {success}")
        True
    """
    # Load environment variables from .env file
    load_dotenv()
    
    # Get MongoDB configuration from environment variables and config
    mongo_uri = os.getenv('MONGO_URI')
    collection_name = os.getenv('COLLECTION_NAME')
    
    # Load configuration from config.json
    with open('config.json', 'r') as f:
        config = json.load(f)
    database_name = config['database_name']
    wallet_address = Web3.to_checksum_address(config['wallet_address'])
    
    # Validate that all required configuration is present
    if not all([mongo_uri, database_name, collection_name]):
        raise ValueError("Missing MongoDB configuration. Please check MONGO_URI, database_name in config.json, and COLLECTION_NAME")
    
    # Get protocol details directly from DeBank API
    portfolio_data = get_all_protocol_details(wallet_address)
    
    # Process portfolio for NAV calculation
    process_portfolio()
    
    # Read processed portfolio data from the generated file
    portfolio_path = Path(__file__).parent.parent / 'nav' / 'data' / 'portfolio_processed.json'
    with open(portfolio_path, 'r') as f:
        portfolio_data = json.load(f)
    
    # Extract and format position data
    positions = extract_positions(portfolio_data)
    
    # Format data for MongoDB - preserve exact structure and add timestamp
    formatted_data = {
        'address': portfolio_data['address'],
        'vault_address': portfolio_data['vault_address'],
        'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'),
        'underlying_asset': portfolio_data['underlying_asset'],
        'nav': convert_to_mongo_compatible(portfolio_data['nav']),
        'positions': positions,
        'network_totals': convert_to_mongo_compatible(portfolio_data['network_totals']),
        'protocols': convert_to_mongo_compatible(portfolio_data['protocols']),
        'spot': convert_to_mongo_compatible(portfolio_data['spot'])
    }
    
    # Save formatted data to local file for backup and debugging
    output_path = Path(__file__).parent / 'data' / 'portfolio_mongo.json'
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(formatted_data, f, indent=2, default=str)
    
    print(f"Data saved to {output_path}")
    
    try:
        # Connect to MongoDB using the provided URI
        client = MongoClient(mongo_uri)
        db = client[database_name]
        
        # Insert formatted data into the specified collection
        collection = db[collection_name]
        result = collection.insert_one(formatted_data)
        
        # Display successful insertion details
        print(f"\n=== Data Inserted into MongoDB ===")
        print(f"Document ID: {result.inserted_id}")
        print(f"Database: {database_name}")
        print(f"Collection: {collection_name}")
        
        return True
        
    except Exception as e:
        # Handle and display any errors during MongoDB insertion
        print(f"Error during MongoDB insertion: {str(e)}")
        return False

if __name__ == "__main__":
    """
    Main execution block for MongoDB formatter
    
    This block runs when the script is executed directly (not imported as a module).
    It calls the format_for_mongodb function to process and store portfolio data.
    """
    format_for_mongodb() 