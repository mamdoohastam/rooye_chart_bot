
from flask import Flask, request
import requests
import os
import re
import psycopg
from datetime import datetime
from zoneinfo import ZoneInfo
import ccxt

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")

CHANNEL_URL = "https://t.me/rooye_chart"
GROUP_URL = "https://t.me/rooye_chart_gap"

# =========================================================
# صرافی‌ها
# =========================================================

EXCHANGES = {
    "nobitex": {
        "name": "نوبیتکس",
        "ccxt_id": "nobitex",
    },
    "tabdeal": {
        "name": "تبدیل",
        "ccxt_id": "tabdeal",
    },
    "bitpin": {
        "name": "بیت‌پین",
        "ccxt_id": "bitpin",
    },
    "abantether": {
        "name": "آبان‌تتر",
        "ccxt_id": "abantether",
    },
}

EXCHANGE_ALIASES = {
    "نوبیتکس": "nobitex",
    "نوبی تکس": "nobitex",
    "نوبی‌تکس": "nobitex",
    "nobitex": "nobitex",

    "تبدیل": "tabdeal",
    "tabdeal": "tabdeal",

    "بیت پین": "bitpin",
    "بیت‌پین": "bitpin",
    "bitpin": "bitpin",

    "آبان تتر": "abantether",
    "آبان‌تتر": "abantether",
    "آبانتتر": "abantether",
    "abantether": "abantether",
}

_exchange_clients = {}

# =========================================================
# نام‌های فارسی ارزها
# =========================================================

ALIASES = {
    "تتر": "USDT",
    "دلار": "USDT",

    "بیت کوین": "BTC",
    "بیتکوین": "BTC",
    "بیت‌کوین": "BTC",

    "اتریوم": "ETH",
    "سولانا": "SOL",
    "ترون": "TRX",

    "دوج": "DOGE",
    "دوج کوین": "DOGE",
    "دوج‌کوین": "DOGE",

    "ریپل": "XRP",

    "بی ان بی": "BNB",
    "بی‌ان‌بی": "BNB",

    "تون": "TON",
    "تون کوین": "TON",

    "کاردانو": "ADA",
    "شیبا": "SHIB",
    "پپه": "PEPE",
    "آپتوس": "APT",
    "نات": "NOT",
    "نات کوین": "NOT",

    "چین لینک": "LINK",
    "چین‌لینک": "LINK",

    "پولکادات": "DOT",
    "آوالانچ": "AVAX",

    "لایت کوین": "LTC",
    "لایت‌کوین": "LTC",

    "لیسک": "LSK",
    "فت": "FET",

    "آربیتروم": "ARB",
    "آپتیمیسم": "OP",
    "سویی": "SUI",
    "نیر": "NEAR",
    "اینجکتیو": "INJ",
    "اوندو": "ONDO",
    "مانترا": "OM",
    "استکس": "STX",
    "فایل کوین": "FIL",
    "گالا": "GALA",
    "سندباکس": "SAND",
    "مانا": "MANA",
    "یونی سواپ": "UNI",
    "یونی‌سواپ": "UNI",
    "آوه": "AAVE",
    "میکر": "MKR",
    "لیدو": "LDO",
    "پنکیک سواپ": "CAKE",
    "پنکیک‌سواپ": "CAKE",
    "کازماس": "ATOM",
    "هدرا": "HBAR",
    "استلار": "XLM",
    "الگوراند": "ALGO",
    "تزوس": "XTZ",
    "کاسپا": "KAS",
    "رندر": "RENDER",
    "رندر توکن": "RENDER",
    "ورلد کوین": "WLD",
    "بیت تنسور": "TAO",
    "بیتنسر": "TAO",
    "پایت": "PYTH",
    "جیتو": "JTO",
    "جاپیتر": "JUP",
    "سلستیا": "TIA",
    "مانتا": "MANTA",
    "پندل": "PENDLE",
    "تورچین": "RUNE",
    "سینتتیکس": "SNX",
    "فلوکی": "FLOKI",
    "بونک": "BONK",
    "داگز": "DOGS",
    "همستر": "HMSTR",
    "وتور توکن": "VTHO",
    "تراست والت توکن": "TWT",
    "توکو توکن": "TKO",
    "استارک نت": "STRK",
    "استارک‌نت": "STRK",
    "بایکو": "BICO",
    "ولوت": "VELVET",
    "هیما": "HEI",
}

DISPLAY_NAMES = {
    "BTC": "بیت‌کوین",
    "ETH": "اتریوم",
    "SOL": "سولانا",
    "TRX": "ترون",
    "DOGE": "دوج‌کوین",
    "XRP": "ریپل",
    "BNB": "BNB",
    "TON": "TON",
    "ADA": "کاردانو",
    "SHIB": "شیبا",
    "PEPE": "PEPE",
    "APT": "APT",
    "NOT": "NOT",
    "LINK": "چین‌لینک",
    "DOT": "پولکادات",
    "AVAX": "آوالانچ",
    "LTC": "لایت‌کوین",
    "USDT": "تتر",
}

# =========================================================
# دیتابیس PostgreSQL / Supabase
# =========================================================

def get_db_connection():
    database_url = os.environ.get("DATABASE_URL")

    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured")

    return psycopg.connect(database_url)


def init_database():
    with get_db_connection() as connection:
        connection.execute("SELECT 1")


init_database()


# =========================================================
# ابزارهای عمومی
# =========================================================

def normalize_text(text):
    text = (text or "").strip()
    text = text.replace("ي", "ی")
    text = text.replace("ى", "ی")
    text = text.replace("ك", "ک")
    text = text.replace("@", "")
    text = text.replace("$", "")
    return text.strip()


def send_message(
    chat_id,
    text,
    reply_to_message_id=None,
    reply_markup=None
):
    payload = {
        "chat_id": chat_id,
        "text": text,
    }

    if reply_markup is not None:
        payload["reply_markup"] = reply_markup

    if reply_to_message_id is not None:
        payload["reply_parameters"] = {
            "message_id": reply_to_message_id
        }

    try:
        response = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json=payload,
            timeout=10,
        )

        print(
            "SEND:",
            response.status_code,
            response.text[:300]
        )

        return response.ok

    except Exception as e:
        print("SEND ERROR:", e)
        return False


def answer_callback(callback_id, text=None):
    payload = {
        "callback_query_id": callback_id
    }

    if text:
        payload["text"] = text

    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery",
            json=payload,
            timeout=10,
        )
    except Exception as e:
        print("CALLBACK ERROR:", e)


def copy_analysis_message(
    target_chat_id,
    source_chat_id,
    source_message_id
):
    payload = {
        "chat_id": target_chat_id,
        "from_chat_id": source_chat_id,
        "message_id": source_message_id,
    }

    try:
        response = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/copyMessage",
            json=payload,
            timeout=10,
        )

        print(
            "COPY:",
            response.status_code,
            response.text[:500]
        )

        return response.ok

    except Exception as e:
        print("COPY ERROR:", e)
        return False


# =========================================================
# ثبت و استخراج هشتگ تحلیل
# =========================================================

def extract_analysis_symbols(caption):
    hashtags = re.findall(
        r"#([A-Za-z0-9_]+)",
        caption or ""
    )

    symbols = set()

    for hashtag in hashtags:
        symbol = hashtag.upper().strip()

        if re.fullmatch(
            r"[A-Z0-9]{2,15}",
            symbol
        ):
            symbols.add(symbol)

    return list(symbols)


def save_analysis(
    chat_id,
    message_id,
    symbol,
    message_date,
    photo_file_id=None
):
    date_text = datetime.fromtimestamp(
        message_date,
        tz=ZoneInfo("Asia/Tehran")
    ).strftime("%Y-%m-%d")

    with get_db_connection() as connection:
        connection.execute(
            """
            INSERT INTO analyses
            (
                chat_id,
                message_id,
                symbol,
                message_date,
                date_text,
                photo_file_id
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                chat_id,
                message_id,
                symbol,
                message_date,
                date_text,
                photo_file_id,
            )
        )

    print(
        f"ANALYSIS SAVED: {symbol} "
        f"chat={chat_id} message={message_id}"
    )


# =========================================================
# آخرین تحلیل
# =========================================================

def get_latest_analysis_info(
    symbol,
    chat_id=None
):
    symbol = (symbol or "").strip().upper()

    with get_db_connection() as connection:

        if chat_id is None:
            row = connection.execute(
                """
                SELECT
                    chat_id,
                    message_id,
                    message_date
                FROM analyses
                WHERE UPPER(TRIM(symbol)) = %s
                ORDER BY message_date DESC, id DESC
                LIMIT 1
                """,
                (symbol,)
            ).fetchone()

        else:
            row = connection.execute(
                """
                SELECT
                    chat_id,
                    message_id,
                    message_date
                FROM analyses
                WHERE chat_id = %s
                  AND UPPER(TRIM(symbol)) = %s
                ORDER BY message_date DESC, id DESC
                LIMIT 1
                """,
                (
                    chat_id,
                    symbol
                )
            ).fetchone()

    return row


# =========================================================
# تحلیل‌های امروز
# =========================================================

def get_today_analyses(chat_id=None):

    today = datetime.now(
        ZoneInfo("Asia/Tehran")
    ).strftime("%Y-%m-%d")

    with get_db_connection() as connection:

        if chat_id is None:
            rows = connection.execute(
                """
                SELECT
                    symbol,
                    message_id,
                    chat_id,
                    message_date
                FROM analyses
                WHERE date_text = %s
                ORDER BY message_date ASC, id ASC
                """,
                (today,)
            ).fetchall()

        else:
            rows = connection.execute(
                """
                SELECT
                    symbol,
                    message_id,
                    chat_id,
                    message_date
                FROM analyses
                WHERE chat_id = %s
                  AND date_text = %s
                ORDER BY message_date ASC, id ASC
                """,
                (
                    chat_id,
                    today
                )
            ).fetchall()

    return rows


# =========================================================
# درخواست تحلیل
# =========================================================

def extract_analysis_request(text):

    normalized = normalize_text(text)

    if normalized in {
        "تحلیل های امروز",
        "تحلیل‌های امروز",
        "تحلیل امروز",
        "تحلیلهای امروز",

