#!/usr/bin/env python3
"""
Advanced debugging script - shows exactly what's on the page
"""

import asyncio
import os
from playwright.async_api import async_playwright

async def debug():
    # Booking URL from environment to keep the script generic.
    url = os.getenv("BOOKING_URL", "https://example.com/appointments")
    
    print("=" * 70)
    print("🔧 DEBUGGING: What's on the page?")
    print("=" * 70)
    print()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        print("📍 Loading page...")
        await page.goto(url, wait_until="networkidle")
        await page.wait_for_timeout(3000)
        print("✓ Page loaded")
        print()
        
        # STEP 1: Click Staatsangehörigkeitsangelegenheiten
        print("=" * 70)
        print("STEP 1: Clicking 'Staatsangehörigkeitsangelegenheiten'...")
        print("=" * 70)
        try:
            staatsangehoerigkeits_button = page.locator(
                "text=Staatsangehörigkeitsangelegenheiten"
            ).first
            await staatsangehoerigkeits_button.wait_for(state="visible", timeout=10000)
            await staatsangehoerigkeits_button.click()
            print("✓ Clicked!")
            await page.wait_for_timeout(2000)
        except Exception as e:
            print(f"✗ Failed: {e}")
            await browser.close()
            return
        
        # STEP 2: Click 02. Antrag Einbürgerung
        print()
        print("=" * 70)
        print("STEP 2: Clicking '02. Antrag Einbürgerung'...")
        print("=" * 70)
        try:
            antrag_button = page.locator(
                "text=02. Antrag Einbürgerung"
            ).first
            await antrag_button.wait_for(state="visible", timeout=10000)
            await antrag_button.click()
            print("✓ Clicked!")
            await page.wait_for_timeout(2000)
        except Exception as e:
            print(f"✗ Failed: {e}")
            await browser.close()
            return
        
        print()
        print("=" * 70)
        print("PAGE CONTENT AFTER NAVIGATION:")
        print("=" * 70)
        
        # Get full page content
        content = await page.locator("body").text_content()
        
        print("=" * 70)
        print("FULL PAGE CONTENT:")
        print("=" * 70)
        print(content)
        print("=" * 70)
        print()
        
        # Look for specific texts
        print("=" * 70)
        print("SEARCHING FOR KEY TEXT:")
        print("=" * 70)
        
        patterns = [
            "Staatsangehörigkeitsangelegenheiten",
            "02. Antrag Einbürgerung",
            "Keine freien Termine gefunden",
            "verfügbar",
            "Termine",
            "Reservierung"
        ]
        
        for pattern in patterns:
            if pattern.lower() in content.lower():
                print(f"  ✓ FOUND: '{pattern}'")
            else:
                print(f"  ✗ NOT FOUND: '{pattern}'")
        
        print()
        print("=" * 70)
        print("SUMMARY:")
        print("=" * 70)
        
        has_keine_freien = "Keine freien Termine gefunden".lower() in content.lower()
        
        if has_keine_freien:
            print("✓ Text 'Keine freien Termine gefunden' FOUND")
            print("  → Meaning: NO appointments available")
            print("  → Bot will NOT send notification")
        else:
            print("✗ Text 'Keine freien Termine gefunden' NOT FOUND")
            print("  → Meaning: Appointments MAY be available!")
            print("  → Bot WILL send notification ⚠️")
        
        print()
        print("=" * 70)
        print("PAGE CONTENT (last 1500 characters):")
        print("=" * 70)
        print(content[-1500:])
        print()
        
        # Save screenshot
        await page.screenshot(path="/tmp/debug_screenshot_after_nav.png")
        print("Screenshot saved to: /tmp/debug_screenshot_after_nav.png")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug())
