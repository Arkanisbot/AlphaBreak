"""
Forex Correlation Model
=======================
Trains correlation models for each currency pair to identify patterns
between forex pairs. Classifies patterns as strong, mid, or weak.

Also applies trend-break analysis to identify notable movements.
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from scipy import stats
from collections import defaultdict

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Correlation Analysis
# ──────────────────────────────────────────────────────────────────────────────

class ForexCorrelationModel:
    """
    Model that tracks correlations between forex pairs and classifies
    pattern strengths as strong, mid, or weak.
    """

    def __init__(self, conn=None):
        self.conn = conn
        self.pairs_data = {}
        self.correlations = {}
        self.thresholds = {}
        self.pattern_counts = {'strong': 0, 'mid': 0, 'weak': 0}

    def load_data_from_db(self, pairs: List[str] = None) -> None:
        """Load forex data from database."""
        if self.conn is None:
            raise ValueError("Database connection required")

        cursor = self.conn.cursor()

        if pairs:
            placeholders = ','.join(['%s'] * len(pairs))
            query = f"""
                SELECT pair, date, close
                FROM forex_daily_data
                WHERE pair IN ({placeholders})
                ORDER BY pair, date
            """
            cursor.execute(query, pairs)
        else:
            cursor.execute("""
                SELECT pair, date, close
                FROM forex_daily_data
                ORDER BY pair, date
            """)

        rows = cursor.fetchall()
        cursor.close()

        # Organize by pair
        for pair, date, close in rows:
            if pair not in self.pairs_data:
                self.pairs_data[pair] = []
            self.pairs_data[pair].append({'date': date, 'close': float(close)})

        # Convert to DataFrames
        for pair in self.pairs_data:
            df = pd.DataFrame(self.pairs_data[pair])
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date').sort_index()
            self.pairs_data[pair] = df

        logger.info(f"Loaded data for {len(self.pairs_data)} pairs")

    def load_data_from_dict(self, data: Dict[str, pd.DataFrame]) -> None:
        """Load forex data from dictionary of DataFrames."""
        for pair, df in data.items():
            if 'close' in df.columns:
                self.pairs_data[pair] = df[['close']].copy()
            elif len(df.columns) == 1:
                self.pairs_data[pair] = df.copy()
                self.pairs_data[pair].columns = ['close']

        logger.info(f"Loaded data for {len(self.pairs_data)} pairs")

    def calculate_returns(self) -> Dict[str, pd.Series]:
        """Calculate daily returns for each pair."""
        returns = {}
        for pair, df in self.pairs_data.items():
            returns[pair] = df['close'].pct_change().dropna()
        return returns

    def compute_correlation_matrix(self, lookback_days: int = None) -> pd.DataFrame:
        """Compute correlation matrix between all pairs."""
        returns = self.calculate_returns()

        # Align all series to common dates
        all_returns = pd.DataFrame(returns)

        if lookback_days:
            all_returns = all_returns.tail(lookback_days)

        return all_returns.corr()

    def compute_all_correlations(self) -> Dict[Tuple[str, str], Dict]:
        """
        Compute correlations between all pairs with multiple lookback periods.
        Returns detailed correlation info for each pair combination.
        """
        returns = self.calculate_returns()
        all_returns = pd.DataFrame(returns).dropna()

        pairs = list(all_returns.columns)
        results = {}

        for i, pair_a in enumerate(pairs):
            for pair_b in pairs[i+1:]:
                # Calculate correlations for different periods
                corr_all = all_returns[pair_a].corr(all_returns[pair_b])

                corr_30d = all_returns[pair_a].tail(30).corr(all_returns[pair_b].tail(30))
                corr_90d = all_returns[pair_a].tail(90).corr(all_returns[pair_b].tail(90))
                corr_1y = all_returns[pair_a].tail(252).corr(all_returns[pair_b].tail(252))

                # Calculate lead/lag correlation
                lead_lag, lead_lag_corr = self._find_lead_lag(
                    all_returns[pair_a], all_returns[pair_b], max_lag=10
                )

                results[(pair_a, pair_b)] = {
                    'correlation_all': corr_all if not np.isnan(corr_all) else 0,
                    'correlation_30d': corr_30d if not np.isnan(corr_30d) else 0,
                    'correlation_90d': corr_90d if not np.isnan(corr_90d) else 0,
                    'correlation_1y': corr_1y if not np.isnan(corr_1y) else 0,
                    'lead_lag_days': lead_lag,
                    'lead_lag_correlation': lead_lag_corr,
                    'data_points': len(all_returns),
                }

        self.correlations = results
        return results

    def _find_lead_lag(self, series_a: pd.Series, series_b: pd.Series,
                       max_lag: int = 10) -> Tuple[int, float]:
        """Find optimal lead/lag relationship between two series."""
        best_lag = 0
        best_corr = abs(series_a.corr(series_b))

        for lag in range(1, max_lag + 1):
            # A leads B (shift B forward)
            corr_a_leads = abs(series_a[:-lag].corr(series_b.shift(-lag)[:-lag]))
            if not np.isnan(corr_a_leads) and corr_a_leads > best_corr:
                best_corr = corr_a_leads
                best_lag = lag

            # B leads A (shift A forward)
            corr_b_leads = abs(series_b[:-lag].corr(series_a.shift(-lag)[:-lag]))
            if not np.isnan(corr_b_leads) and corr_b_leads > best_corr:
                best_corr = corr_b_leads
                best_lag = -lag

        return best_lag, best_corr

    def classify_pattern_strengths(self) -> Dict[Tuple[str, str], str]:
        """
        Classify correlation patterns as strong, mid, or weak.

        Uses relative thresholds based on the data distribution:
        - Strong: top third of correlations
        - Mid: middle third
        - Weak: bottom third
        """
        if not self.correlations:
            self.compute_all_correlations()

        # Get absolute correlation values
        abs_correlations = [abs(v['correlation_all']) for v in self.correlations.values()]

        if not abs_correlations:
            return {}

        # Calculate thresholds based on distribution
        min_corr = min(abs_correlations)
        max_corr = max(abs_correlations)
        range_corr = max_corr - min_corr

        # Divide into thirds
        weak_max = min_corr + (range_corr / 3)
        mid_max = min_corr + (2 * range_corr / 3)

        self.thresholds = {
            'weak_max': weak_max,
            'mid_min': weak_max,
            'mid_max': mid_max,
            'strong_min': mid_max,
            'max_correlation': max_corr,
            'min_correlation': min_corr,
            'avg_correlation': np.mean(abs_correlations),
        }

        logger.info(f"Correlation thresholds: weak=0-{weak_max:.4f}, mid={weak_max:.4f}-{mid_max:.4f}, strong={mid_max:.4f}-{max_corr:.4f}")

        # Classify each pair
        classifications = {}
        self.pattern_counts = {'strong': 0, 'mid': 0, 'weak': 0}

        for pair_combo, data in self.correlations.items():
            abs_corr = abs(data['correlation_all'])

            if abs_corr >= mid_max:
                strength = 'strong'
            elif abs_corr >= weak_max:
                strength = 'mid'
            else:
                strength = 'weak'

            classifications[pair_combo] = strength
            self.pattern_counts[strength] += 1

        return classifications

    def train_model(self) -> Dict:
        """
        Train the correlation model for all pairs.

        Returns summary statistics.
        """
        logger.info("Computing correlations...")
        self.compute_all_correlations()

        logger.info("Classifying pattern strengths...")
        classifications = self.classify_pattern_strengths()

        # Store results in database if connected
        if self.conn:
            self._store_correlations(classifications)

        return {
            'pairs_analyzed': len(self.pairs_data),
            'correlations_computed': len(self.correlations),
            'pattern_counts': self.pattern_counts,
            'thresholds': self.thresholds,
        }

    def _store_correlations(self, classifications: Dict) -> None:
        """Store correlation results in database."""
        cursor = self.conn.cursor()
        today = datetime.now().date()

        # Helper to convert numpy types to Python native
        def to_native(val):
            if val is None:
                return None
            if isinstance(val, (np.floating, np.integer)):
                return float(val)
            return val

        # Store thresholds
        cursor.execute("""
            INSERT INTO forex_correlation_thresholds (
                calculation_date, strong_min, mid_min, weak_max,
                max_correlation, min_correlation, avg_correlation
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (calculation_date) DO UPDATE SET
                strong_min = EXCLUDED.strong_min,
                mid_min = EXCLUDED.mid_min,
                weak_max = EXCLUDED.weak_max,
                max_correlation = EXCLUDED.max_correlation,
                min_correlation = EXCLUDED.min_correlation,
                avg_correlation = EXCLUDED.avg_correlation
        """, (
            today,
            to_native(self.thresholds['strong_min']),
            to_native(self.thresholds['mid_min']),
            to_native(self.thresholds['weak_max']),
            to_native(self.thresholds['max_correlation']),
            to_native(self.thresholds['min_correlation']),
            to_native(self.thresholds['avg_correlation']),
        ))

        # Store correlations
        for (pair_a, pair_b), data in self.correlations.items():
            strength = classifications.get((pair_a, pair_b), 'weak')

            cursor.execute("""
                INSERT INTO forex_correlations (
                    pair_a, pair_b, correlation_30d, correlation_90d,
                    correlation_1y, correlation_all, pattern_strength,
                    lead_lag_days, lead_lag_correlation, calculation_date, data_points
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (pair_a, pair_b, calculation_date) DO UPDATE SET
                    correlation_30d = EXCLUDED.correlation_30d,
                    correlation_90d = EXCLUDED.correlation_90d,
                    correlation_1y = EXCLUDED.correlation_1y,
                    correlation_all = EXCLUDED.correlation_all,
                    pattern_strength = EXCLUDED.pattern_strength,
                    lead_lag_days = EXCLUDED.lead_lag_days,
                    lead_lag_correlation = EXCLUDED.lead_lag_correlation,
                    data_points = EXCLUDED.data_points
            """, (
                pair_a, pair_b,
                to_native(data['correlation_30d']), to_native(data['correlation_90d']),
                to_native(data['correlation_1y']), to_native(data['correlation_all']),
                strength, to_native(data['lead_lag_days']), to_native(data['lead_lag_correlation']),
                today, to_native(data['data_points']),
            ))

        self.conn.commit()
        cursor.close()
        logger.info(f"Stored {len(self.correlations)} correlation records")


# ──────────────────────────────────────────────────────────────────────────────
# Trend Break Analysis for Forex
# ──────────────────────────────────────────────────────────────────────────────

class ForexTrendBreakAnalyzer:
    """
    Applies trend-break analysis to forex data to identify notable movements.
    Uses similar methodology to the equity trend-break model.
    """

    def __init__(self, conn=None):
        self.conn = conn
        self.breaks_by_pair = defaultdict(list)

    def analyze_pair(self, pair: str, df: pd.DataFrame,
                     probability_threshold: float = 0.80) -> List[Dict]:
        """
        Analyze a single forex pair for trend breaks.

        Returns list of detected trend breaks.
        """
        if len(df) < 50:
            logger.warning(f"Insufficient data for {pair}: {len(df)} rows")
            return []

        # Ensure we have the close price
        if 'close' not in df.columns:
            if 'Close' in df.columns:
                df = df.rename(columns={'Close': 'close'})
            else:
                return []

        # Calculate technical indicators
        df = self._calculate_indicators(df.copy())

        # Detect trend breaks
        breaks = self._detect_breaks(pair, df, probability_threshold)

        self.breaks_by_pair[pair] = breaks
        return breaks

    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate technical indicators for trend break detection."""
        close = df['close']

        # RSI (14-period)
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))

        # CCI (20-period)
        tp = close  # For forex, we just use close as typical price
        sma_tp = tp.rolling(20).mean()
        mad = tp.rolling(20).apply(lambda x: np.abs(x - x.mean()).mean())
        df['cci'] = (tp - sma_tp) / (0.015 * mad)

        # MACD
        ema_12 = close.ewm(span=12).mean()
        ema_26 = close.ewm(span=26).mean()
        df['macd'] = ema_12 - ema_26
        df['macd_signal'] = df['macd'].ewm(span=9).mean()
        df['macd_histogram'] = df['macd'] - df['macd_signal']

        # Stochastic (14-period)
        low_14 = close.rolling(14).min()
        high_14 = close.rolling(14).max()
        df['stoch_k'] = 100 * (close - low_14) / (high_14 - low_14)
        df['stoch_d'] = df['stoch_k'].rolling(3).mean()

        # ADX (14-period simplified)
        df['atr'] = close.rolling(14).std()
        df['adx'] = df['atr'].rolling(14).mean() / close * 10000  # Simplified

        # Bollinger Bands
        df['bb_mid'] = close.rolling(20).mean()
        df['bb_std'] = close.rolling(20).std()
        df['bb_upper'] = df['bb_mid'] + (2 * df['bb_std'])
        df['bb_lower'] = df['bb_mid'] - (2 * df['bb_std'])

        # Daily returns
        df['returns'] = close.pct_change()
        df['returns_5d'] = close.pct_change(5)

        return df

    def _detect_breaks(self, pair: str, df: pd.DataFrame,
                       threshold: float = 0.80) -> List[Dict]:
        """Detect trend breaks using multiple signals."""
        breaks = []

        for i in range(50, len(df)):
            row = df.iloc[i]
            date = df.index[i]

            if pd.isna(row['rsi']) or pd.isna(row['cci']):
                continue

            # Score signals
            bullish_signals = 0
            bearish_signals = 0
            total_signals = 0

            # RSI signals
            if row['rsi'] < 30:
                bullish_signals += 2  # Oversold
                total_signals += 2
            elif row['rsi'] > 70:
                bearish_signals += 2  # Overbought
                total_signals += 2
            elif row['rsi'] < 40:
                bullish_signals += 1
                total_signals += 1
            elif row['rsi'] > 60:
                bearish_signals += 1
                total_signals += 1

            # CCI signals
            if not pd.isna(row['cci']):
                if row['cci'] < -200:
                    bullish_signals += 2
                    total_signals += 2
                elif row['cci'] < -100:
                    bullish_signals += 1
                    total_signals += 1
                elif row['cci'] > 200:
                    bearish_signals += 2
                    total_signals += 2
                elif row['cci'] > 100:
                    bearish_signals += 1
                    total_signals += 1

            # MACD histogram crossover
            if i > 0 and not pd.isna(row['macd_histogram']):
                prev_hist = df.iloc[i-1]['macd_histogram']
                if not pd.isna(prev_hist):
                    if row['macd_histogram'] > 0 and prev_hist < 0:
                        bullish_signals += 2  # Bullish crossover
                        total_signals += 2
                    elif row['macd_histogram'] < 0 and prev_hist > 0:
                        bearish_signals += 2  # Bearish crossover
                        total_signals += 2

            # Stochastic signals
            if not pd.isna(row['stoch_k']) and not pd.isna(row['stoch_d']):
                if row['stoch_k'] < 20 and row['stoch_k'] > row['stoch_d']:
                    bullish_signals += 1
                    total_signals += 1
                elif row['stoch_k'] > 80 and row['stoch_k'] < row['stoch_d']:
                    bearish_signals += 1
                    total_signals += 1

            # Bollinger Band signals
            if not pd.isna(row['bb_upper']) and not pd.isna(row['bb_lower']):
                if row['close'] < row['bb_lower']:
                    bullish_signals += 1
                    total_signals += 1
                    bb_position = 'below_lower'
                elif row['close'] > row['bb_upper']:
                    bearish_signals += 1
                    total_signals += 1
                    bb_position = 'above_upper'
                else:
                    bb_position = 'within'
            else:
                bb_position = 'unknown'

            # Calculate probability
            if total_signals == 0:
                continue

            max_signals = max(bullish_signals, bearish_signals)
            probability = 0.30 + (max_signals / total_signals) * 0.50 + min(max_signals / 8.0, 0.15)
            probability = min(probability, 0.98)

            # Only record if above threshold
            if probability >= threshold:
                direction = 'bullish' if bullish_signals > bearish_signals else 'bearish'
                confidence = abs(bullish_signals - bearish_signals) / max(total_signals, 1)

                # Get price context
                price_before_5d = df.iloc[i-5]['close'] if i >= 5 else None
                movement_pct = (row['close'] - price_before_5d) / price_before_5d * 100 if price_before_5d else None

                break_info = {
                    'pair': pair,
                    'break_date': date.date() if hasattr(date, 'date') else date,
                    'break_direction': direction,
                    'break_probability': round(probability, 4),
                    'confidence': round(confidence, 4),
                    'price_at_break': float(row['close']),
                    'price_before_5d': float(price_before_5d) if price_before_5d else None,
                    'movement_pct': round(movement_pct, 4) if movement_pct else None,
                    'rsi_value': round(row['rsi'], 2) if not pd.isna(row['rsi']) else None,
                    'cci_value': round(row['cci'], 2) if not pd.isna(row['cci']) else None,
                    'macd_histogram': round(row['macd_histogram'], 8) if not pd.isna(row['macd_histogram']) else None,
                    'stochastic_k': round(row['stoch_k'], 2) if not pd.isna(row['stoch_k']) else None,
                    'stochastic_d': round(row['stoch_d'], 2) if not pd.isna(row['stoch_d']) else None,
                    'adx_value': round(row['adx'], 2) if not pd.isna(row['adx']) else None,
                    'bb_position': bb_position,
                }

                breaks.append(break_info)

        return breaks

    def analyze_all_pairs(self, pairs_data: Dict[str, pd.DataFrame],
                          probability_threshold: float = 0.80) -> Dict[str, List[Dict]]:
        """Analyze all forex pairs for trend breaks."""
        results = {}

        for pair, df in pairs_data.items():
            logger.info(f"Analyzing trend breaks for {pair}...")
            breaks = self.analyze_pair(pair, df, probability_threshold)
            results[pair] = breaks
            logger.info(f"  -> Found {len(breaks)} trend breaks")

        return results

    def store_breaks(self, breaks: List[Dict]) -> int:
        """Store trend breaks in database."""
        if not self.conn or not breaks:
            return 0

        cursor = self.conn.cursor()
        stored = 0

        # Helper to convert numpy types to Python native
        def to_native(val):
            if val is None:
                return None
            if isinstance(val, (np.floating, np.integer)):
                return float(val)
            return val

        for brk in breaks:
            try:
                cursor.execute("""
                    INSERT INTO forex_trend_breaks (
                        pair, break_date, break_direction, break_probability, confidence,
                        price_at_break, price_before_5d, movement_pct,
                        rsi_value, cci_value, macd_histogram,
                        stochastic_k, stochastic_d, adx_value, bb_position
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (pair, break_date) DO UPDATE SET
                        break_direction = EXCLUDED.break_direction,
                        break_probability = EXCLUDED.break_probability,
                        confidence = EXCLUDED.confidence,
                        price_at_break = EXCLUDED.price_at_break,
                        price_before_5d = EXCLUDED.price_before_5d,
                        movement_pct = EXCLUDED.movement_pct,
                        rsi_value = EXCLUDED.rsi_value,
                        cci_value = EXCLUDED.cci_value,
                        macd_histogram = EXCLUDED.macd_histogram,
                        stochastic_k = EXCLUDED.stochastic_k,
                        stochastic_d = EXCLUDED.stochastic_d,
                        adx_value = EXCLUDED.adx_value,
                        bb_position = EXCLUDED.bb_position
                """, (
                    brk['pair'], brk['break_date'], brk['break_direction'],
                    to_native(brk['break_probability']), to_native(brk['confidence']),
                    to_native(brk['price_at_break']), to_native(brk['price_before_5d']), to_native(brk['movement_pct']),
                    to_native(brk['rsi_value']), to_native(brk['cci_value']), to_native(brk['macd_histogram']),
                    to_native(brk['stochastic_k']), to_native(brk['stochastic_d']), to_native(brk['adx_value']),
                    brk['bb_position'],
                ))
                stored += 1
            except Exception as e:
                logger.warning(f"Failed to store break for {brk['pair']} {brk['break_date']}: {e}")
                self.conn.rollback()  # Rollback to clear aborted transaction

        self.conn.commit()
        cursor.close()

        return stored


# ──────────────────────────────────────────────────────────────────────────────
# Main Training Pipeline
# ──────────────────────────────────────────────────────────────────────────────

def train_forex_models(conn) -> Dict:
    """
    Main training pipeline for forex correlation models.

    1. Load forex data from database
    2. Train correlation models for each pair
    3. Classify patterns as strong/mid/weak
    4. Detect trend breaks
    5. Store results

    Returns summary statistics.
    """
    from forex_data_fetcher import fetch_combined_forex_data, store_forex_data

    logger.info("=== FOREX MODEL TRAINING PIPELINE ===")

    # Step 1: Fetch and store latest data
    logger.info("Step 1: Fetching forex data...")
    forex_data = fetch_combined_forex_data()

    data_counts = {}
    for pair, df in forex_data.items():
        count = store_forex_data(conn, pair, df)
        data_counts[pair] = count

    # Step 2: Train correlation model
    logger.info("Step 2: Training correlation model...")
    corr_model = ForexCorrelationModel(conn)
    corr_model.load_data_from_dict(forex_data)
    corr_results = corr_model.train_model()

    # Step 3: Analyze trend breaks
    logger.info("Step 3: Analyzing trend breaks...")
    break_analyzer = ForexTrendBreakAnalyzer(conn)
    all_breaks = break_analyzer.analyze_all_pairs(forex_data)

    # Store all breaks
    total_breaks_stored = 0
    breaks_by_pair = {}
    for pair, breaks in all_breaks.items():
        count = break_analyzer.store_breaks(breaks)
        total_breaks_stored += count
        breaks_by_pair[pair] = len(breaks)

    # Step 4: Update pairs metadata
    logger.info("Step 4: Updating pairs metadata...")
    cursor = conn.cursor()
    for pair, df in forex_data.items():
        cursor.execute("""
            INSERT INTO forex_pairs (
                pair, base_currency, quote_currency,
                data_start_date, data_end_date, total_records,
                model_trained, model_trained_at, model_version
            ) VALUES (%s, %s, %s, %s, %s, %s, TRUE, NOW(), 'v1.0')
            ON CONFLICT (pair) DO UPDATE SET
                data_start_date = EXCLUDED.data_start_date,
                data_end_date = EXCLUDED.data_end_date,
                total_records = EXCLUDED.total_records,
                model_trained = TRUE,
                model_trained_at = NOW(),
                model_version = 'v1.0'
        """, (
            pair,
            pair.split('/')[0],
            pair.split('/')[1],
            df.index.min().date() if hasattr(df.index.min(), 'date') else df.index.min(),
            df.index.max().date() if hasattr(df.index.max(), 'date') else df.index.max(),
            len(df),
        ))
    conn.commit()
    cursor.close()

    # Step 5: Store model info
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO forex_models (
            pair, model_type, model_version,
            training_samples, strong_patterns, mid_patterns, weak_patterns
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (
        'ALL',
        'correlation',
        'v1.0',
        corr_results['correlations_computed'],
        corr_results['pattern_counts']['strong'],
        corr_results['pattern_counts']['mid'],
        corr_results['pattern_counts']['weak'],
    ))
    conn.commit()
    cursor.close()

    # Summary
    summary = {
        'pairs_analyzed': len(forex_data),
        'data_rows_stored': sum(data_counts.values()),
        'correlations_computed': corr_results['correlations_computed'],
        'pattern_counts': corr_results['pattern_counts'],
        'thresholds': corr_results['thresholds'],
        'trend_breaks_detected': sum(len(b) for b in all_breaks.values()),
        'trend_breaks_by_pair': breaks_by_pair,
    }

    logger.info("\n=== TRAINING COMPLETE ===")
    logger.info(f"Pairs analyzed: {summary['pairs_analyzed']}")
    logger.info(f"Total data rows: {summary['data_rows_stored']}")
    logger.info(f"Correlations computed: {summary['correlations_computed']}")
    logger.info(f"Pattern counts: Strong={summary['pattern_counts']['strong']}, "
                f"Mid={summary['pattern_counts']['mid']}, Weak={summary['pattern_counts']['weak']}")
    logger.info(f"Trend breaks detected: {summary['trend_breaks_detected']}")

    return summary


# ──────────────────────────────────────────────────────────────────────────────
# CLI Entry Point
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    import argparse

    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    parser = argparse.ArgumentParser(description='Train forex correlation models')
    parser.add_argument('--db-host', default='localhost', help='Database host')
    parser.add_argument('--db-port', default=5432, type=int, help='Database port')
    parser.add_argument('--db-name', default='trading', help='Database name')
    parser.add_argument('--db-user', default='trading', help='Database user')
    parser.add_argument('--db-password', default='', help='Database password')

    args = parser.parse_args()

    import psycopg2
    conn = psycopg2.connect(
        host=args.db_host,
        port=args.db_port,
        dbname=args.db_name,
        user=args.db_user,
        password=args.db_password,
    )

    try:
        summary = train_forex_models(conn)

        print("\n" + "="*60)
        print("FOREX MODEL TRAINING SUMMARY")
        print("="*60)
        print(f"Pairs analyzed: {summary['pairs_analyzed']}")
        print(f"Data rows stored: {summary['data_rows_stored']}")
        print(f"Correlations computed: {summary['correlations_computed']}")
        print(f"\nPattern Counts:")
        print(f"  Strong: {summary['pattern_counts']['strong']}")
        print(f"  Mid: {summary['pattern_counts']['mid']}")
        print(f"  Weak: {summary['pattern_counts']['weak']}")
        print(f"\nTrend Breaks Detected: {summary['trend_breaks_detected']}")
        print("\nBreaks by Pair:")
        for pair, count in sorted(summary['trend_breaks_by_pair'].items(), key=lambda x: -x[1]):
            print(f"  {pair}: {count}")
    finally:
        conn.close()
