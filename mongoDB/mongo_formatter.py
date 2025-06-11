import json
from datetime import datetime
from pathlib import Path
from pymongo import MongoClient
from dotenv import load_dotenv
import os
from decimal import Decimal

def extract_positions(portfolio_data):
    """
    Extract positions from protocols and spot balances
    Returns a dictionary of positions in the format:
    {
        "protocol.chain.token": "value",
        "spot.chain": "value"
    }
    Sorted by value in descending order
    """
    positions = {}
    
    # Process protocol positions
    for protocol_id, protocol in portfolio_data['protocols'].items():
        chain = protocol['chain']
        for item in protocol.get('portfolio_item_list', []):
            # Get token symbol from description or supply tokens
            token_symbol = ""
            detail = item.get('detail', {})
            
            # Try to get symbol from description first
            if 'description' in detail:
                token_symbol = detail['description']
            # If no description, use all supply tokens
            elif 'supply_token_list' in detail and detail['supply_token_list']:
                supply_tokens = detail['supply_token_list']
                # Combine all token symbols
                token_symbol = ''.join(token.get('symbol', '') for token in supply_tokens)
            
            if not token_symbol:
                continue
            
            # Create position key and add value
            position_key = f"{protocol_id}.{chain}.{token_symbol}"
            value = item.get('stats', {}).get('net_usd_value', 0)
            if value > 0:
                positions[position_key] = value  # Store as float for sorting
    
    # Process spot positions
    for chain, tokens in portfolio_data['spot']['tokens'].items():
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
    """
    if isinstance(value, (int, float)):
        # Convert to float for MongoDB compatibility
        return float(value)
    elif isinstance(value, dict):
        return {k: convert_to_mongo_compatible(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [convert_to_mongo_compatible(item) for item in value]
    return value

def format_for_mongodb():
    """
    Format portfolio data for MongoDB storage
    """
    # Load environment variables
    load_dotenv()
    
    # Get MongoDB configuration from environment variables and config
    mongo_uri = os.getenv('MONGO_URI')
    collection_name = os.getenv('COLLECTION_NAME')
    
    # Load config.json
    with open('config.json', 'r') as f:
        config = json.load(f)
    database_name = config['database_name']
    
    if not all([mongo_uri, database_name, collection_name]):
        raise ValueError("Missing MongoDB configuration. Please check MONGO_URI, database_name in config.json, and COLLECTION_NAME")
    
    # Read portfolio data
    portfolio_path = Path(__file__).parent.parent / 'nav' / 'data' / 'portfolio_processed.json'
    with open(portfolio_path, 'r') as f:
        portfolio_data = json.load(f)
    
    # Extract positions
    positions = extract_positions(portfolio_data)
    
    # Format data for MongoDB - preserve exact structure and add timestamp
    formatted_data = {
        'address': portfolio_data['address'],
        'vault_address': portfolio_data['vault_address'],
        'script_execution_time': portfolio_data['script_execution_time'],
        'timestamp': datetime.utcnow(),
        'underlying_asset': portfolio_data['underlying_asset'],
        'nav': convert_to_mongo_compatible(portfolio_data['nav']),
        'positions': positions,
        'network_totals': convert_to_mongo_compatible(portfolio_data['network_totals']),
        'protocols': convert_to_mongo_compatible(portfolio_data['protocols']),
        'spot': convert_to_mongo_compatible(portfolio_data['spot'])
    }
    
    # Save formatted data to file first
    output_path = Path(__file__).parent / 'data' / 'portfolio_mongo.json'
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(formatted_data, f, indent=2, default=str)
    
    print(f"Data saved to {output_path}")
    
    try:
        # Connect to MongoDB
        client = MongoClient(mongo_uri)
        db = client[database_name]
        
        # Insert into MongoDB
        collection = db[collection_name]
        result = collection.insert_one(formatted_data)
        print(f"\n=== Data Inserted into MongoDB ===")
        print(f"Document ID: {result.inserted_id}")
        print(f"Database: {database_name}")
        print(f"Collection: {collection_name}")
        
        return True
        
    except Exception as e:
        print(f"Error during MongoDB insertion: {str(e)}")
        return False

if __name__ == "__main__":
    format_for_mongodb() 