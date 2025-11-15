#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MT5 Reverse-Position Bot (One reverse per trade)
- Reverse volume = 2x original
- Opens instantly when an original position is detected
- Reverse TP = original SL, Reverse SL = original TP (kept in sync on modifications)
- Closes the reverse when the original closes
- No spamming: exactly one reverse per original position (tracked by ticket)
- Works for all symbols; compatible with recent MT5 builds
"""
import time
import sys
import re
from typing import Dict, Optional

import MetaTrader5 as mt5

# ========== USER CONFIG ==========
LOGIN: Optional[int] = None           # e.g. 12345678 (leave None to use current terminal login)
PASSWORD: Optional[str] = None        # optional if terminal is already authorized
SERVER: Optional[str] = None          # e.g. "YourBroker-Server"

MAGIC = 987654321                     # Magic to mark the reverse positions
DEVIATION = 20                        # Max slippage, points
POLL_SECONDS = 1.0                    # Polling interval (seconds)
COMMENT_PREFIX = "REV of "            # We embed original ticket in comment to recover state

# ========== HELPERS ==========

def normalize_price(symbol: str, price: float) -> float:
    info = mt5.symbol_info(symbol)
    if not info:
        return price
    digits = info.digits
    # Round to the allowed number of digits
    return round(price, digits)

def price_from_tick(symbol: str, position_type: int):
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        return None
    # For market orders: buy @ ask, sell @ bid
    if position_type == mt5.POSITION_TYPE_BUY:
        return tick.ask
    else:
        return tick.bid

def ensure_symbol(symbol: str) -> bool:
    info = mt5.symbol_info(symbol)
    if info is None:
        return False
    if not info.visible:
        return mt5.symbol_select(symbol, True)
    return True

def get_positions_map() -> Dict[int, mt5.TradePosition]:
    """Return all current positions keyed by ticket."""
    positions = mt5.positions_get()
    result = {}
    if positions:
        for p in positions:
            result[p.ticket] = p
    return result

def is_our_reverse(pos: mt5.TradePosition) -> bool:
    if pos.magic != MAGIC:
        return False
    if pos.comment and pos.comment.startswith(COMMENT_PREFIX):
        return True
    return False

def parse_original_ticket_from_comment(comment: str) -> Optional[int]:
    # Expected comment format: "REV of <ticket>"
    m = re.match(rf"^{re.escape(COMMENT_PREFIX)}(\d+)$", comment or "")
    if not m:
        return None
    try:
        return int(m.group(1))
    except Exception:
        return None

def reverse_type(original_type: int) -> int:
    return mt5.ORDER_TYPE_SELL if original_type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY

def desired_sltp_for_reverse(orig: mt5.TradePosition) -> (Optional[float], Optional[float]):
    """
    For the REVERSE position:
    - SL = original TP (if set)
    - TP = original SL (if set)
    """
    rev_sl = orig.tp if orig.tp and orig.tp > 0 else None
    rev_tp = orig.sl if orig.sl and orig.sl > 0 else None
    return rev_sl, rev_tp

def send_market_order(symbol: str, order_type: int, volume: float, sl: Optional[float], tp: Optional[float], comment: str, magic: int) -> Optional[int]:
    if not ensure_symbol(symbol):
        print(f"[ERROR] Symbol not available: {symbol}", flush=True)
        return None

    price = price_from_tick(symbol, mt5.POSITION_TYPE_BUY if order_type == mt5.ORDER_TYPE_BUY else mt5.POSITION_TYPE_SELL)
    if price is None:
        print(f"[ERROR] No tick for {symbol}", flush=True)
        return None

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "type": order_type,
        "volume": volume,
        "price": price,
        "deviation": DEVIATION,
        "magic": magic,
        "comment": comment,
        "type_filling": mt5.ORDER_FILLING_FOK,
        "type_time": mt5.ORDER_TIME_GTC,
    }
    if sl is not None:
        request["sl"] = normalize_price(symbol, sl)
    if tp is not None:
        request["tp"] = normalize_price(symbol, tp)

    result = mt5.order_send(request)
    if result is None:
        print(f"[ERROR] order_send returned None for {symbol}", flush=True)
        return None
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"[ERROR] order_send failed: retcode={result.retcode}, comment={result.comment}", flush=True)
        return None

    # result.order is the order ticket; result.deal is the deal ticket; position ticket assigned after execution
    print(f"[OK] Sent reverse {symbol} {('BUY' if order_type==mt5.ORDER_TYPE_BUY else 'SELL')} vol={volume} @ {price} (order={result.order}, deal={result.deal})", flush=True)
    # We will find the position by scanning current positions (since Python API doesn't return position ticket directly)
    return result.order

def modify_position_sltp(position_ticket: int, symbol: str, sl: Optional[float], tp: Optional[float]) -> bool:
    req = {
        "action": mt5.TRADE_ACTION_SLTP,
        "position": position_ticket,
        "symbol": symbol,
        "sl": normalize_price(symbol, sl) if sl is not None else 0.0,
        "tp": normalize_price(symbol, tp) if tp is not None else 0.0,
        "magic": MAGIC,
        "comment": "sync sltp",
    }
    res = mt5.order_send(req)
    if res is None or res.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"[WARN] SL/TP modify failed for pos#{position_ticket}: {None if res is None else res.retcode}", flush=True)
        return False
    return True

def close_position(position_ticket: int, symbol: str, volume: float, position_type: int) -> bool:
    # To close a position, send opposite side market deal specifying the position id
    opposite = mt5.ORDER_TYPE_SELL if position_type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY
    price = price_from_tick(symbol, position_type)  # price argument is required; MT5 ignores it for netting close
    req = {
        "action": mt5.TRADE_ACTION_DEAL,
        "position": position_ticket,
        "symbol": symbol,
        "volume": volume,
        "type": opposite,
        "price": price,
        "deviation": DEVIATION,
        "magic": MAGIC,
        "comment": "close reverse (orig closed)",
    }
    res = mt5.order_send(req)
    if res is None or res.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"[WARN] Close failed pos#{position_ticket}: {None if res is None else res.retcode}", flush=True)
        return False
    print(f"[OK] Closed reverse pos#{position_ticket}", flush=True)
    return True

# ========== MAIN LOOP ==========

def main():
    if not mt5.initialize():
        print(f"[FATAL] MT5 initialize() failed: {mt5.last_error()}", file=sys.stderr)
        sys.exit(1)

    try:
        if LOGIN is not None:
            if not mt5.login(LOGIN, PASSWORD or "", SERVER or ""):
                print(f"[FATAL] login() failed: {mt5.last_error()}", file=sys.stderr)
                sys.exit(1)

        print("[*] Reverse bot started.", flush=True)

        # Map original_ticket -> reverse_ticket (position ticket). We rebuild it at each poll.
        orig_to_rev: Dict[int, int] = {}

        # To enforce "one reverse per trade only", we keep a set for originals we've already reversed,
        # even if the reverse later closes. This avoids re-opening repeatedly.
        reversed_once: set[int] = set()

        while True:
            all_positions = mt5.positions_get() or []

            # Build quick lookup maps
            originals = []
            reverses = []
            for p in all_positions:
                if is_our_reverse(p):
                    reverses.append(p)
                else:
                    originals.append(p)

            # Rebuild mapping from comment (survives restarts)
            comment_index: Dict[int, mt5.TradePosition] = {}
            for rp in reverses:
                orig_ticket = parse_original_ticket_from_comment(rp.comment)
                if orig_ticket is not None:
                    comment_index[orig_ticket] = rp
                    orig_to_rev[orig_ticket] = rp.ticket
                    reversed_once.add(orig_ticket)

            # 1) Ensure a reverse exists for every current original (unless already done once)
            for op in originals:
                if op.ticket in reversed_once and op.ticket not in orig_to_rev:
                    # Already reversed once earlier; do not spam a new one
                    continue

                if op.ticket not in orig_to_rev:
                    symbol = op.symbol
                    if not ensure_symbol(symbol):
                        print(f"[WARN] Can't select symbol {symbol}", flush=True)
                        continue

                    reverse_vol = round(op.volume * 2.0, 2)  # typical brokers accept 2 decimals; adjust if needed per symbol
                    rtype = reverse_type(op.type)
                    rsl, rtp = desired_sltp_for_reverse(op)
                    comment = f"{COMMENT_PREFIX}{op.ticket}"

                    order_ticket = send_market_order(symbol, rtype, reverse_vol, rsl, rtp, comment, MAGIC)
                    if order_ticket is None:
                        continue

                    # After sending, find the new reverse position (by comment)
                    time.sleep(0.2)  # tiny wait for server to register position
                    new_positions = mt5.positions_get(symbol=symbol) or []
                    for p in new_positions:
                        if is_our_reverse(p) and parse_original_ticket_from_comment(p.comment) == op.ticket:
                            orig_to_rev[op.ticket] = p.ticket
                            reversed_once.add(op.ticket)
                            print(f"[OK] Linked original#{op.ticket} -> reverse#{p.ticket}", flush=True)
                            break

            # 2) Keep SL/TP in sync (original SL -> reverse TP, original TP -> reverse SL)
            #    And close reverse if original closed
            #    (We also handle updates by comparing desired vs current)
            # First, build a live snapshot for quick access by ticket
            pos_by_ticket = {p.ticket: p for p in mt5.positions_get() or []}

            for orig_ticket, rev_ticket in list(orig_to_rev.items()):
                orig_pos = pos_by_ticket.get(orig_ticket)
                rev_pos = pos_by_ticket.get(rev_ticket)

                if orig_pos is None:
                    # Original closed -> close our reverse if still open
                    if rev_pos is not None:
                        close_position(rev_pos.ticket, rev_pos.symbol, rev_pos.volume, rev_pos.type)
                    # Remove mapping
                    orig_to_rev.pop(orig_ticket, None)
                    continue

                if rev_pos is None:
                    # Our reverse no longer exists (closed by SL/TP/manual).
                    # Respect "one reverse per trade only": do NOT reopen.
                    orig_to_rev.pop(orig_ticket, None)
                    continue

                # Sync SL/TP
                desired_sl, desired_tp = desired_sltp_for_reverse(orig_pos)

                # Current reverse sl/tp are 0.0 if unset
                cur_sl = rev_pos.sl if rev_pos.sl and rev_pos.sl > 0 else None
                cur_tp = rev_pos.tp if rev_pos.tp and rev_pos.tp > 0 else None

                # Only send modify if something changed (with normalization)
                need_modify = False
                if desired_sl is None and cur_sl is not None:
                    need_modify = True
                elif desired_sl is not None and (cur_sl is None or normalize_price(rev_pos.symbol, desired_sl) != normalize_price(rev_pos.symbol, cur_sl)):
                    need_modify = True

                if desired_tp is None and cur_tp is not None:
                    need_modify = True
                elif desired_tp is not None and (cur_tp is None or normalize_price(rev_pos.symbol, desired_tp) != normalize_price(rev_pos.symbol, cur_tp)):
                    need_modify = True

                if need_modify:
                    modify_position_sltp(rev_pos.ticket, rev_pos.symbol, desired_sl, desired_tp)

            time.sleep(POLL_SECONDS)

    finally:
        mt5.shutdown()

if __name__ == "__main__":
    main()
