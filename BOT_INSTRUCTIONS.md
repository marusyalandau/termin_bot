
# Telegram Bot Instructions

**Note:** In the current configuration, the bot sends notifications only to a single chat — the one specified in the environment variable `TELEGRAM_CHAT_ID`.

## To use the bot interactively (with commands), you must run:
```
python bot.py
```
in your terminal. The bot will not respond to commands unless bot.py is running.
At this configuration,

## Commands


Important:

- `/start` and `/status` work only when `bot.py` is currently running
- If only `run_check_once.py` is scheduled with `cron`, the bot will send notifications but will not answer commands
- For automatic checks, choose one mode: `bot.py` or `cron` + `run_check_once.py`
- Automatic notifications are sent only when new appointments are available (no repeat notifications for the same slots)

Here are all the commands you can use with the City X Appointment Bot:


### `/start`
Shows welcome message and all available commands. Start here if you need help!

### `/status`
Shows the current bot status including:
- Last check time
- Next scheduled check (random interval)
- Whether an appointment was previously found

Use this to verify the bot is running.

---


## Automatic Checks

The bot automatically checks for appointments at random intervals (26–34 minutes by default, configurable via `.env` with `MIN_CHECK_INTERVAL` and `MAX_CHECK_INTERVAL`).

### How You'll Be Notified

When the bot finds new available appointment slots, you'll receive a Telegram message that shows:
- ✅ **Available!** notification
- List of new available time slots
- Direct link to the booking page

### When No Appointments Are Found

The bot will:
- Continue checking silently in the background
- **Not spam you** with "no appointments" messages
- Alert you **only when new** appointments become available (no repeat notifications for the same slots)

---


## Usage Tips

1. **First Run**: Send `/start` to see this help
2. **Let It Run**: The bot checks automatically at random intervals
3. **Keep Your Chat Open**: Notifications will come to this chat
4. **When Found**: Click the link in the notification to book immediately

---


## Configuration

You can keep public docs generic and use real links only in your private `.env`:

- `BOT_LABEL=City X Appointment Bot`
- `APPOINTMENT_LINK=https://example.com/appointments` (shown in Telegram messages)
- `BOOKING_URL=https://your-booking-provider.example/calendar` (used by scraper)

The bot's check interval can be customized:

- `MIN_CHECK_INTERVAL=1560` (26 minutes)
- `MAX_CHECK_INTERVAL=2040` (34 minutes)

Note: Don't set intervals too low (less than 5 minutes) to avoid server overload.

---

## Cron Mode

If you use `run_check_once.py` with `cron`, the bot does not listen for Telegram commands.

In this mode:
- `CHECK_INTERVAL` is ignored
- `cron` decides how often checks run
- one result message is sent to `TELEGRAM_CHAT_ID`
- using a group chat ID sends the same message to the whole group
- do not run this together with periodic checks in `bot.py` unless you want duplicate checks and duplicate notifications
- by default, `run_check_once.py` stays silent when there are no appointments

---


## Example Messages

### When New Appointments Are Found
```
✅ AVAILABLE! New slots:
  • 15.04.2026
  • 16.04.2026
  • 17.04.2026

🔗 Check here: https://example.com/appointments
```

If no new appointments are found, the bot stays silent.

### Status Check
```
📊 Bot Status

Last check: 2026-04-07 14:30:45
Next check: 2026-04-07 15:00:00
Appointment found: No
```

---

## Troubleshooting

**Bot not responding to commands?**
- Make sure you sent the message to the correct bot
- Make sure `bot.py` is actually running
- Check that the Telegram token is valid

**Cron is running but `/start` does nothing?**
- That is expected when only `run_check_once.py` is scheduled with cron
- Start `bot.py` if you want Telegram commands

**Getting repeated error messages?**
- The website structure might have changed
- Contact the bot administrator

**Not getting notifications?**
- Check your Telegram silent mode is off
- Make sure you have the bot chat open
- Verify the bot is still running (`/status`)

---


## Quick Reference

| Command   | What It Does    |
|-----------|----------------|
| `/start`  | Show help       |
| `/status` | Show bot status |

---


**Last Updated**: April 19, 2026

For more information, see the full README.md or QUICKSTART.md

---
**Technical notes:**
- The bot uses a persistent browser profile for stealth (cookies/history are reused)
- User-agent is randomly selected per profile
- Supports proxy via `PROXY_URL` in `.env`
- Only new slots trigger notifications
- Random check intervals (not fixed)
