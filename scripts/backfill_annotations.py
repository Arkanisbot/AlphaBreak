#!/usr/bin/env python3
"""
Backfill annotations for journal entries that have annotations = NULL.

Queries all un-annotated entries, generates a market-conditions snapshot
for each ticker using generate_annotations(), and saves the result.

Usage (from the flask_app directory, inside its venv):
    cd /home/ubuntu/AlphaBreak/flask_app
    source venv/bin/activate
    python ../scripts/backfill_annotations.py [--dry-run] [--limit N]

The script sleeps 2 seconds between tickers to avoid hammering yfinance.
"""

import argparse
import json
import os
import sys
import time

# Add flask_app to path so we can import services
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'flask_app'))

from app.utils.database import db_manager
from app.services.journal_service import generate_annotations


def main():
    parser = argparse.ArgumentParser(description='Backfill journal annotations')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without writing')
    parser.add_argument('--limit', type=int, default=0, help='Max entries to process (0 = all)')
    args = parser.parse_args()

    # Find entries missing annotations
    query = """
        SELECT id, ticker, trade_date
        FROM trade_journal
        WHERE annotations IS NULL AND ticker IS NOT NULL
        ORDER BY trade_date DESC
    """
    if args.limit > 0:
        query += f" LIMIT {args.limit}"

    rows = db_manager.execute_query(query)
    if not rows:
        print("No entries need annotation backfill.")
        return

    print(f"Found {len(rows)} entries to backfill.")

    success = 0
    skipped = 0
    failed = 0
    seen_tickers = {}

    for row in rows:
        entry_id, ticker, trade_date = row[0], row[1], row[2]
        ticker = (ticker or '').strip().upper()
        if not ticker:
            skipped += 1
            continue

        print(f"  [{success + failed + skipped + 1}/{len(rows)}] Entry {entry_id}: {ticker} ({trade_date})", end="")

        if args.dry_run:
            print(" — dry run, skipped")
            skipped += 1
            continue

        try:
            # Reuse cached annotations if we already fetched this ticker recently
            if ticker in seen_tickers:
                annotations = seen_tickers[ticker]
            else:
                annotations = generate_annotations(ticker, db_manager=db_manager, trade_date=str(trade_date) if trade_date else None)
                seen_tickers[ticker] = annotations
                time.sleep(2)  # Rate limit yfinance

            if annotations and len(annotations) > 2:
                with db_manager.get_cursor(commit=True) as cur:
                    cur.execute(
                        "UPDATE trade_journal SET annotations = %s WHERE id = %s",
                        (json.dumps(annotations), entry_id)
                    )
                success += 1
                print(f" — OK (regime={annotations.get('market_regime', '?')})")
            else:
                skipped += 1
                print(" — no data")

        except Exception as e:
            failed += 1
            print(f" — ERROR: {e}")

    print(f"\nDone: {success} annotated, {skipped} skipped, {failed} failed")


if __name__ == '__main__':
    main()
