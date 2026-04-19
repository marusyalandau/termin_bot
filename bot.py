"""Telegram bot for checking City X appointments."""

import os
import logging
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from scraper import check_appointments
from hints_state import load_known_hints, save_known_hints, get_new_hints, build_slot_keys

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    filename="bot.log"
)
logger = logging.getLogger(__name__)


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

# State for status
notified_state = {
    "last_available": False,
    "last_check_time": None,
    "next_check_time": None,
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
    last_check_str = last_check.strftime('%Y-%m-%d %H:%M:%S') if last_check else 'Never'
    next_check_str = next_check.strftime('%Y-%m-%d %H:%M:%S') if next_check else 'Unknown'
    found = 'Yes' if notified_state['last_available'] else 'No'
    message = (
        "📊 Bot Status\n\n"
        f"Last check: {last_check_str}\n"
        f"Next check: {next_check_str}\n"
        f"Appointment found: {found}\n\n"
        "The bot checks automatically at random intervals (26–34 min by default)."
    )
    await update.message.reply_text(message)


async def periodic_check(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Periodic job to check for appointments"""
    logger.info("Starting periodic appointment check...")

    notified_state["last_check_time"] = datetime.now()
    result = await check_appointments()

    if result['error']:
        logger.warning("Periodic check failed: %s", result['error'])
        notified_state['last_available'] = False
    elif result['available']:
        slots_by_date = result.get('slots_by_date') or {}
        current_hints = build_slot_keys(slots_by_date, result.get('slots') or [])
        known_hints = load_known_hints()
        new_hints = get_new_hints(current_hints, known_hints)

        if new_hints:
            # Store the latest full set when new hints appear.
            save_known_hints(current_hints, slots_by_date=slots_by_date)
            message = f"✅ AVAILABLE! {result['message']}\n\nNew slots:\n"

            grouped_block = _format_slots_by_date_for_message(slots_by_date, new_hints)
            if grouped_block:
                message += grouped_block
            else:
                # Fallback path for unstructured slot values.
                for slot in sorted(new_hints):
                    message += f"  • {slot}\n"
            message += f"\n🔗 Check here: {APPOINTMENT_LINK}"
            notified_state['last_available'] = True
            if CHAT_ID:
                try:
                    await context.bot.send_message(chat_id=CHAT_ID, text=message)
                except Exception as e:
                    logger.error(f"Failed to send message: {e}")
        else:
            logger.info("Appointments found but no new hints since last saved check.")
            notified_state['last_available'] = False
    else:
        logger.info(f"No appointments available: {result['message']}")
        notified_state['last_available'] = False

    # Random delay before the next check
    next_interval = random.randint(MIN_INTERVAL, MAX_INTERVAL)
    from datetime import timedelta
    next_check_time = datetime.now() + timedelta(seconds=next_interval)
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

    # Schedule the first periodic check immediately
    application.job_queue.run_once(periodic_check, when=0)

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
    asyncio.run(main())
