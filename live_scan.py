"""
FORWARD-TEST SCANNER (demo-konto: kan nu ogsaa eksekvere)
==========================================
Meant to be run in Claude Code, where the MT5 MCP server is connected.

HOW THIS WORKS:
1. In Claude Code, pull the latest ~1000 M15 candles for XAUUSD and XAGUSD
   via the MT5 MCP tool (get_candles_latest).
2. Convert the result into a DataFrame with columns: open, high, low, close
   and a datetime index (see `candles_to_df` below for the expected shape).
3. Call `scan_for_new_signals(df, symbol, account_balance)`.
4. Any NEW signal gets appended to forward_test_log.csv with entry/SL/TP/lot
   size, AND -- since this is running on the DEMO account, not a real funded
   account -- Claude Code should now also EXECUTE it:
   for each entry returned by scan_for_new_signals(), call the MT5 MCP order
   placement tool (e.g. place_market_order) with:
     symbol=entry["symbol"], direction=entry["direction"],
     volume=entry["lot_size"], sl=entry["sl"], tp=entry["tp"]
   Update entry["status"] to reflect whether the order placement succeeded
   or failed, and log the MT5 order ticket ID if returned.

This remains DEMO-ONLY. Do not point this at a real funded account without
first reviewing several weeks of demo execution results together.
"""
import os
import pandas as pd
from datetime import datetime, timedelta

import strat1_crt_tbs
import strat2_trend_ob_v2
import strat3_orb
from position_sizing import calculate_lot_size

try:
    import strat7_powell_capped
    POWELL_IMPORT_ERROR = None
except ImportError as e:
    strat7_powell_capped = None
    POWELL_IMPORT_ERROR = str(e)

LOG_PATH = os.path.join(os.path.dirname(__file__), "forward_test_log.csv")
FRESHNESS_WINDOW_HOURS = 48  # widened from 4h -- strategies' confirmation chains (reclaim->MSS->retest
# etc.) mean the most recent qualifying signal is typically 12h+ behind "now", even scanning every
# 15 min. Dedup against forward_test_log.csv (below) prevents re-logging the same signal twice, so a
# wider window is safe -- it just means we catch a signal once, soon after it forms, not repeatedly.


def candles_to_df(candles):
    """
    Convert MT5 MCP candle output (list of dicts with time/open/high/low/close,
    or similar) into the DataFrame shape our strategy code expects.
    ADJUST the field names below to match whatever the MCP tool actually returns
    -- check one raw candle's keys first in Claude Code.
    """
    df = pd.DataFrame(candles)
    # common MT5 MCP field names -- adjust if yours differ
    time_col = "time" if "time" in df.columns else "datetime"
    df["datetime"] = pd.to_datetime(df[time_col])
    df = df.set_index("datetime").sort_index()
    df = df[["open", "high", "low", "close"]].astype(float)
    return df


def _load_log():
    if os.path.exists(LOG_PATH):
        return pd.read_csv(LOG_PATH, parse_dates=["entry_time", "logged_at"])
    return pd.DataFrame(columns=[
        "logged_at", "symbol", "strategy", "direction", "entry_time",
        "entry_price", "sl", "tp", "lot_size", "risk_pct_used", "status"
    ])


def scan_for_new_signals(df, symbol, account_balance):
    now = df.index[-1]
    cutoff = now - timedelta(hours=FRESHNESS_WINDOW_HOURS)

    all_signals = []

    s1 = strat1_crt_tbs.generate_signals(df)
    for s in s1:
        s["strategy"] = "CRT_TBS"
    all_signals += s1

    s2_raw = strat2_trend_ob_v2.generate_signals(df)
    s2 = strat2_trend_ob_v2._map_entries_to_m15(s2_raw, df.index)
    for s in s2:
        s["strategy"] = "Trend_OB"
    all_signals += s2

    s3 = strat3_orb.generate_signals(df)
    for s in s3:
        s["strategy"] = "ORB"
    all_signals += s3

    if strat7_powell_capped is not None:
        s7 = strat7_powell_capped.generate_signals(df, symbol)
        for s in s7:
            s["strategy"] = "Powell_KeyOpen"
        all_signals += s7
    else:
        print(f"{symbol}: Powell_KeyOpen sprunget over -- strat7_powell_capped kunne ikke "
              f"importeres ({POWELL_IMPORT_ERROR}).")

    fresh = [s for s in all_signals if s["entry_time"] >= cutoff]

    log = _load_log()
    new_entries = []

    for sig in fresh:
        already_logged = (
            (log["symbol"] == symbol)
            & (log["strategy"] == sig["strategy"])
            & (log["entry_time"] == sig["entry_time"])
        ).any()
        if already_logged:
            continue

        sizing = calculate_lot_size(
            account_balance=account_balance,
            strategy=sig["strategy"],
            entry_price=sig["entry_price"],
            sl_price=sig["sl"],
            symbol=symbol,
        )

        entry = {
            "logged_at": datetime.utcnow(),
            "symbol": symbol,
            "strategy": sig["strategy"],
            "direction": sig["direction"],
            "entry_time": sig["entry_time"],
            "entry_price": sig["entry_price"],
            "sl": sig["sl"],
            "tp": sig["tp"],
            "lot_size": sizing.get("lot_size", 0),
            "risk_pct_used": sizing.get("risk_pct_used", 0),
            "status": "AFVENTER EKSEKVERING (demo)",
            "mt5_ticket": None,
        }
        new_entries.append(entry)
        print(f"NYT SIGNAL (klar til eksekvering paa demo): {symbol} {sig['strategy']} {sig['direction']} "
              f"@ {sig['entry_price']:.2f} | SL {sig['sl']:.2f} | TP {sig['tp']:.2f} "
              f"| Lot: {sizing.get('lot_size', 0)}")

    if new_entries:
        updated = pd.concat([log, pd.DataFrame(new_entries)], ignore_index=True)
        updated.to_csv(LOG_PATH, index=False)
    else:
        print(f"{symbol}: ingen nye signaler siden sidste scan.")

    return new_entries


if __name__ == "__main__":
    print("Dette script skal koeres i Claude Code med MT5 MCP-data.")
    print("Se docstring oeverst i filen for hvordan candles hentes og konverteres.")