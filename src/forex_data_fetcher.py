"""
Forex Data Fetcher
==================
Fetches historical forex data from multiple sources:
1. FRED (Federal Reserve) - longest history (1971+)
2. Yahoo Finance - supplement for recent data

Stores data in PostgreSQL/TimescaleDB.
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import requests
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# FRED Exchange Rate Series
# ──────────────────────────────────────────────────────────────────────────────

FRED_FOREX_SERIES = {
    # Major pairs (USD as base or quote)
    'DEXUSEU': {'pair': 'EUR/USD', 'base': 'EUR', 'quote': 'USD', 'invert': True},   # USD per EUR -> EUR/USD
    'DEXUSUK': {'pair': 'GBP/USD', 'base': 'GBP', 'quote': 'USD', 'invert': True},   # USD per GBP -> GBP/USD
    'DEXJPUS': {'pair': 'USD/JPY', 'base': 'USD', 'quote': 'JPY', 'invert': False},  # JPY per USD -> USD/JPY
    'DEXSZUS': {'pair': 'USD/CHF', 'base': 'USD', 'quote': 'CHF', 'invert': False},  # CHF per USD -> USD/CHF
    'DEXUSAL': {'pair': 'AUD/USD', 'base': 'AUD', 'quote': 'USD', 'invert': True},   # USD per AUD -> AUD/USD
    'DEXCAUS': {'pair': 'USD/CAD', 'base': 'USD', 'quote': 'CAD', 'invert': False},  # CAD per USD -> USD/CAD
    'DEXCHUS': {'pair': 'USD/CNY', 'base': 'USD', 'quote': 'CNY', 'invert': False},  # CNY per USD -> USD/CNY
    'DEXMXUS': {'pair': 'USD/MXN', 'base': 'USD', 'quote': 'MXN', 'invert': False},  # MXN per USD -> USD/MXN
    'DEXKOUS': {'pair': 'USD/KRW', 'base': 'USD', 'quote': 'KRW', 'invert': False},  # KRW per USD -> USD/KRW
    'DEXSIUS': {'pair': 'USD/SGD', 'base': 'USD', 'quote': 'SGD', 'invert': False},  # SGD per USD -> USD/SGD
    'DEXSDUS': {'pair': 'USD/SEK', 'base': 'USD', 'quote': 'SEK', 'invert': False},  # SEK per USD -> USD/SEK
    'DEXNOUS': {'pair': 'USD/NOK', 'base': 'USD', 'quote': 'NOK', 'invert': False},  # NOK per USD -> USD/NOK
    'DEXDNUS': {'pair': 'USD/DKK', 'base': 'USD', 'quote': 'DKK', 'invert': False},  # DKK per USD -> USD/DKK
    'DEXHKUS': {'pair': 'USD/HKD', 'base': 'USD', 'quote': 'HKD', 'invert': False},  # HKD per USD -> USD/HKD
    'DEXINUS': {'pair': 'USD/INR', 'base': 'USD', 'quote': 'INR', 'invert': False},  # INR per USD -> USD/INR
    'DEXBZUS': {'pair': 'USD/BRL', 'base': 'USD', 'quote': 'BRL', 'invert': False},  # BRL per USD -> USD/BRL
    'DEXSFUS': {'pair': 'USD/ZAR', 'base': 'USD', 'quote': 'ZAR', 'invert': False},  # ZAR per USD -> USD/ZAR
    'DEXTHUS': {'pair': 'USD/THB', 'base': 'USD', 'quote': 'THB', 'invert': False},  # THB per USD -> USD/THB
    'DEXTAUS': {'pair': 'USD/TWD', 'base': 'USD', 'quote': 'TWD', 'invert': False},  # TWD per USD -> USD/TWD
    'DEXMAUS': {'pair': 'USD/MYR', 'base': 'USD', 'quote': 'MYR', 'invert': False},  # MYR per USD -> USD/MYR
    'DEXNZUS': {'pair': 'NZD/USD', 'base': 'NZD', 'quote': 'USD', 'invert': True},   # USD per NZD -> NZD/USD
}

# Yahoo Finance forex tickers (for supplementing FRED data)
YAHOO_FOREX_TICKERS = {
    'EURUSD=X': 'EUR/USD',
    'GBPUSD=X': 'GBP/USD',
    'USDJPY=X': 'USD/JPY',
    'USDCHF=X': 'USD/CHF',
    'AUDUSD=X': 'AUD/USD',
    'USDCAD=X': 'USD/CAD',
    'NZDUSD=X': 'NZD/USD',
    'USDCNY=X': 'USD/CNY',
    'USDMXN=X': 'USD/MXN',
    'USDINR=X': 'USD/INR',
    'USDBRL=X': 'USD/BRL',
    'USDKRW=X': 'USD/KRW',
    'USDSGD=X': 'USD/SGD',
    'USDHKD=X': 'USD/HKD',
    'USDSEK=X': 'USD/SEK',
    'USDNOK=X': 'USD/NOK',
    'USDDKK=X': 'USD/DKK',
    'USDZAR=X': 'USD/ZAR',
    'USDTHB=X': 'USD/THB',
    'USDTWD=X': 'USD/TWD',
    'USDMYR=X': 'USD/MYR',
}

# Trade Weighted USD Index
FRED_USD_INDEX = {
    'DTWEXBGS': {'name': 'Trade Weighted USD Index (Broad)', 'start': '2006-01-04'},
    'DTWEXAFEGS': {'name': 'Trade Weighted USD vs Advanced Foreign Economies', 'start': '2006-01-04'},
}


# ──────────────────────────────────────────────────────────────────────────────
# FRED Data Fetcher
# ──────────────────────────────────────────────────────────────────────────────

def fetch_fred_series(series_id: str, start_date: str = '1970-01-01',
                      end_date: str = None, api_key: str = None) -> pd.DataFrame:
    """
    Fetch a FRED series using the FRED API.

    If no API key provided, uses the web scraping fallback.
    """
    if end_date is None:
        end_date = datetime.now().strftime('%Y-%m-%d')

    # Try FRED API first (if key provided)
    if api_key:
        return _fetch_fred_api(series_id, start_date, end_date, api_key)

    # Fallback to web scraping via FRED's CSV download
    return _fetch_fred_csv(series_id, start_date, end_date)


def _fetch_fred_api(series_id: str, start_date: str, end_date: str, api_key: str) -> pd.DataFrame:
    """Fetch from FRED API with API key."""
    url = 'https://api.stlouisfed.org/fred/series/observations'
    params = {
        'series_id': series_id,
        'api_key': api_key,
        'file_type': 'json',
        'observation_start': start_date,
        'observation_end': end_date,
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        observations = data.get('observations', [])
        if not observations:
            return pd.DataFrame()

        df = pd.DataFrame(observations)
        df['date'] = pd.to_datetime(df['date'])
        df['value'] = pd.to_numeric(df['value'], errors='coerce')
        df = df[['date', 'value']].dropna()
        df = df.set_index('date')
        df.columns = [series_id]

        return df
    except Exception as e:
        logger.warning(f"FRED API fetch failed for {series_id}: {e}")
        return pd.DataFrame()


def _fetch_fred_csv(series_id: str, start_date: str, end_date: str) -> pd.DataFrame:
    """Fetch from FRED's public CSV download endpoint (no API key required)."""
    url = f'https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}'

    try:
        df = pd.read_csv(url, parse_dates=['DATE'], index_col='DATE')
        df.columns = [series_id]

        # Filter by date range
        df = df.loc[start_date:end_date]

        # Handle missing values (FRED uses '.' for missing)
        df = df.replace('.', np.nan)
        df[series_id] = pd.to_numeric(df[series_id], errors='coerce')
        df = df.dropna()

        return df
    except Exception as e:
        logger.warning(f"FRED CSV fetch failed for {series_id}: {e}")
        return pd.DataFrame()


def fetch_all_fred_forex(start_date: str = '1970-01-01', api_key: str = None) -> Dict[str, pd.DataFrame]:
    """Fetch all FRED forex series."""
    results = {}

    for series_id, info in FRED_FOREX_SERIES.items():
        logger.info(f"Fetching FRED {series_id} ({info['pair']})...")
        df = fetch_fred_series(series_id, start_date, api_key=api_key)

        if not df.empty:
            # Normalize to standard pair format
            if info.get('invert', False):
                # FRED gives USD per foreign currency, we may need to invert
                df[series_id] = df[series_id]  # Keep as-is for now

            df = df.rename(columns={series_id: 'close'})
            df['pair'] = info['pair']
            df['source'] = 'FRED'
            df['series_id'] = series_id
            results[info['pair']] = df

            logger.info(f"  -> {len(df)} rows from {df.index.min()} to {df.index.max()}")

        time.sleep(0.5)  # Rate limiting

    return results


# ──────────────────────────────────────────────────────────────────────────────
# Yahoo Finance Fetcher
# ──────────────────────────────────────────────────────────────────────────────

def fetch_yahoo_forex(ticker: str, period: str = 'max') -> pd.DataFrame:
    """Fetch forex data from Yahoo Finance."""
    import yfinance as yf

    try:
        data = yf.Ticker(ticker)
        df = data.history(period=period, interval='1d')

        if df.empty:
            return pd.DataFrame()

        df = df.reset_index()
        df = df.rename(columns={'Date': 'date', 'Close': 'close', 'Open': 'open',
                                'High': 'high', 'Low': 'low', 'Volume': 'volume'})

        # Handle timezone-aware datetime
        if df['date'].dt.tz is not None:
            df['date'] = df['date'].dt.tz_localize(None)

        df = df.set_index('date')
        df['source'] = 'Yahoo'

        return df[['open', 'high', 'low', 'close', 'volume', 'source']]
    except Exception as e:
        logger.warning(f"Yahoo Finance fetch failed for {ticker}: {e}")
        return pd.DataFrame()


def fetch_all_yahoo_forex() -> Dict[str, pd.DataFrame]:
    """Fetch all Yahoo Finance forex pairs."""
    results = {}

    for ticker, pair in YAHOO_FOREX_TICKERS.items():
        logger.info(f"Fetching Yahoo {ticker} ({pair})...")
        df = fetch_yahoo_forex(ticker)

        if not df.empty:
            df['pair'] = pair
            results[pair] = df
            logger.info(f"  -> {len(df)} rows from {df.index.min()} to {df.index.max()}")

        time.sleep(0.3)  # Rate limiting

    return results


# ──────────────────────────────────────────────────────────────────────────────
# Combined Data Fetcher
# ──────────────────────────────────────────────────────────────────────────────

def fetch_combined_forex_data(fred_api_key: str = None) -> Dict[str, pd.DataFrame]:
    """
    Fetch forex data from both FRED and Yahoo Finance, combining them.

    FRED provides longer history, Yahoo provides more recent OHLC data.
    Priority: FRED for historical, Yahoo for recent/OHLC.
    """
    logger.info("Fetching forex data from FRED...")
    fred_data = fetch_all_fred_forex(api_key=fred_api_key)

    logger.info("Fetching forex data from Yahoo Finance...")
    yahoo_data = fetch_all_yahoo_forex()

    # Combine: use FRED as base, supplement with Yahoo
    combined = {}

    all_pairs = set(fred_data.keys()) | set(yahoo_data.keys())

    for pair in all_pairs:
        fred_df = fred_data.get(pair)
        yahoo_df = yahoo_data.get(pair)

        if fred_df is not None and yahoo_df is not None:
            # FRED has 'close' only, Yahoo has OHLCV
            # Use FRED for dates before Yahoo starts
            yahoo_start = yahoo_df.index.min()

            # FRED data before Yahoo starts
            fred_before = fred_df[fred_df.index < yahoo_start].copy()
            if not fred_before.empty:
                # Add missing columns for FRED data
                fred_before['open'] = fred_before['close']
                fred_before['high'] = fred_before['close']
                fred_before['low'] = fred_before['close']
                fred_before['volume'] = 0
                fred_before = fred_before[['open', 'high', 'low', 'close', 'volume', 'source', 'pair']]

            # Combine
            combined[pair] = pd.concat([fred_before, yahoo_df])
            combined[pair] = combined[pair].sort_index()
            combined[pair] = combined[pair][~combined[pair].index.duplicated(keep='last')]

        elif fred_df is not None:
            # Only FRED data
            fred_df['open'] = fred_df['close']
            fred_df['high'] = fred_df['close']
            fred_df['low'] = fred_df['close']
            fred_df['volume'] = 0
            combined[pair] = fred_df[['open', 'high', 'low', 'close', 'volume', 'source', 'pair']]

        elif yahoo_df is not None:
            # Only Yahoo data
            combined[pair] = yahoo_df

    return combined


# ──────────────────────────────────────────────────────────────────────────────
# Database Storage
# ──────────────────────────────────────────────────────────────────────────────

def store_forex_data(conn, pair: str, df: pd.DataFrame) -> int:
    """Store forex data in the database."""
    if df.empty:
        return 0

    # Normalize pair name for table
    table_suffix = pair.replace('/', '_').lower()

    cursor = conn.cursor()

    inserted = 0
    for date_idx, row in df.iterrows():
        try:
            cursor.execute("""
                INSERT INTO forex_daily_data (
                    pair, date, open, high, low, close, volume, source
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (pair, date) DO UPDATE SET
                    open = EXCLUDED.open,
                    high = EXCLUDED.high,
                    low = EXCLUDED.low,
                    close = EXCLUDED.close,
                    volume = EXCLUDED.volume,
                    source = EXCLUDED.source,
                    updated_at = NOW()
            """, (
                pair,
                date_idx.date() if hasattr(date_idx, 'date') else date_idx,
                float(row['open']) if pd.notna(row['open']) else None,
                float(row['high']) if pd.notna(row['high']) else None,
                float(row['low']) if pd.notna(row['low']) else None,
                float(row['close']) if pd.notna(row['close']) else None,
                int(row['volume']) if pd.notna(row['volume']) else 0,
                row.get('source', 'unknown'),
            ))
            inserted += 1
        except Exception as e:
            logger.warning(f"Failed to insert {pair} {date_idx}: {e}")

    conn.commit()
    cursor.close()

    return inserted


def populate_forex_database(conn, fred_api_key: str = None) -> Dict[str, int]:
    """Populate the database with all forex data."""
    logger.info("Starting forex data population...")

    combined_data = fetch_combined_forex_data(fred_api_key)

    results = {}
    for pair, df in combined_data.items():
        count = store_forex_data(conn, pair, df)
        results[pair] = count
        logger.info(f"Stored {count} rows for {pair}")

    return results


# ──────────────────────────────────────────────────────────────────────────────
# CLI Entry Point
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    import argparse

    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    parser = argparse.ArgumentParser(description='Fetch forex data from FRED and Yahoo Finance')
    parser.add_argument('--fred-api-key', help='FRED API key (optional)')
    parser.add_argument('--db-host', default='localhost', help='Database host')
    parser.add_argument('--db-port', default=5432, type=int, help='Database port')
    parser.add_argument('--db-name', default='trading', help='Database name')
    parser.add_argument('--db-user', default='trading', help='Database user')
    parser.add_argument('--db-password', default='', help='Database password')
    parser.add_argument('--test', action='store_true', help='Test mode - just fetch and print')

    args = parser.parse_args()

    if args.test:
        # Test mode - just fetch and display
        data = fetch_combined_forex_data(args.fred_api_key)
        for pair, df in data.items():
            print(f"\n{pair}: {len(df)} rows")
            print(f"  Date range: {df.index.min()} to {df.index.max()}")
            print(f"  Sources: {df['source'].unique()}")
    else:
        # Production mode - store in database
        import psycopg2

        conn = psycopg2.connect(
            host=args.db_host,
            port=args.db_port,
            dbname=args.db_name,
            user=args.db_user,
            password=args.db_password,
        )

        try:
            results = populate_forex_database(conn, args.fred_api_key)
            print("\n=== POPULATION COMPLETE ===")
            for pair, count in sorted(results.items()):
                print(f"  {pair}: {count} rows")
        finally:
            conn.close()
