import requests
from typing import Dict, Optional

class PriceFetcher:
    def __init__(self):
        self.base_url = "https://api.coingecko.com/api/v3"
        self.cache: Dict[str, float] = {}
    
    def get_price(self, coin_id: str) -> float:
        """
        Retrieves a token's price from CoinGecko
        
        Args:
            coin_id: CoinGecko token identifier (e.g., 'usd-coin')
            
        Returns:
            float: Token price in USD
            
        Raises:
            Exception: If the request fails
        """
        # Check if price is in cache
        if coin_id in self.cache:
            return self.cache[coin_id]
        
        # Make API request
        url = f"{self.base_url}/simple/price?ids={coin_id}&vs_currencies=usd"
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            price = data[coin_id]['usd']
            # Cache the price
            self.cache[coin_id] = price
            return price
        else:
            raise Exception(f"Error retrieving price: {response.status_code}")
    
    def get_prices(self, coin_ids: list[str]) -> Dict[str, float]:
        """
        Retrieves prices for multiple tokens in a single request
        
        Args:
            coin_ids: List of CoinGecko identifiers
            
        Returns:
            Dict[str, float]: Dictionary of prices {coin_id: price}
        """
        # Filter coins that are not in cache
        coins_to_fetch = [coin_id for coin_id in coin_ids if coin_id not in self.cache]
        
        if coins_to_fetch:
            # Make request for non-cached coins
            url = f"{self.base_url}/simple/price?ids={','.join(coins_to_fetch)}&vs_currencies=usd"
            response = requests.get(url)
            
            if response.status_code == 200:
                data = response.json()
                # Update cache
                self.cache.update({coin_id: data[coin_id]['usd'] for coin_id in coins_to_fetch})
            else:
                raise Exception(f"Error retrieving prices: {response.status_code}")
        
        # Return all requested prices (from cache)
        return {coin_id: self.cache[coin_id] for coin_id in coin_ids} 