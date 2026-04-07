#!/usr/bin/env python3
"""
Test script for the appointment scraper
Run this to test if the scraper is working correctly without the full bot

This script will:
1. Navigate to the Halle website
2. Click through the required buttons
3. Look for the text "Keine freien Termine gefunden."
4. Report the results

Usage:
    python test_scraper.py

Expected output:
    - If "Keine freien Termine gefunden." is found: NO appointments available
    - If text is NOT found: Appointments MAY be available
"""

import asyncio
import logging
from scraper import check_appointments

# Configure logging to show detailed info
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def main():
    print("=" * 70)
    print("🔍 HALLE APPOINTMENT SCRAPER - TEST MODE")
    print("=" * 70)
    print()
    print("What this test does:")
    print("  1. Opens the direct booking URL (bypasses main halle.de page)")
    print("  2. Clicks 'Staatsangehörigkeitsangelegenheiten'")
    print("  3. Clicks '02. Antrag Einbürgerung'")
    print("  4. Checks for the text: 'Keine freien Termine gefunden.'")
    print()
    print("  📝 If text IS found   → No appointments available")
    print("  📝 If text NOT found  → Appointments may be available!")
    print()
    print("-" * 70)
    print("⏳ Starting test... (this may take 30-60 seconds)")
    print()
    
    try:
        result = await check_appointments()
        
        print("-" * 70)
        print("✅ TEST COMPLETED")
        print("-" * 70)
        print()
        
        print("RESULTS:")
        print(f"  Available: {result['available']}")
        print(f"  Message: {result['message']}")
        
        if result['slots']:
            print(f"  Found {len(result['slots'])} time slots:")
            for slot in result['slots']:
                print(f"    • {slot}")
        
        if result['error']:
            print(f"  ERROR: {result['error']}")
        
        print()
        print("-" * 70)
        
        # Explain what to do next
        print()
        if result['available']:
            print("🎉 APPOINTMENTS FOUND!")
            print("   The scraper successfully navigated and found available slots.")
            print("   ➜ Visit the website to book: https://halle.de/serviceportal/...")
        else:
            print("😴 No appointments available at this moment.")
            print("   The scraper successfully navigated but found:")
            print("   'Keine freien Termine gefunden.'")
            print("   ➜ The bot will continue checking periodically")
        
        print()
        print("-" * 70)
        print("Next steps:")
        print("  1. If test passed: Configure .env with Telegram credentials")
        print("  2. Run the bot: python bot.py")
        print("  3. Bot will check automatically every 1 hour")
        print("=" * 70)
        
    except Exception as e:
        print()
        print("❌ TEST FAILED")
        print("-" * 70)
        print(f"Error: {e}")
        print()
        print("Troubleshooting:")
        print("  • Check internet connection")
        print("  • Website might be down: https://halle.de/")
        print("  • Website structure might have changed")
        print("  • Playwright browsers not installed: playwright install chromium")
        print("=" * 70)

if __name__ == "__main__":
    asyncio.run(main())
