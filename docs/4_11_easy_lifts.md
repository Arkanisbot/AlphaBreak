# Easy Lifts — April 11, 2026

Ordered by effort (easiest first). Gated items are indented under their dependency.

1. ~~**CORS Configuration** — Lock down Flask CORS to alphabreak.vip origins only. One config change.~~
2. ~~**Dark Pool Data API + UI** — Backend already has 621K rows. Just needs API routes and a frontend widget. No new data work.~~
3. ~~**Connection Pooling** — Upgraded to ThreadedConnectionPool, min=2, max=20, env-configurable.~~
4. ~~**Query Caching (Redis)** — Flask-Caching with RedisCache in prod, SimpleCache in dev. Replaced in-memory dicts in analyze, dashboard, earnings routes.~~
5. ~~**Input Validation** — Ticker regex, interval/period whitelists, safe int conversions across journal, reports, notifications, analyze routes.~~
6. **Secrets Management** — Rotate API keys/DB passwords, move to AWS Secrets Manager. Operational, no feature code.
7. ~~**Email Templates** — 10 branded HTML templates (dark theme, mobile-responsive) + email service with SES sending.~~
   1. ~~**Bounce Handling** — SES bounce/complaint webhook via SNS, auto-disables bounced emails.~~
8. ~~**CDN (CloudFront)** — Setup scripts created (`kubernetes/scripts/setup-cloudfront.sh`, `setup-waf.sh`, `update-nginx-cloudfront.conf`). Ready to run on AWS.~~
   1. ~~**DDoS Protection (WAF)** — WAF script with rate limiting, AWS common rules, bad inputs, IP reputation.~~
9. ~~**Social Proof** — Expanded landing page stats to 6 data points (854K trades, 98.5% win rate, 8.4M holdings, etc.).~~
10. ~~**Free Tool Hooks** — Added "Start free, upgrade when you're ready" section with 3 feature cards (AI scoring, trend breaks, portfolio tracker).~~
11. **SEO Content** — Blog posts targeting "best stock analysis tools", "Bloomberg alternative", etc. Content only.
12. ~~**Structured Thesis Template** — Added 7 structured fields (entry criteria, price target, stop loss, time horizon, catalysts, risks, conviction level) to pre-trade plans via existing JSONB column.~~
13. ~~**Peer Comparison Table** — Side-by-side P/E, EV/EBITDA, ROE, revenue growth vs sector peers. Pro-gated with premium badge.~~
14. **Probability of Profit** — IV-based probability calculations for options positions. Math is well-defined, IV data already exists.
15. **Rate Limiting Tuning** — Flask-Limiter is configured but needs per-user, per-endpoint tuning. Config work.
16. **Query Optimization** — Add indexes on hot query paths, analyze plans, fix N+1 queries. Incremental.
17. **Insider Trading Signals** — SEC Form 4 filings via SEC EDGAR API. New data source + UI.
18. **Unusual Options Activity** — Volume vs 5-day avg, block trades, sweep detection. Needs options flow data.
19. **News NLP Sentiment Scoring** — FinBERT-scored headlines. Needs model deployment (HuggingFace).
20. **Automated Annotations** — Auto-tag journal entries with signals/indicators/conditions at time of trade. Depends on existing journal + indicator data.
21. **Stripe Integration** — Billing, plan management, 14-day trials, upgrade/downgrade flows. Medium lift, gates monetization.
    1. **Referral Program** — "Give 30 days Pro, get 30 days free." Depends on Stripe billing.
    2. **Freemium Conversion Funnel** — Track free → Pro conversion. Depends on Stripe billing.
    3. **Daily Email Digest** — Personalized watchlist alerts. Depends on email templates + user preferences.
    4. **Email Drip Campaign** — Waitlist → free trial → Pro conversion. Depends on Stripe + email templates.
22. **Uptime Monitoring** — External health check pings + status page. Standalone, quick setup.
23. **Structured Logging** — JSON logs → CloudWatch or Loki. Operational.
    1. **Prometheus + Grafana** — Metrics collection and dashboards. Depends on structured logging being useful first.
    2. **Alerting (PagerDuty/Slack)** — Depends on Prometheus metrics being in place.
24. **Multi-Chart Layout** — 2-4 charts side-by-side with synced crosshairs. Moderate frontend work.
    1. **Multi-Timeframe Analysis** — Overlay indicators from multiple timeframes. Depends on multi-chart layout.
25. **WebSocket Infrastructure** — Flask-SocketIO + Redis Pub/Sub. Medium-heavy lift.
    1. **Connection Management** — Handle 10K+ concurrent WebSocket connections. Depends on WebSocket infra.
    2. **Real-Time Data (Polygon.io)** — Live quotes. Depends on WebSocket infra + Polygon subscription.
    3. **Price Feed Integration** — Polygon → Redis → Client pipeline. Depends on WebSocket + Polygon.
    4. **WebSocket Streaming (API tier)** — Depends on WebSocket infra.
