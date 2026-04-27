"""
Currency Conversion Module
Provides real-time forex rate conversion for multi-currency display
Supports: USD, ZAR, GBP, EUR, JPY, CNY, INR, AUD, CAD, SGD, HKD, MXN, BRL
"""

import os
import json
import requests
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from dataclasses import dataclass, asdict
import time

logger = logging.getLogger(__name__)

# Supported currencies
SUPPORTED_CURRENCIES = {
    'USD': {'name': 'US Dollar', 'symbol': '$'},
    'ZAR': {'name': 'South African Rand', 'symbol': 'R'},
    'GBP': {'name': 'British Pound', 'symbol': '£'},
    'EUR': {'name': 'Euro', 'symbol': '€'},
    'JPY': {'name': 'Japanese Yen', 'symbol': '¥'},
    'CNY': {'name': 'Chinese Yuan', 'symbol': '¥'},
    'INR': {'name': 'Indian Rupee', 'symbol': '₹'},
    'AUD': {'name': 'Australian Dollar', 'symbol': 'A$'},
    'CAD': {'name': 'Canadian Dollar', 'symbol': 'C$'},
    'SGD': {'name': 'Singapore Dollar', 'symbol': 'S$'},
    'HKD': {'name': 'Hong Kong Dollar', 'symbol': 'HK$'},
    'MXN': {'name': 'Mexican Peso', 'symbol': '$'},
    'BRL': {'name': 'Brazilian Real', 'symbol': 'R$'},
    'CHF': {'name': 'Swiss Franc', 'symbol': 'CHF'},
    'KRW': {'name': 'South Korean Won', 'symbol': '₩'},
}

# Base currency for conversions
BASE_CURRENCY = 'USD'

@dataclass
class ExchangeRate:
    """Exchange rate data"""
    from_currency: str
    to_currency: str
    rate: float
    timestamp: datetime
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class CurrencyConverter:
    """Handles real-time currency conversion with caching"""
    
    def __init__(self, api_key: Optional[str] = None, cache_ttl_minutes: int = 60):
        """
        Initialize currency converter
        
        Args:
            api_key: OpenExchangeRates API key (optional, uses free tier if not provided)
            cache_ttl_minutes: Cache time-to-live in minutes
        """
        self.api_key = api_key or os.environ.get('OPENEXCHANGE_API_KEY', '')
        self.cache_ttl = timedelta(minutes=cache_ttl_minutes)
        self.cache: Dict[str, ExchangeRate] = {}
        self.last_update: Optional[datetime] = None
        self._fallback_rates = self._get_fallback_rates()
        
    @staticmethod
    def _get_fallback_rates() -> Dict[str, float]:
        """Get fallback exchange rates if API is unavailable"""
        return {
            'USD/ZAR': 18.50,  # Approximate
            'USD/GBP': 0.79,
            'USD/EUR': 0.92,
            'USD/JPY': 149.50,
            'USD/CNY': 7.25,
            'USD/INR': 83.15,
            'USD/AUD': 1.53,
            'USD/CAD': 1.36,
            'USD/SGD': 1.34,
            'USD/HKD': 7.81,
            'USD/MXN': 17.05,
            'USD/BRL': 4.97,
            'USD/CHF': 0.88,
            'USD/KRW': 1310.00,
        }
    
    def get_rates(self, force_refresh: bool = False) -> Dict[str, float]:
        """
        Get current exchange rates from USD to all supported currencies
        
        Args:
            force_refresh: Force API call even if cache is valid
            
        Returns:
            Dict mapping "USD/XXX" to exchange rate
        """
        # Check cache validity
        if (not force_refresh and 
            self.last_update and 
            datetime.now() - self.last_update < self.cache_ttl and
            self.cache):
            logger.info("ℹ️  Using cached exchange rates")
            return self._cache_to_dict()
        
        # Try API first
        try:
            rates = self._fetch_from_api()
            if rates:
                self.last_update = datetime.now()
                self.cache = rates
                logger.info(f"✅ Fetched fresh exchange rates from API ({len(rates)} rates)")
                return self._cache_to_dict()
        except Exception as e:
            logger.warning(f"⚠️  API fetch failed: {e}, using fallback rates")
        
        # Fallback to hardcoded rates
        logger.warning("⚠️  Using fallback exchange rates (API unavailable)")
        self.last_update = datetime.now()
        return self._fallback_rates
    
    def _fetch_from_api(self) -> Optional[Dict[str, ExchangeRate]]:
        """Fetch rates from OpenExchangeRates API"""
        
        # List of free APIs to try
        apis = [
            self._fetch_from_openexchangerates,
            self._fetch_from_exchangerate_api,
            self._fetch_from_fixer,
        ]
        
        for fetch_fn in apis:
            try:
                rates = fetch_fn()
                if rates:
                    return rates
            except Exception as e:
                logger.debug(f"API {fetch_fn.__name__} failed: {e}")
                continue
        
        return None
    
    def _fetch_from_openexchangerates(self) -> Optional[Dict[str, ExchangeRate]]:
        """Fetch from OpenExchangeRates"""
        if not self.api_key:
            return None
            
        url = f'https://openexchangerates.org/api/latest.json'
        params = {
            'app_id': self.api_key,
            'base': BASE_CURRENCY,
            'symbols': ','.join(SUPPORTED_CURRENCIES.keys())
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get('error'):
            raise Exception(f"API Error: {data.get('error_description')}")
        
        rates = {}
        for currency, rate in data.get('rates', {}).items():
            key = f"{BASE_CURRENCY}/{currency}"
            rates[key] = ExchangeRate(
                from_currency=BASE_CURRENCY,
                to_currency=currency,
                rate=float(rate),
                timestamp=datetime.now()
            )
        
        return rates if rates else None
    
    def _fetch_from_exchangerate_api(self) -> Optional[Dict[str, ExchangeRate]]:
        """Fetch from ExchangeRate-API (free tier available)"""
        url = f'https://api.exchangerate-api.com/v4/latest/{BASE_CURRENCY}'
        
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        rates = {}
        for currency in SUPPORTED_CURRENCIES.keys():
            if currency in data.get('rates', {}):
                rate = data['rates'][currency]
                key = f"{BASE_CURRENCY}/{currency}"
                rates[key] = ExchangeRate(
                    from_currency=BASE_CURRENCY,
                    to_currency=currency,
                    rate=float(rate),
                    timestamp=datetime.now()
                )
        
        return rates if rates else None
    
    def _fetch_from_fixer(self) -> Optional[Dict[str, ExchangeRate]]:
        """Fetch from Fixer (free tier available)"""
        url = f'https://api.fixer.io/latest'
        params = {
            'base': BASE_CURRENCY,
            'symbols': ','.join(SUPPORTED_CURRENCIES.keys())
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        rates = {}
        for currency, rate in data.get('rates', {}).items():
            key = f"{BASE_CURRENCY}/{currency}"
            rates[key] = ExchangeRate(
                from_currency=BASE_CURRENCY,
                to_currency=currency,
                rate=float(rate),
                timestamp=datetime.now()
            )
        
        return rates if rates else None
    
    def _cache_to_dict(self) -> Dict[str, float]:
        """Convert cache to simple dict"""
        return {k: v.rate for k, v in self.cache.items()}
    
    def convert(self, amount: float, from_currency: str, to_currency: str, 
                force_refresh: bool = False) -> float:
        """
        Convert amount from one currency to another
        
        Args:
            amount: Amount to convert
            from_currency: Source currency code (e.g., 'USD')
            to_currency: Target currency code (e.g., 'ZAR')
            force_refresh: Force fresh rates
            
        Returns:
            Converted amount
        """
        if from_currency == to_currency:
            return amount
        
        rates = self.get_rates(force_refresh=force_refresh)
        
        # Convert via USD as base
        if from_currency != BASE_CURRENCY:
            # First convert to USD
            from_rate_key = f"{BASE_CURRENCY}/{from_currency}"
            if from_rate_key not in rates:
                logger.warning(f"⚠️  No rate for {from_rate_key}, using 1.0")
                from_rate = 1.0
            else:
                from_rate = rates[from_rate_key]
            amount_in_usd = amount / from_rate
        else:
            amount_in_usd = amount
        
        # Convert from USD to target
        if to_currency != BASE_CURRENCY:
            to_rate_key = f"{BASE_CURRENCY}/{to_currency}"
            if to_rate_key not in rates:
                logger.warning(f"⚠️  No rate for {to_rate_key}, using 1.0")
                to_rate = 1.0
            else:
                to_rate = rates[to_rate_key]
            return amount_in_usd * to_rate
        else:
            return amount_in_usd
    
    def get_rate(self, from_currency: str, to_currency: str, 
                 force_refresh: bool = False) -> Optional[float]:
        """
        Get exchange rate between two currencies
        
        Args:
            from_currency: Source currency
            to_currency: Target currency
            force_refresh: Force fresh rates
            
        Returns:
            Exchange rate or None if not available
        """
        if from_currency == to_currency:
            return 1.0
        
        rates = self.get_rates(force_refresh=force_refresh)
        
        # Try direct rate
        key = f"{from_currency}/{to_currency}"
        if key in rates:
            return rates[key]
        
        # Try reverse rate
        key_reverse = f"{to_currency}/{from_currency}"
        if key_reverse in rates:
            return 1.0 / rates[key_reverse]
        
        # Try via USD
        if from_currency != BASE_CURRENCY and to_currency != BASE_CURRENCY:
            from_key = f"{BASE_CURRENCY}/{from_currency}"
            to_key = f"{BASE_CURRENCY}/{to_currency}"
            
            if from_key in rates and to_key in rates:
                return rates[to_key] / rates[from_key]
        
        return None
    
    def format_price(self, amount: float, currency: str, decimals: int = 2) -> str:
        """
        Format price with currency symbol
        
        Args:
            amount: Price amount
            currency: Currency code
            decimals: Number of decimal places
            
        Returns:
            Formatted price string
        """
        if currency not in SUPPORTED_CURRENCIES:
            currency = 'USD'
        
        info = SUPPORTED_CURRENCIES[currency]
        symbol = info['symbol']
        
        # Format based on currency (some use comma, some period)
        if currency in ['JPY', 'KRW']:
            # No decimals for yen/won
            return f"{symbol} {int(amount):,}"
        else:
            formatted = f"{amount:,.{decimals}f}"
            return f"{symbol} {formatted}"
    
    def get_all_currencies(self) -> List[Dict]:
        """Get list of all supported currencies with metadata"""
        result = []
        for code, info in SUPPORTED_CURRENCIES.items():
            result.append({
                'code': code,
                'name': info['name'],
                'symbol': info['symbol'],
            })
        return sorted(result, key=lambda x: x['code'])


# Global instance
_converter: Optional[CurrencyConverter] = None

def get_converter() -> CurrencyConverter:
    """Get or create global converter instance"""
    global _converter
    if _converter is None:
        _converter = CurrencyConverter()
    return _converter

def convert_price(amount: float, from_currency: str, to_currency: str) -> float:
    """Convenience function for price conversion"""
    return get_converter().convert(amount, from_currency, to_currency)

def format_price(amount: float, currency: str) -> str:
    """Convenience function for price formatting"""
    return get_converter().format_price(amount, currency)

def get_exchange_rate(from_currency: str, to_currency: str) -> Optional[float]:
    """Convenience function for exchange rate lookup"""
    return get_converter().get_rate(from_currency, to_currency)

def get_all_currencies() -> List[Dict]:
    """Convenience function to get all currencies"""
    return get_converter().get_all_currencies()
