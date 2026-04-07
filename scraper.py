"""
Scraper for Halle Einbürgerungsbehörde appointment availability
Uses Playwright for handling JavaScript-driven dynamic content
"""

import asyncio
from playwright.async_api import async_playwright
import logging

logger = logging.getLogger(__name__)


async def _dismiss_cookie_banner(page):
    for text in ("Alle akzeptieren", "Accept all", "Akzeptieren"):
        try:
            button = page.get_by_text(text, exact=False).first
            await button.click(timeout=3000)
            logger.info("Dismissed cookie banner")
            await page.wait_for_timeout(1000)
            return
        except Exception:
            continue


async def _click_text(page, text, timeout=30000):
    await page.wait_for_function(
        "target => document.body && ((document.body.innerText || '').includes(target) || (document.body.textContent || '').includes(target))",
        arg=text,
        timeout=timeout,
    )

    locator = page.get_by_text(text, exact=False).first
    try:
        await locator.click(timeout=5000)
        return
    except Exception as exc:
        logger.info("Regular click for '%s' failed: %s", text, exc)

    clicked = await page.evaluate(
        r"""
        target => {
            const targetLower = target.toLowerCase();
            const elements = Array.from(document.querySelectorAll('*'));
            for (const element of elements) {
                const content = (element.textContent || '').replace(/\s+/g, ' ').trim();
                if (!content.toLowerCase().includes(targetLower)) {
                    continue;
                }

                const clickable = element.closest(
                    '.service_selector, .category, button, a, label, div'
                ) || element;

                clickable.dispatchEvent(new MouseEvent('click', {
                    bubbles: true,
                    cancelable: true,
                    view: window,
                }));
                return true;
            }
            return false;
        }
        """,
        text,
    )

    if not clicked:
        raise TimeoutError(f"Could not click element containing '{text}'")


async def _has_text(page, text):
    body_text = await page.locator("body").text_content()
    return text.lower() in (body_text or "").lower()


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
            context = await browser.new_context(
                locale="de-DE",
                viewport={"width": 1440, "height": 1200},
                user_agent=(
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                ),
            )
            page = await context.new_page()
            
            logger.info(f"Opening direct booking URL")
            await page.goto(url, wait_until="networkidle")
            
            # Wait for page to fully load
            await page.wait_for_timeout(5000)
            await _dismiss_cookie_banner(page)
            logger.info("Page loaded, waiting for buttons to appear...")
            
            # Step 1: Click on "Staatsangehörigkeitsangelegenheiten"
            logger.info("Looking for 'Staatsangehörigkeitsangelegenheiten' button...")
            first_step_ok = False
            try:
                try:
                    await _click_text(page, "Staatsangehörigkeitsangelegenheiten")
                except Exception:
                    await _click_text(page, "Staatsangehorigkeitsangelegenheiten")
                logger.info("Clicked 'Staatsangehörigkeitsangelegenheiten'")
                await page.wait_for_timeout(3000)
                first_step_ok = True
            except Exception as e:
                present = await _has_text(page, "Staatsangehörigkeitsangelegenheiten")
                logger.warning(
                    "Could not click first category; will try direct service selection. error=%s text_present=%s",
                    e,
                    present,
                )
            
            # Step 2: Click on "02. Antrag Einbürgerung"
            logger.info("Looking for '02. Antrag Einbürgerung' button...")
            try:
                try:
                    await _click_text(page, "02. Antrag Einbürgerung")
                except Exception:
                    await _click_text(page, "Antrag Einbürgerung")
                logger.info("Clicked '02. Antrag Einbürgerung'")
                await page.wait_for_timeout(4000)
            except Exception as e:
                present = await _has_text(page, "02. Antrag Einbürgerung") or await _has_text(page, "Antrag Einbürgerung")
                logger.error(f"Error clicking Antrag Einbürgerung: {e}")
                await browser.close()
                return {
                    'available': False,
                    'message': 'Error in second step',
                    'slots': [],
                    'error': f"{e} | text_present={present} | first_step_ok={first_step_ok}"
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
