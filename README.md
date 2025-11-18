# MT5 Reverse-Position Bot

A Python bot that automatically opens and manages reverse positions in MetaTrader5.
See full README.

🚀 Features
✓ Automatic reverse per original trade

Detects every new trade

Opens exactly one reverse position

No spamming (tracked by ticket)

✓ Reversed SL/TP logic

Reverse order always mirrors the original:

Reverse SL = original TP

Reverse TP = original SL

Bot automatically synchronizes when SL/TP changes

✓ Volume Multiplier

Reverse volume = 2 × original volume

✓ Auto-Close Reverse

When original trade closes → reverse position closes instantly.

✓ Cross-symbol compatible

Works on all markets supported by MT5:
Forex, Gold, Crypto CFDs, Indices, Stocks.
