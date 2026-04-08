"""
Canonical AlphaBreak tier assignments (from user input April 3 2026).
Import this from other build scripts to keep all files in sync.
"""

# Maps feature name -> AlphaBreak tier string
# Tier values: "Free", "Pro", "Elite", "No", "Planned (Elite)", "Planned (Future)", "Planned (Q3)", "Planned (Q4)", "API tier"

AB_TIERS = {
    # Overview & Fundamentals
    "Company overview / key stats":     "Free",
    "Income statement":                 "Free",
    "Balance sheet":                    "Free",
    "Cash flow statement":              "Free",
    "Revenue by segment":               "Elite",
    "Revenue by geography":             "Elite",
    "Analyst consensus & targets":      "Free",
    "Earnings estimates & revisions":   "Free",
    "Earnings call transcripts":        "Planned (Elite)",
    "Peer comparison table":            "Pro",
    "Dividend analysis":                "Pro",
    "Insider trading data":             "Pro",
    "Institutional ownership / 13F":    "Free",
    "Supply chain mapping":             "Elite",
    "3-statement financials w/ trends": "Elite",
    "DuPont decomposition":             "Elite",
    "DCF / intrinsic value model":      "Planned (Future)",

    # Charting & Technical Analysis
    "Interactive charting":             "Free",
    "Technical indicators (RSI, MACD, etc.)": "Free",
    "Technical indicators":             "Free",
    "Drawing tools (Fib, trendlines)":  "Pro",
    "Drawing tools":                    "Pro",
    "Multi-timeframe analysis":         "Pro",
    "Auto-detected trendlines":         "Pro",
    "Auto Fibonacci levels":            "No",
    "Candlestick pattern recognition":  "Planned (Future)",
    "Seasonality patterns (return heatmap)": "Pro",
    "Seasonality heatmap":              "Pro",
    "Custom scripting language":        "No",
    "Custom scripting":                 "No",
    "Custom scripting (BQL)":           "No",
    "Raindrop / volume profile charts": "Planned (Future)",
    "Raindrop / volume profile":        "Planned (Future)",
    "Technical opinion signal":         "Free",

    # Options Analytics
    "Options chain":                    "Free",
    "Options chain + Greeks":           "Free",
    "Greeks (Δ, Γ, Θ, V)":             "Elite",
    "Greeks (Delta, Gamma, Theta, Vega)": "Elite",
    "Fair value (Black-Scholes, Binomial)": "Pro",
    "Fair value (Black-Scholes)":       "Pro",
    "IV history / vol surface":         "Elite",
    "Unusual options activity":         "Pro",
    "Probability of profit":            "Pro",
    "Risk profile / P&L diagram":       "Planned (Future)",
    "Strategy builder (spreads, condors)": "Planned (Future)",
    "Strategy builder + P&L diagram":   "Planned (Future)",
    "Market Maker Move":                "Pro",
    "IV crush modeling":                "Elite",
    "ORATS historical data":            "Elite",
    "Options flow dashboard":           "Elite",

    # AI, Scoring & Quantitative
    "Quant letter grades (A-F)":        "Pro",
    "AI trade scoring":                 "Free",
    "Composite tech + fundamental score": "Free",
    "Composite tech+fundamental score": "Free",
    "Smart checklists (multi-indicator)": "Pro",
    "Smart checklists":                 "Pro",
    "Regime-aware analysis":            "Free",
    "News NLP sentiment scoring":       "Pro",
    "Earnings surprise prediction (ML)": "Elite",
    "Earnings surprise prediction":     "Elite",
    "Signal accuracy tracking":         "Free",
    "Short interest / squeeze score":   "Pro",

    # Portfolio, Journal & Workflow
    "Portfolio tracker":                "Free",
    "Trade journal":                    "Free",
    "AI-scored journal entries":        "Free",
    "Trade thesis builder":             "Pro",
    "Pre-trade plans + post-trade reviews": "Pro",
    "Pre/post-trade reviews":           "Pro",
    "Community / shared journal":       "Free",
    "Watchlist":                        "Free",
    "Email / push notifications":       "Free",
    "Backtesting":                      "Elite",
    "Brokerage integration":            "Planned (Q4)",

    # Data & Infrastructure
    "Real-time data":                   "Pro",
    "Delayed data (free)":              "Free",
    "API access":                       "API tier",
    "WebSocket streaming":              "Pro",
    "Mobile app":                       "Planned (Q3)",
    "Dark pool data":                   "Pro",
    "Forex correlations":               "Free",
}
