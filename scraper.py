"""Scraper for City X appointment availability.

Uses Playwright for handling JavaScript-driven dynamic content.
"""

import asyncio
from playwright.async_api import async_playwright
import logging
import re
import os

logger = logging.getLogger(__name__)


def _extract_slot_hints(text: str) -> list[str]:
    # Collect likely appointment hints shown on the booking page.
    dates = re.findall(r"\b\d{1,2}\.\d{1,2}\.\d{4}\b", text)
    times = re.findall(r"\b\d{1,2}:\d{2}\b", text)

    hints = sorted(set(dates + times))
    return hints[:20]


def _has_no_appointments_text(text: str) -> bool:
    lowered = text.lower()
    patterns = [
        "keine freien termine gefunden",
        "es sind keine termine verfügbar",
        "es sind keine termine verfugbar",
        "leider keine termine verfügbar",
    ]
    return any(p in lowered for p in patterns)


def _has_positive_availability_indicators(text: str) -> bool:
    lowered = text.lower()
    positive_patterns = [
        "uhr",
        "termin auswählen",
        "termin auswaehlen",
        "zeit auswählen",
        "zeit auswaehlen",
        "frei",
        "verfügbar",
        "verfugbar",
    ]
    return any(p in lowered for p in positive_patterns)


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
    Check for available appointments on the configured booking website.
    
    Returns:
        dict: {
            'available': bool,
            'message': str,
            'slots': list of available time slots (if any),
            'error': str (if error occurred)
        }
    """
    # Booking URL is configurable via .env to avoid hardcoded public links.
    url = os.getenv(
        "BOOKING_URL",
    )
    
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

            # Detect Cloudflare block before attempting any interaction
            body_text_early = await page.locator("body").text_content() or ""
            if (
                "sorry, you have been blocked" in body_text_early.lower()
                or "cloudflare ray id" in body_text_early.lower()
                or "enable cookies" in body_text_early.lower() and "cloudflare" in body_text_early.lower()
            ):
                ip_match = re.search(r'\d+\.\d+\.\d+\.\d+', body_text_early)
                detected_ip = ip_match.group(0) if ip_match else "unknown"
                logger.warning("Cloudflare block detected! Blocked IP: %s", detected_ip)
                await browser.close()
                return {
                    'available': False,
                    'message': 'Cloudflare block detected',
                    'slots': [],
                    'error': None,
                    'cloudflare_blocked': True,
                    'blocked_ip': detected_ip,
                }

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
                main_content = await page.locator("body").text_content() or ""
                logger.info(f"Page content length: {len(main_content)} characters")

                slot_hints = _extract_slot_hints(main_content)
                has_no_appointments_text = _has_no_appointments_text(main_content)
                has_positive_indicators = _has_positive_availability_indicators(main_content)

                logger.info(
                    "Availability signals: no_appointments=%s positive_indicators=%s slot_hints=%s",
                    has_no_appointments_text,
                    has_positive_indicators,
                    len(slot_hints),
                )
                
                # Save screenshot for debugging
                try:
                    await page.screenshot(path="/tmp/termin_bot_screenshot.png")
                    logger.debug("Screenshot saved to /tmp/termin_bot_screenshot.png")
                except:
                    pass

                # Prefer positive evidence if both signals exist.
                if slot_hints or (has_positive_indicators and not has_no_appointments_text):
                    logger.info("Detected available appointment indicators.")
                    await browser.close()
                    return {
                        'available': True,
                        'message': 'Appointments may be available!',
                        'slots': slot_hints or ["Available slots detected"],
                        'error': None
                    }

                if has_no_appointments_text:
                    logger.info("✓ Found: 'Keine freien Termine gefunden.' - No appointments available")
                    await browser.close()
                    return {
                        'available': False,
                        'message': 'No appointments currently available',
                        'slots': [],
                        'error': None
                    }
                logger.warning(
                    "No explicit no-appointment text and no positive slot indicators found; returning unknown/no slots."
                )
                await browser.close()
                return {
                    'available': False,
                    'message': 'Could not confirm available appointments',
                    'slots': [],
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
