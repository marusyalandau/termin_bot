# 🤖 Halle Einbürgerungsbehörde Appointment Bot

A Telegram bot that automatically checks for available appointments for "Staatsangehörigkeitsangelegenheiten" (citizenship affairs) at the Halle administration website and notifies you when slots become available.

## Features

- ✅ Automated checking for available appointments
- 🔔 Telegram notifications when appointments are available
- ⏰ Configurable check interval
- 🌐 Handles JavaScript-rendered dynamic content
- 🛡️ Error handling and logging

## Problem Solved

The Halle website (https://halle.de/serviceportal/online-terminvergabe/online-terminvereinbarung-einbuergerungsbehoerde-standesamt) uses JavaScript to dynamically load appointment availability. Users must:

1. Click "Staatsangehörigkeitsangelegenheiten"
2. Click "02. Antrag Einbürgerung"
3. Navigate to the reservation page

All without the URL changing. This bot automates this process using **Playwright** (headless browser automation) and checks for available slots periodically.

## Prerequisites

- Python 3.8+
- A Telegram Bot Token (from @BotFather on Telegram)
- Your Telegram Chat ID

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/marusyalandau/halle_bot.git
cd halle_bot
```

### 2. Create your `.env` file

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env`:
```
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
CHECK_INTERVAL=3600
```

### Getting Telegram Credentials

**Bot Token:**
- Contact @BotFather on Telegram
- Create a new bot with `/newbot`
- Copy the token provided

**Chat ID:**
- Send a message to your bot
- Visit: `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
- Find your chat_id in the response

### 3. Install dependencies

```bash
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

### 4. Run the bot

```bash
python bot.py
```

## Run On GitHub Actions (No Always-On Server)

For your use case, this is often the easiest option: run a scheduled check and send one Telegram message per run.

This repository includes:
- one-shot runner: [run_check_once.py](run_check_once.py)
- workflow: [.github/workflows/appointment-check.yml](.github/workflows/appointment-check.yml)

### 1. Add repository secrets

In GitHub: Settings -> Secrets and variables -> Actions -> New repository secret

Create:
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

### 2. Enable the workflow

The workflow runs every 20 minutes and can also be started manually from the Actions tab.

### 3. Optional behavior

In the workflow file, set:
- `SEND_NO_APPOINTMENT_MESSAGE: "true"` to send messages for both states
- `SEND_NO_APPOINTMENT_MESSAGE: "false"` to only notify on available appointments/errors

### 4. Important GitHub Actions notes

- Scheduled workflows are not real-time; delays of a few minutes can happen.
- Minimum schedule granularity is 5 minutes.
- Public repos on standard hosted runners are free.
- Private repos on GitHub Free include limited monthly minutes (currently 2000 minutes).

## Usage

Once the bot is running, you can interact with it via Telegram:

- `/start` - Show welcome message and available commands
- `/check` - Check for appointments immediately
- `/status` - Show bot status and last check time
- `/stop` - Stop the bot

The bot will automatically check for appointments every `CHECK_INTERVAL` seconds (default: 20 minutes).

## How It Works

1. **Playwright Browser**: Opens a headless Chromium browser
2. **Navigation**: Automatically clicks through the required buttons:
   - "Staatsangehörigkeitsangelegenheiten"
   - "02. Antrag Einbürgerung"
3. **Scraping**: Looks for available appointment slots
4. **Notification**: Sends a Telegram message if appointments are found

## Configuration

Edit the `CHECK_INTERVAL` in `.env` to adjust how often the bot checks:

- `3600` = 1 hour (default)
- `1800` = 30 minutes
- `600` = 10 minutes
- `300` = 5 minutes

⚠️ **Note**: Don't set it too low to avoid overloading the server.

## Troubleshooting

### Bot not responding

- Check that `.env` file exists and has correct tokens
- Verify the bot token is valid with: 
  ```bash
  curl https://api.telegram.org/bot<TOKEN>/getMe
  ```

### Playwright issues

- Reinstall browsers: `playwright install chromium`
- Check Chrome/Chromium is installed

### Website structure changed

If the website layout changes:
1. Edit `scraper.py`
2. Update the button selectors in the `check_appointments()` function
3. Adjust appointment slot detection logic

### Debugging

Enable verbose logging by modifying the logging level in `bot.py`:

```python
logging.basicConfig(level=logging.DEBUG)  # Change INFO to DEBUG
```

## Architecture

```
halle_bot/
├── bot.py           # Main Telegram bot with periodic checking
├── scraper.py       # Website scraper using Playwright
├── requirements.txt # Python dependencies
├── .env.example    # Example environment variables
└── README.md       # This file
```

## Notes

- The bot runs continuously. To stop it, use Ctrl+C or the `/stop` command
- The bot stores state in memory; data is lost on restart
- Consider running it on a server or VPS for 24/7 operation

## Future Improvements

- [ ] Database to track appointment history
- [ ] Webhook instead of polling for real-time updates
- [ ] Multiple languages support
- [ ] Appointment confirmation automation
- [ ] Web dashboard for checking status

## License

MIT

## Support

If the bot doesn't work or the website structure changes, check:
1. Website URL is still: https://halle.de/serviceportal/online-terminvergabe/online-terminvereinbarung-einbuergerungsbehoerde-standesamt
2. Button text matches: "Staatsangehörigkeitsangelegenheiten" and "02. Antrag Einbürgerung"
3. Update selectors in `scraper.py` if website layout changed
