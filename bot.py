"""Telegram bot for checking City X appointments."""

import os
import logging
import asyncio
import sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import httpx
from dotenv import load_dotenv
from telegram import Update
from telegram.error import InvalidToken, NetworkError, RetryAfter, TimedOut
from telegram.ext import Application, CommandHandler, ContextTypes
from scraper import check_appointments
from hints_state import (
    load_known_hints,
    save_known_hints,
    get_new_hints,
    build_slot_keys,
    parse_ddmmyyyy,
    filter_slots_by_max_date,
)

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    filename="bot.log"
)
logger = logging.getLogger(__name__)

# Suppress httpx request logs — they expose the bot token in the URL and are too noisy
logging.getLogger("httpx").setLevel(logging.WARNING)


def _format_slots_by_date_for_message(slots_by_date: dict[str, list[str]], new_keys: set[str]) -> str:
    """Build a readable date-only message block for newly discovered slots."""
    dates: list[str] = []
    for date in sorted(slots_by_date):
        has_new_time = any(f"{date}|{slot_time}" in new_keys for slot_time in slots_by_date[date])
        has_date_only_key = f"{date}|" in new_keys
        if has_new_time or has_date_only_key:
            dates.append(date)

    return "\n".join([f"  • {date}" for date in dates])

# Configuration
import random
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
DEFAULT_MIN_INTERVAL = 26 * 60  # Default interval in seconds if not set in .env
DEFAULT_MAX_INTERVAL = 34 * 60
BOT_LABEL = os.getenv("BOT_LABEL", "City X Appointment Bot")
APPOINTMENT_LINK = os.getenv("APPOINTMENT_LINK")

MIN_INTERVAL = int(os.getenv("MIN_CHECK_INTERVAL", str(DEFAULT_MIN_INTERVAL)))  # Can be set via .env
MAX_INTERVAL = int(os.getenv("MAX_CHECK_INTERVAL", str(DEFAULT_MAX_INTERVAL)))
MAX_CONSECUTIVE_ERRORS = int(os.getenv("MAX_CONSECUTIVE_ERRORS", "5"))
STATUS_TIMEZONE_NAME = os.getenv("STATUS_TIMEZONE", "Europe/Berlin")
STOP_ON_NON_TRANSIENT_SCRAPER_ERROR = os.getenv("STOP_ON_NON_TRANSIENT_SCRAPER_ERROR", "true").strip().lower() in {"1", "true", "yes", "on"}
STOP_ON_CLOUDFLARE_BLOCK = os.getenv("STOP_ON_CLOUDFLARE_BLOCK", "true").strip().lower() in {"1", "true", "yes", "on"}


def _status_timezone() -> timezone | ZoneInfo:
    try:
        return ZoneInfo(STATUS_TIMEZONE_NAME)
    except ZoneInfoNotFoundError:
        logger.warning(
            "Invalid STATUS_TIMEZONE='%s', falling back to UTC.",
            STATUS_TIMEZONE_NAME,
        )
        return timezone.utc


def _format_status_time(ts: datetime | None) -> str:
    if ts is None:
        return "Never"

    local_dt = ts.astimezone(_status_timezone())
    offset = local_dt.utcoffset()
    if offset is None:
        return local_dt.strftime('%Y-%m-%d %H:%M:%S UTC')

    total_minutes = int(offset.total_seconds() // 60)
    sign = "+" if total_minutes >= 0 else "-"
    hours, minutes = divmod(abs(total_minutes), 60)

    if minutes == 0:
        gmt_suffix = f"GMT{sign}{hours}"
    else:
        gmt_suffix = f"GMT{sign}{hours:02d}:{minutes:02d}"

    return f"{local_dt.strftime('%Y-%m-%d %H:%M:%S')} {gmt_suffix}"


def _notify_max_date():
    configured = os.getenv("NOTIFY_MAX_DATE", "").strip()
    if not configured:
        return None

    parsed = parse_ddmmyyyy(configured)
    if parsed:
        return parsed

    logger.warning(
        "Invalid NOTIFY_MAX_DATE='%s', disabling date limit.",
        configured,
    )
    return None


def _is_transient_exception(exc: Exception) -> bool:
    """Return True for errors where restart may recover without code/config changes."""
    if isinstance(exc, (TimedOut, NetworkError, RetryAfter, asyncio.TimeoutError, OSError, ConnectionError)):
        return True

    text = str(exc).lower()
    transient_markers = (
        "timed out",
        "timeout",
        "temporary",
        "temporarily",
        "network is unreachable",
        "connection reset",
        "connection aborted",
        "connection refused",
        "service unavailable",
        "bad gateway",
        "name or service not known",
        "try again",
        "429",
    )
    return any(marker in text for marker in transient_markers)


def _should_restart_on_exception(exc: Exception) -> bool:
    """Map unhandled exception to restart policy for systemd."""
    if isinstance(exc, InvalidToken):
        return False
    return _is_transient_exception(exc)


def _is_non_transient_scraper_error(error_text: str | None) -> bool:
    """Return True for scraper errors unlikely to recover without config/code changes."""
    if not error_text:
        return False

    text = error_text.lower()
    fatal_markers = (
        "err_name_not_resolved",
        "name or service not known",
        "nodename nor servname provided",
        "invalid url",
        "failed to parse",
        "unsupported protocol",
        "no host supplied",
    )
    return any(marker in text for marker in fatal_markers)

# State for status
notified_state = {
    "last_available": False,
    "last_slots_found": False,
    "last_slots_outside_filter": False,
    "last_notification_sent": False,
    "last_check_time": None,
    "next_check_time": None,
    "consecutive_errors": 0,
}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start command handler"""
    message = (
        f"🤖 {BOT_LABEL}\n\n"
        "Available commands:\n"
        "/start - Show this message\n"
        "/status - Show bot status\n\n"
        "This bot checks for available appointment slots and notifies you when slots become available."
    )
    await update.message.reply_text(message)




async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show bot status"""
    last_check = notified_state.get("last_check_time")
    next_check = notified_state.get("next_check_time")
    max_date = _notify_max_date()
    last_check_str = _format_status_time(last_check)
    next_check_str = _format_status_time(next_check) if next_check else 'Unknown'
    if notified_state['last_slots_found']:
        found = 'Yes'
    elif notified_state.get('last_slots_outside_filter'):
        found = 'Found, but all outside date filter'
    else:
        found = 'No'
    notified = 'Yes' if notified_state['last_notification_sent'] else 'No'
    filter_status = (
        f"Enabled (<= {max_date.strftime('%d.%m.%Y')})"
        if max_date is not None
        else "Disabled"
    )
    message = (
        "📊 Bot Status\n\n"
        f"Last check: {last_check_str}\n"
        f"Next check: {next_check_str}\n"
        f"Slots found on last check: {found}\n"
        f"Notification sent on last check: {notified}\n"
        f"Date filter: {filter_status}\n\n"
        "The bot checks automatically at random intervals (26–34 min by default)."
    )
    await update.message.reply_text(message)


async def _notify_error(context: ContextTypes.DEFAULT_TYPE, error_text: str) -> None:
    """Send an error notification to the configured chat."""
    if CHAT_ID:
        try:
            await context.bot.send_message(chat_id=CHAT_ID, text=error_text)
        except Exception as exc:
            logger.error("Failed to send error notification: %s", exc)


async def _notify_fatal_error(error_text: str, context: ContextTypes.DEFAULT_TYPE | None = None, update: object | None = None) -> None:
    """Send fatal error message to configured chat and, when possible, to the current update chat."""
    target_chats: list[str] = []
    if isinstance(update, Update) and update.effective_chat:
        target_chats.append(str(update.effective_chat.id))
    if CHAT_ID:
        target_chats.append(str(CHAT_ID))

    # Preserve order and remove duplicates.
    deduped_targets = list(dict.fromkeys(target_chats))
    if not deduped_targets:
        return

    if context is not None:
        for chat_id in deduped_targets:
            try:
                await context.bot.send_message(chat_id=chat_id, text=error_text)
            except Exception as exc:
                logger.error("Failed to send fatal error notification to %s: %s", chat_id, exc)
        return

    if not TELEGRAM_TOKEN:
        logger.error("Cannot send fatal error notification: TELEGRAM_BOT_TOKEN is missing.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    async with httpx.AsyncClient(timeout=15) as client:
        for chat_id in deduped_targets:
            try:
                response = await client.post(url, json={"chat_id": chat_id, "text": error_text})
                response.raise_for_status()
            except Exception as exc:
                logger.error("Failed to send fatal error notification via Bot API to %s: %s", chat_id, exc)


async def _handle_application_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle uncaught handler/job exceptions from python-telegram-bot."""
    exc = context.error
    if exc is None:
        return

    logger.exception("Unhandled application error: %s", exc)
    if isinstance(exc, Exception) and _is_transient_exception(exc):
        logger.warning("Transient application error detected; bot will continue running.")
        return

    stop_text = (
        f"⛔ {BOT_LABEL} stopped due to non-transient internal error:\n"
        f"{type(exc).__name__}: {exc}"
    )
    await _notify_fatal_error(stop_text, context=context, update=update)
    logger.error("Stopping bot due to non-transient application error.")
    sys.exit(0)


async def periodic_check(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Periodic job to check for appointments"""
    logger.info("Starting periodic appointment check...")

    notified_state["last_check_time"] = datetime.now(timezone.utc)
    notified_state["last_notification_sent"] = False
    result = await check_appointments()

    is_error = bool(result.get('error')) or bool(result.get('cloudflare_blocked'))

    if is_error:
        notified_state['consecutive_errors'] += 1
        notified_state['last_available'] = False
        notified_state['last_slots_found'] = False
        notified_state['last_slots_outside_filter'] = False

        if result.get('cloudflare_blocked'):
            error_text = (
                f"🚫 {BOT_LABEL} — Cloudflare block detected\n"
                f"Blocked IP: {result.get('blocked_ip', 'unknown')}\n"
                f"Consecutive errors: {notified_state['consecutive_errors']}/{MAX_CONSECUTIVE_ERRORS}"
            )
        else:
            error_text = (
                f"❌ {BOT_LABEL} — check failed\n"
                f"Error: {result.get('error')}\n"
                f"Consecutive errors: {notified_state['consecutive_errors']}/{MAX_CONSECUTIVE_ERRORS}"
            )

        logger.warning("Periodic check failed: %s", result.get('error') or 'cloudflare_blocked')
        await _notify_error(context, error_text)

        if STOP_ON_CLOUDFLARE_BLOCK and result.get('cloudflare_blocked'):
            stop_text = (
                f"⛔ {BOT_LABEL} stopped due to Cloudflare block.\n"
                f"Blocked IP: {result.get('blocked_ip', 'unknown')}\n"
                "Retrying is unlikely to help until the IP/proxy changes."
            )
            await _notify_fatal_error(stop_text, context=context)
            logger.error("Stopping bot due to Cloudflare block.")
            sys.exit(0)

        if STOP_ON_NON_TRANSIENT_SCRAPER_ERROR and _is_non_transient_scraper_error(result.get('error')):
            stop_text = (
                f"⛔ {BOT_LABEL} stopped due to non-transient scraper error:\n"
                f"{result.get('error')}\n"
                "This usually means the booking URL/domain is invalid or changed."
            )
            await _notify_error(context, stop_text)
            logger.error("Stopping bot due to non-transient scraper error.")
            sys.exit(0)

        if notified_state['consecutive_errors'] >= MAX_CONSECUTIVE_ERRORS:
            stop_text = (
                f"⛔ {BOT_LABEL} is stopping after {MAX_CONSECUTIVE_ERRORS} consecutive errors.\n"
                "Please check the server and restart manually."
            )
            await _notify_error(context, stop_text)
            logger.error("Too many consecutive errors (%s), stopping.", MAX_CONSECUTIVE_ERRORS)
            sys.exit(0)
    elif result['available']:
        notified_state['last_slots_outside_filter'] = False
        slots_by_date = result.get('slots_by_date') or {}
        max_date = _notify_max_date()
        if max_date is not None:
            slots_by_date = filter_slots_by_max_date(slots_by_date, max_date)

        if max_date is not None and not slots_by_date:
            logger.info(
                "Available slots found, but none are within notification range (<= %s).",
                max_date.strftime("%d.%m.%Y"),
            )
            notified_state['last_available'] = False
            notified_state['last_slots_found'] = False
            notified_state['last_slots_outside_filter'] = True
        else:
            notified_state['consecutive_errors'] = 0
            notified_state['last_slots_found'] = True
            current_hints = build_slot_keys(slots_by_date, [])
            known_hints = load_known_hints()
            new_hints = get_new_hints(current_hints, known_hints)

            if new_hints:
                # Store the latest full set when new hints appear.
                save_known_hints(current_hints, slots_by_date=slots_by_date)
                message = f"✅ AVAILABLE! {result['message']}\n\nNew slots:\n"

                grouped_block = _format_slots_by_date_for_message(slots_by_date, new_hints)
                if grouped_block:
                    message += grouped_block
                message += f"\n🔗 Check here: {APPOINTMENT_LINK}"
                notified_state['last_available'] = True
                notified_state['last_notification_sent'] = True
                if CHAT_ID:
                    try:
                        await context.bot.send_message(chat_id=CHAT_ID, text=message)
                    except Exception as e:
                        logger.error(f"Failed to send message: {e}")
            else:
                logger.info("Appointments found but no new hints since last saved check.")
                notified_state['last_available'] = True
    else:
        logger.info(f"No appointments available: {result['message']}")
        notified_state['consecutive_errors'] = 0
        notified_state['last_available'] = False
        notified_state['last_slots_found'] = False
        notified_state['last_slots_outside_filter'] = False

    # Random delay before the next check
    next_interval = random.randint(MIN_INTERVAL, MAX_INTERVAL)
    from datetime import timedelta
    next_check_time = datetime.now(timezone.utc) + timedelta(seconds=next_interval)
    notified_state["next_check_time"] = next_check_time
    logger.info(f"Next check in {next_interval // 60} min {next_interval % 60} sec.")
    context.job_queue.run_once(periodic_check, when=next_interval)


async def main() -> None:
    """Start the bot"""
    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set in .env file")
        return
    
    if not CHAT_ID:
        logger.error("TELEGRAM_CHAT_ID not set in .env file")
        return
    
    # Create the Application
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("status", status))
    application.add_error_handler(_handle_application_error)

    # Schedule the first periodic check after a short delay to ensure the
    # scheduler has fully started (avoids APScheduler misfire on when=0).
    application.job_queue.run_once(periodic_check, when=10)

    # Start the bot
    logger.info("Starting %s...", BOT_LABEL)
    logger.info("Periodic notifications are sent only when appointments are available.")

    await application.initialize()
    await application.start()
    await application.updater.start_polling()

    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    finally:
        await application.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as exc:
        logger.exception("Bot terminated with unhandled exception: %s", exc)
        if _should_restart_on_exception(exc):
            logger.error("Transient failure: exiting with code 1 to allow systemd restart.")
            sys.exit(1)

        try:
            asyncio.run(_notify_fatal_error(
                (
                    f"⛔ {BOT_LABEL} stopped due to non-transient startup/runtime error:\n"
                    f"{type(exc).__name__}: {exc}"
                )
            ))
        except Exception as notify_exc:
            logger.error("Failed while sending fatal shutdown notification: %s", notify_exc)

        logger.error("Non-transient failure: exiting with code 0 to avoid restart loop.")
        sys.exit(0)
