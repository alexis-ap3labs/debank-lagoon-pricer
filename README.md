# DeBank Lagoon Pricer

**Universal Vault Pricing Tool for Multi-Chain DeFi Protocols**

A sophisticated DeFi analytics platform that calculates Net Asset Value (NAV) for vault positions by pricing them in their underlying tokens. Specifically designed for Lagoon vaults across any blockchain network, with fully customizable configuration for seamless integration into your DeFi portfolio management workflow.

## Overview

This tool provides real-time NAV calculations for DeFi vault positions by:
- **Vault-to-Token Pricing**: Converts vault shares to underlying token values
- **Multi-Chain Support**: Works with Lagoon vaults on any blockchain network
- **Customizable Configuration**: Adaptable to different vault types and token pairs
- **Automated NAV Tracking**: Continuous monitoring and calculation of portfolio values

## Requirements

- Python 3.x
- MongoDB
- DeBank Pro API Key
- Base RPC Access

## Installation

1. Clone the repository:
```bash
git clone https://github.com/your-username/debank-lagoon-pricer.git
cd debank-lagoon-pricer
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables:
Create a `.env` file with the following variables:
```
DEBANK_ACCESS_KEY=your_debank_api_key
MONGO_URI=your_mongodb_uri
COLLECTION_NAME=your_collection_name
RPC_URL=your_base_rpc_url
```

4. Configure `config.json`:
```json
{
  "wallet_address": "0x...",
  "vault_address": "0x...",
  "asset": {
    "ticker": "USDC",
    "coingecko_id": "usd-coin"
  },
  "database_name": "your-database-name"
}
```

## Usage

### Local Execution Options

#### 1. Data Retrieval Only (Local Files)
To retrieve DeBank protocol data and save locally:
```bash
python mongoDB/get_protocol_details.py
```
This will create local JSON files with raw protocol data without NAV calculations.

#### 2. NAV Calculation (Local Files)
To process portfolio data and calculate NAV locally:
```bash
python nav/process_portfolio.py
```
This requires the protocol data to be retrieved first and generates NAV calculations in local files.

#### 3. Complete Analysis + MongoDB Storage
To run the complete analysis, NAV calculation, and push to MongoDB:
```bash
python mongoDB/mongo_formatter.py
```
This is the **main command** that orchestrates the entire process:
- Retrieves protocol data from DeBank
- Calculates NAV and processes portfolio
- Formats data for MongoDB
- Saves to both local files and MongoDB database

### Using GitHub Actions

1. Fork this repository
2. Configure the following GitHub secrets:
   - `DEBANK_ACCESS_KEY`
   - `MONGO_URI`
   - `COLLECTION_NAME`
   - `RPC_URL`
3. Use the webhook to trigger the analysis

## Project Structure

```
debank-lagoon-pricer/
├── .github/
│   └── workflows/
│       └── run-analysis.yml
├── debank/
│   ├── data/
│   ├── chain_balance.py
│   ├── complex_protocol_list.py
│   ├── protocol_details.py
│   └── spot_balance.py
├── mongoDB/
│   ├── data/
│   ├── get_protocol_details.py
│   └── mongo_formatter.py
├── nav/
│   ├── data/
│   ├── process_portfolio.py
│   ├── price_fetcher.py
│   └── supply_reader.py
├── .env
├── .gitignore
├── config.json
├── config.template.json
├── README.md
└── requirements.txt
```

## Features

- DeFi position analysis on DeBank
- Lagoon vault NAV calculation
- Multi-chain position tracking
- MongoDB data storage
- GitHub Actions integration for automation

## Security

- API keys and sensitive information are stored in environment variables
- `.env` file is not versioned
- Sensitive data is excluded from Git tracking

 