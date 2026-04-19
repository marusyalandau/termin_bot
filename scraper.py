"""Scraper for City X appointment availability.

Uses Playwright for handling JavaScript-driven dynamic content.
"""

import asyncio
from playwright.async_api import async_playwright
import logging
import re
import os
import random
import time
from pathlib import Path

logger = logging.getLogger(__name__)



def _random_delay(min_ms=1200, max_ms=4200):
    time.sleep(random.uniform(min_ms, max_ms) / 1000)

def _load_user_agents(path="user_agents.txt"):
    try:
        with open(path, encoding="utf-8") as f:
            return [ua.strip() for ua in f if ua.strip()]
    except Exception:
        return []

def _pick_user_agent(profile_path=None):
    # For a single user_data_dir always use the same user-agent
    ua_file = None
    if profile_path:
        ua_file = Path(profile_path) / "user_agent.txt"
        if ua_file.exists():
            return ua_file.read_text(encoding="utf-8").strip()
    agents = _load_user_agents()
    ua = random.choice(agents) if agents else (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
    if ua_file:
        ua_file.write_text(ua, encoding="utf-8")
    return ua

async def _simulate_human(page):
    # Random mouse movements and scrolling
    width = random.randint(200, 1200)
    height = random.randint(200, 900)
    try:
        await page.mouse.move(width, height, steps=random.randint(5, 20))
        await page.mouse.wheel(delta_x=random.randint(0, 100), delta_y=random.randint(0, 500))
        await page.wait_for_timeout(random.randint(400, 2200))
    except Exception:
        pass

def _extract_slots_by_date(text: str) -> dict[str, list[str]]:
    """Infer date -> times mapping from page text lines.

    The booking page often mixes dates and times in nearby lines. This parser
    associates times with the most recently seen date line and also supports
    lines that contain both dates and times.
    """
    date_pattern = re.compile(r"\b\d{1,2}\.\d{1,2}\.\d{4}\b")
    time_pattern = re.compile(r"\b\d{1,2}:\d{2}\b")

    slots_by_date: dict[str, list[str]] = {}
    current_dates: list[str] = []

    for raw_line in text.splitlines():
        line = " ".join(raw_line.split())
        if not line:
            continue

        dates_in_line = list(dict.fromkeys(date_pattern.findall(line)))
        times_in_line = list(dict.fromkeys(time_pattern.findall(line)))

        if dates_in_line:
            current_dates = dates_in_line
            for date in dates_in_line:
                slots_by_date.setdefault(date, [])

        if times_in_line and current_dates:
            for date in current_dates:
                bucket = slots_by_date.setdefault(date, [])
                for slot_time in times_in_line:
                    if slot_time not in bucket:
                        bucket.append(slot_time)

    # Keep deterministic output for stable comparisons/messages.
    normalized: dict[str, list[str]] = {}
    for date in sorted(slots_by_date):
        times = sorted(set(slots_by_date[date]))
        normalized[date] = times
    return normalized


def _flatten_slot_map(slots_by_date: dict[str, list[str]]) -> list[str]:
    """Flatten mapping into display-ready entries for backward compatibility."""
    flattened: list[str] = []
    for date in sorted(slots_by_date):
        times = slots_by_date[date]
        if times:
            flattened.extend([f"{date} {slot_time}" for slot_time in times])
        else:
            flattened.append(date)
    return flattened


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

    url = os.getenv("BOOKING_URL")
    # Use persistent context
    profile_dir = os.getenv("BROWSER_PROFILE_DIR", "browser_profile")
    Path(profile_dir).mkdir(exist_ok=True)
    user_agent = _pick_user_agent(profile_dir)

    try:
        async with async_playwright() as p:
            proxy_url = os.getenv("PROXY_URL")
            context_args = {
                "user_data_dir": profile_dir,
                "headless": True,
                "locale": "de-DE",
                "viewport": {"width": 1440, "height": 1200},
                "args": [f"--user-agent={user_agent}"]
            }
            if proxy_url:
                context_args["proxy"] = {"server": proxy_url}
            browser_context = await p.chromium.launch_persistent_context(**context_args)
            page = browser_context.pages[0] if browser_context.pages else await browser_context.new_page()

            logger.info(f"Opening direct booking URL")
            await page.goto(url, wait_until="networkidle")
            await _simulate_human(page)
            _random_delay()
            await _dismiss_cookie_banner(page)
            _random_delay()

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
            await _simulate_human(page)
            _random_delay()

            # Step 1: Click on "Staatsangehörigkeitsangelegenheiten"
            logger.info("Looking for 'Staatsangehörigkeitsangelegenheiten' button...")
            first_step_ok = False
            try:
                try:
                    await _click_text(page, "Staatsangehörigkeitsangelegenheiten")
                except Exception:
                    await _click_text(page, "Staatsangehorigkeitsangelegenheiten")
                logger.info("Clicked 'Staatsangehörigkeitsangelegenheiten'")
                await _simulate_human(page)
                _random_delay()
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
                await _simulate_human(page)
                _random_delay()
            except Exception as e:
                present = await _has_text(page, "02. Antrag Einbürgerung") or await _has_text(page, "Antrag Einbürgerung")
                logger.error(f"Error clicking Antrag Einbürgerung: {e}")
                await browser_context.close()
                return {
                    'available': False,
                    'message': 'Error in second step',
                    'slots': [],
                    'error': f"{e} | text_present={present} | first_step_ok={first_step_ok}"
                }

            # Step 3: Access the reservation page and check for available appointments
            logger.info("Checking for available appointments...")
            try:
                await _simulate_human(page)
                _random_delay()
                # Get page content
                main_content = await page.locator("body").text_content() or ""
                logger.info(f"Page content length: {len(main_content)} characters")

                slots_by_date = _extract_slots_by_date(main_content)
                slot_hints = _flatten_slot_map(slots_by_date)
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
                    await browser_context.close()
                    return {
                        'available': True,
                        'message': 'Appointments may be available!',
                        'slots': slot_hints or ["Available slots detected"],
                        'slots_by_date': slots_by_date,
                        'error': None
                    }

                if has_no_appointments_text:
                    logger.info("✓ Found: 'Keine freien Termine gefunden.' - No appointments available")
                    await browser_context.close()
                    return {
                        'available': False,
                        'message': 'No appointments currently available',
                        'slots': [],
                        'error': None
                    }
                logger.warning(
                    "No explicit no-appointment text and no positive slot indicators found; returning unknown/no slots."
                )
                await browser_context.close()
                return {
                    'available': False,
                    'message': 'Could not confirm available appointments',
                    'slots': [],
                    'error': None
                }
            except Exception as e:
                logger.error(f"Error checking appointments: {e}")
                await browser_context.close()
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
