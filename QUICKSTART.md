# Quick Start Guide

## What's Been Created

✅ **bot.py** - Main Telegram bot that:
  - Receives commands (/check, /status, /start)
  - Periodically checks for appointments (every 1 hour by default)
  - Sends Telegram notifications when appointments are found

✅ **scraper.py** - Website scraper that:
  - Uses Playwright headless browser to handle JavaScript
  - Automatically clicks "Staatsangehörigkeitsangelegenheiten"
  - Automatically clicks "02. Antrag Einbürgerung"
  - Extracts available appointment slots
  - Handles errors gracefully

✅ **requirements.txt** - All Python dependencies

✅ **test_scraper.py** - Standalone test script to verify the scraper works

✅ **.env.example** - Configuration template

✅ **.gitignore** - Git ignore patterns

✅ **README.md** - Comprehensive documentation

✅ **setup.sh** - Automated setup script

✅ **halle-bot.service** - Systemd service file for 24/7 running

---

## Quick Setup (5 minutes)

### 1. Clone and setup
```bash
git clone https://github.com/marusyalandau/halle_bot.git
cd halle_bot
chmod +x setup.sh
./setup.sh
```

### 2. Get Telegram Credentials
- **Bot Token**: Contact @BotFather on Telegram → /newbot
- **Chat ID**: Send a message to your bot, then visit:
  ```
  https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates
  ```
  Look for "chat":{"id": YOUR_CHAT_ID}

### 3. Edit .env
```bash
nano .env
```
Add:
```
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHAT_ID=your_chat_id
```

### 4. Test it (optional)
```bash
source venv/bin/activate
python test_scraper.py
```

### 5. Start the bot (Choose one):

**Option A: Run directly**
```bash
source venv/bin/activate
python bot.py
```

**Option B: Run as system service (recommended for 24/7)**
```bash
sudo cp halle-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable halle-bot
sudo systemctl start halle-bot
sudo systemctl status halle-bot
```

**Option C: GitHub Actions schedule (no always-on machine)**
1. Push this repo to GitHub
2. Add secrets in repo settings:
  - `TELEGRAM_BOT_TOKEN`
  - `TELEGRAM_CHAT_ID`
3. Enable and run workflow [appointment-check.yml](.github/workflows/appointment-check.yml)

---

## Bot Commands

Once running, message your bot on Telegram:

- `/start` - Show help
- `/check` - Check appointments now
- `/status` - Show bot status
- `/stop` - Stop the bot

---

## How the Bot Works

1. **Opens headless browser** → Loads https://halle.de/...
2. **Clicks buttons automatically** → "Staatsangehörigkeitsangelegenheiten" then "02. Antrag Einbürgerung"
3. **Extracts appointment data** → Looks for available time slots
4. **Sends Telegram notification** → Alerts you when appointments found
5. **Repeats** → Checks every 3600 seconds (1 hour) by default

---

## Customization

### Change check frequency
Edit `.env`:
```
CHECK_INTERVAL=1800  # Check every 30 minutes instead of 1 hour
```

### Run as system service (Linux)
```bash
sudo cp halle-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable halle-bot
sudo systemctl start halle-bot

# View logs
sudo journalctl -u halle-bot -f
```

---

## Troubleshooting

**Bot not responding?**
- Check `.env` exists with correct tokens
- Test token: `curl https://api.telegram.org/bot<TOKEN>/getMe`

**Playwright errors?**
- Reinstall: `playwright install chromium`

**Not finding appointments?**
- Run: `python test_scraper.py` to debug
- Check if website layout changed

---

## Next Steps

1. Configure `.env` with your Telegram credentials
2. Test with `python test_scraper.py`
3. Start the bot with `python bot.py` or use systemd
4. Send `/check` command to your bot on Telegram
5. Wait for appointments! The bot checks automatically

## Viewing Logs (if using systemd)
```bash
# Real-time logs
sudo journalctl -u halle-bot -f

# Last 50 lines
sudo journalctl -u halle-bot -n 50
```

Good luck getting your appointment! 🍀
