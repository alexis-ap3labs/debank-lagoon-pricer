# DeBank USDC Portfolio Analyzer

This project analyzes DeFi portfolios on DeBank, with a particular focus on USDC positions. It calculates the NAV (Net Asset Value) and stores data in MongoDB.

## Requirements

- Python 3.x
- MongoDB
- DeBank Pro API Key
- Base RPC Access

## Installation

1. Clone the repository:
```bash
git clone https://github.com/your-username/debank-usdc.git
cd debank-usdc
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

### Local Execution

To run the analysis:
```bash
python mongoDB/get_protocol_details.py
```

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
debank-usdc/
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
- USDC NAV calculation
- Multi-chain position tracking
- MongoDB data storage
- GitHub Actions integration for automation

## Security

- API keys and sensitive information are stored in environment variables
- `.env` file is not versioned
- Sensitive data is excluded from Git tracking

## Contributing

Contributions are welcome! Feel free to:
1. Fork the project
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

## License

MIT 