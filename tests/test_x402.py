"""Smoke tests for agent-x402-paywall-mcp."""
import sys, os, inspect, traceback
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import (
    list_supported_chains,
    build_402_challenge,
    verify_payment,
    estimate_settlement_cost,
    get_payment,
    list_recent_payments,
    _PAYMENTS,
    CHAINS,
)


def test_supported_chains_includes_base():
    r = list_supported_chains()
    ids = {c["id"] for c in r["chains"]}
    assert "base" in ids and "lightning" in ids and "solana" in ids


def test_build_challenge_returns_402():
    r = build_402_challenge("https://api.meok.ai/v1/x/y", 1000, "USDC", "base")
    assert r["http_status"] == 402
    assert "x-402-amount" in r["headers"]
    assert r["body"]["challenge"]["chain"] == "base"


def test_build_challenge_unknown_chain():
    r = build_402_challenge("https://x", 100, "USDC", "ZZZ")
    assert "error" in r


def test_verify_valid_tx():
    challenge = build_402_challenge("https://x", 1000, "USDC", "base")
    cid = challenge["body"]["challenge"]["challenge_id"]
    r = verify_payment(cid, tx_hash="0xabc1234567890def", chain="base")
    assert r["verified"] is True
    assert r["payment_id"] is not None


def test_verify_invalid_tx():
    r = verify_payment("any_challenge", tx_hash="invalid", chain="base")
    assert r["verified"] is False


def test_estimate_settlement_cost_base_is_cheap():
    r = estimate_settlement_cost("base", 1000)
    assert r["gas_estimate_minor"] < r["amount_minor"] * 0.5


def test_estimate_settlement_eth_warns_high():
    r = estimate_settlement_cost("ethereum", 100)  # tiny tx on expensive chain
    assert "HIGH" in r["recommendation"]


def test_get_payment_unknown():
    r = get_payment("does_not_exist")
    assert "error" in r


def test_payment_round_trip():
    _PAYMENTS.clear()
    challenge = build_402_challenge("https://x", 500, "USDC", "polygon")
    cid = challenge["body"]["challenge"]["challenge_id"]
    v = verify_payment(cid, "0xpolytx0123456789abc", "polygon")
    pid = v["payment_id"]
    p = get_payment(pid)
    assert p["verified"] is True
    rec = list_recent_payments()
    assert rec["count"] >= 1


if __name__ == "__main__":
    g = dict(globals())
    fns = [v for k, v in g.items() if k.startswith("test_") and inspect.isfunction(v)]
    p = f = 0
    for fn in fns:
        try:
            fn(); print(f"✓ {fn.__name__}"); p += 1
        except Exception as e:
            print(f"✗ {fn.__name__}: {type(e).__name__}: {e}")
            traceback.print_exc()
            f += 1
    print(f"\n{p} passed, {f} failed")
