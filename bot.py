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
                copied_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                UNIQUE (source_chat_id, source_message_id, target_chat_id)
            )
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_analysis_copies_target_symbol
            ON analysis_copies (target_chat_id, symbol, copied_at DESC)
            """
        )
        connection.commit()


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
    source_message_id,
    reply_to_message_id=None
):
    payload = {
        "chat_id": target_chat_id,
        "from_chat_id": source_chat_id,
        "message_id": source_message_id,
    }

    if reply_to_message_id is not None:
        payload["reply_parameters"] = {
            "message_id": reply_to_message_id
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

        if not response.ok:
            return None

        result = response.json().get("result", {}) or {}
        copied_message_id = result.get("message_id")

        if copied_message_id is None:
            print("COPY ERROR: Telegram response has no message_id")
            return None

        return copied_message_id

    except Exception as e:
        print("COPY ERROR:", e)
        return None


def save_analysis_copy(
    source_chat_id,
    source_message_id,
    target_chat_id,
    copied_message_id,
    symbol=None
):
    """شناسه آخرین کپی یک تحلیل را در چت مقصد ثبت می‌کند."""
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
                    symbol
                )
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (
                    source_chat_id,
                    source_message_id,
                    target_chat_id
                )
                DO UPDATE SET
                    copied_message_id = EXCLUDED.copied_message_id,
                    symbol = EXCLUDED.symbol,
                    copied_at = NOW()
                """,
                (
                    source_chat_id,
                    source_message_id,
                    target_chat_id,
                    copied_message_id,
                    symbol,
                )
            )
            connection.commit()
    except Exception as e:
        print("ANALYSIS COPY SAVE ERROR:", e)


def get_analysis_copy_message_id(
    source_chat_id,
    source_message_id,
    target_chat_id
):
    """message_id واقعیِ کپی‌شده در چت مقصد را برمی‌گرداند."""
    try:
        with get_db_connection() as connection:
            row = connection.execute(
                """
                SELECT copied_message_id
                FROM analysis_copies
                WHERE source_chat_id = %s
                  AND source_message_id = %s
                  AND target_chat_id = %s
                LIMIT 1
                """,
                (
                    source_chat_id,
                    source_message_id,
                    target_chat_id,
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
                SELECT
                    chat_id,
                    message_id,
                    message_date
                FROM analyses
                WHERE UPPER(TRIM(symbol)) = %s
                ORDER BY message_date DESC, id DESC
                LIMIT 2
                """,
                (symbol,)
            ).fetchall()

        else:
            rows = connection.execute(
                """
                SELECT
                    chat_id,
                    message_id,
                    message_date
                FROM analyses
                WHERE chat_id = %s
                  AND UPPER(TRIM(symbol)) = %s
                ORDER BY message_date DESC, id DESC
                LIMIT 2
                """,
                (
                    chat_id,
                    symbol
                )
            ).fetchall()

    return rows


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
        "تحلیل‌های امروزم",
    }:
        return "TODAY"

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

            if callback_chat_type in {
                "group",
                "supergroup"
            } and len(analyses) > 1:

                previous_source_chat = analyses[1][0]
                previous_source_message = analyses[1][1]

                # اولویت با message_id واقعیِ کپی‌شده در همین گروه است.
                reply_to_message_id = get_analysis_copy_message_id(
                    previous_source_chat,
                    previous_source_message,
                    callback_chat_id
                )

                # اگر تحلیل قبلی مستقیماً داخل همین گروه ثبت شده باشد،
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

            if not copied_message_id:

                send_message(
                    callback_chat_id,
                    "❌ ارسال تحلیل انجام نشد."
                )

            else:
                save_analysis_copy(
                    source_chat,
                    message_id,
                    callback_chat_id,
                    copied_message_id,
                    symbol
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


# =====================================================
# ثبت تحلیل عکس + هشتگ
# =====================================================

    if "photo" in message:

        caption = message.get(
            "caption",
            ""
        )

        # فقط تحلیل‌های خود کانال/گروه روی چارت ثبت شوند.
        # این شرط عمداً بر اساس @rooye_chart است، نه User ID فرستنده.
        if "@rooye_chart" not in caption.lower():
            return "ok"

        symbols = extract_analysis_symbols(
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
                photo_file_id
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

            if len(analyses) > 1:
                previous_source_chat = analyses[1][0]
                previous_source_message = analyses[1][1]

                # message_id پیام اصلیِ قبلی کافی نیست؛ برای Reply باید
                # شناسه همان پیام در گروه مقصد را داشته باشیم.
                reply_to_message_id = get_analysis_copy_message_id(
                    previous_source_chat,
                    previous_source_message,
                    chat_id
                )

                # اگر منبع تحلیل خودش همین گروه باشد، message_id منبع
                # همان message_id معتبر گروه است.
                if (
                    reply_to_message_id is None
                    and previous_source_chat == chat_id
                ):
                    reply_to_message_id = previous_source_message

            if reply_to_message_id is not None:

                copied_message_id = copy_analysis_message(
                    chat_id,
                    source_chat_id,
                    source_message_id,
                    reply_to_message_id=reply_to_message_id
                )

                if copied_message_id:
                    save_analysis_copy(
                        source_chat_id,
                        source_message_id,
                        chat_id,
                        copied_message_id,
                        symbol
                    )
                else:
                    send_message(
                        chat_id,
                        "⚠️ پیام تحلیل پیدا شد "
                        "ولی Telegram اجازه کپی "
                        "آن را نداد."
                    )

            else:

                # اگر هنوز شناسه پیام قبلی در گروه را نداریم، رفتار قدیمی
                # حفظ می‌شود. این حالت برای تحلیل‌های قدیمیِ قبل از ایجاد
                # جدول analysis_copies هم ممکن است رخ دهد.
                send_message(
                    chat_id,
                    f"📊 آخرین تحلیل {name}\n"
                    f"🕐 {analysis_time}",
                    reply_to_message_id=(
                        source_message_id
                        if source_chat_id == chat_id
                        else None
                    )
                )


        else:

            # چت خصوصی: خودِ message_id تحلیل قبلیِ گروه در این چت معتبر نیست.
            # اگر قبلاً تحلیل قبلی را برای همین کاربر کپی کرده‌ایم، به همان کپی Reply می‌کنیم.
            # اگر lookup دیتابیس به هر دلیل شکست خورد، همچنان تحلیل جدید را بدون Reply می‌فرستیم؛
            # بنابراین خراب شدن زنجیره نباید باعث شود دستور «تحلیل ...» هیچ پاسخی ندهد.
            reply_to_message_id = None

            try:
                if len(analyses) > 1:
                    previous_source_chat = analyses[1][0]
                    previous_source_message = analyses[1][1]
                    reply_to_message_id = get_analysis_copy_message_id(
                        previous_source_chat,
                        previous_source_message,
                        chat_id
                    )
            except Exception as e:
                print("PRIVATE REPLY LOOKUP ERROR:", e)
                reply_to_message_id = None

            print(
                "PRIVATE ANALYSIS:",
                "target=", chat_id,
                "source=", source_chat_id, source_message_id,
                "reply_to=", reply_to_message_id,
                "symbol=", symbol
            )

            copied_message_id = copy_analysis_message(
                chat_id,
                source_chat_id,
                source_message_id,
                reply_to_message_id=reply_to_message_id
            )

            if copied_message_id:
                save_analysis_copy(
                    source_chat_id,
                    source_message_id,
                    chat_id,
                    copied_message_id,
                    symbol
                )
            else:
                send_message(
                    chat_id,
                    "⚠️ پیام تحلیل پیدا شد "
                    "ولی Telegram اجازه کپی "
                    "آن را نداد."
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
                "• تحلیل های امروز"
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
