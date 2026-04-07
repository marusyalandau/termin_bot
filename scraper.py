"""
Scraper for Halle Einbürgerungsbehörde appointment availability
Uses Playwright for handling JavaScript-driven dynamic content
"""

import asyncio
from playwright.async_api import async_playwright
import logging

logger = logging.getLogger(__name__)


async def check_appointments():
    """
    Check for available appointments on the Halle website.
    
    Returns:
        dict: {
            'available': bool,
            'message': str,
            'slots': list of available time slots (if any),
            'error': str (if error occurred)
        }
    """
    # Direct URL to the appointment booking system (extracted from iframe)
    url = "https://itc-halle.saas.smartcjm.com/m/standesamt/extern/calendar/?uid=9da900ff-e9a5-46be-a622-ecdfa078121c"
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            logger.info(f"Opening direct booking URL")
            await page.goto(url, wait_until="networkidle")
            
            # Wait for page to fully load
            await page.wait_for_timeout(3000)
            logger.info("Page loaded, waiting for buttons to appear...")
            
            # Step 1: Click on "Staatsangehörigkeitsangelegenheiten"
            logger.info("Looking for 'Staatsangehörigkeitsangelegenheiten' button...")
            try:
                # Wait for the button to be visible (with timeout)
                staatsangehoerigkeits_button = page.locator(
                    "text=Staatsangehörigkeitsangelegenheiten"
                ).first
                
                # Wait up to 10 seconds for button to be visible
                await staatsangehoerigkeits_button.wait_for(state="visible", timeout=10000)
                logger.info("Button found, clicking...")
                await staatsangehoerigkeits_button.click()
                logger.info("Clicked 'Staatsangehörigkeitsangelegenheiten'")
                await page.wait_for_timeout(2000)
            except Exception as e:
                logger.error(f"Error clicking Staatsangehörigkeitsangelegenheiten: {e}")
                await browser.close()
                return {
                    'available': False,
                    'message': 'Error in first step',
                    'slots': [],
                    'error': str(e)
                }
            
            # Step 2: Click on "02. Antrag Einbürgerung"
            logger.info("Looking for '02. Antrag Einbürgerung' button...")
            try:
                antrag_button = page.locator(
                    "text=02. Antrag Einbürgerung"
                ).first
                
                # Wait up to 10 seconds for button to be visible
                await antrag_button.wait_for(state="visible", timeout=10000)
                logger.info("Button found, clicking...")
                await antrag_button.click()
                logger.info("Clicked '02. Antrag Einbürgerung'")
                await page.wait_for_timeout(2000)
            except Exception as e:
                logger.error(f"Error clicking Antrag Einbürgerung: {e}")
                await browser.close()
                return {
                    'available': False,
                    'message': 'Error in second step',
                    'slots': [],
                    'error': str(e)
                }
            
            # Step 3: Access the reservation page and check for available appointments
            logger.info("Checking for available appointments...")
            try:
                # Get page content
                main_content = await page.locator("body").text_content()
                logger.info(f"Page content length: {len(main_content)} characters")
                
                # Check if the "no appointments" message is present
                no_appointments_text = "Keine freien Termine gefunden"
                
                logger.info(f"Looking for text: '{no_appointments_text}'")
                
                # Save screenshot for debugging
                try:
                    await page.screenshot(path="/tmp/halle_screenshot.png")
                    logger.debug("Screenshot saved to /tmp/halle_screenshot.png")
                except:
                    pass
                
                if no_appointments_text.lower() in main_content.lower():
                    logger.info("✓ Found: 'Keine freien Termine gefunden.' - No appointments available")
                    await browser.close()
                    return {
                        'available': False,
                        'message': 'No appointments currently available',
                        'slots': [],
                        'error': None
                    }
                else:
                    # If the "no appointments" text is NOT found, appointments might be available
                    logger.info("✗ NOT found: 'Keine freien Termine gefunden.' - Appointments may be available!")
                    
                    # Try to extract date patterns to show available slots
                    import re
                    dates = re.findall(r'\d{1,2}\.\d{1,2}\.\d{4}', main_content)
                    available_slots = list(set(dates)) if dates else ["Available slots detected"]
                    
                    logger.info(f"Found slots: {available_slots}")
                    
                    await browser.close()
                    return {
                        'available': True,
                        'message': f'Appointments may be available!',
                        'slots': available_slots,
                        'error': None
                    }
                    
            except Exception as e:
                logger.error(f"Error checking appointments: {e}")
                await browser.close()
                return {
                    'available': False,
                    'message': 'Error checking appointments',
                    'slots': [],
                    'error': str(e)
                }
                
    except Exception as e:
        logger.error(f"Fatal error in check_appointments: {e}")
        return {
            'available': False,
            'message': 'Fatal error accessing website',
            'slots': [],
            'error': str(e)
        }


if __name__ == "__main__":
    # Test the scraper
    logging.basicConfig(level=logging.INFO)
    result = asyncio.run(check_appointments())
    print(result)
