"""
Vault Supply Reader Module for Blockchain Integration

This module provides functionality to read vault supply information directly from
the blockchain. It handles address validation, Web3 connections, and smart contract
interactions to retrieve total supply data for NAV calculations.

Key Features:
- Read total supply from vault smart contract
- Validate and clean Ethereum addresses
- Handle Web3 connections to Base network
- Convert raw supply values to human-readable format
- Update NAV calculations with current supply data

Blockchain Integration:
- Connects to Base mainnet RPC endpoint
- Interacts with ERC20 totalSupply() function
- Handles address validation and checksum formatting
- Converts wei to decimal format (1e18 division)

Dependencies:
- web3: For blockchain interactions and address validation
- json: For configuration file handling
- os: For environment variable access
"""

import os
from web3 import Web3
import json

def clean_address(address):
    """
    Clean the address by removing any invisible characters and spaces
    
    This function sanitizes Ethereum addresses by removing whitespace and
    non-hexadecimal characters while preserving the 0x prefix.
    
    Args:
        address (str): Raw address string that may contain formatting issues
        
    Returns:
        str: Cleaned address string with only valid hex characters
        
    Example:
        >>> clean_address(" 0x1234abcd... ")
        '0x1234abcd...'
    """
    # Remove any whitespace from the address
    address = address.strip()
    # Remove any non-hex characters except 0x prefix
    if address.startswith('0x'):
        address = '0x' + ''.join(c for c in address[2:] if c in '0123456789abcdefABCDEF')
    return address

def is_valid_ethereum_address(address):
    """
    Check if the address is a valid Ethereum address
    
    This function performs comprehensive validation of Ethereum addresses including:
    - Type checking (must be string)
    - Length validation (42 characters including 0x)
    - Checksum validation using Web3
    
    Args:
        address (str): Address string to validate
        
    Returns:
        bool: True if address is valid, False otherwise
        
    Example:
        >>> is_valid_ethereum_address("0x1234567890123456789012345678901234567890")
        True
        >>> is_valid_ethereum_address("invalid_address")
        False
    """
    if not isinstance(address, str):
        return False
    
    # Clean the address first to remove formatting issues
    address = clean_address(address)
    
    # Check for 0x prefix
    if not address.startswith('0x'):
        return False
    # Check length (0x + 40 hex characters = 42 total)
    if len(address) != 42:
        print(f"Address length: {len(address)}")  # Debug print
        return False
    try:
        # Try to convert to checksum address for final validation
        Web3.to_checksum_address(address)
        return True
    except ValueError:
        return False

def get_vault_supply():
    """
    Read total supply from vault smart contract on Base network
    
    This function connects to the Base mainnet and calls the totalSupply()
    function on the vault contract to get the current total supply of vault tokens.
    
    Configuration Requirements:
    - config.json must contain vault_address field
    - Base RPC endpoint must be accessible
    
    Returns:
        float: Total supply in decimal format (divided by 1e18)
        
    Raises:
        Exception: If unable to connect to Base RPC
        ValueError: If vault address is invalid
        Exception: If contract call fails
        
    Example:
        >>> supply = get_vault_supply()
        >>> print(f"Total vault supply: {supply:.2f}")
        309698.31
    """
    # Initialize Web3 connection with Base RPC endpoint
    RPC_URL = "https://mainnet.base.org"
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    
    # Verify connection to Base network
    if not w3.is_connected():
        raise Exception("Unable to connect to Base RPC")
    
    # Load configuration to get vault address
    with open('config.json', 'r') as f:
        config = json.load(f)
    vault_address = config['vault_address']
    
    # Clean and validate the vault address
    vault_address = clean_address(vault_address)
    print(f"Cleaned address: {vault_address}")  # Debug print
    print(f"Address length: {len(vault_address)}")  # Debug print
    
    # Validate address format and checksum
    if not is_valid_ethereum_address(vault_address):
        raise ValueError(f"Invalid vault address: {vault_address}. Must be a valid Ethereum address (42 characters including '0x')")
    
    # Convert address to checksum format for contract interaction
    vault_address = Web3.to_checksum_address(vault_address)
    
    # Minimal ABI for totalSupply function (ERC20 standard)
    vault_abi = [
        {
            "constant": True,
            "inputs": [],
            "name": "totalSupply",
            "outputs": [{"name": "", "type": "uint256"}],
            "type": "function"
        }
    ]
    
    # Create contract instance for interaction
    vault_contract = w3.eth.contract(address=vault_address, abi=vault_abi)
    
    try:
        # Call totalSupply function on the vault contract
        total_supply = vault_contract.functions.totalSupply().call()
        print(f"Raw total supply: {total_supply}")
        
        # Convert from wei to decimal format (divide by 1e18)
        formatted_supply = total_supply / 1e18
        print(f"Formatted total supply: {formatted_supply}")
        
        return formatted_supply
    except Exception as e:
        print(f"Error calling totalSupply: {str(e)}")
        raise

def update_nav_with_share_price():
    """
    Update NAV calculations with current share price and supply data
    
    This function reads the processed portfolio data, fetches current vault supply,
    and updates the NAV calculations with the latest share price information.
    
    Process:
    1. Read portfolio_processed.json file
    2. Get current vault supply from blockchain
    3. Calculate updated share price (NAV / supply)
    4. Update portfolio data with new metrics
    5. Save updated data back to file
    
    Requirements:
    - nav/data/portfolio_processed.json must exist
    - Vault contract must be accessible on Base network
    
    Output:
    - Updates nav/data/portfolio_processed.json with current share price
    - Displays updated metrics in console
        
    Raises:
        Exception: If file read/write fails or blockchain interaction fails
        
    Example:
        >>> update_nav_with_share_price()
        Share price: $1.036112
        Total supply: 309698.31
    """
    try:
        # Read existing portfolio_processed.json file
        with open('nav/data/portfolio_processed.json', 'r') as f:
            portfolio = json.load(f)
        
        # Get current vault supply from blockchain
        total_supply = get_vault_supply()
        
        # Calculate updated share price (NAV / total supply)
        nav_usd = portfolio['nav']['usd']
        share_price_usd = nav_usd / total_supply
        
        # Update NAV section with current share price and supply
        portfolio['nav']['share_price_usd'] = share_price_usd
        portfolio['nav']['total_supply'] = total_supply
        
        # Save updated portfolio data back to file
        with open('nav/data/portfolio_processed.json', 'w') as f:
            json.dump(portfolio, f, indent=2)
        
        # Display updated NAV metrics
        print(f"Share price: ${share_price_usd:.6f}")
        print(f"Total supply: {total_supply:.2f}")
    except Exception as e:
        print(f"Error updating NAV: {str(e)}")
        raise

if __name__ == "__main__":
    """
    Main execution block for supply reader
    
    This block runs when the script is executed directly (not imported as a module).
    It calls the update_nav_with_share_price function to update NAV calculations
    with current vault supply data.
    """
    update_nav_with_share_price() 