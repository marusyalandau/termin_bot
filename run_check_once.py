"""Run a single appointment check and send one Telegram message.

Designed for cron usage (no long-running polling bot).
"""

import asyncio
import logging
import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from telegram import Bot

from scraper import check_appointments
from hints_state import (
    load_known_hints,
    save_known_hints,
    get_new_hints,
    build_slot_keys,
    parse_ddmmyyyy,
    filter_slots_by_max_date,
)


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def _truthy(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


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


def _select_new_slots_by_date(slots_by_date: dict[str, list[str]], new_keys: set[str]) -> dict[str, list[str]]:
    selected: dict[str, list[str]] = {}
    for date in sorted(slots_by_date):
        times = [
            slot_time
            for slot_time in slots_by_date[date]
            if f"{date}|{slot_time}" in new_keys
        ]
        if times or f"{date}|" in new_keys:
            selected[date] = sorted(set(times))
    return selected


def build_message(result: dict) -> str:
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    bot_label = os.getenv("BOT_LABEL", "City X Termincheck")
    appointment_link = os.getenv("APPOINTMENT_LINK", "https://example.com/appointments")

    if result.get("cloudflare_blocked"):
        ip = result.get("blocked_ip", "unbekannt")
        return (
            f"🚫 {bot_label} - Cloudflare blockiert\n"
            f"Zeit: {now_utc}\n"
            f"IP: {ip}\n"
            "Status: Diese IP wurde von Cloudflare geblockt.\n"
            "Lösung: Anderen Server / Self-hosted Runner verwenden."
        )

    if result.get("error"):
        return (
            f"❌ {bot_label} Fehler\n"
            f"Zeit: {now_utc}\n"
            f"Fehler: {result['error']}"
        )

    if result.get("available"):
        slots = result.get("slots") or []
        slots_by_date = result.get("slots_by_date") or {}
        lines = [
            f"✅ {bot_label}",
            f"Zeit: {now_utc}",
            "Status: Termine moeglich verfuegbar!",
        ]
        if slots_by_date:
            lines.append("Neue Slots nach Datum:")
            for date in sorted(slots_by_date):
                lines.append(f"- {date}")
        elif slots:
            lines.append("Gefundene Hinweise:")
            lines.extend([f"- {slot}" for slot in slots])
        lines.append(f"Link: {appointment_link}")
        return "\n".join(lines)

    return (
        f"ℹ️ {bot_label}\n"
        f"Zeit: {now_utc}\n"
        "Status: Keine freien Termine gefunden."
    )


async def main() -> int:
    load_dotenv()

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    send_no_appointment_message = _truthy(
        os.getenv("SEND_NO_APPOINTMENT_MESSAGE"), default=False
    )

    if not token or not chat_id:
        logger.error("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID")
        return 2

    result = await check_appointments()

    if result.get("available"):
        slots_by_date = result.get("slots_by_date") or {}
        max_date = _notify_max_date()
        if max_date is not None:
            slots_by_date = filter_slots_by_max_date(slots_by_date, max_date)

        if max_date is not None and not slots_by_date:
            logger.info(
                "Available slots found, but none are within notification range (<= %s).",
                max_date.strftime("%d.%m.%Y"),
            )
            result["available"] = False
            result["slots"] = []
            result["slots_by_date"] = {}
            result["message"] = "No appointments in configured date range"
        else:
            current_hints = build_slot_keys(slots_by_date, [])
            known_hints = load_known_hints()
            new_hints = get_new_hints(current_hints, known_hints)

            if new_hints:
                # Persist current hints once genuinely new entries appear.
                save_known_hints(current_hints, slots_by_date=slots_by_date)
                result["slots_by_date"] = _select_new_slots_by_date(slots_by_date, new_hints)
                result["slots"] = sorted(new_hints)
                result["message"] = "New appointments detected!"
            else:
                logger.info("Appointments found but no new hints since last saved check.")
                result["available"] = False
                result["slots"] = []
                result["slots_by_date"] = {}
                result["message"] = "No new appointments since last check"

    if (not result.get("available")) and (not send_no_appointment_message):
        logger.info("No appointments found or check failed; SEND_NO_APPOINTMENT_MESSAGE is false, skipping message.")
        return 0

    message = build_message(result)

    bot = Bot(token=token)
    await bot.send_message(chat_id=chat_id, text=message)

    logger.info("Message sent successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
