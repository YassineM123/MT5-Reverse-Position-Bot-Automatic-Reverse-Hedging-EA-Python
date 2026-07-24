# 🤖 MT5 Reverse-Position Bot

A fully automated **Python bot** that instantly creates reverse (hedge) positions in MetaTrader5 whenever a new trade opens. Designed for risk hedging, strategy testing, and automated counter-trading across all market types.

## 🎯 Purpose

- **Risk Management** - Hedge original positions with automatic reverse trades
- **Strategy Testing** - Test counter-strategies simultaneously with live trades
- **Automated Hedging** - No manual intervention needed
- **Loss Prevention** - Quick position mirroring for protection

## ✨ Key Features

### ✓ **Automatic Reverse Position**
- Detects every new trade instantly
- Opens exactly **one reverse position** per original trade
- No spamming or duplicate reverses (tracked by ticket)

### ✓ **Mirrored SL/TP Logic**
- Reverse Stop Loss = Original Take Profit
- Reverse Take Profit = Original Stop Loss
- Auto-synchronizes when original SL/TP changes
- Real-time SL/TP updates without manual adjustment

### ✓ **Volume Multiplier**
- Reverse volume = **2 × original volume**
- Customizable multiplier (change `REVERSE_VOLUME_MULTIPLIER`)
- Works with partial position modifications

### ✓ **Auto-Close Reverse**
- When original trade closes → reverse position closes **instantly**
- Maintains 1:1 position lifecycle
- Prevents orphaned reverse positions

### ✓ **Cross-Symbol Compatible**
- Works on **all markets** supported by MetaTrader5:
  - 💱 Forex (EUR/USD, GBP/USD, etc.)
  - 🏆 Indices (EUROSTOXX, DAX, etc.)
  - 💰 Precious Metals (Gold, Silver)
  - 🪙 Cryptocurrencies (BTC/USD, ETH/USD, etc.)
  - 📈 Stocks & CFDs
  - 🌾 Commodities (Oil, Natural Gas, etc.)

### ✓ **Persistent State Recovery**
- Survives bot restarts
- Recovers position mappings from trade comments
- Tracks original→reverse relationships

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- MetaTrader5 installed on Windows
- MT5 account with trading permissions
- Admin rights to run Python scripts

### Installation

```bash
# Clone the repository
git clone https://github.com/YassineM123/MT5-Reverse-Position-Bot-Automatic-Reverse-Hedging-EA-Python.git
cd MT5-Reverse-Position-Bot-Automatic-Reverse-Hedging-EA-Python

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Edit the constants at the top of `mt5_reverse_bot.py`:

```python
# User Configuration (optional - leave as None to use terminal login)
LOGIN = None           # Leave None or set to your MT5 account number
PASSWORD = None        # Leave None or set your password
SERVER = None          # Leave None or set to broker server name

# Bot Configuration
MAGIC = 987654321      # Magic number for reverse positions
DEVIATION = 20         # Max allowed slippage in points
POLL_SECONDS = 1.0     # How often to check for new positions (seconds)
COMMENT_PREFIX = "REV of "  # Comment prefix for reverse position
```

### Run the Bot

```bash
# Start the bot
python mt5_reverse_bot.py

# Expected output:
# [*] Reverse bot started.
# [OK] Sent reverse EURUSD BUY vol=0.2 @ 1.0856 (order=123456789, deal=987654321)
# [OK] Linked original#456789 -> reverse#123456
```

The bot runs infinitely. Press `Ctrl+C` to stop.

## 📊 How It Works

### Position Detection
```
┌─────────────────────────────────────┐
│  MT5 Terminal - Open Positions      │
├─────────────────────────────────────┤
│  Original: BUY EURUSD 0.1           │ ← Detected
│  SL: 1.0500, TP: 1.0900             │
└─────────────────────────────────────┘
```

### Reverse Creation
```
┌──────────────────────────────────────────┐
│  Bot Action                              │
├──────────────────────────────────────────┤
│  1. Detected original BUY                │
│  2. Calculate reverse: SELL              │
│  3. Volume: 0.1 × 2 = 0.2               │
│  4. Reverse SL = original TP = 1.0900   │
│  5. Reverse TP = original SL = 1.0500   │
│  6. Send SELL order with magic #987...  │
│  7. Link positions by comment           │
└──────────────────────────────────────────┘
```

### Synchronization
```
Original Position Changed:
  SL: 1.0500 → 1.0400
  TP: 1.0900 → 1.1000

Reverse Position Updated (Instantly):
  TP: 1.0500 → 1.0400  (now mirrors new SL)
  SL: 1.0900 → 1.1000  (now mirrors new TP)
```

### Close & Cleanup
```
Original Closes:
  ↓
Reverse Closes (Instantly)
  ↓
Position Mappings Cleared
```

## ⚙️ Configuration Options

### Basic Settings
| Setting | Default | Description |
|---------|---------|-------------|
| `LOGIN` | `None` | MT5 account number (None = use terminal login) |
| `PASSWORD` | `None` | Account password (None = use terminal) |
| `SERVER` | `None` | Broker server name (None = use terminal) |
| `MAGIC` | `987654321` | Magic number to identify reverse positions |
| `DEVIATION` | `20` | Max slippage in points |
| `POLL_SECONDS` | `1.0` | Check interval in seconds |
| `COMMENT_PREFIX` | `"REV of "` | Text prefix for position comments |

### Advanced Customization

**Change reverse volume multiplier:**
```python
reverse_vol = round(op.volume * 3.0, 2)  # 3x instead of 2x
```

**Change polling speed (faster detection):**
```python
POLL_SECONDS = 0.5  # Check every 500ms (more CPU usage)
```

**Change magic number (to avoid conflicts):**
```python
MAGIC = 111222333  # Unique identifier
```

## 📋 State Management

### Position Mapping
The bot maintains `original_ticket → reverse_ticket` mappings:

```python
# Stored in memory during runtime
orig_to_rev: Dict[int, int] = {
    456789: 123456,    # Original ticket 456789 → Reverse ticket 123456
    789012: 654321,    # Original ticket 789012 → Reverse ticket 654321
}

# Survives restarts via trade comments
# Comment format: "REV of 456789" → extracted on next run
```

### Recovery After Restart
1. Bot reads all current positions
2. Scans comments for format `"REV of <ticket>"`
3. Rebuilds original→reverse mappings
4. Resumes monitoring and syncing

## 🔄 Workflow Example

### Step 1: You Open a Buy Position
```
Account: 12345678
Symbol: EURUSD
Type: BUY
Volume: 0.1 lot
Entry: 1.0856
SL: 1.0500
TP: 1.0900
Ticket: 456789
```

### Step 2: Bot Detects & Creates Reverse
```
[OK] Sent reverse EURUSD SELL vol=0.2 @ 1.0856
[OK] Linked original#456789 -> reverse#123456

Position Created:
Symbol: EURUSD
Type: SELL
Volume: 0.2 lot
Entry: 1.0856
SL: 1.0900  ← Mirrored from TP
TP: 1.0500  ← Mirrored from SL
Ticket: 123456
Magic: 987654321
Comment: "REV of 456789"
```

### Step 3: You Modify Original (e.g., Move SL)
```
Original SL: 1.0500 → 1.0400
Original TP: 1.0900 → 1.0900
```

### Step 4: Bot Syncs Reverse
```
[OK] Modifying reverse SL/TP
Reverse TP: 1.0500 → 1.0400  ← Updated to match new SL
Reverse SL: 1.0900 → 1.0900  ← No change (already matches)
```

### Step 5: You Close Original
```
Original Position: CLOSED
```

### Step 6: Bot Auto-Closes Reverse
```
[OK] Closed reverse pos#123456
Reverse Position: CLOSED
Mapping Cleared
```

## 🛡️ Error Handling

### Automatic Retries
```python
# Failed order? Bot retries automatically
if res.retcode != mt5.TRADE_RETCODE_DONE:
    print(f"[WARN] SL/TP modify failed: {res.retcode}")
    # Continues trying on next poll cycle
```

### Missing Symbols
```python
# Symbol not available? Tries to select it
if not ensure_symbol(symbol):
    print(f"[WARN] Can't select symbol {symbol}")
    # Skips and tries again next cycle
```

## 📊 Logging & Monitoring

### Sample Output
```
[*] Reverse bot started.
[OK] Sent reverse EURUSD BUY vol=0.2 @ 1.0856 (order=123456789, deal=987654321)
[OK] Linked original#456789 -> reverse#123456
[OK] Modifying reverse SL/TP
[WARN] SL/TP modify failed for pos#123456: retcode=10005
[OK] Closed reverse pos#123456
[OK] Linked original#789012 -> reverse#654321
```

### Check Positions in MT5
```
Terminal → View → Positions
Magic: 987654321  ← Filter by magic to see bot's reverses
```

## ⚠️ Important Notes

### Broker Requirements
- ✅ Netting margin account required
- ✅ Must allow reverse positions
- ✅ Account must have sufficient margin
- ❌ Hedging margin accounts NOT supported (different PT model)

### Risks
- 💰 **Margin Usage**: Reverse positions consume margin (2x volume = more margin needed)
- 📊 **Slippage**: Real-world entry may differ from original
- ⚡ **Speed**: Network delays may affect sync precision
- 🔧 **Customization**: Unsuitable brokers may have different order validation

### Best Practices
1. **Test First** - Test on demo account before live trading
2. **Monitor Margin** - Ensure sufficient balance for reverses
3. **Adjust Deviation** - Increase if orders frequently fail
4. **Log Review** - Check console output regularly
5. **Broker Check** - Verify your broker allows reverse positions

## 🐛 Troubleshooting

### "MT5 initialize() failed"
```bash
# Solution: Ensure MT5 is running
# 1. Open MetaTrader5 application
# 2. Log in to your account
# 3. Try running bot again
```

### "order_send failed: retcode=10014"
```
Error: Invalid volume
Solution: 
- Check minimum lot size for symbol
- Verify account has sufficient margin
- Increase DEVIATION for slippage
```

### "order_send failed: retcode=10015"
```
Error: Invalid price
Solution:
- Ensure symbol has current tick
- Verify price within bid-ask spread
```

### "Can't select symbol"
```
Error: Symbol not available
Solution:
- Add symbol to Watchlist in MT5
- Use exact symbol name (e.g., "EURUSD", not "EUR/USD")
```

### Reverse positions not created
```
Checklist:
✓ MT5 terminal is open and logged in
✓ You've opened at least one original position
✓ Bot is running (no errors in console)
✓ Account has sufficient margin
✓ Symbol is in your Watchlist
```

## 📦 Project Structure

```
.
├── mt5_reverse_bot.py       # Main bot script (300+ lines)
│   ├── User Configuration
│   ├── Helper Functions
│   ├── Order Management
│   └── Main Loop
├── requirements.txt         # Dependencies
└── README.md               # This file
```

## 🔧 Dependencies

```txt
MetaTrader5==5.0.39    # MT5 Python API
```

Install with:
```bash
pip install -r requirements.txt
```

## 📈 Performance Metrics

- **Latency**: ~100-500ms per cycle (depends on POLL_SECONDS)
- **CPU Usage**: Minimal (<1% typically)
- **Memory**: ~50-100MB
- **Network**: Minimal (only MT5 terminal communication)

## 📚 Resources

- **MT5 Documentation**: https://www.metatrader5.com/en/docs/python
- **MT5 Python API**: https://www.mql5.com/en/docs/integration
- **Reverse Trading**: https://en.wikipedia.org/wiki/Pair_trading
- **Hedging Guide**: https://www.investopedia.com/terms/h/hedge.asp

## 🤝 Contributing

Found a bug or want to improve? Contributions welcome!

```bash
git clone https://github.com/YassineM123/MT5-Reverse-Position-Bot.git
git checkout -b feature/improvement
git commit -am 'Your improvement'
git push origin feature/improvement
```

## 📄 License

MIT License - See LICENSE file for details.

## ⚠️ Disclaimer

This bot is provided **as-is** for educational and automated trading purposes. Users are responsible for:
- Trading strategy validation
- Risk management and position sizing
- Broker compliance and account rules
- Monitoring and system maintenance

**Trade at your own risk.** Past performance ≠ future results.

## 📧 Support

- 🐛 Issues: Open a GitHub issue
- 💬 Questions: Start a discussion
- 📖 Docs: Read this README thoroughly
- 🆘 Emergency: Stop the bot immediately (`Ctrl+C`)

---

**Made with ❤️ for traders by [YassineM123](https://github.com/YassineM123)**

**Happy hedging! 📈**
