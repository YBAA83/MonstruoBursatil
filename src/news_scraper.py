import os
import requests
from dotenv import load_dotenv

load_dotenv()

class NewsScraper:
    def __init__(self):
        self.api_key = os.getenv("CRYPTOPANIC_API_KEY")
        self.base_url = "https://cryptopanic.com/api/v1/posts/"

    def get_news_for_asset(self, symbol="BTC"):
        """
        Fetches latest news for a specific asset from CryptoPanic.
        """
        if not self.api_key:
            print("Warning: CRYPTOPANIC_API_KEY not found. Returning empty news.")
            return []

        # CryptoPanic uses currency codes, so strip USDT/BTC suffix if needed
        currency = symbol.replace("USDT", "").replace("BTC", "") # diligent cleanup
        if currency == "": currency = "BTC" # Default fallback
        
        params = {
            "auth_token": self.api_key,
            "currencies": currency,
            "kind": "news",
            "filter": "important"
        }
        
        try:
            response = requests.get(self.base_url, params=params)
            if response.status_code != 200:
                print(f"Error CryptoPanic: Status {response.status_code}")
                return []
                
            data = response.json()
            if "results" in data:
                return data["results"][:5]
            return []
        except requests.exceptions.JSONDecodeError:
            print(f"Error: Respuesta inválida de CryptoPanic (no JSON)")
            return []
        except Exception as e:
            print(f"Error fetching news for {symbol}: {e}")
            return []

if __name__ == "__main__":
    scraper = NewsScraper()
    print(scraper.get_news_for_asset("BTCUSDT"))
