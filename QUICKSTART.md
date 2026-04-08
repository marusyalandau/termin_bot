# Quick Start Guide

## What's Been Created

✅ **bot.py** - Long-running Telegram bot that:
  - Receives commands (`/check`, `/status`, `/start`)
  - Periodically checks for appointments
  - Uses `CHECK_INTERVAL` from `.env`

✅ **scraper.py** - Website scraper that:
  - Uses Playwright headless browser to handle JavaScript
  - Automatically clicks "Staatsangehoerigkeitsangelegenheiten"
  - Automatically clicks "02. Antrag Einbuergerung"
  - Extracts available appointment slots
  - Handles errors gracefully

✅ **run_check_once.py** - One-shot runner that:
  - Checks appointments one time
  - Sends one Telegram message
  - Is designed for `cron`

✅ **requirements.txt** - All Python dependencies

✅ **test_scraper.py** - Standalone test script to verify the scraper works

✅ **.env.example** - Configuration template

✅ **.gitignore** - Git ignore patterns

✅ **README.md** - Comprehensive documentation

✅ **setup.sh** - Automated setup script

✅ **termin-bot.service** - Systemd service file for 24/7 running

---

## Quick Setup (5 minutes)

### 1. Clone and setup
```bash
git clone https://github.com/marusyalandau/termin_bot.git
cd termin_bot
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
BOT_LABEL=City X Appointment Bot
APPOINTMENT_LINK=https://example.com/appointments
BOOKING_URL=https://your-booking-provider.example/calendar
SEND_NO_APPOINTMENT_MESSAGE=false
```

### 4. Test it (optional)
```bash
source venv/bin/activate
python test_scraper.py
```

### 5. Start it (choose one mode)

Important:

- `bot.py` and `run_check_once.py` are two different operating modes for the same bot
- Telegram commands work only when `bot.py` is running
- For automatic checks, run only one mode at a time to avoid duplicate notifications

**Option A: Long-running bot with commands**
```bash
source venv/bin/activate
python bot.py
```

In this mode, automatic notifications are sent only when appointments are available. Manual `/check` always replies.

**Option B: Run as system service (recommended for 24/7)**
```bash
sudo cp termin-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable termin-bot
sudo systemctl start termin-bot
sudo systemctl status termin-bot
```

**Option C: Cron + one-shot runner**
```bash
crontab -e
```

Add this line for every 5 minutes:

```bash
*/5 * * * * cd /home/ubuntu/termin_bot && /home/ubuntu/termin_bot/venv/bin/python /home/ubuntu/termin_bot/run_check_once.py >> /home/ubuntu/termin_bot/cron.log 2>&1
```

Then check:

```bash
crontab -l
tail -n 50 /home/ubuntu/termin_bot/cron.log
```

---

## Bot Commands

These commands work only in `bot.py` mode:

- `/start` - Show help
- `/check` - Check appointments now
- `/status` - Show bot status

---

## How the Bot Works

1. **Opens headless browser** → Loads `BOOKING_URL` from `.env`
2. **Clicks buttons automatically** → Goes through the configured booking flow
3. **Extracts appointment data** → Looks for available time slots
4. **Sends Telegram notification** → Alerts you when appointments found
5. **Repeats** → In `bot.py` mode, checks every `CHECK_INTERVAL` seconds

In `run_check_once.py` mode, the schedule comes from `cron` instead.

Do not run both automatic modes at the same time unless you want duplicate checks.

---

## Customization

### Change check frequency
Edit `.env`:
```
CHECK_INTERVAL=1800  # Check every 30 minutes instead of 1 hour
```

This affects `bot.py` only.

### Change cron frequency

Edit `crontab -e` and change the schedule expression, for example:

```bash
*/10 * * * * cd /home/ubuntu/termin_bot && /home/ubuntu/termin_bot/venv/bin/python /home/ubuntu/termin_bot/run_check_once.py >> /home/ubuntu/termin_bot/cron.log 2>&1
```

### Run as system service (Linux)
```bash
sudo cp termin-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable termin-bot
sudo systemctl start termin-bot

# View logs
sudo journalctl -u termin-bot -f
```

---

## Troubleshooting

**Bot not responding to `/start` or `/check`?**
- Check `.env` exists with correct tokens
- Make sure you started `python bot.py`
- Test token: `curl https://api.telegram.org/bot<TOKEN>/getMe`

**Playwright errors?**
- Reinstall: `playwright install chromium`

**Need to hide real target links in public repo?**
- Keep placeholders in docs/examples.
- Store real values only in your private `.env` on your machine/server.

**Cron mode sends messages only to one chat?**
- That is expected. `run_check_once.py` sends one message to the configured `TELEGRAM_CHAT_ID`.
- Use a group chat ID if multiple people should receive the same notification.

**Cron mode sends nothing when there are no appointments?**
- That is the default behavior when `SEND_NO_APPOINTMENT_MESSAGE=false`.
- Set it to `true` if you want a message for every run.

**Not finding appointments?**
- Run: `python test_scraper.py` to debug
- Check if website layout changed

---

## Next Steps

1. Configure `.env` with your Telegram credentials
2. Test with `python test_scraper.py`
3. Choose a run mode:
  - `python bot.py` or systemd for interactive bot commands
  - `cron` + `run_check_once.py` for one-shot scheduled messages
4. If using `bot.py`, send `/check` in Telegram
5. If using `cron`, wait for the next scheduled run or run `python run_check_once.py` manually

## Viewing Logs (if using systemd)
```bash
# Real-time logs
sudo journalctl -u termin-bot -f

# Last 50 lines
sudo journalctl -u termin-bot -n 50
```

Good luck getting your appointment.
