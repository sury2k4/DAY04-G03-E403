from __future__ import annotations

from typing import Any
import requests

from tools._shared import TIMEOUT, err


SYMBOL_MAP = {
    "btc": "bitcoin",
    "bitcoin": "bitcoin",
    "eth": "ethereum",
    "ethereum": "ethereum",
    "sol": "solana",
    "solana": "solana",
    "bnb": "binancecoin",
    "xrp": "ripple",
    "doge": "dogecoin",
    "ada": "cardano",
}


def get_crypto_price(symbol: str = "btc", currency: str = "usd") -> dict[str, Any]:
    """Tra cứu giá cryptocurrency theo symbol và currency."""
    try:
        clean_symbol = str(symbol).strip().lower()
        clean_currency = str(currency).strip().lower() or "usd"
        coin_id = SYMBOL_MAP.get(clean_symbol, clean_symbol)

        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies={clean_currency}"
        response = requests.get(url, timeout=TIMEOUT)
        
        if response.status_code == 200:
            data = response.json()
            if coin_id in data and clean_currency in data[coin_id]:
                price = data[coin_id][clean_currency]
                return {
                    "tool": "get_crypto_price",
                    "symbol": clean_symbol,
                    "coin_id": coin_id,
                    "currency": clean_currency,
                    "price": price,
                    "error": None,
                }

        # Fallback API (CoinCap) if CoinGecko rate-limits
        fallback_url = f"https://api.coincap.io/v2/assets/{coin_id}"
        fb_resp = requests.get(fallback_url, timeout=TIMEOUT)
        if fb_resp.status_code == 200:
            fb_data = fb_resp.json().get("data", {})
            price_usd = float(fb_data.get("priceUsd", 0))
            return {
                "tool": "get_crypto_price",
                "symbol": clean_symbol,
                "coin_id": coin_id,
                "currency": "usd",
                "price": price_usd,
                "error": None,
            }

        return {
            "tool": "get_crypto_price",
            "symbol": clean_symbol,
            "currency": clean_currency,
            "price": None,
            "error": f"Price not found for symbol '{symbol}'",
        }
    except Exception as exc:
        return err("get_crypto_price", exc)
