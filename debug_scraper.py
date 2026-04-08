#!/usr/bin/env python3
"""
Advanced debugging script for the appointment scraper
Use this if you need more details about what's happening on the page

Usage:
    python debug_scraper.py

This will:
1. Show the full page content
2. Save a screenshot
3. Look for the "Keine freien Termine gefunden." text
4. Show you exactly what the scraper sees
"""

import asyncio
import os
from playwright.async_api import async_playwright
import logging

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)

async def debug_scraper():
    """
    Debug version of the scraper with more verbose output
    """
    url = os.getenv("BOOKING_URL", "https://example.com/appointments")
    
    print("=" * 70)
    print("🔧 CITY X SCRAPER - DEBUG MODE")
    print("=" * 70)
    print()
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            print(f"📍 Opening: {url}")
            await page.goto(url, wait_until="networkidle")
            print("✓ Page loaded")
            print()
            
            # Step 1: Click on "Staatsangehörigkeitsangelegenheiten"
            print("Step 1: Looking for 'Staatsangehörigkeitsangelegenheiten'...")
            try:
                staatsangehoerigkeits_button = await page.locator(
                    "text=Staatsangehörigkeitsangelegenheiten"
                ).first
                
                if await staatsangehoerigkeits_button.is_visible():
                    await staatsangehoerigkeits_button.click()
                    print("  ✓ Clicked 'Staatsangehörigkeitsangelegenheiten'")
                    await page.wait_for_timeout(1500)
                else:
                    print("  ✗ Button not visible")
                    return
            except Exception as e:
                print(f"  ✗ Error: {e}")
                return
            
            # Step 2: Click on "02. Antrag Einbürgerung"
            print()
            print("Step 2: Looking for '02. Antrag Einbürgerung'...")
            try:
                antrag_button = await page.locator(
                    "text=02. Antrag Einbürgerung"
                ).first
                
                if await antrag_button.is_visible():
                    await antrag_button.click()
                    print("  ✓ Clicked '02. Antrag Einbürgerung'")
                    await page.wait_for_timeout(1500)
                else:
                    print("  ✗ Button not visible")
                    return
            except Exception as e:
                print(f"  ✗ Error: {e}")
                return
            
            # Step 3: Get and analyze page content
            print()
            print("Step 3: Analyzing page content...")
            main_content = await page.locator("body").text_content()
            
            print(f"  📄 Page content size: {len(main_content)} characters")
            print()
            
            # Check for the key text
            no_appointments_text = "Keine freien Termine gefunden"
            found = no_appointments_text.lower() in main_content.lower()
            
            print(f"Searching for: '{no_appointments_text}'")
            print(f"Result: {'✓ FOUND' if found else '✗ NOT FOUND'}")
            print()
            
            # Show relevant page content
            print("-" * 70)
            print("PAGE CONTENT (showing last 2000 characters):")
            print("-" * 70)
            print(main_content[-2000:])
            print("-" * 70)
            print()
            
            # Save screenshot
            print("📸 Saving screenshot...")
            screenshot_path = "/tmp/termin_bot_debug_screenshot.png"
            await page.screenshot(path=screenshot_path)
            print(f"  ✓ Screenshot saved to: {screenshot_path}")
            print()
            
            # Summary
            print("=" * 70)
            print("SUMMARY")
            print("=" * 70)
            if found:
                print("✓ Text 'Keine freien Termine gefunden.' WAS found")
                print("  → This means: NO appointments available right now")
                print("  → Scraper status: WORKING CORRECTLY ✓")
            else:
                print("✗ Text 'Keine freien Termine gefunden.' was NOT found")
                print("  → This means: Appointments may be available!")
                print("  → Scraper status: WORKING CORRECTLY ✓")
            print()
            print("=" * 70)
            
            await browser.close()
            
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        print()
        print("Common issues:")
        print("  1. Internet connection down")
        print("  2. Website is down or BOOKING_URL is unreachable")
        print("  3. Playwright not installed: playwright install chromium")
        print("  4. Website structure changed - button names might be different")

if __name__ == "__main__":
    asyncio.run(debug_scraper())
