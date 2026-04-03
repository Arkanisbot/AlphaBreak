"""
Portfolio Analytics Module
==========================
Computes performance metrics: Sharpe ratio, max drawdown, win streaks,
P&L calendar, best/worst trades.
"""

import logging
import math
from datetime import date, timedelta

logger = logging.getLogger(__name__)


def get_analytics_summary():
    """Compute full analytics summary from portfolio data."""
    from app.utils.database import db_manager

    # Get performance history
    perf_rows = db_manager.execute_query("""
        SELECT snapshot_date, total_value, daily_pnl, daily_pnl_pct, total_pnl, total_pnl_pct, win_rate
        FROM portfolio_performance ORDER BY snapshot_date ASC
    """)

    # Get transaction stats
    tx_rows = db_manager.execute_query("""
        SELECT action, realized_pnl, realized_pnl_pct, executed_at
        FROM portfolio_transactions
        WHERE action IN ('sell', 'sell_to_close')
          AND realized_pnl IS NOT NULL
        ORDER BY executed_at
    """)

    if not perf_rows:
        return {'error': 'No performance data available'}

    # Daily returns for Sharpe
    daily_returns = [float(r[3] or 0) for r in perf_rows if r[3] is not None]
    equity_values = [float(r[1]) for r in perf_rows]
    total_value = equity_values[-1] if equity_values else 100000
    total_pnl = float(perf_rows[-1][4] or 0)
    total_pnl_pct = float(perf_rows[-1][5] or 0)

    # Sharpe ratio
    sharpe = compute_sharpe_ratio(daily_returns)

    # Max drawdown
    max_dd, max_dd_pct = compute_max_drawdown(equity_values)

    # Trade stats
    trades = [{'pnl': float(r[1]), 'pnl_pct': float(r[2] or 0), 'date': r[3]} for r in (tx_rows or [])]
    wins = [t for t in trades if t['pnl'] > 0]
    losses = [t for t in trades if t['pnl'] <= 0]
    total_trades = len(trades)
    win_rate = len(wins) / total_trades if total_trades > 0 else 0
    avg_win = sum(t['pnl'] for t in wins) / len(wins) if wins else 0
    avg_loss = sum(t['pnl'] for t in losses) / len(losses) if losses else 0
    avg_win_pct = sum(t['pnl_pct'] for t in wins) / len(wins) if wins else 0
    avg_loss_pct = sum(t['pnl_pct'] for t in losses) / len(losses) if losses else 0

    # Streaks
    win_streak, loss_streak = compute_streaks(trades)

    # Profit factor
    gross_profit = sum(t['pnl'] for t in wins)
    gross_loss = abs(sum(t['pnl'] for t in losses))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf') if gross_profit > 0 else 0

    return {
        'total_value': total_value,
        'total_pnl': total_pnl,
        'total_pnl_pct': total_pnl_pct,
        'sharpe_ratio': sharpe,
        'max_drawdown': max_dd,
        'max_drawdown_pct': max_dd_pct,
        'total_trades': total_trades,
        'winning_trades': len(wins),
        'losing_trades': len(losses),
        'win_rate': win_rate,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'avg_win_pct': avg_win_pct,
        'avg_loss_pct': avg_loss_pct,
        'profit_factor': profit_factor,
        'best_win_streak': win_streak,
        'worst_loss_streak': loss_streak,
        'days_tracked': len(perf_rows),
    }


def get_equity_curve(days=90):
    """Get equity curve data for charting."""
    from app.utils.database import db_manager

    rows = db_manager.execute_query("""
        SELECT snapshot_date, total_value, daily_pnl, total_pnl_pct, cash_balance, holdings_value
        FROM portfolio_performance
        WHERE snapshot_date >= CURRENT_DATE - INTERVAL '%s days'
        ORDER BY snapshot_date ASC
    """, (days,))

    if not rows:
        return []

    equity_values = [float(r[1]) for r in rows]
    running_max = equity_values[0]
    curve = []

    for r in rows:
        val = float(r[1])
        running_max = max(running_max, val)
        drawdown = (val - running_max) / running_max if running_max > 0 else 0

        curve.append({
            'date': r[0].isoformat(),
            'value': val,
            'daily_pnl': float(r[2] or 0),
            'total_return_pct': float(r[3] or 0),
            'cash': float(r[4] or 0),
            'holdings': float(r[5] or 0),
            'drawdown_pct': drawdown,
        })

    return curve


def get_pnl_calendar(days=90):
    """Get daily P&L grouped for calendar heatmap."""
    from app.utils.database import db_manager

    rows = db_manager.execute_query("""
        SELECT snapshot_date, daily_pnl, daily_pnl_pct
        FROM portfolio_performance
        WHERE snapshot_date >= CURRENT_DATE - INTERVAL '%s days'
        ORDER BY snapshot_date ASC
    """, (days,))

    calendar = []
    for r in (rows or []):
        calendar.append({
            'date': r[0].isoformat(),
            'pnl': float(r[1] or 0),
            'pnl_pct': float(r[2] or 0),
            'weekday': r[0].weekday(),  # 0=Mon, 6=Sun
        })

    return calendar


def get_best_worst_trades(n=5):
    """Get top N best and worst trades by realized P&L."""
    from app.utils.database import db_manager

    best = db_manager.execute_query("""
        SELECT ticker, action, holding_type, asset_type, quantity, price, total_value,
               realized_pnl, realized_pnl_pct, signal_source, executed_at, option_type
        FROM portfolio_transactions
        WHERE realized_pnl IS NOT NULL AND realized_pnl > 0
        ORDER BY realized_pnl DESC LIMIT %s
    """, (n,))

    worst = db_manager.execute_query("""
        SELECT ticker, action, holding_type, asset_type, quantity, price, total_value,
               realized_pnl, realized_pnl_pct, signal_source, executed_at, option_type
        FROM portfolio_transactions
        WHERE realized_pnl IS NOT NULL AND realized_pnl < 0
        ORDER BY realized_pnl ASC LIMIT %s
    """, (n,))

    def format_trade(row):
        return {
            'ticker': row[0], 'action': row[1], 'holding_type': row[2],
            'asset_type': row[3], 'quantity': float(row[4]),
            'price': float(row[5]), 'total_value': float(row[6]),
            'realized_pnl': float(row[7]), 'realized_pnl_pct': float(row[8] or 0),
            'signal_source': row[9],
            'executed_at': row[10].isoformat() if row[10] else None,
            'option_type': row[11],
        }

    return {
        'best': [format_trade(r) for r in (best or [])],
        'worst': [format_trade(r) for r in (worst or [])],
    }


def compute_sharpe_ratio(daily_returns, risk_free_rate=0.05):
    """Compute annualized Sharpe ratio."""
    if len(daily_returns) < 2:
        return 0

    rf_daily = risk_free_rate / 252
    excess = [r - rf_daily for r in daily_returns]
    mean_excess = sum(excess) / len(excess)
    variance = sum((r - mean_excess) ** 2 for r in excess) / (len(excess) - 1)
    std = math.sqrt(variance) if variance > 0 else 0

    if std == 0:
        return 0

    return (mean_excess / std) * math.sqrt(252)


def compute_max_drawdown(equity_values):
    """Compute maximum drawdown (dollar amount and percentage)."""
    if not equity_values:
        return 0, 0

    running_max = equity_values[0]
    max_dd = 0
    max_dd_pct = 0

    for val in equity_values:
        running_max = max(running_max, val)
        dd = running_max - val
        dd_pct = dd / running_max if running_max > 0 else 0

        if dd > max_dd:
            max_dd = dd
        if dd_pct > max_dd_pct:
            max_dd_pct = dd_pct

    return max_dd, max_dd_pct


def compute_streaks(trades):
    """Compute longest winning and losing streaks."""
    if not trades:
        return 0, 0

    max_win = 0
    max_loss = 0
    current_win = 0
    current_loss = 0

    for t in trades:
        if t['pnl'] > 0:
            current_win += 1
            current_loss = 0
            max_win = max(max_win, current_win)
        else:
            current_loss += 1
            current_win = 0
            max_loss = max(max_loss, current_loss)

    return max_win, max_loss
