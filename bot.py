"""
Telegram bot for checking Halle Einbürgerungsbehörde appointments
"""

import os
import logging
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from scraper import check_appointments

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "3600"))  # Default: 1 hour

# Dictionary to track if user has already been notified (to avoid spam)
notified_state = {"last_available": False}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start command handler"""
    message = """
🤖 Halle Einbürgerungsbehörde Appointment Bot

Available commands:
/start - Show this message
/check - Check appointments now
/status - Show bot status
/stop - Stop the bot

This bot checks for available appointment slots for 'Staatsangehörigkeitsangelegenheiten' 
and notifies you when slots become available.
    """
    await update.message.reply_text(message)


async def check_now(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Command to check appointments immediately"""
    await update.message.reply_text("⏳ Checking for available appointments...")
    
    result = await check_appointments()
    
    if result['error']:
        response = f"❌ Error: {result['error']}"
    elif result['available']:
        response = f"✅ {result['message']}\n\nAvailable slots:\n"
        for slot in result['slots']:
            response += f"  • {slot}\n"
    else:
        response = f"❌ {result['message']}"
    
    await update.message.reply_text(response)


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show bot status"""
    message = f"""
📊 Bot Status

Last check: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Check interval: {CHECK_INTERVAL} seconds ({CHECK_INTERVAL // 60} minutes)
Appointment found: {'Yes' if notified_state['last_available'] else 'No'}

The bot will automatically check for appointments every {CHECK_INTERVAL // 60} minutes.
    """
    await update.message.reply_text(message)


async def periodic_check(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Periodic job to check for appointments"""
    logger.info("Starting periodic appointment check...")
    
    result = await check_appointments()
    
    message = None
    
    if result['error']:
        message = f"❌ Error during check: {result['error']}"
    elif result['available']:
        message = f"✅ AVAILABLE! {result['message']}\n\nSlots:\n"
        for slot in result['slots']:
            message += f"  • {slot}\n"
        message += f"\n🔗 Check here: https://halle.de/serviceportal/online-terminvergabe/online-terminvereinbarung-einbuergerungsbehoerde-standesamt"
        notified_state['last_available'] = True
    else:
        # Only log, don't send message every time
        logger.info(f"No appointments available: {result['message']}")
        if notified_state['last_available']:
            message = "😢 No more appointments available"
            notified_state['last_available'] = False
    
    if message and CHAT_ID:
        try:
            await context.bot.send_message(chat_id=CHAT_ID, text=message)
        except Exception as e:
            logger.error(f"Failed to send message: {e}")


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
    application.add_handler(CommandHandler("check", check_now))
    application.add_handler(CommandHandler("status", status))
    
    # Add periodic job for checking appointments
    application.job_queue.run_repeating(
        periodic_check,
        interval=CHECK_INTERVAL,
        first=10  # Run first check after 10 seconds
    )
    
    # Start the bot
    logger.info("Starting Halle Appointment Bot...")
    logger.info(f"Check interval: {CHECK_INTERVAL} seconds")
    
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
