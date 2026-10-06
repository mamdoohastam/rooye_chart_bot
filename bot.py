from flask import Flask, request
import requests
import os
import re
import psycopg
from datetime import datetime, timedelta
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

    "ourbit": {
        "name": "Ourbit",
        "ccxt_id": None,
    },

    "lbank": {
        "name": "LBank",
        "ccxt_id": "lbank",
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

    "ourbit": "ourbit",
    "lbank": "lbank",
    "ال بانک": "lbank",
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


# =========================================================
# ثبت کلیک‌های استعلام قیمت
# =========================================================

def get_click_user_info(callback):
    user = callback.get("from", {}) or {}
    return {
        "user_id": user.get("id"),
        "username": user.get("username"),
        "first_name": user.get("first_name"),
        "last_name": user.get("last_name"),
    }


def log_price_click(
    callback,
    asset,
    exchange_id,
    allowed=True,
    block_reason=None
):
    """ثبت کلیک قیمت برای شناسایی کاربر و بررسی رفتار کلیک‌ها."""
    try:
        user = get_click_user_info(callback)
        message = callback.get("message", {}) or {}
        chat = message.get("chat", {}) or {}

        with get_db_connection() as connection:
            connection.execute(
                """
                INSERT INTO price_click_logs
                (
                    user_id, username, first_name, last_name,
                    chat_id, chat_type, asset, exchange_id,
                    allowed, block_reason
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    user.get("user_id"),
                    user.get("username"),
                    user.get("first_name"),
                    user.get("last_name"),
                    chat.get("id"),
                    chat.get("type"),
                    asset,
                    exchange_id,
                    allowed,
                    block_reason,
                )
            )
    except Exception as e:
        # خطای ثبت لاگ نباید عملکرد اصلی ربات را متوقف کند.
        print("PRICE CLICK LOG ERROR:", e)


def init_database():
    # تحلیل‌های دارای #WATCHLIST را جداگانه نگه می‌داریم.
    with get_db_connection() as connection:
        connection.execute(
            """
            ALTER TABLE analyses
            ADD COLUMN IF NOT EXISTS watchlist BOOLEAN NOT NULL DEFAULT FALSE
            """
        )
        connection.commit()
    with get_db_connection() as connection:
        connection.execute("SELECT 1")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS price_click_logs (
                id BIGSERIAL PRIMARY KEY,
                clicked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                user_id BIGINT,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                chat_id BIGINT,
                chat_type TEXT,
                asset TEXT,
                exchange_id TEXT,
                allowed BOOLEAN NOT NULL DEFAULT TRUE,
                block_reason TEXT
            )
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_price_click_logs_chat_time
            ON price_click_logs (chat_id, clicked_at DESC)
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_price_click_logs_user_time
            ON price_click_logs (user_id, clicked_at DESC)
            """
        )

        # شناسه پیامِ کپی‌شده در چت مقصد را نگه می‌داریم تا Replyهای بعدی
        # به پیام واقعی داخل همان گروه/چت اشاره کنند، نه به message_id منبع.
        # این جدول فقط برای قابلیت Reply زنجیره‌ای است و اطلاعات analyses را تغییر نمی‌دهد.
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS analysis_copies (
                id BIGSERIAL PRIMARY KEY,
                source_chat_id BIGINT NOT NULL,
                source_message_id BIGINT NOT NULL,
                target_chat_id BIGINT NOT NULL,
                copied_message_id BIGINT NOT NULL,
                symbol TEXT,
                target_message_thread_id BIGINT,
                copied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )

        connection.execute(
            """
            ALTER TABLE analysis_copies
            ADD COLUMN IF NOT EXISTS target_message_thread_id BIGINT
            """
        )

        # نسخه‌های قبلی یک UNIQUE اشتباه داشتند که symbol را در کلید حساب نمی‌کرد.
        # نتیجه این بود که اگر یک پیام چند ارز داشت، رکورد یک ارز روی ارز دیگر
        # overwrite می‌شد و زنجیره Reply به هم می‌ریخت.
        connection.execute(
            """
            ALTER TABLE analysis_copies
            DROP CONSTRAINT IF EXISTS
                analysis_copies_source_chat_id_source_message_id_target_chat_id_key
            """
        )
        connection.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS
                ux_analysis_copies_source_target_symbol
            ON analysis_copies
            (source_chat_id, source_message_id, target_chat_id, symbol)
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_analysis_copies_target_symbol
            ON analysis_copies (target_chat_id, symbol, copied_at DESC)
            """
        )

        # رکوردهای نسخه خراب قبلی قابل اعتماد نیستند، چون ممکن است symbol آنها
        # به‌علت overwrite شدن متعلق به ارز دیگری باشد. فقط جدول ردیابی کپی‌ها
        # پاک می‌شود؛ جدول analyses و خود تحلیل‌ها دست‌نخورده می‌مانند.
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS bot_migrations (
                migration_key TEXT PRIMARY KEY,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        migration_key = "analysis_copies_symbol_key_v2"
        migration_row = connection.execute(
            "SELECT 1 FROM bot_migrations WHERE migration_key = %s LIMIT 1",
            (migration_key,)
        ).fetchone()
        if migration_row is None:
            connection.execute("DELETE FROM analysis_copies")
            connection.execute(
                "INSERT INTO bot_migrations (migration_key) VALUES (%s)",
                (migration_key,)
            )

        connection.commit()


init_database()


# =========================================================
# ابزارهای عمومی
# =========================================================

def gregorian_to_jalali(gy, gm, gd):
    """تبدیل تاریخ میلادی به شمسی بدون نیاز به کتابخانه جانبی."""
    g_days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    j_days_in_month = [31, 31, 31, 31, 31, 31, 30, 30, 30, 30, 30, 29]

    gy2 = gy - 1600
    gm2 = gm - 1
    gd2 = gd - 1

    g_day_no = (365 * gy2
                + (gy2 + 3) // 4
                - (gy2 + 99) // 100
                + (gy2 + 399) // 400)

    for i in range(gm2):
        g_day_no += g_days_in_month[i]
    if gm2 > 1 and ((gy % 4 == 0 and gy % 100 != 0) or (gy % 400 == 0)):
        g_day_no += 1
    g_day_no += gd2

    j_day_no = g_day_no - 79
    j_np = j_day_no // 12053
    j_day_no %= 12053

    jy = 979 + 33 * j_np + 4 * (j_day_no // 1461)
    j_day_no %= 1461

    if j_day_no >= 366:
        jy += (j_day_no - 1) // 365
        j_day_no = (j_day_no - 1) % 365

    i = 0
    while i < 11 and j_day_no >= j_days_in_month[i]:
        j_day_no -= j_days_in_month[i]
        i += 1

    jm = i + 1
    jd = j_day_no + 1
    return jy, jm, jd


PERSIAN_MONTHS = {
    1: "فروردین", 2: "اردیبهشت", 3: "خرداد",
    4: "تیر", 5: "مرداد", 6: "شهریور",
    7: "مهر", 8: "آبان", 9: "آذر",
    10: "دی", 11: "بهمن", 12: "اسفند",
}


def format_jalali_date(timestamp):
    dt = datetime.fromtimestamp(timestamp, tz=ZoneInfo("Asia/Tehran"))
    jy, jm, jd = gregorian_to_jalali(dt.year, dt.month, dt.day)
    return f"{jd} {PERSIAN_MONTHS[jm]} {jy}"


def send_analysis_date(chat_id, copied_message_id, timestamp):
    """تاریخ شمسی تحلیل را بلافاصله زیر/در Reply به خود تحلیل می‌فرستد."""
    return send_message(
        chat_id,
        f"📅 تاریخ تحلیل: {format_jalali_date(timestamp)}",
        reply_to_message_id=copied_message_id,
    )


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


LAST_COPY_ERROR = ""

def copy_analysis_message(
    target_chat_id,
    source_chat_id,
    source_message_id,
    reply_to_message_id=None,
    target_message_thread_id=None,
    return_metadata=False,
):
    """کپی تحلیل با امکان قرار دادن آن در Topic و Reply به پیام قبلی.

    حالت پیش‌فرض دقیقاً همان مقدار قبلی را برمی‌گرداند (فقط message_id)،
    بنابراین مسیر خصوصی و سایر فراخوانی‌های قدیمی تغییر رفتاری ندارند.
    در صورت return_metadata=True، علاوه بر message_id، اطلاعات Thread واقعی
    برگشتی از Telegram نیز در اختیار مسیر گروه قرار می‌گیرد.
    """
    payload = {
        "chat_id": target_chat_id,
        "from_chat_id": source_chat_id,
        "message_id": source_message_id,
    }

    if target_message_thread_id is not None:
        payload["message_thread_id"] = target_message_thread_id

    if reply_to_message_id is not None:
        payload["reply_parameters"] = {
            "message_id": reply_to_message_id
        }

    global LAST_COPY_ERROR
    LAST_COPY_ERROR = ""

    try:
        response = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/copyMessage",
            json=payload,
            timeout=10,
        )

        print(
            "COPY:",
            response.status_code,
            response.text[:700]
        )

        if not response.ok:
            LAST_COPY_ERROR = response.text[:1000]
            return None

        result = response.json().get("result", {}) or {}
        copied_message_id = result.get("message_id")

        if copied_message_id is None:
            LAST_COPY_ERROR = response.text[:1000]
            print("COPY ERROR: Telegram response has no message_id")
            return None

        metadata = {
            "message_id": copied_message_id,
            "message_thread_id": result.get("message_thread_id"),
        }

        if return_metadata:
            return metadata

        return copied_message_id

    except Exception as e:
        LAST_COPY_ERROR = str(e)
        print("COPY ERROR:", e)
        return None


def save_analysis_copy(
    source_chat_id,
    source_message_id,
    target_chat_id,
    copied_message_id,
    symbol=None,
    target_message_thread_id=None,
):
    """شناسه کپی و در صورت وجود، Topic مقصد را ثبت می‌کند."""
    try:
        with get_db_connection() as connection:
            connection.execute(
                """
                INSERT INTO analysis_copies
                (
                    source_chat_id,
                    source_message_id,
                    target_chat_id,
                    copied_message_id,
                    symbol,
                    target_message_thread_id
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (
                    source_chat_id,
                    source_message_id,
                    target_chat_id,
                    symbol
                )
                DO UPDATE SET
                    copied_message_id = EXCLUDED.copied_message_id,
                    target_message_thread_id = EXCLUDED.target_message_thread_id,
                    copied_at = NOW()
                """,
                (
                    source_chat_id,
                    source_message_id,
                    target_chat_id,
                    copied_message_id,
                    symbol,
                    target_message_thread_id,
                )
            )
            connection.commit()
    except Exception as e:
        print("ANALYSIS COPY SAVE ERROR:", e)


def get_analysis_copy_target_thread_id(
    source_chat_id,
    source_message_id,
    target_chat_id,
    symbol=None,
):
    """Thread واقعی پیام کپی‌شده قبلی را برمی‌گرداند."""
    try:
        with get_db_connection() as connection:
            row = connection.execute(
                """
                SELECT target_message_thread_id
                FROM analysis_copies
                WHERE source_chat_id = %s
                  AND source_message_id = %s
                  AND target_chat_id = %s
                  AND UPPER(TRIM(COALESCE(symbol, ''))) = %s
                ORDER BY copied_at DESC, id DESC
                LIMIT 1
                """,
                (
                    source_chat_id,
                    source_message_id,
                    target_chat_id,
                    (symbol or "").strip().upper(),
                )
            ).fetchone()
        return row[0] if row else None
    except Exception as e:
        print("ANALYSIS COPY THREAD LOOKUP ERROR:", e)
        return None


def get_latest_analysis_copy_for_symbol(
    target_chat_id,
    symbol
):
    """آخرین پیام کپی‌شده همان ارز را در چت مقصد پیدا می‌کند."""
    try:
        with get_db_connection() as connection:
            row = connection.execute(
                """
                SELECT copied_message_id
                FROM analysis_copies
                WHERE target_chat_id = %s
                  AND UPPER(TRIM(symbol)) = %s
                ORDER BY copied_at DESC, id DESC
                LIMIT 1
                """,
                (
                    target_chat_id,
                    (symbol or "").strip().upper(),
                )
            ).fetchone()

        return row[0] if row else None

    except Exception as e:
        print("LATEST ANALYSIS COPY LOOKUP ERROR:", e)
        return None


def get_analysis_copy_message_id(
    source_chat_id,
    source_message_id,
    target_chat_id,
    symbol=None
):
    """message_id واقعیِ کپی‌شده همان ارز را در چت مقصد برمی‌گرداند."""
    try:
        with get_db_connection() as connection:
            row = connection.execute(
                """
                SELECT copied_message_id
                FROM analysis_copies
                WHERE source_chat_id = %s
                  AND source_message_id = %s
                  AND target_chat_id = %s
                  AND UPPER(TRIM(COALESCE(symbol, ''))) = %s
                ORDER BY copied_at DESC, id DESC
                LIMIT 1
                """,
                (
                    source_chat_id,
                    source_message_id,
                    target_chat_id,
                    (symbol or "").strip().upper(),
                )
            ).fetchone()
        return row[0] if row else None
    except Exception as e:
        print("ANALYSIS COPY LOOKUP ERROR:", e)
        return None


# =========================================================
# ثبت و استخراج هشتگ تحلیل
# =========================================================

def extract_analysis_symbols(caption):
    hashtags = re.findall(
        r"#([A-Za-z0-9_]+)",
        caption or ""
    )

    symbols = set()
    is_watchlist = False

    for hashtag in hashtags:
        symbol = hashtag.upper().strip()

        if symbol in {
            "WATCHLIST",
            "WATCH_LIST",
            "WATCH-LIST"
        }:
            is_watchlist = True
            continue

        if re.fullmatch(
            r"[A-Z0-9]{2,15}",
            symbol
        ):
            symbols.add(symbol)

    return list(symbols), is_watchlist


def save_analysis(
    chat_id,
    message_id,
    symbol,
    message_date,
    photo_file_id=None,
    watchlist=False
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
                photo_file_id,
                watchlist
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                chat_id,
                message_id,
                symbol,
                message_date,
                date_text,
                photo_file_id,
                watchlist,
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


def get_analysis_candidates(
    symbol,
    chat_id=None,
    limit=30
):
    """تحلیل‌های اخیر را برای یافتن اولین پیام منبع معتبر برمی‌گرداند."""
    symbol = (symbol or "").strip().upper()
    with get_db_connection() as connection:
        if chat_id is None:
            rows = connection.execute(
                """
                SELECT chat_id, message_id, message_date
                FROM (
                    SELECT DISTINCT ON (chat_id, message_id)
                        chat_id, message_id, message_date, id
                    FROM analyses
                    WHERE UPPER(TRIM(symbol)) = %s
                    ORDER BY chat_id, message_id, message_date DESC, id DESC
                ) AS unique_messages
                ORDER BY message_date DESC, id DESC
                LIMIT %s
                """, (symbol, limit)
            ).fetchall()
        else:
            rows = connection.execute(
                """
                SELECT chat_id, message_id, message_date
                FROM (
                    SELECT DISTINCT ON (message_id)
                        chat_id, message_id, message_date, id
                    FROM analyses
                    WHERE chat_id = %s
                      AND UPPER(TRIM(symbol)) = %s
                    ORDER BY message_id, message_date DESC, id DESC
                ) AS unique_messages
                ORDER BY message_date DESC, id DESC
                LIMIT %s
                """, (chat_id, symbol, limit)
            ).fetchall()
    return rows


def get_latest_two_analysis_info(
    symbol,
    chat_id=None
):
    """آخرین و تحلیل قبلی یک ارز را برای ساخت زنجیره Reply برمی‌گرداند."""
    symbol = (symbol or "").strip().upper()

    with get_db_connection() as connection:

        if chat_id is None:
            rows = connection.execute(
                """
                SELECT chat_id, message_id, message_date
                FROM (
                    SELECT DISTINCT ON (chat_id, message_id)
                        chat_id, message_id, message_date, id
                    FROM analyses
                    WHERE UPPER(TRIM(symbol)) = %s
                    ORDER BY chat_id, message_id, message_date DESC, id DESC
                ) AS unique_messages
                ORDER BY message_date DESC, id DESC
                LIMIT 2
                """,
                (symbol,)
            ).fetchall()

        else:
            rows = connection.execute(
                """
                SELECT chat_id, message_id, message_date
                FROM (
                    SELECT DISTINCT ON (message_id)
                        chat_id, message_id, message_date, id
                    FROM analyses
                    WHERE chat_id = %s
                      AND UPPER(TRIM(symbol)) = %s
                    ORDER BY message_id, message_date DESC, id DESC
                ) AS unique_messages
                ORDER BY message_date DESC, id DESC
                LIMIT 2
                """,
                (
                    chat_id,
                    symbol
                )
            ).fetchall()

    return rows


def get_analysis_chain_diagnostic(symbol, target_chat_id=None):
    """اطلاعات تشخیصی زنجیره تحلیل و mapping کپی‌ها را بدون تغییر داده‌ها برمی‌گرداند."""
    symbol = (symbol or "").strip().upper()

    with get_db_connection() as connection:
        analyses_rows = connection.execute(
            """
            SELECT chat_id, message_id, message_date, id
            FROM analyses
            WHERE UPPER(TRIM(symbol)) = %s
            ORDER BY message_date DESC, id DESC
            LIMIT 30
            """,
            (symbol,)
        ).fetchall()

        if target_chat_id is None:
            copies_rows = connection.execute(
                """
                SELECT
                    source_chat_id,
                    source_message_id,
                    target_chat_id,
                    copied_message_id,
                    symbol,
                    target_message_thread_id,
                    copied_at
                FROM analysis_copies
                WHERE UPPER(TRIM(COALESCE(symbol, ''))) = %s
                ORDER BY copied_at DESC, id DESC
                LIMIT 50
                """,
                (symbol,)
            ).fetchall()
        else:
            copies_rows = connection.execute(
                """
                SELECT
                    source_chat_id,
                    source_message_id,
                    target_chat_id,
                    copied_message_id,
                    symbol,
                    target_message_thread_id,
                    copied_at
                FROM analysis_copies
                WHERE target_chat_id = %s
                  AND UPPER(TRIM(COALESCE(symbol, ''))) = %s
                ORDER BY copied_at DESC, id DESC
                LIMIT 50
                """,
                (target_chat_id, symbol)
            ).fetchall()

    return analyses_rows, copies_rows


# =========================================================
# تحلیل‌های امروز
# =========================================================
def was_analysis_sent(user_chat_id, source_chat_id, source_message_id):
    with get_db_connection() as connection:
        row = connection.execute(
            """
            SELECT 1
            FROM sent_today_analyses
            WHERE user_chat_id = %s
              AND source_chat_id = %s
              AND source_message_id = %s
            LIMIT 1
            """,
            (
                user_chat_id,
                source_chat_id,
                source_message_id,
            )
        ).fetchone()

    return row is not None

def mark_analysis_as_sent(
    user_chat_id,
    source_chat_id,
    source_message_id
):
    with get_db_connection() as connection:
        connection.execute(
            """
            INSERT INTO sent_today_analyses
            (
                user_chat_id,
                source_chat_id,
                source_message_id
            )
            VALUES (%s, %s, %s)
            ON CONFLICT (
                user_chat_id,
                source_chat_id,
                source_message_id
            )
            DO NOTHING
            """,
            (
                user_chat_id,
                source_chat_id,
                source_message_id,
            )
        )
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


def get_analysis_range(start_date, end_date, chat_id=None):
    """تحلیل‌های ثبت‌شده در یک بازه تاریخ شمسی را برمی‌گرداند."""
    with get_db_connection() as connection:

        if chat_id is None:
            rows = connection.execute(
                """
                SELECT
                    symbol,
                    message_id,
                    chat_id,
                    message_date,
                    date_text
                FROM analyses
                WHERE date_text BETWEEN %s AND %s
                ORDER BY message_date ASC, id ASC
                """,
                (
                    start_date,
                    end_date
                )
            ).fetchall()

        else:
            rows = connection.execute(
                """
                SELECT
                    symbol,
                    message_id,
                    chat_id,
                    message_date,
                    date_text
                FROM analyses
                WHERE chat_id = %s
                  AND date_text BETWEEN %s AND %s
                ORDER BY message_date ASC, id ASC
                """,
                (
                    chat_id,
                    start_date,
                    end_date
                )
            ).fetchall()

    return rows


def get_watchlist_range(start_date, end_date, chat_id=None):
    """
    تحلیل‌هایی که با #WATCHLIST علامت خورده‌اند را در بازه مشخص برمی‌گرداند.
    """
    with get_db_connection() as connection:

        if chat_id is None:
            rows = connection.execute(
                """
                SELECT
                    symbol,
                    message_id,
                    chat_id,
                    message_date,
                    date_text
                FROM analyses
                WHERE date_text BETWEEN %s AND %s
                  AND watchlist = TRUE
                ORDER BY message_date DESC, id DESC
                """,
                (start_date, end_date)
            ).fetchall()

        else:
            rows = connection.execute(
                """
                SELECT
                    symbol,
                    message_id,
                    chat_id,
                    message_date,
                    date_text
                FROM analyses
                WHERE chat_id = %s
                  AND date_text BETWEEN %s AND %s
                  AND watchlist = TRUE
                ORDER BY message_date DESC, id DESC
                """,
                (chat_id, start_date, end_date)
            ).fetchall()

    return rows


def get_analysis_for_date(symbol, date_text, chat_id=None):
    """آخرین تحلیل یک ارز در یک تاریخ مشخص را برمی‌گرداند."""
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
                  AND date_text = %s
                ORDER BY message_date DESC, id DESC
                LIMIT 1
                """,
                (
                    symbol,
                    date_text
                )
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
                  AND date_text = %s
                ORDER BY message_date DESC, id DESC
                LIMIT 1
                """,
                (
                    chat_id,
                    symbol,
                    date_text
                )
            ).fetchone()

    return row


def get_analysis_candidates_for_date(symbol, date_text, chat_id=None):
    """همه رکوردهای یک ارز در یک تاریخ را برای یافتن پیام منبع معتبر برمی‌گرداند."""
    symbol = (symbol or "").strip().upper()
    with get_db_connection() as connection:
        if chat_id is None:
            rows = connection.execute(
                """
                SELECT chat_id, message_id, message_date
                FROM analyses
                WHERE UPPER(TRIM(symbol)) = %s
                  AND date_text = %s
                ORDER BY message_date DESC, id DESC
                """,
                (symbol, date_text)
            ).fetchall()
        else:
            rows = connection.execute(
                """
                SELECT chat_id, message_id, message_date
                FROM analyses
                WHERE chat_id = %s
                  AND UPPER(TRIM(symbol)) = %s
                  AND date_text = %s
                ORDER BY message_date DESC, id DESC
                """,
                (chat_id, symbol, date_text)
            ).fetchall()
    return rows


def get_previous_analysis_info(symbol, before_message_date, chat_id=None):
    """نزدیک‌ترین تحلیل قبلی همان ارز را قبل از یک تحلیل مشخص پیدا می‌کند."""
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
                  AND message_date < %s
                ORDER BY message_date DESC, id DESC
                LIMIT 1
                """,
                (
                    symbol,
                    before_message_date
                )
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
                  AND message_date < %s
                ORDER BY message_date DESC, id DESC
                LIMIT 1
                """,
                (
                    chat_id,
                    symbol,
                    before_message_date
                )
            ).fetchone()

    return row


# =========================================================
# درخواست تحلیل
# =========================================================

def extract_analysis_request(text):

    normalized = normalize_text(text)

    if normalized in {
        "واچ لیست",
        "واچ‌لیست",
        "واچ لیست ها",
        "واچ‌لیست‌ها",
    } or normalized.lower() in {
        "watchlist",
        "watch list",
        "watch-list",
    }:
        return "WATCHLIST"

    if normalized in {
        "تحلیل های امروز",
        "تحلیل‌های امروز",
        "تحلیل امروز",
        "تحلیلهای امروز",
        "تحلیل‌های امروزم",
    }:
        return "TODAY"

    if normalized in {
        "تحلیل های دیروز",
        "تحلیل‌های دیروز",
        "تحلیل دیروز",
        "تحلیلهای دیروز",
    }:
        return "YESTERDAY"

    if normalized in {
        "تحلیل های 7 روز اخیر",
        "تحلیل‌های 7 روز اخیر",
        "تحلیل 7 روز اخیر",
        "تحلیلهای 7 روز اخیر",
        "تحلیل های هفت روز اخیر",
        "تحلیل‌های هفت روز اخیر",
        "تحلیل هفت روز اخیر",
        "تحلیلهای هفت روز اخیر",
    }:
        return "LAST7"

    if "تحلیل" not in normalized:
        return None

    remaining = normalized.replace(
        "تحلیل",
        ""
    ).strip()

    remaining = remaining.replace(
        "های",
        ""
    ).strip()

    remaining = remaining.replace(
        "آخرین",
        ""
    ).strip()

    if remaining in ALIASES:
        return ALIASES[remaining]

    upper = remaining.upper()

    if re.fullmatch(
        r"[A-Z0-9]{2,15}",
        upper
    ):
        return upper

    return None


# =========================================================
# موتور قیمت صرافی‌ها
# =========================================================

def get_exchange_client(exchange_id):

    if exchange_id not in EXCHANGES:
        raise ValueError("صرافی نامعتبر است.")

    if exchange_id not in _exchange_clients:

        ccxt_id = EXCHANGES[
            exchange_id
        ]["ccxt_id"]

        exchange_class = getattr(
            ccxt,
            ccxt_id
        )

        _exchange_clients[
            exchange_id
        ] = exchange_class(
            {
                "enableRateLimit": True,
                "timeout": 10000,
            }
        )

    return _exchange_clients[exchange_id]


def find_exchange_market(
    exchange_id,
    asset
):
    exchange = get_exchange_client(
        exchange_id
    )

    markets = exchange.load_markets()

    asset = asset.upper()

    candidates = []

    for symbol, market in markets.items():

        if (
            market.get("base") or ""
        ).upper() != asset:
            continue

        if market.get("active") is False:
            continue

        if (
            market.get("spot") is False
            and market.get("type")
            not in (None, "spot")
        ):
            continue

        quote = (
            market.get("quote") or ""
        ).upper()

        if quote in {
            "IRT",
            "TMN",
            "IRR",
            "USDT"
        }:
            candidates.append(
                (
                    symbol,
                    quote
                )
            )

    if not candidates:
        return None, None

    priority = {
        "IRT": 0,
        "TMN": 0,
        "IRR": 1,
        "USDT": 2,
    }

    candidates.sort(
        key=lambda item:
        priority.get(
            item[1],
            99
        )
    )

    return candidates[0]


def find_irt_market(exchange):

    markets = exchange.load_markets()

    candidates = []

    for symbol, market in markets.items():

        if (
            market.get("base") or ""
        ).upper() != "USDT":
            continue

        if market.get("active") is False:
            continue

        if (
            market.get("spot") is False
            and market.get("type")
            not in (None, "spot")
        ):
            continue

        quote = (
            market.get("quote") or ""
        ).upper()

        if quote in {
            "IRT",
            "TMN",
            "IRR"
        }:
            candidates.append(
                (
                    symbol,
                    quote
                )
            )

    if not candidates:
        return None, None

    priority = {
        "IRT": 0,
        "TMN": 0,
        "IRR": 1,
    }

    candidates.sort(
        key=lambda item:
        priority.get(
            item[1],
            99
        )
    )

    return candidates[0]


def get_exchange_prices(
    exchange_id,
    asset
):

# =====================================================
# Ourbit - Public Spot API
# =====================================================
    if exchange_id == "ourbit":

        symbol = f"{asset.upper()}USDT"

        response = requests.get(
            "https://api.ourbit.com/api/v3/ticker/price",
            params={
                "symbol": symbol
            },
            timeout=10,
        )

        response.raise_for_status()

        data = response.json()

        print(
            "OURBIT RESPONSE:",
            data
        )

        if not isinstance(data, dict):
            raise LookupError(
                "پاسخ نامعتبر از Ourbit دریافت شد."
            )

        price = data.get("price")

        if price is None:
            raise LookupError(
                f"قیمت {symbol} در Ourbit پیدا نشد."
            )

        return {
            "irt_price": None,
            "usdt_price": float(price),
            "irt_symbol": None,
            "usdt_symbol": symbol,
        }


    exchange = get_exchange_client(
        exchange_id
    )

    markets = exchange.load_markets()

    asset = asset.upper()

    irt_symbol = None
    irt_quote = None
    usdt_symbol = None

# آبان‌تتر
    if exchange_id == "abantether":

        for direct_symbol in (
            f"{asset}/IRT",
            f"{asset}/IRR",
            f"{asset}/TMN"
        ):

            try:
                exchange.fetch_ticker(
                    direct_symbol
                )

                irt_symbol = direct_symbol

                irt_quote = (
                    direct_symbol
                    .split("/")[-1]
                    .upper()
                )

                break

            except Exception:
                pass

        try:
            exchange.fetch_ticker(
                f"{asset}/USDT"
            )

            usdt_symbol = (
                f"{asset}/USDT"
            )

        except Exception:
            pass

    for symbol, market in markets.items():

        if (
            market.get("base") or ""
        ).upper() != asset:
            continue

        if market.get("active") is False:
            continue

        if (
            market.get("spot") is False
            and market.get("type")
            not in (None, "spot")
        ):
            continue

        quote = (
            market.get("quote") or ""
        ).upper()

        if (
            quote in {
                "IRT",
                "TMN",
                "IRR"
            }
            and irt_symbol is None
        ):
            irt_symbol = symbol
            irt_quote = quote

        elif (
            quote == "USDT"
            and usdt_symbol is None
        ):
            usdt_symbol = symbol

    if not irt_symbol and not usdt_symbol:

        raise LookupError(
            f"بازار {asset} در "
            f"{EXCHANGES[exchange_id]['name']} "
            f"پیدا نشد."
        )

    irt_price = None

    if irt_symbol:

        ticker = exchange.fetch_ticker(
            irt_symbol
        )

        last = ticker.get("last")

        if last is not None:

            irt_price = float(last)

            if irt_quote == "IRR":
                irt_price /= 10

    usdt_price = None

    if usdt_symbol:

        ticker = exchange.fetch_ticker(
            usdt_symbol
        )

        last = ticker.get("last")

        if last is not None:
            usdt_price = float(last)

    if (
        irt_price is None
        and usdt_price is None
    ):
        raise LookupError(
            "آخرین قیمت معامله "
            "از صرافی دریافت نشد."
        )

    return {
        "irt_price": irt_price,
        "usdt_price": usdt_price,
        "irt_symbol": irt_symbol,
        "usdt_symbol": usdt_symbol,
    }


# =========================================================
# تشخیص ارز
# =========================================================

def looks_like_coin(text):

    text = normalize_text(text)

    if text in ALIASES:
        return True

    return bool(
        re.fullmatch(
            r"[A-Za-z0-9]{2,15}",
            text
        )
        or re.fullmatch(
            r"[آ-ی‌]{2,20}"
            r"(?: [آ-ی‌]{2,20})?",
            text
        )
    )


def parse_price_request(text):

    normalized = normalize_text(text)

    if not normalized:
        return None, None

    exchange_id = None
    coin_text = normalized

    aliases = sorted(
        EXCHANGE_ALIASES.items(),
        key=lambda x: len(x[0]),
        reverse=True
    )

# ارز + صرافی
    for alias, ex_id in aliases:

        if normalized == alias:
            return None, ex_id

        if normalized.endswith(
            " " + alias
        ):

            coin_text = normalized[
                :-(len(alias) + 1)
            ].strip()

            exchange_id = ex_id

            break

# صرافی + ارز
    if exchange_id is None:

        for alias, ex_id in aliases:

            prefix = alias + " "

            if normalized.startswith(prefix):

                coin_text = normalized[
                    len(prefix):
                ].strip()

                exchange_id = ex_id

                break

    if not coin_text:
        return None, exchange_id

    asset = ALIASES.get(
        coin_text,
        coin_text.upper()
    )

    if not re.fullmatch(
        r"[A-Z0-9]{2,15}",
        asset
    ):
        return None, exchange_id

    return asset, exchange_id


# =========================================================
# منوی صرافی
# =========================================================

def exchange_keyboard(asset):
    return {
        "inline_keyboard": [
            [
                {
                    "text": "🟢 نوبیتکس",
                    "callback_data": f"price:{asset}:nobitex"
                },
                {
                    "text": "🔵 تبدیل",
                    "callback_data": f"price:{asset}:tabdeal"
                },
            ],
            [
                {
                    "text": "🟣 بیت‌پین",
                    "callback_data": f"price:{asset}:bitpin"
                },
                {
                    "text": "🟠 آبان‌تتر",
                    "callback_data": f"price:{asset}:abantether"
                },
            ],
            [
                {
                    "text": "⚫ Ourbit",
                    "callback_data": f"price:{asset}:ourbit"
                },
                {
                    "text": "🔴 LBank",
                    "callback_data": f"price:{asset}:lbank"
                },
            ],
        ]
    }


def send_exchange_menu(
    chat_id,
    asset
):
    name = DISPLAY_NAMES.get(
        asset,
        asset
    )

    send_message(
        chat_id,
        f"💰 قیمت آخرین معامله {name}\n\n"
        "صرافی را انتخاب کنید:",
        reply_markup=exchange_keyboard(
            asset
        ),
    )


# =========================================================
# نمایش قیمت
# =========================================================

def send_exchange_price(
    chat_id,
    asset,
    exchange_id,
    reply_to_message_id=None
):

    exchange_name = EXCHANGES[
        exchange_id
    ]["name"]

    display_name = DISPLAY_NAMES.get(
        asset,
        asset
    )

    try:

        prices = get_exchange_prices(
            exchange_id,
            asset
        )

        lines = [
            f"🪙 {display_name}",
            "",
            f"🏦 {exchange_name}",
        ]

        if prices["irt_price"] is not None:

            lines.append(
                "💰 آخرین معامله ریالی: "
                f"{prices['irt_price']:,.0f} تومان"
            )

        if prices["usdt_price"] is not None:

            lines.append(
                "💵 آخرین معامله تتری: "
                f"{prices['usdt_price']:,.4f} USDT"
            )

        markets = []

        if prices["irt_symbol"]:
            markets.append(
                prices["irt_symbol"]
            )

        if prices["usdt_symbol"]:
            markets.append(
                prices["usdt_symbol"]
            )

        if markets:

            lines.append(
                "📌 بازار: "
                + " | ".join(markets)
            )

        text = "\n".join(lines)

        send_message(
            chat_id,
            text,
            reply_to_message_id=
                reply_to_message_id,
        )

    except Exception as e:

        print(
            f"EXCHANGE PRICE ERROR "
            f"[{exchange_id}][{asset}]:",
            e
        )

        send_message(
            chat_id,
            f"⚠️ قیمت {display_name} "
            f"در {exchange_name} "
            "در حال حاضر دریافت نشد.\n\n"
            "ممکن است بازار این ارز "
            "در این صرافی فعال نباشد.",
            reply_to_message_id=
                reply_to_message_id,
        )


# =========================================================
# وضعیت دیتابیس
# =========================================================

def get_db_status():

    try:

        with get_db_connection() as connection:

            total = connection.execute(
                """
                SELECT COUNT(*)
                FROM analyses
                """
            ).fetchone()[0]

            by_symbol = connection.execute(
                """
                SELECT
                    symbol,
                    COUNT(*),
                    MAX(message_date)
                FROM analyses
                GROUP BY symbol
                ORDER BY MAX(message_date) DESC
                LIMIT 20
                """
            ).fetchall()

        return total, by_symbol

    except Exception as e:

        print(
            "DB STATUS ERROR:",
            e
        )

        return None


def get_price_click_report(minutes=60, limit=20):
    """گزارش کاربران پرکلیک در گروه‌ها در بازه زمانی مشخص."""
    minutes = max(1, min(int(minutes), 10080))
    limit = max(1, min(int(limit), 50))

    with get_db_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                user_id,
                MAX(username) AS username,
                MAX(first_name) AS first_name,
                MAX(last_name) AS last_name,
                COUNT(*) AS total_clicks,
                COUNT(*) FILTER (WHERE allowed = TRUE) AS allowed_clicks,
                COUNT(*) FILTER (WHERE allowed = FALSE) AS blocked_clicks,
                MAX(clicked_at) AS last_click_at
            FROM price_click_logs
            WHERE clicked_at >= NOW() - (%s * INTERVAL '1 minute')
              AND chat_type IN ('group', 'supergroup')
              AND user_id IS NOT NULL
            GROUP BY user_id
            ORDER BY total_clicks DESC, last_click_at DESC
            LIMIT %s
            """,
            (minutes, limit)
        ).fetchall()

    return rows


def get_price_click_user(user_id, minutes=1440):
    """جزئیات کلیک‌های یک کاربر در گروه‌ها."""
    minutes = max(1, min(int(minutes), 10080))

    with get_db_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                clicked_at, username, first_name, last_name,
                chat_id, asset, exchange_id, allowed, block_reason
            FROM price_click_logs
            WHERE user_id = %s
              AND clicked_at >= NOW() - (%s * INTERVAL '1 minute')
              AND chat_type IN ('group', 'supergroup')
            ORDER BY clicked_at DESC
            LIMIT 100
            """,
            (user_id, minutes)
        ).fetchall()

    return rows


def is_admin_user(user_id):
    """فقط مدیر ربات اجازه دیدن گزارش کلیک‌ها را دارد."""
    try:
        configured = os.environ.get("ADMIN_USER_ID")
        if configured:
            return int(configured) == int(user_id)

        # همان شناسه‌ای که در نسخه فعلی برای ثبت تحلیل‌ها به‌عنوان مدیر استفاده شده است.
        return int(user_id) == 6738956694
    except Exception:
        return False


def format_user_name(user_id, username, first_name, last_name):
    parts = [p for p in (first_name, last_name) if p]
    name = " ".join(parts).strip()

    if username:
        handle = f"@{username}"
    else:
        handle = "بدون یوزرنیم"

    if name:
        return f"{handle} | {name} | ID: {user_id}"

    return f"{handle} | ID: {user_id}"


def send_price_click_report(chat_id, minutes=60):
    try:
        rows = get_price_click_report(minutes, 20)
    except Exception as e:
        print("PRICE REPORT ERROR:", e)
        send_message(chat_id, "❌ خطا در خواندن گزارش کلیک‌ها.")
        return

    if not rows:
        send_message(
            chat_id,
            f"📊 در {minutes} دقیقه گذشته هیچ کلیک قیمتی در گروه ثبت نشده است."
        )
        return

    reply = (
        f"📊 کاربران پرکلیک ربات در گروه\n"
        f"🕐 بازه: {minutes} دقیقه اخیر\n\n"
    )

    for i, row in enumerate(rows, 1):
        (
            user_id, username, first_name, last_name,
            total_clicks, allowed_clicks, blocked_clicks, last_click_at
        ) = row

        last_click = last_click_at.astimezone(ZoneInfo("Asia/Tehran")).strftime(
            "%H:%M:%S"
        ) if last_click_at else "-"

        reply += (
            f"{i}. {format_user_name(user_id, username, first_name, last_name)}\n"
            f"   🖱 کل کلیک: {total_clicks} | "
            f"✅ مجاز: {allowed_clicks} | 🚫 مسدود: {blocked_clicks}\n"
            f"   🕐 آخرین کلیک: {last_click}\n\n"
        )

    send_message(chat_id, reply)


def get_symbol_db_status(symbol):

    symbol = (
        symbol or ""
    ).strip().upper()

    with get_db_connection() as connection:

        rows = connection.execute(
            """
            SELECT
                chat_id,
                message_id,
                symbol,
                message_date,
                date_text
            FROM analyses
            WHERE UPPER(TRIM(symbol)) = %s
            ORDER BY
                message_date DESC,
                id DESC
            LIMIT 10
            """,
            (symbol,)
        ).fetchall()

    return rows


# =========================================================
# Webhook
# =========================================================

@app.route(
    "/webhook",
    methods=["POST"]
)
def webhook():

    data = request.get_json()

    if not data:
        return "ok"


# =====================================================
# Callback Query
# =====================================================

    if "callback_query" in data:

        callback = data[
            "callback_query"
        ]

        callback_id = callback.get(
            "id"
        )

        callback_data = callback.get(
            "data",
            ""
        )

# ================================================
# انتخاب تحلیل امروز
# ================================================

        if callback_data.startswith(
            "today_analysis:"
        ):

            symbol = callback_data.split(
                ":",
                1
            )[1].upper().strip()

            callback_message = callback.get(
                "message",
                {}
            )

            callback_chat = callback_message.get(
                "chat",
                {}
            )

            callback_chat_id = callback_chat.get(
                "id"
            )

            callback_chat_type = callback_chat.get(
                "type",
                "private"
            )

            if callback_chat_id is None:

                answer_callback(
                    callback_id,
                    "⚠️ خطا در تشخیص چت."
                )

                return "ok"

            if callback_chat_type in {
                "group",
                "supergroup"
            }:

                search_chat_id = callback_chat_id

            else:

                search_chat_id = None

            analyses = get_latest_two_analysis_info(
                symbol,
                search_chat_id
            )

            if not analyses:

                answer_callback(
                    callback_id,
                    "❌ تحلیل این ارز پیدا نشد."
                )

                return "ok"

            latest_analysis = analyses[0]
            source_chat = latest_analysis[0]
            message_id = latest_analysis[1]

            answer_callback(
                callback_id,
                "📊 در حال ارسال تحلیل..."
            )

            reply_to_message_id = None

            if len(analyses) > 1:

                previous_source_chat = analyses[1][0]
                previous_source_message = analyses[1][1]

                # در گروه و همچنین داخل خود ربات، ابتدا دنبال
                # message_id واقعیِ کپی‌شده از تحلیل قبلی می‌گردیم.
                # بنابراین تحلیل امروز به آخرین تحلیل قبلی همان ارز
                # Reply می‌شود؛ حتی اگر تحلیل قبلی مربوط به دیروز
                # یا روزهای قبل باشد.
                reply_to_message_id = get_analysis_copy_message_id(
                    previous_source_chat,
                    previous_source_message,
                    callback_chat_id,
                    symbol
                )

                # اگر تحلیل قبلی مستقیماً در همین چت ثبت شده باشد،
                # همان message_id منبع برای Reply معتبر است.
                if (
                    reply_to_message_id is None
                    and previous_source_chat == callback_chat_id
                ):
                    reply_to_message_id = previous_source_message

            copied_message_id = copy_analysis_message(
                callback_chat_id,
                source_chat,
                message_id,
                reply_to_message_id=reply_to_message_id
            )

            if not copied_message_id and reply_to_message_id is not None:
                copied_message_id = copy_analysis_message(
                    callback_chat_id,
                    source_chat,
                    message_id,
                    reply_to_message_id=None
                )

            if not copied_message_id:
                send_message(
                    callback_chat_id,
                    "❌ ارسال تحلیل انجام نشد.\n\n"
                    f"خطای واقعی Telegram:\n{LAST_COPY_ERROR or 'نامشخص'}"
                )
            else:
                save_analysis_copy(
                    source_chat,
                    message_id,
                    callback_chat_id,
                    copied_message_id,
                    symbol
                )
                send_analysis_date(
                    callback_chat_id,
                    copied_message_id,
                    latest_analysis[2]
                )

            return "ok"


# ================================================
# انتخاب تحلیل تاریخی
# ================================================

        if callback_data.startswith(
            "historical_analysis:"
        ):

            parts = callback_data.split(
                ":",
                2
            )

            if len(parts) != 3:

                answer_callback(
                    callback_id,
                    "⚠️ اطلاعات تحلیل نامعتبر است."
                )

                return "ok"

            date_text = parts[1]
            symbol = parts[2].upper().strip()

            callback_message = callback.get(
                "message",
                {}
            )

            callback_chat = callback_message.get(
                "chat",
                {}
            )

            callback_chat_id = callback_chat.get(
                "id"
            )

            callback_chat_type = callback_chat.get(
                "type",
                "private"
            )

            if callback_chat_id is None:

                answer_callback(
                    callback_id,
                    "⚠️ خطا در تشخیص چت."
                )

                return "ok"

            if callback_chat_type in {
                "group",
                "supergroup"
            }:
                search_chat_id = callback_chat_id
            else:
                search_chat_id = None

            candidates = get_analysis_candidates_for_date(
                symbol,
                date_text,
                search_chat_id
            )

            if not candidates:
                answer_callback(
                    callback_id,
                    "❌ تحلیل انتخاب‌شده پیدا نشد."
                )
                return "ok"

            answer_callback(
                callback_id,
                "📊 در حال ارسال تحلیل..."
            )

            copied_message_id = None
            selected = None
            last_error = ""

            # ممکن است در یک روز برای یک ارز چند رکورد وجود داشته باشد.
            # اگر جدیدترین رکورد به پیام حذف‌شده/نامعتبر اشاره کند، رکورد بعدی
            # همان تاریخ را امتحان می‌کنیم.
            for candidate in candidates:
                source_chat = candidate[0]
                message_id = candidate[1]

                previous = get_previous_analysis_info(
                    symbol,
                    candidate[2],
                    search_chat_id
                )

                reply_to_message_id = None
                if previous:
                    reply_to_message_id = get_analysis_copy_message_id(
                        previous[0],
                        previous[1],
                        callback_chat_id,
                        symbol
                    )
                    if (
                        reply_to_message_id is None
                        and previous[0] == callback_chat_id
                    ):
                        reply_to_message_id = previous[1]

                copied_message_id = copy_analysis_message(
                    callback_chat_id,
                    source_chat,
                    message_id,
                    reply_to_message_id=reply_to_message_id
                )

                # اگر فقط Reply قبلی خراب بود، خود تحلیل را بدون Reply بفرست.
                if not copied_message_id and reply_to_message_id is not None:
                    copied_message_id = copy_analysis_message(
                        callback_chat_id,
                        source_chat,
                        message_id,
                        reply_to_message_id=None
                    )

                if copied_message_id:
                    selected = candidate
                    break

                last_error = LAST_COPY_ERROR or "نامشخص"
                if "message to copy not found" not in last_error.lower():
                    break

            if not copied_message_id or selected is None:
                send_message(
                    callback_chat_id,
                    "❌ ارسال تحلیل انجام نشد.\n\n"
                    f"خطای واقعی Telegram:\n{last_error}"
                )
                return "ok"

            save_analysis_copy(
                selected[0],
                selected[1],
                callback_chat_id,
                copied_message_id,
                symbol
            )

            # تاریخ شمسی باید برای انتخاب‌های دیروز/۷ روز اخیر هم نمایش داده شود.
            send_analysis_date(
                callback_chat_id,
                copied_message_id,
                selected[2]
            )

            return "ok"


# ================================================
# انتخاب صرافی
# ================================================

        if callback_data.startswith(
            "price:"
        ):

            parts = callback_data.split(
                ":"
            )

            if len(parts) == 3:

                asset = parts[
                    1
                ].upper()

                exchange_id = parts[
                    2
                ]

                if exchange_id in EXCHANGES:

                    # فقط کلیک را ثبت می‌کنیم؛ فعلاً هیچ محدودیتی اعمال نمی‌شود.
                    log_price_click(
                        callback,
                        asset,
                        exchange_id,
                        allowed=True
                    )

                    answer_callback(
                        callback_id,
                        "در حال دریافت قیمت..."
                    )

                    callback_message = callback.get(
                        "message",
                        {}
                    )

                    callback_chat = callback_message.get(
                        "chat",
                        {}
                    )

                    callback_chat_id = callback_chat.get(
                        "id"
                    )

                    callback_message_id = callback_message.get(
                        "message_id"
                    )

                    if callback_chat_id is not None:

                        send_exchange_price(
                            callback_chat_id,
                            asset,
                            exchange_id,
                            reply_to_message_id=
                                callback_message_id,
                        )

                    return "ok"


# ================================================
# بررسی عضویت
# ================================================

        if callback_data == "check_membership":

            user_id = callback.get(
                "from",
                {}
            ).get(
                "id"
            )

            try:

                member = requests.get(
                    f"https://api.telegram.org/"
                    f"bot{BOT_TOKEN}/getChatMember",
                    params={
                        "chat_id": "@rooye_chart",
                        "user_id": user_id
                    },
                    timeout=10
                ).json()

                status = member.get(
                    "result",
                    {}
                ).get(
                    "status"
                )

                if status in {
                    "creator",
                    "administrator",
                    "member"
                }:

                    answer_callback(
                        callback_id,
                        "✅ عضویت شما تأیید شد."
                    )

                    send_message(
                        user_id,
                        "✅ عضویت شما تأیید شد.\n\n"
                        "🤖 حالا می‌توانید "
                        "از ربات روی چارت استفاده کنید."
                    )

                else:

                    answer_callback(
                        callback_id,
                        "❌ هنوز عضو کانال روی چارت نیستید."
                    )

                    send_message(
                        user_id,
                        "❌ عضویت شما تأیید نشد.\n\n"
                        "ابتدا عضو کانال روی چارت شوید "
                        "و سپس دوباره روی "
                        "«بررسی عضویت» بزنید."
                    )

            except Exception as e:

                print(
                    "MEMBERSHIP CHECK ERROR:",
                    e
                )

                answer_callback(
                    callback_id,
                    "⚠️ خطا در بررسی عضویت."
                )

            return "ok"


        answer_callback(
            callback_id
        )

        return "ok"

# =====================================================
# پیام عادی
# =====================================================

    if "message" not in data:
        return "ok"


    message = data[
        "message"
    ]

    chat_id = message[
        "chat"
    ][
        "id"
    ]

    chat_type = message[
        "chat"
    ].get(
        "type",
        "private"
    )

    message_id = message.get(
        "message_id"
    )

    message_date = message.get(
        "date"
    )

    # در سوپرگروه‌های Forum، این شناسه Topic جاری پیام ورودی است.
    # برای زنجیره Reply گروه از آن به‌عنوان fallback استفاده می‌کنیم،
    # مخصوصاً برای رکوردهای قدیمی که Thread در دیتابیس ذخیره نشده‌اند.
    message_thread_id = message.get(
        "message_thread_id"
    )


# =====================================================
# دستورهای دیتابیس
# =====================================================

    text_for_command = message.get(
        "text",
        ""
    ).strip()


    if (
        chat_type == "private"
        and text_for_command.startswith("/priceusers")
    ):
        if not is_admin_user(chat_id):
            send_message(chat_id, "⛔ این دستور فقط برای مدیر ربات فعال است.")
            return "ok"

        parts = text_for_command.split()
        minutes = 60

        if len(parts) > 1:
            try:
                minutes = int(parts[1])
            except ValueError:
                send_message(
                    chat_id,
                    "مثال: /priceusers 60\n\n"
                    "عدد، تعداد دقیقه موردنظر است."
                )
                return "ok"

        send_price_click_report(chat_id, minutes)
        return "ok"


    if (
        chat_type == "private"
        and text_for_command.startswith("/priceuser")
    ):
        if not is_admin_user(chat_id):
            send_message(chat_id, "⛔ این دستور فقط برای مدیر ربات فعال است.")
            return "ok"

        parts = text_for_command.split()
        if len(parts) < 2:
            send_message(
                chat_id,
                "مثال: /priceuser 123456789"
            )
            return "ok"

        try:
            target_user_id = int(parts[1])
        except ValueError:
            send_message(chat_id, "❌ User ID باید عددی باشد.")
            return "ok"

        minutes = 1440
        if len(parts) > 2:
            try:
                minutes = int(parts[2])
            except ValueError:
                send_message(chat_id, "مثال: /priceuser 123456789 1440")
                return "ok"

        try:
            rows = get_price_click_user(target_user_id, minutes)
        except Exception as e:
            print("PRICE USER ERROR:", e)
            send_message(chat_id, "❌ خطا در خواندن اطلاعات کاربر.")
            return "ok"

        if not rows:
            send_message(
                chat_id,
                f"🔎 برای User ID {target_user_id} در {minutes} دقیقه اخیر کلیکی ثبت نشده است."
            )
            return "ok"

        first = rows[0]
        _, username, first_name, last_name, _, _, _, _, _ = first
        reply = (
            "🔎 جزئیات کلیک کاربر\n\n"
            f"{format_user_name(target_user_id, username, first_name, last_name)}\n"
            f"🕐 بازه: {minutes} دقیقه اخیر\n"
            f"🖱 تعداد ثبت‌شده: {len(rows)}\n\n"
        )

        for row in rows[:30]:
            clicked_at, username, first_name, last_name, group_id, asset, exchange_id, allowed, block_reason = row
            dt = clicked_at.astimezone(ZoneInfo("Asia/Tehran")).strftime("%H:%M:%S")
            exchange_name = EXCHANGES.get(exchange_id, {}).get("name", exchange_id)
            status = "✅" if allowed else f"🚫 {block_reason or 'blocked'}"
            reply += f"• {dt} | {asset} | {exchange_name} | {status} | گروه: {group_id}\n"

        send_message(chat_id, reply)
        return "ok"


    if (
        chat_type == "private"
        and text_for_command == "/dbstatus"
    ):

        status = get_db_status()

        if status is None:

            send_message(
                chat_id,
                "❌ خطا در خواندن دیتابیس."
            )

            return "ok"

        total, by_symbol = status

        reply = (
            "🗄 وضعیت دیتابیس ربات\n\n"
            f"تعداد کل تحلیل‌های ثبت‌شده: "
            f"{total}\n\n"
            "آخرین رکوردهای ارزها:\n"
        )

        if by_symbol:

            for (
                symbol,
                count,
                latest_ts
            ) in by_symbol:

                latest = datetime.fromtimestamp(
                    latest_ts,
                    tz=ZoneInfo(
                        "Asia/Tehran"
                    )
                ).strftime(
                    "%Y-%m-%d %H:%M"
                )

                reply += (
                    f"• {symbol}: "
                    f"{count} رکورد | "
                    f"{latest}\n"
                )

        else:

            reply += (
                "هیچ تحلیلی "
                "در دیتابیس وجود ندارد."
            )

        send_message(
            chat_id,
            reply
        )

        return "ok"


    if (
        chat_type == "private"
        and text_for_command.startswith(
            "/dbsymbol"
        )
    ):

        parts = text_for_command.split(
            maxsplit=1
        )

        if len(parts) != 2:

            send_message(
                chat_id,
                "مثال: /dbsymbol NEAR"
            )

            return "ok"

        symbol = parts[
            1
        ].strip().upper()

        rows = get_symbol_db_status(
            symbol
        )

        if not rows:

            send_message(
                chat_id,
                f"🔎 برای {symbol} "
                "هیچ رکوردی در دیتابیس پیدا نشد."
            )

            return "ok"

        reply = (
            f"🔎 رکوردهای {symbol}\n\n"
        )

        for (
            db_chat_id,
            db_message_id,
            db_symbol,
            ts,
            date_text
        ) in rows:

            dt = datetime.fromtimestamp(
                ts,
                tz=ZoneInfo(
                    "Asia/Tehran"
                )
            ).strftime(
                "%Y-%m-%d %H:%M"
            )

            reply += (
                f"• {dt}\n"
                f"  chat_id: {db_chat_id}\n"
                f"  message_id: {db_message_id}\n"
                f"  date_text: {date_text}\n\n"
            )

        send_message(
            chat_id,
            reply
        )

        return "ok"


    if (
        chat_type == "private"
        and text_for_command.startswith("/dbchain")
    ):
        parts = text_for_command.split(maxsplit=1)

        if len(parts) != 2:
            send_message(
                chat_id,
                "مثال: /dbchain SIREN"
            )
            return "ok"

        symbol = parts[1].strip().upper()
        analyses_rows, copies_rows = get_analysis_chain_diagnostic(
            symbol,
            target_chat_id=None
        )

        if not analyses_rows:
            send_message(
                chat_id,
                f"🔎 برای {symbol} هیچ رکوردی در analyses پیدا نشد."
            )
            return "ok"

        reply = f"🔎 تشخیص زنجیره {symbol}\n\n"
        reply += "📌 analyses (منبع‌ها):\n"

        for db_chat_id, db_message_id, db_message_date, db_id in analyses_rows:
            reply += (
                f"• chat={db_chat_id} | message={db_message_id}\n"
                f"  date={db_message_date} | db_id={db_id}\n"
            )

        reply += "\n🔗 analysis_copies:\n"

        if not copies_rows:
            reply += "هیچ mapping کپی برای این ارز پیدا نشد.\n"
        else:
            for (
                source_chat_id,
                source_message_id,
                target_chat_id,
                copied_message_id,
                copy_symbol,
                target_thread_id,
                copied_at,
            ) in copies_rows:
                reply += (
                    f"• source={source_chat_id}:{source_message_id}\n"
                    f"  target={target_chat_id}:{copied_message_id}\n"
                    f"  thread={target_thread_id}\n"
                    f"  copied_at={copied_at}\n"
                )

        reply += (
            "\n⚠️ نکته: این گزارش فقط دیتابیس را بررسی می‌کند؛ "
            "در جدول analyses متن/کپشن منبع ذخیره نشده، بنابراین از این خروجی "
            "به‌تنهایی نمی‌توان تشخیص داد یک تحلیل قدیمی @rooye_chart داشته یا نه."
        )

        send_message(chat_id, reply)
        return "ok"


# =====================================================
# ثبت تحلیل عکس + هشتگ
# =====================================================

    if "photo" in message:

        # پیام‌هایی که Telegram از کانال به Discussion برمی‌گرداند
        # automatic forward هستند و نباید به‌عنوان تحلیل مستقل ثبت شوند.
        # تحلیل اصلی که مستقیماً در گروه ارسال شده، همچنان بدون تغییر ثبت می‌شود.
        if message.get("is_automatic_forward"):
            return "ok"

        caption = message.get(
            "caption",
            ""
        )

        # فقط تحلیل‌های خود کانال/گروه روی چارت ثبت شوند.
        # این شرط عمداً بر اساس @rooye_chart است، نه User ID فرستنده.
        if "@rooye_chart" not in caption.lower():
            return "ok"

        symbols, is_watchlist = extract_analysis_symbols(
            caption
        )

        photo_file_id = message[
            "photo"
        ][-1][
            "file_id"
        ]

        for symbol in symbols:

            save_analysis(
                chat_id,
                message_id,
                symbol,
                message_date,
                photo_file_id,
                is_watchlist
            )

        return "ok"

# =====================================================
# متن
# =====================================================

    text = message.get(
        "text",
        ""
    ).strip()

    if not text:
        return "ok"


# =====================================================
# تشخیص درخواست تحلیل
# =====================================================

    analysis_request = extract_analysis_request(
        text
    )


# =====================================================
# واچ‌لیست ۷ روز اخیر
# =====================================================

    if analysis_request == "WATCHLIST":

        tehran_now = datetime.now(
            ZoneInfo("Asia/Tehran")
        )

        today_date = tehran_now.date()
        start_date = today_date - timedelta(days=6)
        end_date = today_date

        start_text = start_date.strftime("%Y-%m-%d")
        end_text = end_date.strftime("%Y-%m-%d")

        if chat_type in {
            "group",
            "supergroup"
        }:
            search_chat_id = chat_id
        else:
            search_chat_id = None

        rows = get_watchlist_range(
            start_text,
            end_text,
            search_chat_id
        )

        if not rows:
            send_message(
                chat_id,
                "⭐ در ۷ روز اخیر هنوز ارزی در واچ‌لیست ثبت نشده است."
            )
            return "ok"

        latest = {}

        for (
            symbol,
            msg_id,
            source_chat,
            msg_date,
            date_text
        ) in rows:

            if (
                symbol not in latest
                or msg_date >= latest[symbol][3]
            ):
                latest[symbol] = (
                    symbol,
                    msg_id,
                    source_chat,
                    msg_date,
                    date_text
                )

        buttons = []
        row = []

        for symbol in latest:

            row.append({
                "text": f"⭐ {DISPLAY_NAMES.get(symbol, symbol)}",
                "callback_data":
                    f"historical_analysis:{latest[symbol][4]}:{symbol}"
            })

            if len(row) == 2:
                buttons.append(row)
                row = []

        if row:
            buttons.append(row)

        send_message(
            chat_id,
            "⭐ واچ‌لیست روی چارت\n"
            "فقط ارزهایی که با #WATCHLIST علامت خورده‌اند.\n\n"
            "🔽 ارز موردنظر را انتخاب کنید:",
            reply_markup={
                "inline_keyboard": buttons
            }
        )

        return "ok"


# =====================================================
# تحلیل‌های دیروز / ۷ روز اخیر
# =====================================================

    if analysis_request in {
        "YESTERDAY",
        "LAST7"
    }:

        tehran_now = datetime.now(
            ZoneInfo("Asia/Tehran")
        )

        today_date = tehran_now.date()

        if analysis_request == "YESTERDAY":
            start_date = today_date - timedelta(days=1)
            end_date = start_date
            title = "📊 تحلیل‌های دیروز روی چارت"
        else:
            start_date = today_date - timedelta(days=6)
            end_date = today_date
            title = "📊 تحلیل‌های ۷ روز اخیر روی چارت"

        start_text = start_date.strftime("%Y-%m-%d")
        end_text = end_date.strftime("%Y-%m-%d")

        if chat_type in {
            "group",
            "supergroup"
        }:
            search_chat_id = chat_id
        else:
            search_chat_id = None

        rows = get_analysis_range(
            start_text,
            end_text,
            search_chat_id
        )

        if not rows:

            send_message(
                chat_id,
                "📊 در این بازه هنوز تحلیلی ثبت نشده است."
            )

            return "ok"

        # از هر ارز فقط آخرین تحلیل موجود در بازه را در منو نشان می‌دهیم.
        latest = {}

        for (
            symbol,
            msg_id,
            source_chat,
            msg_date,
            date_text
        ) in rows:

            if (
                symbol not in latest
                or msg_date >= latest[symbol][3]
            ):
                latest[symbol] = (
                    symbol,
                    msg_id,
                    source_chat,
                    msg_date,
                    date_text
                )

        buttons = []
        row = []

        for symbol in latest:

            row.append({
                "text": DISPLAY_NAMES.get(
                    symbol,
                    symbol
                ),
                "callback_data":
                    f"historical_analysis:{latest[symbol][4]}:{symbol}"
            })

            if len(row) == 2:
                buttons.append(row)
                row = []

        if row:
            buttons.append(row)

        send_message(
            chat_id,
            title + "\n\n🔽 ارز موردنظر را انتخاب کنید:",
            reply_markup={
                "inline_keyboard": buttons
            }
        )

        return "ok"


# =====================================================
# تحلیل‌های امروز
# =====================================================

    if analysis_request == "TODAY":
        if chat_type in {
            "group",
            "supergroup"
        }:
            search_chat_id = chat_id

        else:
            search_chat_id = None

        rows = get_today_analyses(
            search_chat_id
        )

        if not rows:

            send_message(
                chat_id,
                "📊 امروز هنوز تحلیلی ثبت نشده است."
            )

            return "ok"

        latest = {}

        for (
            symbol,
            msg_id,
            source_chat,
            msg_date
        ) in rows:

            if (
                symbol not in latest
                or msg_date >= latest[
                    symbol
                ][3]
            ):

                latest[
                    symbol
                ] = (
                    symbol,
                    msg_id,
                    source_chat,
                    msg_date
                )

        buttons = []
        row = []

        for symbol in latest:

            row.append({
                "text": DISPLAY_NAMES.get(
                    symbol,
                    symbol
                ),
                "callback_data":
                    f"today_analysis:{symbol}"
            })

            if len(row) == 2:

                buttons.append(row)
                row = []

        if row:
            buttons.append(row)

        reply_markup = {
            "inline_keyboard": buttons
        }

        send_message(
            chat_id,
            "📊 تحلیل‌های امروز روی چارت\n\n"
            "🔽 تحلیل موردنظر را انتخاب کنید:",
            reply_markup=reply_markup
        )

        return "ok"


# =====================================================
# آخرین تحلیل یک ارز
# =====================================================

    if analysis_request:

        symbol = analysis_request

        if chat_type in {
            "group",
            "supergroup"
        }:
            search_chat_id = chat_id

        else:
            search_chat_id = None


        analyses = get_latest_two_analysis_info(
            symbol,
            search_chat_id
        )


        if not analyses:

            send_message(
                chat_id,
                f"❌ هنوز تحلیلی برای "
                f"{DISPLAY_NAMES.get(symbol, symbol)} "
                "ثبت نشده است."
            )

            return "ok"


        latest_analysis = analyses[0]
        source_chat_id = latest_analysis[0]
        source_message_id = latest_analysis[1]
        analysis_date = latest_analysis[2]


        name = DISPLAY_NAMES.get(
            symbol,
            symbol
        )


        analysis_time = datetime.fromtimestamp(
            analysis_date,
            tz=ZoneInfo(
                "Asia/Tehran"
            )
        ).strftime(
            "%Y-%m-%d | %H:%M"
        )


        if chat_type in {
            "group",
            "supergroup"
        }:

            reply_to_message_id = None
            reply_thread_id = message_thread_id

            if len(analyses) > 1:
                previous_source_chat = analyses[1][0]
                previous_source_message = analyses[1][1]

                # هرگز پیام فعلی را به خودش Reply نکن.
                if (
                    previous_source_chat == source_chat_id
                    and previous_source_message == source_message_id
                ):
                    previous_source_chat = None
                    previous_source_message = None

                if previous_source_chat is not None:
                    reply_to_message_id = get_analysis_copy_message_id(
                        previous_source_chat,
                        previous_source_message,
                        chat_id,
                        symbol
                    )

                    stored_thread_id = get_analysis_copy_target_thread_id(
                        previous_source_chat,
                        previous_source_message,
                        chat_id,
                        symbol
                    )

                    if stored_thread_id is not None:
                        reply_thread_id = stored_thread_id

                # اگر تحلیل قبلی مستقیماً در همین گروه ثبت شده باشد، همان
                # message_id منبع قابل Reply است.
                if (
                    reply_to_message_id is None
                    and previous_source_chat == chat_id
                ):
                    reply_to_message_id = previous_source_message

            # در Topic جاری، اگر رکورد قبلی Thread نداشته باشد، Thread پیام
            # ورودی را نگه می‌داریم. این دقیقاً برای رکوردهای قدیمی مثل 59873
            # مهم است که قبل از اضافه شدن ستون Thread ذخیره شده‌اند.
            if reply_to_message_id is not None and reply_thread_id is not None:
                print(
                    "GROUP ANALYSIS REPLY TARGET:",
                    symbol,
                    "reply_to=",
                    reply_to_message_id,
                    "thread=",
                    reply_thread_id
                )

            if (
                reply_to_message_id is not None
                and reply_to_message_id == source_message_id
                and source_chat_id == chat_id
            ):
                reply_to_message_id = None

            # ===== DIAGNOSTIC ONLY: هیچ رفتار ربات را تغییر نمی‌دهد =====
            print("========== GROUP REPLY DEBUG ==========")
            print("SYMBOL:", symbol)
            print("CURRENT CHAT ID:", chat_id)
            print("SOURCE CHAT ID:", source_chat_id)
            print("SOURCE MESSAGE ID:", source_message_id)
            print("PREVIOUS SOURCE CHAT ID:", previous_source_chat if len(analyses) > 1 else None)
            print("PREVIOUS SOURCE MESSAGE ID:", previous_source_message if len(analyses) > 1 else None)
            print("REPLY TO MESSAGE ID:", reply_to_message_id)
            print("INCOMING MESSAGE THREAD ID:", message_thread_id)
            print("TARGET MESSAGE THREAD ID:", reply_thread_id)
            print("========================================")

            copy_result = copy_analysis_message(
                chat_id,
                source_chat_id,
                source_message_id,
                reply_to_message_id=reply_to_message_id,
                target_message_thread_id=reply_thread_id,
                return_metadata=True,
            )

            # اگر Reply به رکورد قدیمی به‌خاطر Thread اشتباه شکست خورد، یک بار
            # دیگر با Thread پیام ورودی (و بدون Thread ذخیره‌شده قدیمی) امتحان
            # می‌کنیم؛ اما فقط وقتی Reply target داریم. در صورت شکست، دیگر
            # تحلیل را بدون Reply مخفیانه ارسال نمی‌کنیم.
            if (
                copy_result is None
                and reply_to_message_id is not None
                and message_thread_id is not None
                and reply_thread_id != message_thread_id
            ):
                copy_result = copy_analysis_message(
                    chat_id,
                    source_chat_id,
                    source_message_id,
                    reply_to_message_id=reply_to_message_id,
                    target_message_thread_id=message_thread_id,
                    return_metadata=True,
                )

            print("GROUP COPY RESULT:", copy_result)
            print("GROUP COPY LAST ERROR:", LAST_COPY_ERROR)

            if copy_result is None and reply_to_message_id is not None:
                send_message(
                    chat_id,
                    "⚠️ تحلیل پیدا شد، اما Reply به تحلیل قبلی انجام نشد.\n\n"
                    f"خطای واقعی Telegram:\n{LAST_COPY_ERROR or 'نامشخص'}"
                )
                return "ok"

            # اگر تحلیل قبلی نداریم، این اولین تحلیل زنجیره در گروه است.
            if copy_result is None:
                copy_result = copy_analysis_message(
                    chat_id,
                    source_chat_id,
                    source_message_id,
                    reply_to_message_id=None,
                    target_message_thread_id=message_thread_id,
                    return_metadata=True,
                )

            if copy_result is None:
                send_message(
                    chat_id,
                    "❌ ارسال تحلیل انجام نشد.\n\n"
                    f"خطای واقعی Telegram:\n{LAST_COPY_ERROR or 'نامشخص'}"
                )
                return "ok"

            copied_message_id = copy_result["message_id"]
            actual_thread_id = copy_result.get("message_thread_id")

            save_analysis_copy(
                source_chat_id,
                source_message_id,
                chat_id,
                copied_message_id,
                symbol,
                target_message_thread_id=actual_thread_id,
            )

            send_analysis_date(
                chat_id,
                copied_message_id,
                analysis_date
            )
        else:

            # چت خصوصی: از جدیدترین رکورد شروع می‌کنیم، اما اگر پیام منبع
            # دیگر در Telegram وجود نداشت، رکورد خراب را کنار می‌گذاریم و
            # سراغ جدیدترین تحلیل معتبر بعدی همان ارز می‌رویم.
            candidates = get_analysis_candidates(symbol, None, 30)
            copied_message_id = None
            selected_source = None
            already_sent = False

            for candidate_index, candidate in enumerate(candidates):
                candidate_source_chat = candidate[0]
                candidate_source_message = candidate[1]
                candidate_date = candidate[2]

                existing_current_copy = get_analysis_copy_message_id(
                    candidate_source_chat,
                    candidate_source_message,
                    chat_id,
                    symbol
                )

                if existing_current_copy is not None:
                    # اگر جدیدترین تحلیل معتبر قبلاً ارسال شده، همان رفتار
                    # قبلی حفظ می‌شود و به تحلیل قدیمی‌تر برنمی‌گردیم.
                    if candidate is candidates[0]:
                        already_sent = True
                    break

                # Reply باید دقیقاً به آخرین کپیِ قبلی همین ارز در همین چت
                # وصل شود؛ نه به آخرین رکورد تصادفیِ جدول.
                reply_to_message_id = None

                for previous_candidate in candidates[candidate_index + 1:]:
                    previous_source_chat = previous_candidate[0]
                    previous_source_message = previous_candidate[1]

                    previous_copy = get_analysis_copy_message_id(
                        previous_source_chat,
                        previous_source_message,
                        chat_id,
                        symbol
                    )

                    if previous_copy is not None:
                        reply_to_message_id = previous_copy
                        break

                # اگر تحلیل قبلی مستقیماً در همین چت ثبت شده، همان message_id
                # منبع قابل استفاده است.
                if (
                    reply_to_message_id is None
                    and candidate_source_chat == chat_id
                    and len(candidates) > candidate_index + 1
                ):
                    previous_candidate = candidates[candidate_index + 1]
                    if previous_candidate[0] == chat_id:
                        reply_to_message_id = previous_candidate[1]

                print(
                    "PRIVATE ANALYSIS REPLY TARGET:",
                    symbol,
                    "source=",
                    candidate_source_chat,
                    candidate_source_message,
                    "reply_to=",
                    reply_to_message_id
                )

                copied_message_id = copy_analysis_message(
                    chat_id,
                    candidate_source_chat,
                    candidate_source_message,
                    reply_to_message_id=reply_to_message_id
                )

                if copied_message_id:
                    selected_source = (
                        candidate_source_chat,
                        candidate_source_message,
                        candidate_date
                    )
                    break

                # اگر Telegram گفت پیام منبع پیدا نشد، این رکورد احتمالاً قدیمی
                # یا حذف‌شده است؛ حلقه به تحلیل معتبر بعدی می‌رود.
                if 'message to copy not found' in (LAST_COPY_ERROR or '').lower():
                    print(
                        "SKIP INVALID SOURCE MESSAGE:",
                        symbol,
                        candidate_source_chat,
                        candidate_source_message
                    )
                    continue

                # خطاهای دیگر را بی‌جهت روی رکوردهای قدیمی پخش نکن؛ همان خطا را
                # به کاربر نشان می‌دهیم.
                break

            if already_sent:
                send_message(
                    chat_id,
                    "ℹ️ این تحلیل قبلاً برای شما ارسال شده است."
                )
                return "ok"

            if copied_message_id and selected_source:
                selected_chat, selected_message, selected_date = selected_source
                save_analysis_copy(
                    selected_chat,
                    selected_message,
                    chat_id,
                    copied_message_id,
                    symbol
                )
                send_analysis_date(
                    chat_id,
                    copied_message_id,
                    selected_date
                )
            else:
                send_message(
                    chat_id,
                    "⚠️ کپی تحلیل توسط Telegram انجام نشد.\n\n"
                    f"خطای واقعی Telegram:\n{LAST_COPY_ERROR or 'نامشخص'}"
                )

        return "ok"


# =====================================================
# بررسی عضویت برای استفاده از ربات
# =====================================================

    if chat_type == "private":

        try:

            member = requests.get(
                f"https://api.telegram.org/"
                f"bot{BOT_TOKEN}/getChatMember",
                params={
                    "chat_id": "@rooye_chart",
                    "user_id": chat_id
                },
                timeout=10
            ).json()

            status = member.get(
                "result",
                {}
            ).get(
                "status"
            )


            if status not in {
                "creator",
                "administrator",
                "member"
            }:

                send_message(
                    chat_id,
                    "🔒 برای استفاده از ربات، "
                    "ابتدا باید عضو کانال روی چارت شوید.\n\n"
                    "بعد از عضویت، روی "
                    "«بررسی عضویت» بزنید.",
                    reply_markup={
                        "inline_keyboard": [
                            [
                                {
                                    "text":
                                        "📢 عضویت در کانال",
                                    "url":
                                        CHANNEL_URL
                                }
                            ],
                            [
                                {
                                    "text":
                                        "✅ بررسی عضویت",
                                    "callback_data":
                                        "check_membership"
                                }
                            ]
                        ]
                    }
                )

                return "ok"


        except Exception as e:

            print(
                "MEMBERSHIP ERROR:",
                e
            )

            send_message(
                chat_id,
                "⚠️ در بررسی عضویت مشکلی پیش آمد. "
                "لطفاً چند لحظه بعد دوباره تلاش کنید."
            )

            return "ok"


# =================================================
# /start
# =================================================

        if text == "/start":

            send_message(
                chat_id,
                "🤖 ربات روی چارت\n\n"
                "برای قیمت، فقط نام یا نماد ارز را بنویسید.\n"
                "مثال: سولانا یا SOL\n\n"
                "اگر نام صرافی را هم بنویسید، "
                "قیمت همان صرافی مستقیم نمایش داده می‌شود.\n"
                "مثال: سولانا تبدیل\n"
                "یا: سولانا نوبیتکس\n\n"
                "برای تحلیل:\n"
                "• تحلیل سولانا\n"
                "• تحلیل XRP\n"
                "• تحلیل FET\n\n"
                "برای همه تحلیل‌های امروز:\n"
                "• تحلیل های امروز\n\n"
                "برای واچ‌لیست روزهای قبل:\n"
                "• تحلیل های دیروز\n"
                "• تحلیل های 7 روز اخیر"
            )

            return "ok"


# =====================================================
# پیام‌های غیرارزی در گروه
# =====================================================

    if chat_type in {
        "group",
        "supergroup"
    } and not looks_like_coin(text):

        return "ok"


# =====================================================
# قیمت چند صرافی
# =====================================================

    asset, requested_exchange = parse_price_request(
        text
    )


    if asset:

# فقط نام ارز
# نمایش منوی صرافی

        if requested_exchange is None:

            send_exchange_menu(
                chat_id,
                asset
            )

            return "ok"


# ارز + نام صرافی
# استعلام مستقیم

        if requested_exchange in EXCHANGES:

            send_exchange_price(
                chat_id,
                asset,
                requested_exchange
            )

            return "ok"


# =====================================================
# درخواست نامعتبر
# =====================================================

    if chat_type in {
        "group",
        "supergroup"
    }:

        return "ok"


    send_message(
        chat_id,
        "❌ درخواست قیمت قابل تشخیص نیست.\n\n"
        "مثال:\n"
        "• سولانا\n"
        "• SOL\n"
        "• سولانا تبدیل\n"
        "• سولانا نوبیتکس"
    )

    return "ok"


# =========================================================
# اجرای Flask
# =========================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(
            os.environ.get(
                "PORT",
                10000
            )
        )
    )
