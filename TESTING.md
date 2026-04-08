# Testing Without Telegram

## Quick Start - Just Test If It Works

You don't need Telegram to test the scraper! Follow these steps:

### 1. Install dependencies

```bash
git clone https://github.com/marusyalandau/termin_bot.git
cd termin_bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

### 2. Run the simple test

```bash
python test_scraper.py
```

This will:
- Open the booking system (uses direct URL for reliability)
- Click "Staatsangehörigkeitsangelegenheiten"
- Click "02. Antrag Einbürgerung"
- Look for the text **"Keine freien Termine gefunden."**
- Show you if appointments are available

**Expected output:**
```
✅ AVAILABLE!
  → Appointments may be available

OR

😴 No appointments
  → Found "Keine freien Termine gefunden."
```

### 3. For detailed debugging

```bash
python debug_simple.py
```

This will:
- Navigate through all steps (click both buttons)
- Show you the full page content
- Look for "Keine freien Termine gefunden" text
- Save a screenshot to `/tmp/debug_screenshot_after_nav.png`
- Tell you exactly if appointments are available

---

## How It Works

The scraper looks for this exact text on the appointment page:

```
"Keine freien Termine gefunden."
```

### Logic:

| Text Found? | Meaning | Bot Action |
|-------------|---------|-----------|
| ✓ YES | No appointments available | Silent check (no notification) |
| ✗ NO | Appointments may be available | 🔔 Send Telegram notification |

---

## Testing Flow

```
1. Run: python test_scraper.py
        ↓
2. Does it work?
   
   YES → Continue to step 3
   NO  → Run debug_scraper.py to see what's wrong
        ↓
3. Configure Telegram (.env file)
        ↓
4. Choose a run mode after testing:
  - `python bot.py` for the long-running bot
  - `python run_check_once.py` or cron for one-shot checks
```

---

## Files for Testing

| File | Purpose |
|------|---------|
| `test_scraper.py` | Simple test - what most people need |
| `debug_scraper.py` | Advanced debug - shows page content & screenshot |
| `scraper.py` | The actual scraper (no need to modify) |

---

## Troubleshooting

### Error: "No module named playwright"
```bash
pip install playwright
playwright install chromium
```

### Error: "Button not found"
- Website structure might have changed
- Run `debug_scraper.py` to see the page
- Contact administrator to update button names

### Error: Connection refused / Website not loading
- Check internet connection
- Website might be down or `BOOKING_URL` is wrong
- Try again in a few minutes

### Error: Cloudflare block detected
- The target site is blocking the server IP
- Try from another machine or server
- Oracle may work even if GitHub Actions did not

### Screenshot shows nothing
- Website might have blocked headless browsers
- This would need a different solution (not Playwright)

---

## What To Do After Testing

1. **If test_scraper.py works** ✓
  - Get Telegram bot token from @BotFather
  - Get your Telegram chat ID or group chat ID
  - Edit `.env` file with credentials
  - Run `python bot.py` or `python run_check_once.py`

2. **If test_scraper.py fails** ✗
   - Run `python debug_scraper.py`
  - Check the screenshot at `/tmp/termin_bot_debug_screenshot.png`
   - Look at the page content output
   - Update the button names in `scraper.py` if needed

---

## Example Test Output

### When Appointments Are Available

```
🎉 APPOINTMENTS FOUND!
  Available: True
  Message: Appointments may be available!
  Slots: ['Available slots detected']
```

### When No Appointments

```
😴 No appointments available at this moment.
  Available: False
  Message: No appointments currently available
  Slots: []
```

---

## Need Help?

1. Run the test: `python test_scraper.py`
2. If it fails, run debug: `python debug_scraper.py`
3. Check the output and screenshot
4. Update `scraper.py` if button names changed on the website

The scraper is just looking for a simple German text, so it's very reliable!
