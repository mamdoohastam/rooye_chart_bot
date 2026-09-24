from flask import Flask, request
import requests
import os
import sqlite3
import re
from datetime import datetime
from zoneinfo import ZoneInfo

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")

DB_FILE = "analyses.db"

TEHRAN = ZoneInfo("Asia/Tehran")


# =========================================================
# نام فارسی ارزها مطابق نام‌های رایج در تبدیل
# =========================================================

ALIASES = {

    # -------------------------
    # اصلی
    # -------------------------

    "تتر": "USDT",
    "دلار": "USDT",

    "بیت کوین": "BTC",
    "بیتکوین": "BTC",
    "بیت‌کوین": "BTC",

    "اتریوم": "ETH",

    "سولانا": "SOL",

    "ریپل": "XRP",

    "ترون": "TRX",

    "دوج": "DOGE",
    "دوج کوین": "DOGE",
    "دوج‌کوین": "DOGE",

    "بی ان بی": "BNB",
    "بی‌ان‌بی": "BNB",

    "کاردانو": "ADA",

    "تون": "TON",
    "تون کوین": "TON",

    "پولکادات": "DOT",

    "آوالانچ": "AVAX",

    "لایت کوین": "LTC",
    "لایت‌کوین": "LTC",

    "شیبا": "SHIB",

    "پپه": "PEPE",

    "چین لینک": "LINK",
    "چین‌لینک": "LINK",

    # -------------------------
    # ارزهای لایه اول / معروف
    # -------------------------

    "نیر": "NEAR",

    "آپتوس": "APT",

    "سویی": "SUI",

    "کازماس": "ATOM",

    "الگورند": "ALGO",

    "هدرا": "HBAR",

    "استلار": "XLM",

    "الگوراند": "ALGO",

    "تزوس": "XTZ",

    "ایاس": "EOS",

    "مونرو": "XMR",

    "کوانت": "QNT",

    "فلو": "FLOW",

    "اینترنت کامپیوتر": "ICP",

    "کاسپا": "KAS",

    "کرونوس": "CRO",

    "هلیوم": "HNT",

    "رندر": "RENDER",
    "رندر توکن": "RENDER",

    # -------------------------
    # اتریوم / DeFi
    # -------------------------

    "یونی سواپ": "UNI",
    "یونی‌سواپ": "UNI",

    "آوه": "AAVE",

    "میکر": "MKR",

    "لیدو": "LDO",

    "میکر دائو": "MKR",

    "پنکیک سواپ": "CAKE",
    "پنکیک‌سواپ": "CAKE",

    "سوشی": "SUSHI",

    "کامپاند": "COMP",

    "کریو": "CRV",

    "مپل": "MPL",

    # -------------------------
    # لایه دوم
    # -------------------------

    "آربیتروم": "ARB",

    "آپتیمیسم": "OP",

    "استارک نت": "STRK",
    "استارک‌نت": "STRK",

    "منتل": "MNT",

    "زک سینک": "ZK",
    "zk": "ZK",

    "اسکرول": "SCR",

    "پالیگان": "POL",
    "متیک": "POL",

    # -------------------------
    # پروژه‌های جدیدتر
    # -------------------------

    "سلستیا": "TIA",

    "مانتا": "MANTA",

    "جیتو": "JTO",

    "جاپیتر": "JUP",

    "پایت": "PYTH",

    "پندل": "PENDLE",

    "بلاسوم": "BLAST",

    "زد کی سینک": "ZK",

    # -------------------------
    # هوش مصنوعی
    # -------------------------

    "فت": "FET",
    "آلترا": "TAO",
    "بیت تنسور": "TAO",

    "آکاش": "AKT",

    "ورلد کوین": "WLD",

    "ورلد": "WLD",

    "بیتنسر": "TAO",

    # -------------------------
    # گیمینگ
    # -------------------------

    "ایموتبل ایکس": "IMX",

    "سندباکس": "SAND",

    "مانا": "MANA",

    "انجین": "ENJ",

    "گالا": "GALA",

    "ایپ کوین": "APE",

    "رون": "RON",

    # -------------------------
    # میم کوین
    # -------------------------

    "فلوکی": "FLOKI",

    "بونک": "BONK",

    "برِت": "BRETT",

    "بون": "BONE",

    "شیبا اینو": "SHIB",

    # -------------------------
    # قدیمی / شناخته‌شده
    # -------------------------

    "لیسک": "LSK",

    "ریون": "RVN",

    "ویچین": "VET",

    "اتم": "ATOM",

    "ایپ کوین": "APE",

    "تزوس": "XTZ",

    "نم": "XEM",

    "دش": "DASH",

    "زی کش": "ZEC",
    "زی‌کش": "ZEC",

    "دیکرد": "DCR",

    # -------------------------
    # توکن‌های مختلف
    # -------------------------

    "وتور توکن": "VTHO",

    "توکو توکن": "TKO",

    "تراست والت توکن": "TWT",

    "اس اس وی": "SSV",

    "آربیتروم": "ARB",

    "استارک نت": "STRK",

    "اسکیل": "SKL",

    "انکر": "ANKR",

    "سلر": "CELR",

    "اسک": "SKL",

    "بند": "BAND",

    "اوشن": "OCEAN",

    "گراف": "GRT",

    "سان": "SUN",

    "آربی": "ARB",

    # -------------------------
    # TON / Telegram
    # -------------------------

    "نات کوین": "NOT",

    "نات": "NOT",

    "داگز": "DOGS",

    "همستر": "HMSTR",

    # -------------------------
    # موارد خاص
    # -------------------------

    "تورچین": "RUNE",

    "تورچین": "RUNE",

    "کرو دائو": "CRV",

    "سینتتیکس": "SNX",

    "آپتوس": "APT",

    "استکس": "STX",

    "استک": "STX",

    "کانستنت": "CONST",

    "فایل کوین": "FIL",

    "آربیتروم": "ARB",

    "اینجکتیو": "INJ",

    "سِی": "SEI",
    "سی": "SEI",

    "مانترا": "OM",

    "اوندو": "ONDO",

    "بِراچین": "BERA",

    "برچین": "BERA",
}


# =========================================================
# دیتابیس
# =========================================================

def get_db():

    conn = sqlite3.connect(
        DB_FILE,
        timeout=10
    )

    conn.row_factory = sqlite3.Row

    return conn


def init_db():

    conn = get_db()

    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            message_id INTEGER NOT NULL,
            symbol TEXT NOT NULL,
            message_date INTEGER NOT NULL,
            date_text TEXT NOT NULL
        )
    """)

    conn.commit()

    conn.close()


init_db()


# =========================================================
# نرمال سازی فارسی
# =========================================================

def normalize_text(text):

    if not text:
        return ""

    text = text.strip()

    text = text.replace(
        "ي",
        "ی"
    )

    text = text.replace(
        "ى",
        "ی"
    )

    text = text.replace(
        "ك",
        "ک"
    )

    text = text.replace(
        "‌",
        " "
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# =========================================================
# گرفتن بازارهای تبدیل
# =========================================================

def get_markets():

    url = (
        "https://api1.tabdeal.org/"
        "r/api/v1/exchangeInfo"
    )

    response = requests.get(
        url,
        timeout=10
    )

    response.raise_for_status()

    data = response.json()

    if isinstance(data, list):

        return data

    return data.get(
        "symbols",
        []
    )


# =========================================================
# پیدا کردن نماد از متن
# =========================================================

def find_symbol_from_text(text):

    text = normalize_text(
        text
    )

    lower = text.lower()

    # اول نام فارسی
    aliases = sorted(
        ALIASES.items(),
        key=lambda x: len(x[0]),
        reverse=True
    )

    for name, symbol in aliases:

        if name.lower() in lower:

            return symbol


    # اگر نام فارسی پیدا نشد،
    # دنبال نماد انگلیسی بگرد

    words = re.findall(
        r"[A-Za-z0-9]{2,20}",
        text
    )

    ignored = {
        "تحلیل",
        "امروز",
        "TODAY"
    }

    for word in words:

        upper = word.upper()

        if upper in ignored:
            continue

        if re.fullmatch(
            r"[A-Z0-9]{2,20}",
            upper
        ):

            return upper


    return None


# =========================================================
# پیدا کردن بازار تومانی
# =========================================================

def find_irt_market(asset):

    asset = asset.upper()

    markets = get_markets()

    for market in markets:

        if market.get(
            "status"
        ) != "TRADING":

            continue

        if market.get(
            "quoteAsset"
        ) != "IRT":

            continue

        base = market.get(
            "baseAsset",
            ""
        ).upper()

        if base == asset:

            return market.get(
                "symbol"
            )

    return None


# =========================================================
# قیمت
# =========================================================

def get_price(
    symbol
):

    url = (
        "https://api1.tabdeal.org/"
        "r/api/v1/depth"
    )

    response = requests.get(
        url,
        params={
            "symbol": symbol,
            "limit": 1
        },
        timeout=10
    )

    response.raise_for_status()

    data = response.json()

    asks = data.get(
        "asks",
        []
    )

    if not asks:

        return None

    return float(
        asks[0][0]
    )


# =========================================================
# استخراج هشتگ‌های تحلیل
# =========================================================

def extract_symbols_from_caption(
    caption
):

    if not caption:

        return []

    hashtags = re.findall(
        r"#([A-Za-z0-9_]+)",
        caption
    )

    symbols = []

    for hashtag in hashtags:

        symbol = hashtag.upper()

        if re.fullmatch(
            r"[A-Z0-9]{2,20}",
            symbol
        ):

            symbols.append(
                symbol
            )

    return list(
        dict.fromkeys(symbols)
    )


# =========================================================
# ذخیره تحلیل
# =========================================================

def save_analysis(
    chat_id,
    message_id,
    symbol,
    message_date
):

    dt = datetime.fromtimestamp(
        message_date,
        tz=TEHRAN
    )

    date_text = dt.strftime(
        "%Y-%m-%d"
    )

    conn = get_db()

    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO analyses
        (
            chat_id,
            message_id,
            symbol,
            message_date,
            date_text
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            chat_id,
            message_id,
            symbol,
            message_date,
            date_text
        )
    )

    conn.commit()

    conn.close()


# =========================================================
# آخرین تحلیل یک ارز
# =========================================================

def get_latest_analysis(
    chat_id,
    symbol
):

    conn = get_db()

    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT *
        FROM analyses
        WHERE chat_id = ?
        AND symbol = ?
        ORDER BY message_date DESC
        LIMIT 1
        """,
        (
            chat_id,
            symbol
        )
    )

    result = cursor.fetchone()

    conn.close()

    return result


# =========================================================
# آخرین تحلیل‌های امروز، بدون تکرار ارز
# =========================================================

def get_today_latest_analyses(
    chat_id
):

    today = datetime.now(
        TEHRAN
    ).strftime(
        "%Y-%m-%d"
    )

    conn = get_db()

    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT *
        FROM analyses
        WHERE chat_id = ?
        AND date_text = ?
        ORDER BY message_date DESC
        """,
        (
            chat_id,
            today
        )
    )

    rows = cursor.fetchall()

    conn.close()


    # فقط آخرین تحلیل هر ارز
    latest = {}

    for row in rows:

        symbol = row["symbol"]

        if symbol not in latest:

            latest[symbol] = row


    return list(
        latest.values()
    )


# =========================================================
# نام نمایشی ارز
# =========================================================

DISPLAY_NAMES = {

    "BTC": "بیت‌کوین",
    "ETH": "اتریوم",
    "SOL": "سولانا",
    "XRP": "ریپل",
    "TRX": "ترون",
    "DOGE": "دوج‌کوین",
    "BNB": "BNB",
    "ADA": "کاردانو",
    "TON": "تون کوین",
    "DOT": "پولکادات",
    "AVAX": "آوالانچ",
    "LTC": "لایت‌کوین",
    "SHIB": "شیبا",
    "PEPE": "پپه",
    "LINK": "چین‌لینک",
    "APT": "آپتوس",
    "SUI": "سویی",
    "ARB": "آربیتروم",
    "OP": "آپتیمیسم",
    "STRK": "استارک‌نت",
    "TIA": "سلستیا",
    "MANTA": "مانتا",
    "FET": "فت",
    "TAO": "بیت‌تنسر",
    "WLD": "ورلد کوین",
    "INJ": "اینجکتیو",
    "NEAR": "نیر",
    "ICP": "اینترنت کامپیوتر",
    "HBAR": "هدرا",
    "XLM": "استلار",
    "ALGO": "الگوراند",
    "XTZ": "تزوس",
    "ATOM": "کازماس",
    "ICP": "اینترنت کامپیوتر",
    "KAS": "کاسپا",
    "RENDER": "رندر",
    "AAVE": "آوه",
    "UNI": "یونی‌سواپ",
    "MKR": "میکر",
    "LDO": "لیدو",
    "CAKE": "پنکیک‌سواپ",
    "SAND": "سندباکس",
    "MANA": "مانا",
    "IMX": "ایمیوتبل ایکس",
    "GALA": "گالا",
    "APE": "ایپ کوین",
    "FLOKI": "فلوکی",
    "BONK": "بونک",
    "LSK": "لیسک",
    "VET": "ویچین",
    "DASH": "دش",
    "ZEC": "زی‌کش",
    "FIL": "فایل‌کوین",
    "STX": "استکس",
    "SEI": "سی",
    "OM": "مانترا",
    "ONDO": "اوندو",
    "NOT": "نات‌کوین",
    "DOGS": "داگز",
    "HMSTR": "همستر",
    "RUNE": "تورچین",
    "SNX": "سینتتیکس",
    "VTHO": "وتور توکن",
    "TWT": "تراست والت توکن",
    "TKO": "توکو توکن",
}


# =========================================================
# ارسال پیام
# =========================================================

def send_message(
    chat_id,
    text,
    reply_to=None
):

    url = (
        f"https://api.telegram.org/"
        f"bot{BOT_TOKEN}/sendMessage"
    )

    payload = {
        "chat_id": chat_id,
        "text": text
    }

    if reply_to:

        payload[
            "reply_parameters"
        ] = {
            "message_id": reply_to
        }

    requests.post(
        url,
        json=payload,
        timeout=10
    )


# =========================================================
# تشخیص درخواست تحلیل
# =========================================================

def is_analysis_request(
    text
):

    text = normalize_text(
        text
    )

    return (
        "تحلیل" in text
    )


# =========================================================
# تشخیص درخواست تحلیل‌های امروز
# =========================================================

def is_today_request(
    text
):

    text = normalize_text(
        text
    )

    compact = text.replace(
        " ",
        ""
    )

    return (
        compact == "تحلیلهایامروز"
        or
        compact == "تحلیلهایروز"
        or
        compact == "تحلیلامروز"
    )


# =========================================================
# تشخیص اینکه پیام احتمالاً درخواست قیمت است
# =========================================================

def looks_like_coin(
    text
):

    text = normalize_text(
        text
    )

    if text in ALIASES:

        return True

    if re.fullmatch(
        r"[A-Za-z0-9]{2,20}",
        text
    ):

        return True

    return False


# =========================================================
# Home
# =========================================================

@app.route("/")
def home():

    return "Rooye Chart Bot is running"


# =========================================================
# Webhook
# =========================================================

@app.route(
    "/webhook",
    methods=["POST"]
)
def webhook():

    try:

        data = request.get_json()

        if not data:

            return "ok"


        if "message" not in data:

            return "ok"


        message = data[
            "message"
        ]

        chat = message.get(
            "chat",
            {}
        )

        chat_id = chat.get(
            "id"
        )

        chat_type = chat.get(
            "type",
            ""
        )

        message_id = message.get(
            "message_id"
        )

        message_date = message.get(
            "date",
            int(
                datetime.now().timestamp()
            )
        )


        # =================================================
        # ثبت تحلیل از روی عکس + هشتگ
        # =================================================

        if "photo" in message:

            caption = message.get(
                "caption",
                ""
            )

            symbols = (
                extract_symbols_from_caption(
                    caption
                )
            )

            for symbol in symbols:

                # فقط اگر بازار تومانی
                # در تبدیل وجود دارد ذخیره کن
                market = find_irt_market(
                    symbol
                )

                if market:

                    save_analysis(
                        chat_id,
                        message_id,
                        symbol,
                        message_date
                    )

            return "ok"


        # =================================================
        # متن
        # =================================================

        text = message.get(
            "text",
            ""
        ).strip()


        if not text:

            return "ok"


        # =================================================
        # START
        # =================================================

        if text.lower() == "/start":

            send_message(
                chat_id,

                "🤖 ربات روی چارت\n\n"
                "برای قیمت، نام یا نماد ارز را "
                "بنویسید.\n\n"
                "برای تحلیل:\n"
                "تحلیل سولانا\n"
                "تحلیل FET\n"
                "تحلیل لیسک\n\n"
                "برای همه تحلیل‌های امروز:\n"
                "تحلیل های امروز"
            )

            return "ok"


        # =================================================
        # تحلیل‌های امروز
        # =================================================

        if is_today_request(
            text
        ):

            results = (
                get_today_latest_analyses(
                    chat_id
                )
            )


            if not results:

                send_message(
                    chat_id,
                    "📊 امروز هنوز "
                    "تحلیلی ثبت نشده است."
                )

                return "ok"


            reply = (
                "📊 تحلیل‌های امروز "
                "روی چارت\n\n"
            )


            # مرتب کردن از قدیمی به جدید
            results = sorted(
                results,
                key=lambda x:
                    x["message_date"]
            )


            for result in results:

                symbol = result[
                    "symbol"
                ]

                name = DISPLAY_NAMES.get(
                    symbol,
                    symbol
                )

                reply += (
                    f"• {name} "
                    f"#{symbol}\n"
                )


            send_message(
                chat_id,
                reply
            )

            return "ok"


        # =================================================
        # درخواست تحلیل
        # =================================================

        if is_analysis_request(
            text
        ):

            symbol = (
                find_symbol_from_text(
                    text
                )
            )


            if not symbol:

                send_message(
                    chat_id,
                    "❌ ارز موردنظر "
                    "تشخیص داده نشد."
                )

                return "ok"


            result = (
                get_latest_analysis(
                    chat_id,
                    symbol
                )
            )


            if not result:

                send_message(
                    chat_id,

                    "❌ هنوز تحلیلی برای "
                    f"{DISPLAY_NAMES.get(symbol, symbol)} "
                    "ثبت نشده است."
                )

                return "ok"


            name = DISPLAY_NAMES.get(
                symbol,
                symbol
            )


            send_message(
                chat_id,

                f"📊 آخرین تحلیل "
                f"{name}",

                reply_to=result[
                    "message_id"
                ]
            )

            return "ok"


        # =================================================
        # فیلتر گروه
        # =================================================

        if chat_type in [
            "group",
            "supergroup"
        ]:

            if not looks_like_coin(
                text
            ):

                return "ok"


        # =================================================
        # قیمت
        # =================================================

        asset = (
            find_symbol_from_text(
                text
            )
        )


        if not asset:

            if chat_type in [
                "group",
                "supergroup"
            ]:

                return "ok"

            send_message(
                chat_id,
                "❌ ارز شناخته نشد."
            )

            return "ok"


        # =================================================
        # بازار تومانی
        # =================================================

        market = find_irt_market(
            asset
        )


        if not market:

            if chat_type in [
                "group",
                "supergroup"
            ]:

                return "ok"

            send_message(
                chat_id,

                "❌ این ارز در بازار "
                "تومانی تبدیل پیدا نشد."
            )

            return "ok"


        # =================================================
        # قیمت تومان
        # =================================================

        toman_price = None

        try:

            toman_price = get_price(
                market
            )

        except Exception as e:

            print(
                "TOMAN PRICE ERROR:",
                e
            )


        # =================================================
        # قیمت تتر
        # =================================================

        usdt_price = None

        if asset != "USDT":

            try:

                usdt_market = (
                    asset + "USDT"
                )

                usdt_price = get_price(
                    usdt_market
                )

            except Exception as e:

                print(
                    "USDT PRICE ERROR:",
                    e
                )


        if (
            toman_price is None
            and
            usdt_price is None
        ):

            if chat_type in [
                "group",
                "supergroup"
            ]:

                return "ok"

            send_message(
                chat_id,

                "❌ قیمت این ارز در حال "
                "حاضر دریافت نشد."
            )

            return "ok"


        name = DISPLAY_NAMES.get(
            asset,
            text
        )


        reply = (
            f"🪙 {name}\n\n"
        )


        if toman_price is not None:

            reply += (
                f"🇮🇷 تومان: "
                f"{toman_price:,.0f}\n"
            )


        if usdt_price is not None:

            usdt_text = (
                f"{usdt_price:.8f}"
                .rstrip("0")
                .rstrip(".")
            )

            reply += (
                f"💵 تتر: "
                f"{usdt_text} USDT"
            )


        send_message(
            chat_id,
            reply
        )


    except Exception as e:

        print(
            "GENERAL ERROR:",
            repr(e)
        )

    return "ok"


# =========================================================
# اجرای برنامه
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
