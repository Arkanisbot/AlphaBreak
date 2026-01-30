# Data Sources Comparison: Free vs Subscription vs Enterprise

## Executive Summary

This document compares data sources across three tiers for the AlphaBreak trading platform:
1. **Current (Free Tier)** - Yahoo Finance, FRED, free APIs
2. **Subscription Ready (Mid-Tier)** - Paid APIs suitable for a $20-50/month product
3. **Enterprise (Premium)** - Bloomberg-level institutional data

---

## Quick Comparison Matrix

| Feature | Free (Current) | Mid-Tier ($500-2k/mo) | Enterprise ($2k-25k/mo) |
|---------|---------------|----------------------|------------------------|
| **Real-time Quotes** | 15-20 min delay | Real-time | Real-time + Level 2 |
| **Historical Data** | 5-20 years | 30+ years | 50+ years |
| **Options Data** | Basic chains | Full Greeks, IV | Tick-level, exotics |
| **Dark Pool Data** | FINRA (delayed) | Real-time ATS | Full venue breakdown |
| **13F Filings** | SEC (45-day lag) | Parsed + analytics | Predictive + custom |
| **Forex** | Daily OHLC | Tick-level | Interbank rates |
| **News/Sentiment** | None | Basic NLP | Real-time sentiment |
| **API Rate Limits** | 100-500/day | 10k-100k/day | Unlimited |
| **Support** | Community | Email/chat | Dedicated account |
| **SLA Uptime** | None | 99.5% | 99.99% |

---

## Tier 1: Current Free Data Sources

### Equity Data
| Source | Data Type | Delay | Limits | Quality |
|--------|-----------|-------|--------|---------|
| Yahoo Finance | OHLCV, fundamentals | 15 min | ~2k/hr | Good |
| Alpha Vantage Free | OHLCV, indicators | 15 min | 5/min, 500/day | Good |
| Finnhub Free | Quotes, news | 15 min | 60/min | Moderate |
| IEX Cloud Free | US equities | 15 min | 50k/mo | Good |

### Options Data
| Source | Data Type | Delay | Limits | Quality |
|--------|-----------|-------|--------|---------|
| Yahoo Finance | Basic chains | EOD | ~500/day | Basic |
| CBOE (scraping) | Delayed quotes | 15 min | Manual | Moderate |

### Institutional/Dark Pool
| Source | Data Type | Delay | Limits | Quality |
|--------|-----------|-------|--------|---------|
| SEC EDGAR | 13F filings | 45 days | None | Raw |
| FINRA ATS | Dark pool volume | T+1 | None | Aggregate |

### Forex/Macro
| Source | Data Type | Delay | Limits | Quality |
|--------|-----------|-------|--------|---------|
| Yahoo Finance | Daily FX | EOD | Same as equity | Good |
| FRED | Economic indicators | Varies | 120/min | Excellent |

### Current Limitations
- **Delayed quotes** make intraday signals unreliable
- **No Level 2 data** for order flow analysis
- **Limited options Greeks** - must calculate ourselves
- **No real-time news** for event-driven trading
- **Rate limits** restrict concurrent users
- **No historical tick data** for backtesting HFT strategies
- **Unreliable uptime** - sources can block/throttle without notice

---

## Tier 2: Subscription-Ready Data Sources

### Recommended Primary Provider: **Polygon.io**

| Plan | Cost | Requests | Features |
|------|------|----------|----------|
| Starter | $29/mo | Unlimited | 15-min delay, 2yr history |
| Developer | $79/mo | Unlimited | Real-time, 5yr history |
| Advanced | $199/mo | Unlimited | Real-time, full history, options |
| Business | $499/mo | Unlimited | Everything + websockets |

**Why Polygon:**
- Single API for stocks, options, forex, crypto
- True real-time data (not delayed)
- WebSocket streaming for live updates
- Full historical tick data
- Options with Greeks pre-calculated
- 99.9% uptime SLA

### Alternative/Supplementary Providers

#### IEX Cloud
| Plan | Cost | Messages/mo | Best For |
|------|------|-------------|----------|
| Launch | $9/mo | 500k | Small apps |
| Grow | $49/mo | 5M | Growing platforms |
| Scale | $499/mo | 50M | Production apps |

**Strengths:** Excellent fundamentals, earnings estimates, insider transactions

#### Tradier
| Plan | Cost | Features |
|------|------|----------|
| Market Data | $0 (w/brokerage) | Real-time quotes |
| Developer | $10/mo | API access, paper trading |

**Strengths:** Free real-time if users open brokerage accounts

#### Unusual Whales
| Plan | Cost | Features |
|------|------|----------|
| Basic | $39/mo | Options flow alerts |
| Premium | $79/mo | Dark pool data, congress trades |
| Institutional | $199/mo | Full historical data |

**Strengths:** Pre-analyzed unusual options activity, dark pool flow

#### Quiver Quantitative
| Plan | Cost | Features |
|------|------|----------|
| Basic | $15/mo | Congress, lobbying, contracts |
| Pro | $50/mo | API access, bulk data |

**Strengths:** Alternative data (congress trades, gov contracts, patents)

### Recommended Mid-Tier Stack

**Total Cost: ~$400-800/month**

| Provider | Plan | Cost | Data |
|----------|------|------|------|
| Polygon.io | Advanced | $199/mo | Core market data |
| Unusual Whales | Premium | $79/mo | Options flow |
| IEX Cloud | Grow | $49/mo | Fundamentals |
| Quiver Quant | Pro | $50/mo | Alternative data |
| News API | Pro | $49/mo | News headlines |

### What This Enables
- Real-time quotes and streaming
- Full options chains with Greeks
- Unusual options activity detection
- Dark pool flow analysis
- Congress/insider trading alerts
- News-driven signal generation
- Reliable 99.9% uptime
- 10-50 concurrent users

---

## Tier 3: Enterprise Data Sources

### Bloomberg Terminal / B-PIPE

| Product | Cost | Features |
|---------|------|----------|
| Terminal | $24,000/yr/seat | Full terminal access |
| B-PIPE | $2,000-10,000/mo | Data feed only |
| Enterprise | Custom | Unlimited redistribution |

**Unique Features:**
- BVAL (Bloomberg Valuation Service)
- PORT (Portfolio analytics)
- Real-time earnings estimates
- M&A deal data
- Fixed income analytics
- 50+ years of history

### Refinitiv (formerly Reuters)

| Product | Cost | Features |
|---------|------|----------|
| Eikon | $22,000/yr | Terminal + API |
| DataScope | $1,500-5,000/mo | Historical data |
| Elektron | Custom | Real-time feed |

**Unique Features:**
- Tick History (every trade since 1996)
- StarMine (quantitative models)
- I/B/E/S (analyst estimates)
- World-Check (compliance)

### FactSet

| Product | Cost | Features |
|---------|------|----------|
| Workstation | $12,000/yr | Terminal |
| Data Feeds | $2,000-8,000/mo | API access |
| StreetAccount | $500/mo | Real-time news |

**Unique Features:**
- Ownership data (who owns what)
- Supply chain mapping
- Estimate revisions
- Private company data

### S&P Capital IQ

| Product | Cost | Features |
|---------|------|----------|
| Platform | $18,000/yr | Full access |
| Xpressfeed | $3,000-15,000/mo | Data feed |

**Unique Features:**
- Credit ratings
- Private company financials
- M&A comps
- Key developments

### Specialized Enterprise Providers

#### Options/Derivatives
| Provider | Cost | Specialty |
|----------|------|-----------|
| ORATS | $500-2,000/mo | Options analytics, IV |
| LiveVol | $300-1,000/mo | Options flow, unusual activity |
| OptionMetrics | $5,000+/mo | Academic-grade options data |

#### Alternative Data
| Provider | Cost | Specialty |
|----------|------|-----------|
| Thinknum | $2,000+/mo | Web scraped data |
| Quandl | $500-5,000/mo | Alternative datasets |
| SimilarWeb | $1,000+/mo | Web traffic data |
| Sensor Tower | $5,000+/mo | App analytics |

#### Sentiment/News
| Provider | Cost | Specialty |
|----------|------|-----------|
| RavenPack | $3,000-10,000/mo | News sentiment |
| Alexandria | $2,000+/mo | NLP on filings |
| Estimize | $500+/mo | Crowdsourced estimates |

---

## Feature Comparison by Use Case

### Real-Time Trading Signals

| Feature | Free | Mid-Tier | Enterprise |
|---------|------|----------|------------|
| Quote latency | 15-20 min | <100ms | <10ms |
| Level 2 data | No | Limited | Full book |
| Time & Sales | No | Yes | Tick-by-tick |
| Order imbalance | No | Basic | Full |
| Pre/post market | Limited | Yes | Full |

### Options Analysis

| Feature | Free | Mid-Tier | Enterprise |
|---------|------|----------|------------|
| Chains | Basic | Full | All expirations |
| Greeks | Calculate | Pre-calc | Real-time |
| IV surface | No | Basic | Full surface |
| Unusual activity | Manual | Alerts | Predictive |
| Historical | Limited | 5 years | 20+ years |

### Institutional Flow

| Feature | Free | Mid-Tier | Enterprise |
|---------|------|----------|------------|
| 13F filings | Raw SEC | Parsed | Predictive |
| Dark pool | FINRA T+1 | Real-time | Venue breakdown |
| Block trades | No | Alerts | Full tape |
| Insider trades | Form 4 | Analyzed | Predictive |

### Fundamental Analysis

| Feature | Free | Mid-Tier | Enterprise |
|---------|------|----------|------------|
| Financials | Basic | Full | Standardized |
| Estimates | No | Consensus | I/B/E/S |
| Revisions | No | Basic | Detailed |
| Transcripts | No | Some | Full + NLP |
| Private co | No | No | Yes |

---

## Recommended Upgrade Path

### Phase 1: MVP to Paid Product ($400/mo data cost)
**Target: $20-30/mo subscription, 50-100 users**

```
Current Free Stack
        ↓
Add: Polygon.io Advanced ($199/mo)
     - Real-time quotes
     - Full options chains
     - Historical data
        ↓
Add: Unusual Whales Basic ($39/mo)
     - Options flow alerts
        ↓
Add: IEX Cloud Grow ($49/mo)
     - Better fundamentals
     - Earnings estimates
```

**New Capabilities:**
- Real-time price alerts
- Options flow notifications
- Earnings surprise detection
- Reliable production uptime

### Phase 2: Growth ($800-1,500/mo data cost)
**Target: $50-100/mo subscription, 500-1,000 users**

```
Phase 1 Stack
        ↓
Upgrade: Polygon.io Business ($499/mo)
         - WebSocket streaming
         - Higher rate limits
        ↓
Add: Unusual Whales Premium ($79/mo)
     - Dark pool data
        ↓
Add: Quiver Quant Pro ($50/mo)
     - Congress trades
     - Government contracts
        ↓
Add: News API Business ($199/mo)
     - Real-time news feed
```

**New Capabilities:**
- Live streaming quotes
- Dark pool analysis
- Political trading signals
- News-driven alerts

### Phase 3: Professional ($3,000-5,000/mo data cost)
**Target: $200-500/mo subscription, professional traders**

```
Phase 2 Stack
        ↓
Add: ORATS Professional ($500/mo)
     - IV surfaces
     - Historical volatility
        ↓
Add: RavenPack Edge ($3,000/mo)
     - Sentiment scores
        ↓
Add: Thinknum Basic ($2,000/mo)
     - Alternative data
```

**New Capabilities:**
- Professional-grade options analytics
- Sentiment-driven signals
- Alternative data insights

### Phase 4: Institutional ($10,000+/mo)
**Target: Hedge funds, family offices**

```
Phase 3 Stack
        ↓
Add: Bloomberg B-PIPE or Refinitiv
     - Tick data
     - Full history
        ↓
Add: FactSet or Capital IQ
     - Private company data
     - Full ownership data
```

---

## Cost-Benefit Analysis

### Break-Even Calculator

| Data Cost | Users Needed @ $29/mo | Users Needed @ $99/mo |
|-----------|----------------------|----------------------|
| $400/mo | 14 users | 5 users |
| $800/mo | 28 users | 9 users |
| $1,500/mo | 52 users | 16 users |
| $5,000/mo | 173 users | 51 users |

### Value Add Per Tier

| Feature | User Value | Data Cost to Enable |
|---------|------------|---------------------|
| Real-time quotes | High | $199/mo (Polygon) |
| Options flow | High | $79/mo (UW) |
| Dark pool data | Medium | Included in UW |
| Congress trades | Medium | $50/mo (Quiver) |
| News alerts | Medium | $49-199/mo |
| Sentiment scores | Low-Medium | $3,000/mo |
| Tick data | Low (retail) | $2,000+/mo |

---

## Implementation Recommendations

### Immediate (Free)
1. Optimize current Yahoo Finance usage with caching
2. Add retry logic and fallback sources
3. Implement rate limit management

### Short-Term ($400/mo)
1. Add Polygon.io for real-time core data
2. Replace Yahoo Finance for quotes
3. Keep Yahoo for backup/fallback

### Medium-Term ($800/mo)
1. Add options flow from Unusual Whales
2. Implement WebSocket streaming
3. Add news integration

### Long-Term ($2,000+/mo)
1. Add professional options analytics
2. Implement sentiment analysis
3. Consider enterprise feeds for institutional clients

---

## Appendix: API Comparison

### Rate Limits

| Provider | Free | Paid |
|----------|------|------|
| Yahoo Finance | ~2,000/hr | N/A |
| Alpha Vantage | 5/min | 75/min |
| Polygon.io | N/A | Unlimited |
| IEX Cloud | 50k/mo | 5M-50M/mo |
| Finnhub | 60/min | 300/min |

### Data Freshness

| Provider | Delay | WebSocket |
|----------|-------|-----------|
| Yahoo Finance | 15-20 min | No |
| Polygon.io Paid | Real-time | Yes |
| IEX Cloud | 15 min / Real-time | Yes (paid) |
| Tradier | Real-time | Yes |

### Historical Depth

| Provider | Stocks | Options |
|----------|--------|---------|
| Yahoo Finance | ~20 years | 2-3 years |
| Polygon.io | Full history | 5+ years |
| IEX Cloud | 15+ years | Limited |
| Bloomberg | 50+ years | 30+ years |

---

## Conclusion

**Recommended Next Step:** Upgrade to Polygon.io Advanced ($199/mo) as the foundation for a subscription product. This single upgrade provides:
- Real-time data (eliminates 15-min delay)
- Full options chains with Greeks
- Reliable uptime for paying customers
- Room to grow without changing providers

This enables launching a $29-49/mo subscription product with meaningful improvements over free alternatives.
