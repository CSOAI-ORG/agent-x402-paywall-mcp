#!/usr/bin/env python3
"""
Agent x402 Paywall MCP — HTTP 402 + on-chain settlement
========================================================

By MEOK AI Labs · https://meok.ai · MIT
<!-- mcp-name: io.github.CSOAI-ORG/agent-x402-paywall-mcp -->

WHAT THIS DOES
--------------
Wraps the Coinbase x402 protocol — agents pay per-API-call without needing
a Stripe account. Settle on-chain via USDC (Base / Polygon / Solana) or
Lightning Network (Bitcoin). Pure HTTP. Zero SDK requirement.

The killer feature: agents don't need to register, sign up, or share PII.
They just hit a URL, get HTTP 402, settle on-chain, retry, get the answer.
This is THE plumbing for the agent economy.

USE CASES
---------
- Charge agents £0.0002 per MCP call without a Stripe customer relationship
- Sell premium agent tools on a per-use basis
- Build "API for agents" that monetises calls cleanly
- Bypass Stripe Connect for micropayments
- Cross-border agent commerce (USDC works everywhere)

PRICING
-------
Free MIT self-host · £29/mo Starter · £79/mo Pro (rate-card management) ·
A2A Substrate £499/mo (https://meok.ai/a2a) · Universe £1,499/mo.
"""

from __future__ import annotations
import hashlib
import hmac
import json
import os
import time
from datetime import datetime, timezone
from typing import Optional
from mcp.server.fastmcp import FastMCP
import urllib.request as _meter_urlreq
import urllib.error as _meter_urlerr


mcp = FastMCP("agent-x402-paywall")

_HMAC_SECRET = os.environ.get("MEOK_HMAC_SECRET", "")
_SETTLE_TO = os.environ.get("X402_SETTLE_ADDR", "0xMEOKplaceholder000000000000000000000000")


# Supported settlement chains + their min-confirmation windows
CHAINS = {
    "base":        {"name": "Base (USDC)", "currency": "USDC", "min_confirmations": 1, "settle_seconds": 3},
    "polygon":     {"name": "Polygon (USDC)", "currency": "USDC", "min_confirmations": 1, "settle_seconds": 3},
    "solana":      {"name": "Solana (USDC)", "currency": "USDC", "min_confirmations": 1, "settle_seconds": 2},
    "lightning":   {"name": "Bitcoin Lightning", "currency": "SAT", "min_confirmations": 0, "settle_seconds": 1},
    "ethereum":    {"name": "Ethereum mainnet (USDC)", "currency": "USDC", "min_confirmations": 6, "settle_seconds": 90},
}


# In-memory paid-call ledger. Production: KV store + on-chain reconciliation.
_PAYMENTS: dict[str, dict] = {}


def _sign(payload: dict) -> str:
    if not _HMAC_SECRET:
        return "unsigned-no-key-configured"
    body = json.dumps(payload, sort_keys=True).encode()
    return hmac.new(_HMAC_SECRET.encode(), body, hashlib.sha256).hexdigest()


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


# ────────────────────────────────────────────────────────────────────────
# Tools
# ────────────────────────────────────────────────────────────────────────

def _server_meter_check(api_key: str = "") -> dict:
    """Calls the live /verify endpoint for server-side metering. Returns the JSON dict.
    Fail-open: if /verify is unreachable or KV isn't configured, returns allowed=True
    (so the local rate-limit in _check_rate_limit remains the safety net)."""
    try:
        data = json.dumps({"api_key": api_key, "tool": ""}).encode()
        req = _meter_urlreq.Request(_METER_URL, data=data,
            headers={"Content-Type": "application/json"}, method="POST")
        with _meter_urlreq.urlopen(req, timeout=2.5) as r:
            d = json.loads(r.read())
            if isinstance(d, dict) and "allowed" in d:
                return d
    except Exception:
        pass
    return {"allowed": True, "tier": "anonymous", "remaining": 200, "upgrade_url": "https://meok.ai/pricing"}


_METER_URL = "https://proofof.ai/verify"


@mcp.tool()
def list_supported_chains() -> dict:
    """List on-chain settlement options + min-confirmation windows."""
    return {
        "chains": [{"id": k, **v} for k, v in CHAINS.items()],
        "default": "base",
        "note": "USDC on Base is the default — fastest + cheapest. Lightning Network is the fallback for Bitcoin-native agents.",
    }


@mcp.tool()
def build_402_challenge(
    resource_url: str,
    amount_minor: int,
    currency: str = "USDC",
    chain: str = "base",
    settle_to: Optional[str] = None,
    expires_in_seconds: int = 600,
) -> dict:
    """
    Build an HTTP 402 Payment-Required challenge for a resource.

    Args:
        resource_url: The URL the agent tried to access.
        amount_minor: Amount in minor units (e.g. cents for USDC, satoshi for Lightning).
        currency: ISO 4217 or token symbol. Default USDC.
        chain: Settlement chain — "base", "polygon", "solana", "lightning", "ethereum".
        settle_to: Override settlement address. Default reads from $X402_SETTLE_ADDR.
        expires_in_seconds: Challenge TTL. Default 600 (10 min).

    Returns:
        {http_status: 402, headers, body, signed_challenge}
    """
    if chain not in CHAINS:
        return {"error": "unknown_chain", "valid": list(CHAINS.keys())}

    cfg = CHAINS[chain]
    expires_at = int(time.time()) + expires_in_seconds
    challenge_id = f"x402_{int(time.time())}_{os.urandom(4).hex()}"
    challenge = {
        "challenge_id": challenge_id,
        "resource_url": resource_url,
        "amount_minor": amount_minor,
        "amount_display": f"{amount_minor / 1000000:.6f} {currency}" if currency == "USDC" else f"{amount_minor} {currency}",
        "currency": currency.upper(),
        "chain": chain,
        "chain_name": cfg["name"],
        "min_confirmations": cfg["min_confirmations"],
        "expected_settle_seconds": cfg["settle_seconds"],
        "settle_to": settle_to or _SETTLE_TO,
        "expires_at": expires_at,
        "ts": _ts(),
    }
    sig = _sign(challenge)

    headers = {
        "x-402-payment-required": "true",
        "x-402-challenge-id": challenge_id,
        "x-402-amount": str(amount_minor),
        "x-402-currency": currency.upper(),
        "x-402-chain": chain,
        "x-402-settle-to": challenge["settle_to"],
        "x-402-expires-at": str(expires_at),
        "x-402-signature": sig,
        "x-meok-attestation": sig,
    }

    return {
        "http_status": 402,
        "headers": headers,
        "body": {
            "error": "payment_required",
            "challenge": challenge,
            "signature": sig,
            "instructions": "Settle on-chain, then retry the original call with header `x-402-payment-id: <tx_hash>`.",
            "alternative_protocols": ["stripe-acp (via agent-commerce-protocol-mcp)", "ap2 (via agent-commerce-payments-mcp)"],
        },
    }


@mcp.tool()
def verify_payment(
    challenge_id: str,
    tx_hash: str,
    chain: str = "base",
    auto_record: bool = True,
) -> dict:
    """
    Verify an on-chain payment claim against an issued 402 challenge.

    Args:
        challenge_id: The challenge_id from build_402_challenge().
        tx_hash: The on-chain transaction hash provided by the paying agent.
        chain: Chain the tx was settled on.
        auto_record: If True (default), record the payment in the ledger.

    Returns:
        {verified, status, audit_chain_entry, retry_url}
    """
    if chain not in CHAINS:
        return {"error": "unknown_chain", "valid": list(CHAINS.keys())}

    # Production wiring would query the chain RPC + verify recipient + amount.
    # Scaffold: accept any non-empty tx_hash. Pro tier wires real RPC checks.
    verified = bool(tx_hash and len(tx_hash) >= 16 and not tx_hash.startswith("invalid"))
    status = "settled" if verified else "tx_not_found"

    payment_id = f"x402_pay_{int(time.time())}_{os.urandom(4).hex()}"
    record = {
        "payment_id": payment_id,
        "challenge_id": challenge_id,
        "tx_hash": tx_hash,
        "chain": chain,
        "verified": verified,
        "status": status,
        "ts": _ts(),
    }
    sig = _sign(record)
    audit_entry = {**record, "signature": sig}
    if auto_record:
        _PAYMENTS[payment_id] = audit_entry

    return {
        "verified": verified,
        "status": status,
        "payment_id": payment_id if verified else None,
        "audit_chain_entry": audit_entry,
        "signature": sig,
        "retry_url": "Add header `x-402-payment-id: " + payment_id + "` to your retry call." if verified else None,
        "verify_url": "https://verify.meok.ai",
    }


@mcp.tool()
def estimate_settlement_cost(
    chain: str,
    amount_minor: int,
) -> dict:
    """
    Estimate the on-chain fee for a settlement, for agent budget planning.

    Args:
        chain: One of "base", "polygon", "solana", "lightning", "ethereum".
        amount_minor: Amount being settled (minor units).

    Returns:
        {gas_estimate_minor, total_minor, recommendation}
    """
    if chain not in CHAINS:
        return {"error": "unknown_chain", "valid": list(CHAINS.keys())}

    # Conservative gas estimates (refresh quarterly):
    gas_minor = {
        "base":      100,   # ~$0.001 USDC
        "polygon":   100,
        "solana":     20,
        "lightning":  1,    # 1 satoshi
        "ethereum":  20000, # mainnet expensive
    }[chain]

    total = amount_minor + gas_minor
    recommendation = "OK" if gas_minor < amount_minor * 0.1 else "FEE_HIGH_VS_AMOUNT — consider Base or Lightning"
    return {
        "chain": chain,
        "amount_minor": amount_minor,
        "gas_estimate_minor": gas_minor,
        "total_minor": total,
        "fee_ratio": round(gas_minor / max(amount_minor, 1) * 100, 3),
        "recommendation": recommendation,
    }


@mcp.tool()
def get_payment(payment_id: str) -> dict:
    """Retrieve a verified payment record."""
    p = _PAYMENTS.get(payment_id)
    if not p:
        return {"error": "unknown_payment_id"}
    return p


@mcp.tool()
def list_recent_payments(limit: int = 20) -> dict:
    """List recent verified payments for monitoring."""
    items = list(_PAYMENTS.values())[-limit:]
    return {
        "count": len(items),
        "payments": items,
        "total_settled_gbp_estimate": "Use sum of amount_minor / 1_000_000 for USDC chains.",
    }


def main():
    mcp.run()


if __name__ == "__main__":
    main()
