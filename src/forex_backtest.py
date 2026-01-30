"""
Forex Correlation Model Backtesting
====================================
Tests each currency pair correlation model against historical trend breaks
to evaluate predictive accuracy.

For each notable movement in pair A:
- Check if correlated pairs' prior movements could have predicted it
- Record 1 if prediction was correct, 0 if incorrect
- Store results in forex_model_predictions table
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from collections import defaultdict

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Database Schema for Predictions
# ──────────────────────────────────────────────────────────────────────────────

PREDICTION_SCHEMA = """
-- Forex model prediction results (backtesting)
CREATE TABLE IF NOT EXISTS forex_model_predictions (
    id SERIAL PRIMARY KEY,
    target_pair VARCHAR(10) NOT NULL,           -- Pair that had the movement
    break_date DATE NOT NULL,                   -- Date of the movement
    break_direction VARCHAR(10) NOT NULL,       -- 'bullish' or 'bearish'

    -- Prediction results from each pair's correlation (1=correct, 0=incorrect, NULL=no signal)
    aud_usd_pred SMALLINT,
    eur_usd_pred SMALLINT,
    gbp_usd_pred SMALLINT,
    nzd_usd_pred SMALLINT,
    usd_brl_pred SMALLINT,
    usd_cad_pred SMALLINT,
    usd_chf_pred SMALLINT,
    usd_cny_pred SMALLINT,
    usd_dkk_pred SMALLINT,
    usd_hkd_pred SMALLINT,
    usd_inr_pred SMALLINT,
    usd_jpy_pred SMALLINT,
    usd_krw_pred SMALLINT,
    usd_mxn_pred SMALLINT,
    usd_myr_pred SMALLINT,
    usd_nok_pred SMALLINT,
    usd_sek_pred SMALLINT,
    usd_sgd_pred SMALLINT,
    usd_thb_pred SMALLINT,
    usd_twd_pred SMALLINT,
    usd_zar_pred SMALLINT,

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(target_pair, break_date)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_forex_pred_pair ON forex_model_predictions (target_pair);
CREATE INDEX IF NOT EXISTS idx_forex_pred_date ON forex_model_predictions (break_date);

-- Grant permissions
GRANT ALL PRIVILEGES ON forex_model_predictions TO trading;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO trading;
"""

# Map pair names to column names
PAIR_TO_COLUMN = {
    'AUD/USD': 'aud_usd_pred',
    'EUR/USD': 'eur_usd_pred',
    'GBP/USD': 'gbp_usd_pred',
    'NZD/USD': 'nzd_usd_pred',
    'USD/BRL': 'usd_brl_pred',
    'USD/CAD': 'usd_cad_pred',
    'USD/CHF': 'usd_chf_pred',
    'USD/CNY': 'usd_cny_pred',
    'USD/DKK': 'usd_dkk_pred',
    'USD/HKD': 'usd_hkd_pred',
    'USD/INR': 'usd_inr_pred',
    'USD/JPY': 'usd_jpy_pred',
    'USD/KRW': 'usd_krw_pred',
    'USD/MXN': 'usd_mxn_pred',
    'USD/MYR': 'usd_myr_pred',
    'USD/NOK': 'usd_nok_pred',
    'USD/SEK': 'usd_sek_pred',
    'USD/SGD': 'usd_sgd_pred',
    'USD/THB': 'usd_thb_pred',
    'USD/TWD': 'usd_twd_pred',
    'USD/ZAR': 'usd_zar_pred',
}


class ForexBacktester:
    """
    Backtests correlation models against historical trend breaks.
    """

    def __init__(self, conn):
        self.conn = conn
        self.correlations = {}  # {(pair_a, pair_b): correlation_value}
        self.trend_breaks = {}  # {pair: {date: direction}}
        self.lookback_days = 5  # Days to look back for predictor signals

    def create_schema(self):
        """Create the predictions table if it doesn't exist."""
        cursor = self.conn.cursor()
        cursor.execute(PREDICTION_SCHEMA)
        self.conn.commit()
        cursor.close()
        logger.info("Created forex_model_predictions table")

    def load_correlations(self):
        """Load correlation matrix from database."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT pair_a, pair_b, correlation_all
            FROM forex_correlations
            WHERE calculation_date = (SELECT MAX(calculation_date) FROM forex_correlations)
        """)

        for pair_a, pair_b, corr in cursor.fetchall():
            self.correlations[(pair_a, pair_b)] = float(corr)
            # Store reverse direction too
            self.correlations[(pair_b, pair_a)] = float(corr)

        cursor.close()
        logger.info(f"Loaded {len(self.correlations)} correlation pairs")

    def load_trend_breaks(self):
        """Load all trend breaks from database."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT pair, break_date, break_direction
            FROM forex_trend_breaks
            ORDER BY break_date
        """)

        for pair, date, direction in cursor.fetchall():
            if pair not in self.trend_breaks:
                self.trend_breaks[pair] = {}
            self.trend_breaks[pair][date] = direction

        cursor.close()

        total = sum(len(breaks) for breaks in self.trend_breaks.values())
        logger.info(f"Loaded {total} trend breaks across {len(self.trend_breaks)} pairs")

    def get_predictor_signal(self, predictor_pair: str, target_date, lookback: int = 5) -> str:
        """
        Get the signal from a predictor pair in the days before target_date.
        Returns 'bullish', 'bearish', or None if no signal.
        """
        if predictor_pair not in self.trend_breaks:
            return None

        pair_breaks = self.trend_breaks[predictor_pair]

        # Look for signals in the lookback period
        bullish_count = 0
        bearish_count = 0

        for i in range(1, lookback + 1):
            check_date = target_date - timedelta(days=i)
            if check_date in pair_breaks:
                if pair_breaks[check_date] == 'bullish':
                    bullish_count += 1
                else:
                    bearish_count += 1

        if bullish_count > bearish_count:
            return 'bullish'
        elif bearish_count > bullish_count:
            return 'bearish'
        return None

    def predict_from_correlation(self, predictor_signal: str, correlation: float) -> str:
        """
        Predict target direction based on predictor signal and correlation.

        - Positive correlation: same direction
        - Negative correlation: opposite direction
        """
        if predictor_signal is None:
            return None

        if correlation >= 0:
            return predictor_signal
        else:
            return 'bearish' if predictor_signal == 'bullish' else 'bullish'

    def evaluate_prediction(self, predicted: str, actual: str) -> int:
        """Return 1 if prediction matches actual, 0 otherwise."""
        if predicted is None:
            return None
        return 1 if predicted == actual else 0

    def backtest_single_break(self, target_pair: str, break_date, break_direction: str) -> Dict:
        """
        Backtest all correlation models against a single trend break.
        Returns dict of {predictor_pair: prediction_result}
        """
        results = {}

        for predictor_pair in PAIR_TO_COLUMN.keys():
            if predictor_pair == target_pair:
                results[predictor_pair] = None  # Can't predict itself
                continue

            # Get correlation between predictor and target
            corr_key = (predictor_pair, target_pair)
            correlation = self.correlations.get(corr_key, 0)

            # Skip weak correlations
            if abs(correlation) < 0.1:
                results[predictor_pair] = None
                continue

            # Get predictor's signal before the break
            predictor_signal = self.get_predictor_signal(predictor_pair, break_date, self.lookback_days)

            # Make prediction based on correlation
            predicted_direction = self.predict_from_correlation(predictor_signal, correlation)

            # Evaluate prediction
            results[predictor_pair] = self.evaluate_prediction(predicted_direction, break_direction)

        return results

    def run_backtest(self, batch_size: int = 1000) -> Dict:
        """
        Run backtest on all trend breaks.
        Returns summary statistics.
        """
        logger.info("Starting backtest...")

        # Clear existing predictions
        cursor = self.conn.cursor()
        cursor.execute("TRUNCATE forex_model_predictions")
        self.conn.commit()

        # Collect all breaks to process
        all_breaks = []
        for pair, breaks in self.trend_breaks.items():
            for date, direction in breaks.items():
                all_breaks.append((pair, date, direction))

        logger.info(f"Processing {len(all_breaks)} trend breaks...")

        # Process in batches
        processed = 0
        batch_data = []

        for target_pair, break_date, break_direction in all_breaks:
            # Get predictions from all models
            predictions = self.backtest_single_break(target_pair, break_date, break_direction)

            # Build row data
            row = {
                'target_pair': target_pair,
                'break_date': break_date,
                'break_direction': break_direction,
            }
            for pair, result in predictions.items():
                col = PAIR_TO_COLUMN[pair]
                row[col] = result

            batch_data.append(row)
            processed += 1

            # Insert batch
            if len(batch_data) >= batch_size:
                self._insert_batch(batch_data)
                batch_data = []
                logger.info(f"Processed {processed}/{len(all_breaks)} breaks...")

        # Insert remaining
        if batch_data:
            self._insert_batch(batch_data)

        self.conn.commit()
        cursor.close()

        logger.info(f"Backtest complete. Processed {processed} trend breaks.")

        return self.calculate_summary()

    def _insert_batch(self, batch_data: List[Dict]):
        """Insert a batch of prediction results."""
        cursor = self.conn.cursor()

        columns = ['target_pair', 'break_date', 'break_direction'] + list(PAIR_TO_COLUMN.values())
        placeholders = ', '.join(['%s'] * len(columns))

        query = f"""
            INSERT INTO forex_model_predictions ({', '.join(columns)})
            VALUES ({placeholders})
            ON CONFLICT (target_pair, break_date) DO UPDATE SET
                break_direction = EXCLUDED.break_direction,
                {', '.join([f'{col} = EXCLUDED.{col}' for col in PAIR_TO_COLUMN.values()])}
        """

        for row in batch_data:
            values = [row.get('target_pair'), row.get('break_date'), row.get('break_direction')]
            values.extend([row.get(col) for col in PAIR_TO_COLUMN.values()])
            cursor.execute(query, values)

        self.conn.commit()
        cursor.close()

    def calculate_summary(self) -> Dict:
        """Calculate accuracy summary for each model."""
        cursor = self.conn.cursor()

        summary = {}

        for pair, col in PAIR_TO_COLUMN.items():
            cursor.execute(f"""
                SELECT
                    COUNT(*) FILTER (WHERE {col} = 1) as correct,
                    COUNT(*) FILTER (WHERE {col} = 0) as incorrect,
                    COUNT(*) FILTER (WHERE {col} IS NOT NULL) as total
                FROM forex_model_predictions
            """)

            correct, incorrect, total = cursor.fetchone()

            if total > 0:
                accuracy = correct / total * 100
            else:
                accuracy = 0

            summary[pair] = {
                'correct': correct or 0,
                'incorrect': incorrect or 0,
                'total': total or 0,
                'accuracy': round(accuracy, 2),
            }

        cursor.close()
        return summary

    def get_prediction_matrix_sample(self, limit: int = 100) -> pd.DataFrame:
        """Get a sample of the prediction matrix for display."""
        cursor = self.conn.cursor()

        columns = ['target_pair', 'break_date', 'break_direction'] + list(PAIR_TO_COLUMN.values())

        cursor.execute(f"""
            SELECT {', '.join(columns)}
            FROM forex_model_predictions
            ORDER BY break_date DESC
            LIMIT {limit}
        """)

        rows = cursor.fetchall()
        cursor.close()

        df = pd.DataFrame(rows, columns=columns)
        return df


def run_forex_backtest(conn) -> Dict:
    """
    Main function to run forex correlation backtesting.
    """
    backtester = ForexBacktester(conn)

    # Create schema
    backtester.create_schema()

    # Load data
    backtester.load_correlations()
    backtester.load_trend_breaks()

    # Run backtest
    summary = backtester.run_backtest()

    return summary


if __name__ == '__main__':
    import psycopg2

    logging.basicConfig(level=logging.INFO)

    conn = psycopg2.connect(
        host='127.0.0.1',
        database='trading_data',
        user='trading',
        password='trading_password'
    )

    summary = run_forex_backtest(conn)

    print("\n" + "=" * 60)
    print("FOREX CORRELATION MODEL ACCURACY")
    print("=" * 60)

    # Sort by accuracy
    sorted_summary = sorted(summary.items(), key=lambda x: x[1]['accuracy'], reverse=True)

    print(f"\n{'Pair':<12} {'Correct':>10} {'Incorrect':>10} {'Total':>10} {'Accuracy':>10}")
    print("-" * 54)

    for pair, stats in sorted_summary:
        print(f"{pair:<12} {stats['correct']:>10,} {stats['incorrect']:>10,} {stats['total']:>10,} {stats['accuracy']:>9.1f}%")

    # Overall stats
    total_correct = sum(s['correct'] for s in summary.values())
    total_incorrect = sum(s['incorrect'] for s in summary.values())
    total_predictions = total_correct + total_incorrect
    overall_accuracy = total_correct / total_predictions * 100 if total_predictions > 0 else 0

    print("-" * 54)
    print(f"{'OVERALL':<12} {total_correct:>10,} {total_incorrect:>10,} {total_predictions:>10,} {overall_accuracy:>9.1f}%")

    conn.close()
