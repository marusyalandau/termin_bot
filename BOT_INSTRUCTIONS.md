# Telegram Bot Instructions

## Commands

Important:

- `/start`, `/check`, and `/status` work only when `bot.py` is currently running
- If only `run_check_once.py` is scheduled with `cron`, the bot will send notifications but will not answer commands
- For automatic checks, choose one mode: `bot.py` or `cron` + `run_check_once.py`
- Automatic notifications are sent only when appointments are available, unless you explicitly enable no-appointment messages in `run_check_once.py`

Here are all the commands you can use with the Halle Appointment Bot:

### `/start`
Shows welcome message and all available commands. Start here if you need help!

### `/check`
Check for available appointments **immediately**. Use this if you want to manually check right now instead of waiting for the automatic check.

**Response**: The bot will:
- Show ✅ if appointments are available
- List all available time slots
- Show ❌ if no appointments are available

### `/status`
Shows the current bot status including:
- Last check time
- Check interval (how often it checks)
- Whether an appointment was previously found

Use this to verify the bot is running.

---

## Automatic Checks

The bot automatically checks for appointments every **1 hour** by default in `bot.py` mode. This can be changed with `CHECK_INTERVAL` in `.env`.

### How You'll Be Notified

When the bot finds available appointment slots, you'll receive a Telegram message that shows:
- ✅ **Available!** notification
- List of available time slots
- Direct link to the booking page

### When No Appointments Are Found

The bot will:
- Continue checking silently in the background
- **Not spam you** with "no appointments" messages
- Alert you **only when** appointments become available

---

## Usage Tips

1. **First Run**: Send `/start` to see this help
2. **Manual Check**: Send `/check` to see results immediately
3. **Let It Run**: The bot checks automatically based on `CHECK_INTERVAL`
4. **Keep Your Chat Open**: Notifications will come to this chat
5. **When Found**: Click the link in the notification to book immediately

---

## Configuration

The bot's check interval can be customized:

| Interval | Frequency |
|----------|-----------|
| 300 | Every 5 minutes |
| 600 | Every 10 minutes |
| 1800 | Every 30 minutes |
| 3600 | Every 1 hour (default) |
| 7200 | Every 2 hours |

Note: Don't set it too low (less than 5 minutes) to avoid server overload.

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

## FAQ

**Q: Will the bot spam me?**
A: No. Automatic checks are silent when there are no appointments. Manual `/check` still replies with the current result.

**Q: How long does a check take?**
A: 30-60 seconds. The bot opens a browser, navigates through the website, and checks for slots.

**Q: Can I change how often it checks?**
A: Yes! Edit the `CHECK_INTERVAL` in the bot's .env file and restart.

**Q: What if the website changes?**
A: The bot will report an error. Contact the bot administrator to update the selectors.

**Q: Can multiple people use the same bot?**
A: In `bot.py` mode, multiple people can use commands if the bot is running. In `run_check_once.py` mode, notifications go only to the configured `TELEGRAM_CHAT_ID`, so use a group chat if multiple people should receive them.

---

## Example Messages

### When Appointments Are Found
```
✅ AVAILABLE! Found 3 available appointment slots!

Slots:
  • 15.04.2026
  • 16.04.2026
  • 17.04.2026

🔗 Check here: https://halle.de/serviceportal/...
```

### When No Appointments Are Available
```
❌ No appointments currently available
```

This kind of message is returned by manual `/check`. Automatic background checks stay silent by default.

### Status Check
```
📊 Bot Status

Last check: 2026-04-07 14:30:45
Check interval: 3600 seconds (60 minutes)
Appointment found: No

The bot will automatically check for appointments every 60 minutes.
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

| Command | What It Does |
|---------|-------------|
| `/start` | Show help |
| `/check` | Check now |
| `/status` | Show bot status |

---

**Last Updated**: April 7, 2026

For more information, see the full README.md or QUICKSTART.md
