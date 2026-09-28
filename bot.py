from flask import Flask, request
import os
import re
import requests
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
# DATABASE
# =========================================================

def get_db_connection():
    database_url = os.environ.get("DATABASE_URL")

    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is not configured"
        )

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

    return text.replace("@", "").replace("$", "").strip()


# =========================================================
# ثبت تحلیل‌های عکس
# =========================================================

def extract_analysis_symbols(caption):
    hashtags = re.findall(
        r"#([A-Za-z0-9_]+)",
        caption or "",
    )

    symbols = set()

    for hashtag in hashtags:
        symbol = hashtag.upper().strip()

        if re.fullmatch(
            r"[A-Z0-9]{2,15}",
            symbol,
        ):
            symbols.add(symbol)

    return list(symbols)


def save_analysis(
    chat_id,
    message_id,
    symbol,
    message_date,
    photo_file_id=None,
):
    date_text = datetime.fromtimestamp(
        message_date,
        tz=ZoneInfo("Asia/Tehran"),
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
            ),
        )


# =========================================================
# تحلیل‌ها
# =========================================================

def get_latest_analysis_info(
    symbol,
    chat_id=None,
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
                (symbol,),
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
                    symbol,
                ),
            ).fetchone()

    return row


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
                (today,),
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
                    today,
                ),
            ).fetchall()

    return rows


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
        "",
    ).strip()

    remaining = remaining.replace(
        "های",
        "",
    ).strip()

    remaining = remaining.replace(
        "آخرین",
        "",
    ).strip()

    if remaining in ALIASES:
        return ALIASES[remaining]

    upper = remaining.upper()

    if re.fullmatch(
        r"[A-Z0-9]{2,15}",
        upper,
    ):
        return upper

    return None


# =========================================================
# CCXT
# =========================================================

def get_exchange_client(exchange_id):

    if exchange_id not in EXCHANGES:
        raise ValueError(
            "صرافی نامعتبر است."
        )

    if exchange_id not in _exchange_clients:

        ccxt_id = EXCHANGES[
            exchange_id
        ]["ccxt_id"]

        if not hasattr(
            ccxt,
            ccxt_id,
        ):
            raise RuntimeError(
                f"CCXT exchange '{ccxt_id}' "
                "is not available."
            )

        exchange_class = getattr(
            ccxt,
            ccxt_id,
        )

        _exchange_clients[
            exchange_id
        ] = exchange_class(
            {
                "enableRateLimit": True,
                "timeout": 10000,
            }
        )

    return _exchange_clients[
        exchange_id
    ]


def get_exchange_prices(
    exchange_id,
    asset,
):
    exchange = get_exchange_client(
        exchange_id
    )

    markets = exchange.load_markets()

    asset = asset.upper()

    irt_symbol = None
    irt_quote = None
    usdt_symbol = None

    # -----------------------------------------
    # آبان‌تتر
    # -----------------------------------------

    if exchange_id == "abantether":

        for direct_symbol in (
            f"{asset}/IRT",
            f"{asset}/IRR",
            f"{asset}/TMN",
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

    # -----------------------------------------
    # بررسی بازارهای CCXT
    # -----------------------------------------

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
                "IRR",
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

    if (
        not irt_symbol
        and not usdt_symbol
    ):
        raise LookupError(
            f"بازار {asset} در "
            f"{EXCHANGES[exchange_id]['name']} "
            "پیدا نشد."
        )

    # -----------------------------------------
    # قیمت ریالی
    # -----------------------------------------

    irt_price = None

    if irt_symbol:

        ticker = exchange.fetch_ticker(
            irt_symbol
        )

        last = ticker.get("last")

        if last is not None:

            irt_price = float(last)

            # ریال → تومان
            if irt_quote == "IRR":
                irt_price /= 10

    # -----------------------------------------
    # قیمت USDT
    # -----------------------------------------

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
# تشخیص درخواست قیمت
# =========================================================

def parse_price_request(text):

    normalized = normalize_text(text)

    if not normalized:
        return None, None

    exchange_id = None
    coin_text = normalized

    aliases = sorted(
        EXCHANGE_ALIASES.items(),
        key=lambda item: len(item[0]),
        reverse=True,
    )

    # مثال:
    # SOL نوبیتکس
    # سولانا نوبیتکس

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

    # مثال:
    # نوبیتکس SOL

    if exchange_id is None:

        for alias, ex_id in aliases:

            prefix = alias + " "

            if normalized.startswith(
                prefix
            ):

                coin_text = normalized[
                    len(prefix):
                ].strip()

                exchange_id = ex_id
                break

    if not coin_text:
        return None, exchange_id

    asset = ALIASES.get(
        coin_text,
        coin_text.upper(),
    )

    if not re.fullmatch(
        r"[A-Z0-9]{2,15}",
        asset,
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
                    "callback_data":
                        f"price:{asset}:nobitex",
                },
                {
                    "text": "🔵 تبدیل",
                    "callback_data":
                        f"price:{asset}:tabdeal",
                },
            ],
            [
                {
                    "text": "🟣 بیت‌پین",
                    "callback_data":
                        f"price:{asset}:bitpin",
                },
                {
                    "text": "🟠 آبان‌تتر",
                    "callback_data":
                        f"price:{asset}:abantether",
                },
            ],
        ]
    }


def send_exchange_menu(
    chat_id,
    asset,
):

    name = DISPLAY_NAMES.get(
        asset,
        asset,
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
# Telegram
# =========================================================

def answer_callback(
    callback_id,
    text=None,
):

    payload = {
        "callback_query_id":
            callback_id
    }

    if text:
        payload["text"] = text

    try:

        requests.post(
            f"https://api.telegram.org/"
            f"bot{BOT_TOKEN}/"
            f"answerCallbackQuery",
            json=payload,
            timeout=10,
        )

    except Exception as exc:
        print(
            "CALLBACK ANSWER ERROR:",
            exc,
        )


def send_message(
    chat_id,
    text,
    reply_to_message_id=None,
    reply_markup=None,
):

    payload = {
        "chat_id": chat_id,
        "text": text,
    }

    if reply_markup is not None:
        payload[
            "reply_markup"
        ] = reply_markup

    if reply_to_message_id is not None:

        payload[
            "reply_parameters"
        ] = {
            "message_id":
                reply_to_message_id
        }

    try:

        response = requests.post(
            f"https://api.telegram.org/"
            f"bot{BOT_TOKEN}/"
            f"sendMessage",
            json=payload,
            timeout=10,
        )

        print(
            "SEND:",
            response.status_code,
            response.text[:300],
        )

        return response.ok

    except Exception as exc:

        print(
            "SEND ERROR:",
            exc,
        )

        return False


def copy_analysis_message(
    target_chat_id,
    source_chat_id,
    source_message_id,
):

    payload = {
        "chat_id": target_chat_id,
        "from_chat_id": source_chat_id,
        "message_id": source_message_id,
    }

    try:

        response = requests.post(
            f"https://api.telegram.org/"
            f"bot{BOT_TOKEN}/"
            f"copyMessage",
            json=payload,
            timeout=10,
        )

        print(
            "COPY:",
            response.status_code,
            response.text[:500],
        )

        return response.ok

    except Exception as exc:

        print(
            "COPY ERROR:",
            exc,
        )

        return False


# =========================================================
# بررسی عضویت
# =========================================================

def check_channel_membership(
    user_id,
):

    try:

        response = requests.get(
            f"https://api.telegram.org/"
            f"bot{BOT_TOKEN}/"
            f"getChatMember",
            params={
                "chat_id":
                    "@rooye_chart",
                "user_id":
                    user_id,
            },
            timeout=10,
        )

        result = response.json()

        status = (
            result
            .get("result", {})
            .get("status")
        )

        return status in {
            "creator",
            "administrator",
            "member",
        }

    except Exception as exc:

        print(
            "MEMBERSHIP CHECK ERROR:",
            exc,
        )

        return None


# =========================================================
# پیام /start
# =========================================================

def send_start_message(
    chat_id,
):

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
        "• تحلیل های امروز",
    )


# =========================================================
# DB STATUS
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

    except Exception as exc:

        print(
            "DB STATUS ERROR:",
            exc,
        )

        return None


def get_symbol_db_status(
    symbol,
):

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
            ORDER BY message_date DESC, id DESC
            LIMIT 10
            """,
            (symbol,),
        ).fetchall()

    return rows


# =========================================================
# WEBHOOK
# =========================================================

@app.route(
    "/webhook",
    methods=["POST"],
)
def webhook():

    data = request.get_json(
        silent=True
    )

    if not data:
        return "ok"

    # =====================================================
    # CALLBACK
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
            "",
        )

        # -----------------------------------------------
        # انتخاب صرافی
        # -----------------------------------------------

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

                    answer_callback(
                        callback_id,
                        "در حال دریافت قیمت...",
                    )

                    callback_message = (
                        callback.get(
                            "message",
                            {},
                        )
                    )

                    callback_chat = (
                        callback_message.get(
                            "chat",
                            {},
                        )
                    )

                    callback_chat_id = (
                        callback_chat.get(
                            "id"
                        )
                    )

                    callback_message_id = (
                        callback_message.get(
                            "message_id"
                        )
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

        # -----------------------------------------------
        # بررسی عضویت
        # -----------------------------------------------

        if callback_data == (
            "check_membership"
        ):

            user_id = (
                callback
                .get("from", {})
                .get("id")
            )

            membership = (
                check_channel_membership(
                    user_id
                )
            )

            if membership is True:

                answer_callback(
                    callback_id,
                    "✅ عضویت شما تأیید شد.",
                )

                send_message(
                    user_id,
                    "✅ عضویت شما تأیید شد.\n\n"
                    "🤖 حالا می‌توانید "
                    "از ربات روی چارت استفاده کنید.",
                )

            elif membership is False:

                answer_callback(
                    callback_id,
                    "❌ هنوز عضو کانال روی چارت نیستید.",
                )

                send_message(
                    user_id,
                    "❌ عضویت شما تأیید نشد.\n\n"
                    "ابتدا عضو کانال روی چارت شوید "
                    "و سپس دوباره روی "
                    "«بررسی عضویت» بزنید.",
                )

            else:

                answer_callback(
                    callback_id,
                    "⚠️ خطا در بررسی عضویت.",
                )

            return "ok"

        answer_callback(
            callback_id
        )

        return "ok"

    # =====================================================
    # MESSAGE
    # =====================================================

    if "message" not in data:
        return "ok"

    message = data[
        "message"
    ]

    chat = message.get(
        "chat",
        {},
    )

    chat_id = chat.get(
        "id"
    )

    chat_type = chat.get(
        "type",
        "private",
    )

    message_id = message.get(
        "message_id"
    )

    message_date = message.get(
        "date"
    )

    if (
        chat_id is None
        or message_id is None
        or message_date is None
    ):
        return "ok"

    # =====================================================
    # MEMBERSHIP GATE
    #
    # نکته بسیار مهم:
    # اینجا فقط عضویت بررسی می‌شود.
    # دیگر بعد از هر پیام return نمی‌کنیم.
    # =====================================================

    if chat_type == "private":

        membership = (
            check_channel_membership(
                chat_id
            )
        )

        if membership is False:

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
                                    CHANNEL_URL,
                            }
                        ],
                        [
                            {
                                "text":
                                    "✅ بررسی عضویت",
                                "callback_data":
                                    "check_membership",
                            }
                        ],
                    ]
                },
            )

            return "ok"

        if membership is None:

            send_message(
                chat_id,
                "⚠️ در بررسی عضویت مشکلی پیش آمد. "
                "لطفاً چند لحظه بعد دوباره تلاش کنید.",
            )

            return "ok"

    # =====================================================
    # COMMANDS
    # =====================================================

    text_for_command = (
        message
        .get("text", "")
        .strip()
    )

    # /dbstatus

    if (
        chat_type == "private"
        and text_for_command
        == "/dbstatus"
    ):

        status = get_db_status()

        if status is None:

            send_message(
                chat_id,
                "❌ خطا در خواندن دیتابیس.",
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
                latest_ts,
            ) in by_symbol:

                latest = (
                    datetime.fromtimestamp(
                        latest_ts,
                        tz=ZoneInfo(
                            "Asia/Tehran"
                        ),
                    ).strftime(
                        "%Y-%m-%d %H:%M"
                    )
                )

                reply += (
                    f"• {symbol}: "
                    f"{count} رکورد | "
                    f"{latest}\n"
                )

        else:

            reply += (
                "هیچ تحلیلی در دیتابیس "
                "وجود ندارد."
            )

        send_message(
            chat_id,
            reply,
        )

        return "ok"

    # /dbsymbol

    if (
        chat_type == "private"
        and text_for_command.startswith(
            "/dbsymbol"
        )
    ):

        parts = (
            text_for_command.split(
                maxsplit=1
            )
        )

        if len(parts) != 2:

            send_message(
                chat_id,
                "مثال: /dbsymbol NEAR",
            )

            return "ok"

        symbol = (
            parts[1]
            .strip()
            .upper()
        )

        rows = get_symbol_db_status(
            symbol
        )

        if not rows:

            send_message(
                chat_id,
                f"🔎 برای {symbol} "
                "هیچ رکوردی در دیتابیس پیدا نشد.",
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
            date_text,
        ) in rows:

            dt = (
                datetime.fromtimestamp(
                    ts,
                    tz=ZoneInfo(
                        "Asia/Tehran"
                    ),
                ).strftime(
                    "%Y-%m-%d %H:%M"
                )
            )

            reply += (
                f"• {dt}\n"
                f"  chat_id: "
                f"{db_chat_id}\n"
                f"  message_id: "
                f"{db_message_id}\n"
                f"  date_text: "
                f"{date_text}\n\n"
            )

        send_message(
            chat_id,
            reply,
        )

        return "ok"

    # =====================================================
    # PHOTO + HASHTAGS
    # =====================================================

    if "photo" in message:

        caption = message.get(
            "caption",
            "",
        )

        symbols = (
            extract_analysis_symbols(
                caption
            )
        )

        photo_file_id = (
            message["photo"][-1]["file_id"]
        )

        for symbol in symbols:

            save_analysis(
                chat_id,
                message_id,
                symbol,
                message_date,
                photo_file_id,
            )

        return "ok"

    # =====================================================
    # TEXT
    # =====================================================

    text = (
        message
        .get("text", "")
        .strip()
    )

    if not text:
        return "ok"

    # =====================================================
    # /start
    # =====================================================

    if text == "/start":

        send_start_message(
            chat_id
        )

        return "ok"

    # =====================================================
    # ANALYSIS REQUEST
    # =====================================================

    analysis_request = (
        extract_analysis_request(
            text
        )
    )

    # -----------------------------------------------------
    # تحلیل‌های امروز
    # -----------------------------------------------------

    if analysis_request == "TODAY":

        search_chat_id = (
            chat_id
            if chat_type
            in {
                "group",
                "supergroup",
            }
            else None
        )

        rows = (
            get_today_analyses(
                search_chat_id
            )
        )

        if not rows:

            send_message(
                chat_id,
                "📊 امروز هنوز تحلیلی ثبت نشده است.",
            )

            return "ok"

        latest = {}

        for (
            symbol,
            msg_id,
            source_chat,
            msg_date,
        ) in rows:

            if (
                symbol not in latest
                or msg_date
                >= latest[symbol][3]
            ):

                latest[symbol] = (
                    symbol,
                    msg_id,
                    source_chat,
                    msg_date,
                )

        reply = (
            "📊 تحلیل‌های امروز روی چارت\n\n"
        )

        for symbol in latest:

            reply += (
                f"• "
                f"{DISPLAY_NAMES.get(symbol, symbol)} "
                f"#{symbol}\n"
            )

        send_message(
            chat_id,
            reply,
        )

        if chat_type == "private":

            for (
                symbol,
                (
                    _,
                    msg_id,
                    source_chat,
                    _,
                ),
            ) in latest.items():

                copy_analysis_message(
                    chat_id,
                    source_chat,
                    msg_id,
                )

        return "ok"

    # -----------------------------------------------------
    # آخرین تحلیل یک ارز
    # -----------------------------------------------------

    if analysis_request:

        symbol = analysis_request

        search_chat_id = (
            chat_id
            if chat_type
            in {
                "group",
                "supergroup",
            }
            else None
        )

        row = (
            get_latest_analysis_info(
                symbol,
                search_chat_id,
            )
        )

        if not row:

            send_message(
                chat_id,
                f"❌ هنوز تحلیلی برای "
                f"{DISPLAY_NAMES.get(symbol, symbol)} "
                "ثبت نشده است.",
            )

            return "ok"

        (
            source_chat_id,
            source_message_id,
            analysis_date,
        ) = row

        name = DISPLAY_NAMES.get(
            symbol,
            symbol,
        )

        analysis_time = (
            datetime.fromtimestamp(
                analysis_date,
                tz=ZoneInfo(
                    "Asia/Tehran"
                ),
            ).strftime(
                "%Y-%m-%d | %H:%M"
            )
        )

        if chat_type in {
            "group",
            "supergroup",
        }:

            send_message(
                chat_id,
                f"📊 آخرین تحلیل {name}\n"
                f"🕐 {analysis_time}",
                reply_to_message_id=
                    source_message_id,
            )

        else:

            send_message(
                chat_id,
                f"📊 آخرین تحلیل {name}\n"
                f"🕐 {analysis_time}",
            )

            if not copy_analysis_message(
                chat_id,
                source_chat_id,
                source_message_id,
            ):

                send_message(
                    chat_id,
                    "⚠️ پیام تحلیل پیدا شد "
                    "ولی Telegram اجازه کپی "
                    "آن را نداد.",
                )

        return "ok"

    # =====================================================
    # PRICE REQUEST
    #
    # این قسمت عمداً قبل از فیلتر گروه قرار گرفته.
    # بنابراین:
    #
    # SOL
    # سولانا
    # SOL نوبیتکس
    # سولانا تبدیل
    #
    # همگی به بخش قیمت می‌رسند.
    # =====================================================

    asset, requested_exchange = (
        parse_price_request(text)
    )

    if asset:

        # فقط نام ارز
        if requested_exchange is None:

            send_exchange_menu(
                chat_id,
                asset,
            )

            return "ok"

        # ارز + صرافی
        if requested_exchange in EXCHANGES:

            send_exchange_price(
                chat_id,
                asset,
                requested_exchange,
            )

            return "ok"

    # =====================================================
    # گروه
    # =====================================================

    if chat_type in {
        "group",
        "supergroup",
    }:

        return "ok"

    # =====================================================
    # درخواست نامشخص در خصوصی
    # =====================================================

    send_message(
        chat_id,

        "❌ درخواست قابل تشخیص نیست.\n\n"

        "مثال:\n"
        "• سولانا\n"
        "• SOL\n"
        "• سولانا تبدیل\n"
        "• سولانا نوبیتکس",
    )

    return "ok"


# =========================================================
# START SERVER
# =========================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(
            os.environ.get(
                "PORT",
                10000,
            )
        ),
    )
