# City X Appointment Bot

A friend asked me to build a bot to monitor appointment slots for citizenship applications in her city. She became worried that the city name and direct links could make the bot easier to discover and increase competition for limited slots, so I anonymized it in a later commit to make it less obvious at first glance.

This project supports two ways to monitor appointments in City X:

- `bot.py`: a long-running Telegram bot with commands and periodic checks
- `run_check_once.py`: a one-shot checker designed to be launched by `cron`

Both modes use the same scraper in `scraper.py`.


Important:

- Telegram commands work only while `bot.py` is running
- For automatic checks, choose one mode: either `bot.py` or `cron` + `run_check_once.py`
- Running both automatic modes at the same time will cause duplicate checks and possibly duplicate notifications
- Only new slots trigger notifications (no repeat notifications for the same slots)
- In `bot.py` mode, checks are performed at random intervals between `MIN_CHECK_INTERVAL` and `MAX_CHECK_INTERVAL` (in seconds)

## Features

- Automated appointment checks with Playwright
- Telegram notifications
- Works with a personal chat ID or a group chat ID
- Cloudflare block detection in one-shot mode
- Two supported run modes for different deployment styles

## Prerequisites

- Python 3.8+
- A Telegram bot token from @BotFather
- A Telegram chat ID or group chat ID

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/marusyalandau/termin_bot.git
cd termin_bot
- Persistent browser profile (cookies/history reused for stealth)
- User-agent rotation per profile
- Proxy support via `PROXY_URL` in `.env`
- Only new slots trigger notifications
- Random check intervals (not fixed)
```

### 2. Install dependencies

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

### 3. Create `.env`

```bash
cp .env.example .env
```

Example:

```dotenv

TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
BOT_LABEL=City X Appointment Bot
APPOINTMENT_LINK=https://example.com/appointments
BOOKING_URL=https://your-booking-provider.example/calendar
SEND_NO_APPOINTMENT_MESSAGE=false
MIN_CHECK_INTERVAL=1560
MAX_CHECK_INTERVAL=2040
```

Meaning:

- `TELEGRAM_BOT_TOKEN`: required in both modes
- `TELEGRAM_CHAT_ID`: required in both modes
- `BOT_LABEL`: display name used in Telegram messages
- `APPOINTMENT_LINK`: link shown in notifications
- `BOOKING_URL`: actual page that Playwright opens for checks
- `SEND_NO_APPOINTMENT_MESSAGE`: used only by `run_check_once.py`; set it to `false` to notify only when appointments are available
- `CHECK_INTERVAL`: used only by `bot.py`

### 4. Get Telegram credentials
CHECK_INTERVAL=300

- Create the bot via @BotFather with `/newbot`

**Chat ID**

- Send a message to the bot or to the target group
- Open `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
- Find `chat.id` in the response
- Group chat IDs are usually negative, for example `-1001234567890`

## Mode 1: `bot.py`

Run:

```bash
source venv/bin/activate
python bot.py
```

Use this mode if you want interactive Telegram commands.


Available commands:

- `/start`
- `/status`


This mode uses `MIN_CHECK_INTERVAL` and `MAX_CHECK_INTERVAL` from `.env` to pick a random interval for each check.

If `bot.py` is not running, `/start` and `/status` will not work.

Background notifications in this mode are sent only when new appointments are available (no repeat notifications for the same slots).

## Mode 2: `run_check_once.py` with cron

Run once manually:

```bash
source venv/bin/activate
```

Use this mode if you want scheduled checks without running a long-lived polling bot.

Example `crontab` entry for every 5 minutes:

```bash
*/5 * * * * cd /home/ubuntu/termin_bot && /home/ubuntu/termin_bot/venv/bin/python /home/ubuntu/termin_bot/run_check_once.py >> /home/ubuntu/termin_bot/cron.log 2>&1
```

Notes:

- `run_check_once.py` sends one message and exits
- It does not reply to `/start` or other Telegram commands
- The schedule is controlled only by `cron`
- Do not use this together with the periodic checking inside `bot.py` unless you explicitly want duplicate checks

`SEND_NO_APPOINTMENT_MESSAGE` behavior:

- `true`: send a message for both states
- `false`: send a message only when appointments are available

## How It Works

1. Open the booking system in a headless browser
2. Click through the required service selection
3. Detect whether "Keine freien Termine gefunden" is present
4. Send the result to Telegram

## Configuration


### `bot.py` frequency

Set `MIN_CHECK_INTERVAL` and `MAX_CHECK_INTERVAL` in `.env` (in seconds):

- `MIN_CHECK_INTERVAL=1560` (26 minutes)
- `MAX_CHECK_INTERVAL=2040` (34 minutes)

The bot will pick a random interval in this range for each check.

### `run_check_once.py` frequency

Set the schedule in `crontab`, for example:

- `*/5 * * * *` = every 5 minutes
- `*/10 * * * *` = every 10 minutes
- `*/20 * * * *` = every 20 minutes

 Set `MIN_CHECK_INTERVAL` and `MAX_CHECK_INTERVAL` in `.env` (in seconds):

 - `MIN_CHECK_INTERVAL=1560` (26 minutes)
 - `MAX_CHECK_INTERVAL=2040` (34 minutes)
git pull
 The bot will pick a random interval in this range for each check.
```

Then:

- if you use `bot.py`, restart the running process or systemd service
- if you use `cron` with `run_check_once.py`, `git pull` is enough unless you changed the cron command itself

## Troubleshooting

### `bot.py` does not answer commands

- Make sure `python bot.py` is actually running
- Verify the token with `curl https://api.telegram.org/bot<TOKEN>/getMe`
- Check that `.env` contains the correct token

### `run_check_once.py` sends messages only to one person

- That is expected
- It sends only to `TELEGRAM_CHAT_ID`
- Use a group chat ID if multiple people should receive the same message

### Cron job not sending messages

- Check `crontab -l`
- Check the log file with `tail -n 50 /home/ubuntu/termin_bot/cron.log`
- Run `python run_check_once.py` manually once

### Playwright issues

- Reinstall browsers with `playwright install chromium`

### Website flow changed

- Update selectors or text checks in `scraper.py`

## Project Structure

```text
termin_bot/
├── bot.py
├── run_check_once.py
├── scraper.py
├── .env.example
├── QUICKSTART.md
├── TESTING.md
└── BOT_INSTRUCTIONS.md
```
