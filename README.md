# Agent x402 Paywall MCP

> ## 🧱 Part of the MEOK A2A Substrate (£499/mo)
> See [meok.ai/a2a](https://meok.ai/a2a).

# HTTP 402 + on-chain settlement — pay-per-call for agents

<!-- mcp-name: io.github.CSOAI-ORG/agent-x402-paywall-mcp -->

[![PyPI](https://img.shields.io/pypi/v/agent-x402-paywall-mcp)](https://pypi.org/project/agent-x402-paywall-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## The product

Wraps the **Coinbase x402** protocol (HTTP 402 Payment Required) so AI agents can pay per-API-call without a Stripe customer relationship. Pure HTTP. Zero SDK. Settles on-chain via USDC (Base / Polygon / Solana) or Lightning Network.

Combine with `agent-commerce-protocol-mcp` (Stripe ACP) and `agent-commerce-payments-mcp` (AP2 / PSD2 / MiCA) for full coverage of all 3 live agent-payment protocols.

## Tools

| Tool | Purpose |
|---|---|
| `list_supported_chains()` | Base · Polygon · Solana · Lightning · Ethereum mainnet |
| `build_402_challenge(url, amount, currency, chain, expires?)` | Build HTTP 402 response |
| `verify_payment(challenge_id, tx_hash, chain)` | Verify on-chain settlement |
| `estimate_settlement_cost(chain, amount)` | Gas/fee preview |
| `get_payment(payment_id)` | Look up a verified payment |
| `list_recent_payments(limit)` | Monitor recent settlements |

## Why this unlocks revenue

The agent economy needs frictionless micropayments. Stripe Connect requires KYC, US-bank linkage, and customer accounts — fine for SaaS, fatal for agent-to-API calls. x402 is the inverse: agent hits URL → 402 → settles on-chain → retries → gets the answer. No accounts, no PII.

For MEOK specifically: this MCP wraps `api.meok.ai` itself so external agents can pay £0.0002/call to access our 52 MCPs **without** signing up for Stripe Universal PAYG. Stripe customers stay on Stripe; on-chain customers settle on-chain; same gateway behind both.

## Sister MCPs

- `agent-commerce-protocol-mcp` — Stripe ACP bridge
- `agent-commerce-payments-mcp` — PSD2/MiCA/AP2
- `agent-rate-limiter-mcp` — call-count throttling
- `agent-token-budget-mcp` — spend cap
- `agent-audit-logger-mcp` — hash-chained payment log

Full catalogue: [meok.ai/anthropic-registry](https://meok.ai/anthropic-registry)

## Protocol coverage + Universal PAYG

| Option | Price |
|---|---|
| Self-host MIT | £0 |
| Universal PAYG | £29/mo + £0.0002/call |
| A2A Substrate | £499/mo |
| Universe (all 52) | £1,499/mo |
| Defence | £4,990/mo |

Buy: https://meok.ai/a2a

## Licence

MIT. By [MEOK AI Labs](https://meok.ai) (CSOAI LTD, UK Companies House 16939677).
