import asyncio
import logging
from datetime import datetime
from typing import List, Dict

from supabase import create_client

logger = logging.getLogger(__name__)


async def fetch_birthdays(supabase_url: str, supabase_key: str) -> List[Dict]:

    client = create_client(supabase_url, supabase_key)

    # This is a simple fetch. For production, use pagination and error handling.
    resp = client.table("Cumples").select("id,nombre,cumple").execute()
    if resp.error:
        logger.error("Supabase error: %s", resp.error)
        return []
    return resp.data or []


def is_today(date_str: str) -> bool:

    dt = parse_date(date_str)
    if not dt:
        return False
    now = datetime.now()
    return dt.month == now.month and dt.day == now.day


def parse_date(date_str: str) -> datetime | None:
    if not date_str:
        return None
    # If it's already a datetime, return it
    if isinstance(date_str, datetime):
        return date_str

    s = str(date_str).strip()
    # Remove timezone Z suffix for simpler parsing
    if s.endswith("Z"):
        s = s[:-1]

    # Try fromisoformat first (handles YYYY-MM-DD and YYYY-MM-DDTHH:MM:SS)
    try:
        return datetime.fromisoformat(s)
    except Exception:
        pass

    # Try several common formats (year-first and day-first)
    fmts = [
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%m/%d/%Y",
    ]
    for f in fmts:
        try:
            return datetime.strptime(s, f)
        except Exception:
            continue

    # Last resort: try extracting digits and attempt Y-M-D or D-M-Y
    parts = [p for p in s.replace("T", " ").replace("/", "-").split() if any(c.isdigit() for c in p)]
    if parts:
        p = parts[0]
        segs = p.split("-")
        if len(segs) == 3:
            a, b, c = segs
            # Heuristic: if first segment has 4 digits assume Y-M-D
            if len(a) == 4:
                try:
                    return datetime(int(a), int(b), int(c))
                except Exception:
                    pass
            else:
                # assume D-M-Y
                try:
                    return datetime(int(c), int(b), int(a))
                except Exception:
                    pass

    return None


async def birthday_job(application, config):

    supabase_url = config.SUPABASE_URL
    supabase_key = config.SUPABASE_KEY
    chat_id = config.BIRTHDAY_CHAT_ID

    if not (supabase_url and supabase_key):
        logger.error("Supabase config not set; skipping birthday job.")
        return

    # fetch_birthdays_sync is a blocking function; run it in the default executor
    users = await asyncio.get_event_loop().run_in_executor(None, fetch_birthdays_sync, supabase_url, supabase_key)

    # Normalize date field extraction to handle different column names / casing
    def get_date_field(u: dict):
        for k in ("cumple", "Cumple", "cumple_date", "fecha", "Fecha", "birthday", "Birthday"):
            if k in u and u.get(k):
                return u.get(k)
        # fallback: try any key that looks like a date
        for v in u.values():
            if isinstance(v, str) and any(ch.isdigit() for ch in v):
                return v
        return None

    def get_name_field(u: dict):
        for k in ("nombre", "Nombre", "name", "Name"):
            if k in u and u.get(k):
                return u.get(k)
        # fallback to id
        return u.get("id")

    todays = [u for u in users if get_date_field(u) and is_today(get_date_field(u))]

    if todays:
        names = ", ".join(str(get_name_field(u)) for u in todays)
        message = f"Hoy cumple años: {names}"
    else:
        message = "Hoy nadie cumple años"

    if chat_id:
        try:
            await application.bot.send_message(chat_id=int(chat_id), text=message)
            logger.info("Sent birthday message: %s", message)
        except Exception as e:
            logger.exception("Failed to send birthday message: %s", e)
    else:
        logger.info("Birthday message (not sent): %s", message)


def fetch_birthdays_sync(supabase_url: str, supabase_key: str) -> List[Dict]:
    try:
        client = create_client(supabase_url, supabase_key)
        resp = client.table("Cumples").select("id,nombre,cumple").execute()
        if getattr(resp, "error", None):
            logger.error("Supabase returned error: %s", resp.error)
            return []
        return resp.data or []
    except Exception as e:
        # Catch PostgREST / network / auth errors and return empty list so the
        # scheduled job / command won't crash the whole bot.
        logger.error("Failed to fetch birthdays from Supabase: %s", e)
        return []


def get_birthday_message_sync(supabase_url: str, supabase_key: str) -> str:

    users = fetch_birthdays_sync(supabase_url, supabase_key)

    def get_date_field(u: dict):
        for k in ("cumple", "Cumple", "cumple_date", "fecha", "Fecha", "birthday", "Birthday"):
            if k in u and u.get(k):
                return u.get(k)
        for v in u.values():
            if isinstance(v, str) and any(ch.isdigit() for ch in v):
                return v
        return None

    def get_name_field(u: dict):
        for k in ("nombre", "Nombre", "name", "Name"):
            if k in u and u.get(k):
                return u.get(k)
        return u.get("id")

    todays = [u for u in users if get_date_field(u) and is_today(get_date_field(u))]
    if todays:
        names = ", ".join(str(get_name_field(u)) for u in todays)
        return f"Hoy cumple años: {names}. Muchas felicidades!"
    return "Hoy nadie cumple años"


def get_next_birthday_sync(supabase_url: str, supabase_key: str) -> Dict:
    """Return the next upcoming birthday as a dict with keys: name, date, days_until.

    If multiple people share the same next date, returns the first found and include others in 'others' list.
    """
    users = fetch_birthdays_sync(supabase_url, supabase_key)
    today = datetime.now().date()

    def next_occurrence(dt: datetime) -> datetime.date:
        # Compute the next occurrence using only month and day (ignore birth year).
        # Use current year as base; if that date is past, use next year.
        # Handle Feb 29 by falling back to Feb 28 on non-leap years.
        try:
            target = datetime(today.year, dt.month, dt.day).date()
        except ValueError:
            # Likely Feb 29 on a non-leap current year -> fallback to Feb 28
            if dt.month == 2 and dt.day == 29:
                try:
                    target = datetime(today.year, 2, 28).date()
                except Exception:
                    return None
            else:
                return None

        if target < today:
            # use next year
            try:
                return datetime(today.year + 1, dt.month, dt.day).date()
            except ValueError:
                # handle Feb 29 -> fallback to Feb 28 next year as well
                if dt.month == 2 and dt.day == 29:
                    try:
                        return datetime(today.year + 1, 2, 28).date()
                    except Exception:
                        return None
                return None
        return target

    candidates = []
    for u in users:
        date_str = None
        for k in ("cumple", "Cumple", "cumple_date", "fecha", "Fecha", "birthday", "Birthday"):
            if k in u and u.get(k):
                date_str = u.get(k)
                break
        if not date_str:
            # try any value
            for v in u.values():
                if isinstance(v, str) and any(ch.isdigit() for ch in v):
                    date_str = v
                    break
        if not date_str:
            continue
        dt = parse_date(date_str)
        if not dt:
            continue
        occ = next_occurrence(dt)
        if not occ:
            continue
        days = (occ - today).days
        candidates.append((days, u, occ))

    if not candidates:
        return {"found": False}

    candidates.sort(key=lambda x: x[0])
    days, user, occ = candidates[0]
    name = None
    for k in ("nombre", "Nombre", "name", "Name"):
        if k in user and user.get(k):
            name = user.get(k)
            break
    if not name:
        name = user.get("id")

    # find others with same occ
    others = [u for d, u, o in candidates if o == occ and u is not user]

    return {
        "found": True,
        "name": name,
        "date": occ.isoformat(),
        "days_until": days,
        "others": [ (u.get("nombre") or u.get("id")) for u in others ],
    }

