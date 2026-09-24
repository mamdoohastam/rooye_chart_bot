from flask import Flask, request
import requests
import os
import re
import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")

DB_FILE = "analyses.db"

TEHRAN = ZoneInfo("Asia/Tehran")


# =========================================================
# لینک‌های روی چارت
# =========================================================

CHANNEL_URL = "https://t.me/Rooye_chart"
GROUP_URL = "https://t.me/Rooye_chart_gap"


# =========================================================
# نام‌های فارسی شناخته‌شده
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

    # STRK
    "استارک نت": "STRK",
    "استارک‌نت": "STRK",
    "استارکنت": "STRK",
}


# =========================================================
# نام‌های نمایشی
# =========================================================

DISPLAY_NAMES = {
    "BTC": "بیت‌کوین",
    "ETH": "اتریوم",
    "SOL": "سولانا",
    "TRX": "ترون",
    "DOGE": "دوج‌کوین",
    "XRP": "ریپل",
    "BNB": "BNB",
    "TON": "تون کوین",
    "ADA": "کاردانو",
    "SHIB": "شیبا",
    "PEPE": "پپه",
    "APT": "آپتوس",
    "NOT": "نات‌کوین",
    "LINK": "چین‌لینک",
    "DOT": "پولکادات",
    "AVAX": "آوالانچ",
    "LTC": "لایت‌کوین",
    "USDT": "تتر",
    "LSK": "لیسک",
    "FET": "فت",
    "ARB": "آربیتروم",
    "OP": "آپتیمیسم",
    "SUI": "سویی",
    "NEAR": "نیر",
    "INJ": "اینجکتیو",
    "ONDO": "اوندو",
    "OM": "مانترا",
    "STX": "استکس",
    "FIL": "فایل‌کوین",
    "GALA": "گالا",
    "SAND": "سندباکس",
    "MANA": "مانا",
    "UNI": "یونی‌سواپ",
    "AAVE": "آوه",
    "MKR": "میکر",
    "LDO": "لیدو",
    "CAKE": "پنکیک‌سواپ",
    "ATOM": "کازماس",
    "HBAR": "هدرا",
    "XLM": "استلار",
    "ALGO": "الگوراند",
    "XTZ": "تزوس",
    "KAS": "کاسپا",
    "RENDER": "رندر",
    "WLD": "ورلد کوین",
    "TAO": "بیت‌تنسر",
    "PYTH": "پایت",
    "JTO": "جیتو",
    "JUP": "جاپیتر",
    "TIA": "سلستیا",
    "MANTA": "مانتا",
    "PENDLE": "پندل",
    "RUNE": "تورچین",
    "SNX": "سینتتیکس",
    "FLOKI": "فلوکی",
    "BONK": "بونک",
    "DOGS": "داگز",
    "HMSTR": "همستر",
    "VTHO": "وتور توکن",
    "TWT": "تراست والت توکن",
    "TKO": "توکو توکن",

    # STRK
    "STRK": "استارک نت",
}


# =========================================================
# اتصال دیتابیس
# =========================================================

def get_connection():

    return sqlite3.connect(
        DB_FILE,
        timeout=10
    )


# =========================================================
# ساخت / به‌روزرسانی دیتابیس
# =========================================================

def init_database():

    connection = get_connection()
    cursor = connection.cursor()

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

    cursor.execute(
        "PRAGMA table_info(analyses)"
    )

    columns = [
        row[1]
        for row in cursor.fetchall()
    ]

    # ستون caption برای نسخه‌های قدیمی
    if "caption" not in columns:

        cursor.execute("""
            ALTER TABLE analyses
            ADD COLUMN caption TEXT DEFAULT ''
        """)

    # متن نرمال‌شده برای جست‌وجوی بهتر
    if "search_text" not in columns:

        cursor.execute("""
            ALTER TABLE analyses
            ADD COLUMN search_text TEXT DEFAULT ''
        """)

    connection.commit()
    connection.close()


init_database()


# =========================================================
# نرمال‌سازی متن
# =========================================================

def normalize_text(text):

    if not text:
        return ""

    text = str(text).strip()

    # حروف عربی → فارسی
    text = text.replace("ي", "ی")
    text = text.replace("ى", "ی")
    text = text.replace("ك", "ک")

    # نیم‌فاصله → فاصله
    text = text.replace("‌", " ")

    # حذف فاصله‌های اضافی
    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# =========================================================
# نسخه فشرده متن
#
# مثال:
# استارک نت
# استارک‌نت
# استارکنت
#
# هر سه → استارکنت
# =========================================================

def compact_text(text):

    text = normalize_text(text)

    return re.sub(
        r"\s+",
        "",
        text
    )


# =========================================================
# استخراج هشتگ‌های تحلیل
# =========================================================

def extract_analysis_symbols(caption):

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

            symbols.append(symbol)

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
    message_date,
    caption=""
):

    tehran_time = datetime.fromtimestamp(
        message_date,
        tz=TEHRAN
    )

    date_text = tehran_time.strftime(
        "%Y-%m-%d"
    )

    normalized_caption = normalize_text(
        caption
    )

    search_text = compact_text(
        normalized_caption
    )

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO analyses
        (
            chat_id,
            message_id,
            symbol,
            message_date,
            date_text,
            caption,
            search_text
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            chat_id,
            message_id,
            symbol,
            message_date,
            date_text,
            caption,
            search_text
        )
    )

    connection.commit()
    connection.close()

    print(
        f"SAVED ANALYSIS: "
        f"{symbol} | "
        f"chat={chat_id} | "
        f"message={message_id}"
    )


# =========================================================
# ذخیره یک پیام تحلیل
#
# هم برای پیام متنی
# هم برای عکس + کپشن
# =========================================================

def save_analysis_message(
    chat_id,
    message_id,
    message_date,
    text
):

    if not text:
        return False

    symbols = extract_analysis_symbols(
        text
    )

    if not symbols:
        return False

    for symbol in symbols:

        save_analysis(
            chat_id,
            message_id,
            symbol,
            message_date,
            text
        )

    return True


# =========================================================
# آخرین تحلیل بر اساس نماد
# =========================================================

def get_latest_analysis(
    chat_id,
    symbol
):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT message_id
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

    connection.close()

    if result:
        return result[0]

    return None


# =========================================================
# پیدا کردن آخرین تحلیل با نام فارسی
#
# این قسمت نسبت به نسخه قبلی قوی‌تر شده:
#
# استارک نت
# استارک‌نت
# استارکنت
#
# هر سه می‌توانند یک تحلیل را پیدا کنند.
# =========================================================

def get_latest_analysis_by_name(
    chat_id,
    name
):

    name = normalize_text(
        name
    )

    if not name:
        return None

    compact_name = compact_text(
        name
    )

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT message_id, symbol, caption, search_text
        FROM analyses
        WHERE chat_id = ?
        ORDER BY message_date DESC
        """,
        (
            chat_id,
        )
    )

    rows = cursor.fetchall()

    connection.close()

    # اول جست‌وجوی دقیق‌تر
    for row in rows:

        message_id = row[0]
        symbol = row[1]
        caption = row[2] or ""
        search_text = row[3] or ""

        normalized_caption = normalize_text(
            caption
        )

        normalized_compact = compact_text(
            normalized_caption
        )

        if (
            name in normalized_caption
            or
            compact_name in normalized_compact
            or
            name in normalize_text(search_text)
        ):

            return (
                message_id,
                symbol
            )

    return None


# =========================================================
# تحلیل‌های امروز
# =========================================================

def get_today_analyses(
    chat_id
):

    today = datetime.now(
        TEHRAN
    ).strftime(
        "%Y-%m-%d"
    )

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT symbol, message_id, message_date
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

    results = cursor.fetchall()

    connection.close()

    return results


# =========================================================
# تشخیص درخواست تحلیل
# =========================================================

def extract_analysis_request(text):

    normalized = normalize_text(
        text
    )

    compact = normalized.replace(
        " ",
        ""
    )

    # -----------------------------------------------------
    # تحلیل‌های امروز
    # -----------------------------------------------------

    today_patterns = {
        "تحلیلهایامروز",
        "تحلیلامروز",
        "تحلیلهایروز",
        "تحلیلهایامروزروچارت"
    }

    if compact in today_patterns:

        return "TODAY"

    # -----------------------------------------------------
    # باید کلمه تحلیل وجود داشته باشد
    # -----------------------------------------------------

    if "تحلیل" not in normalized:

        return None

    # -----------------------------------------------------
    # حذف کلمه تحلیل
    # -----------------------------------------------------

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

    if not remaining:

        return None

    # -----------------------------------------------------
    # نام فارسی شناخته‌شده
    # -----------------------------------------------------

    if remaining in ALIASES:

        return ALIASES[
            remaining
        ]

    # -----------------------------------------------------
    # بررسی نسخه فشرده نام
    #
    # برای:
    # استارکنت
    # استارک نت
    # استارک‌نت
    # -----------------------------------------------------

    remaining_compact = compact_text(
        remaining
    )

    for alias, symbol in ALIASES.items():

        if compact_text(alias) == remaining_compact:

            return symbol

    # -----------------------------------------------------
    # اگر نماد انگلیسی باشد
    # -----------------------------------------------------

    upper = remaining.upper()

    if re.fullmatch(
        r"[A-Z0-9]{2,20}",
        upper
    ):

        return upper

    # -----------------------------------------------------
    # نام فارسی ناشناخته
    #
    # بعداً داخل دیتابیس جست‌وجو می‌شود.
    # -----------------------------------------------------

    return {
        "NAME": remaining
    }


# =========================================================
# بازارهای تبدیل
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

    if isinstance(
        data,
        list
    ):

        return data

    return data.get(
        "symbols",
        []
    )


# =========================================================
# پیدا کردن بازار تومانی
# =========================================================

def find_symbol(
    user_text
):

    text = normalize_text(
        user_text
    )

    if text in ALIASES:

        asset = ALIASES[
            text
        ]

    else:

        compact = compact_text(
            text
        )

        asset = None

        for alias, symbol in ALIASES.items():

            if compact_text(alias) == compact:

                asset = symbol
                break

        if asset is None:

            asset = text.upper()

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

        base_asset = market.get(
            "baseAsset",
            ""
        ).upper()

        if base_asset == asset:

            return market.get(
                "symbol"
            )

    return None


# =========================================================
# تشخیص پیام شبیه درخواست قیمت
# =========================================================

def looks_like_coin(
    text
):

    text = normalize_text(
        text
    )

    if text in ALIASES:

        return True

    compact = compact_text(
        text
    )

    for alias in ALIASES:

        if compact_text(alias) == compact:

            return True

    if len(
        text.split()
    ) > 3:

        return False

    if re.fullmatch(
        r"[A-Za-z0-9]{2,20}",
        text
    ):

        return True

    if re.fullmatch(
        r"[آ-ی‌]{2,25}",
        text
    ):

        return True

    return False


# =========================================================
# دریافت قیمت
# =========================================================

def get_price(
    symbol,
    quote="IRT"
):

    if quote == "USDT":

        if symbol.endswith(
            "IRT"
        ):

            market_symbol = (
                symbol[:-3]
                + "USDT"
            )

        else:

            market_symbol = symbol

    else:

        market_symbol = symbol

    url = (
        "https://api1.tabdeal.org/"
        "r/api/v1/depth"
    )

    response = requests.get(
        url,
        params={
            "symbol": market_symbol,
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
# ارسال پیام
# =========================================================

def send_message(
    chat_id,
    text,
    reply_to_message_id=None,
    reply_markup=None
):

    url = (
        f"https://api.telegram.org/"
        f"bot{BOT_TOKEN}/sendMessage"
    )

    payload = {
        "chat_id": chat_id,
        "text": text
    }

    if reply_to_message_id is not None:

        payload[
            "reply_parameters"
        ] = {
            "message_id":
                reply_to_message_id
        }

    if reply_markup is not None:

        payload[
            "reply_markup"
        ] = reply_markup

    response = requests.post(
        url,
        json=payload,
        timeout=10
    )

    # برای اینکه اگر تلگرام خطایی داد
    # متوجه شویم
    if not response.ok:

        print(
            "TELEGRAM SEND ERROR:",
            response.text
        )

    return response


# =========================================================
# پیام خوش‌آمدگویی
# =========================================================

def send_welcome(
    chat_id
):

    welcome_text = (
        "🤖 ربات روی چارت\n\n"
        "قیمت ارز را با نام یا نماد آن "
        "دریافت کنید.\n\n"
        "📊 برای آخرین تحلیل یک ارز:\n"
        "تحلیل سولانا\n"
        "تحلیل FET\n"
        "تحلیل استارک نت\n\n"
        "📅 برای دیدن تحلیل‌های امروز:\n"
        "تحلیل های امروز\n\n"
        "📢 کانال: @Rooye_chat\n"
        "💬 گروه: @Rooye_chart_gap"
    )

    keyboard = {
        "inline_keyboard": [
            [
                {
                    "text": "📢 کانال روی چارت",
                    "url": CHANNEL_URL
                },
                {
                    "text": "💬 گروه روی چارت",
                    "url": GROUP_URL
                }
            ]
        ]
    }

    send_message(
        chat_id,
        welcome_text,
        reply_markup=keyboard
    )


# =========================================================
# صفحه اصلی
# =========================================================

@app.route("/")
def home():

    return (
        "Rooye Chart Bot is running"
    )


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


        # =================================================
        # /start
        #
        # قبل از پردازش‌های دیگر
        # =================================================

        text = message.get(
            "text",
            ""
        ).strip()

        if text.lower() == "/start":

            send_welcome(
                chat_id
            )

            return "ok"


        # =================================================
        # ثبت تحلیل تصویری
        # =================================================

        if "photo" in message:

            caption = message.get(
                "caption",
                ""
            ).strip()

            if caption:

                saved = save_analysis_message(
                    chat_id,
                    message_id,
                    message_date,
                    caption
                )

                if saved:

                    return "ok"


        # =================================================
        # پیام متنی
        # =================================================

        if text:

            # -------------------------------------------------
            # اگر پیام متنی دارای هشتگ تحلیل باشد
            # ذخیره شود
            # -------------------------------------------------

            if extract_analysis_symbols(text):

                save_analysis_message(
                    chat_id,
                    message_id,
                    message_date,
                    text
                )

                return "ok"


        if not text:

            return "ok"


        # =================================================
        # درخواست تحلیل
        # =================================================

        analysis_request = (
            extract_analysis_request(
                text
            )
        )


        # =================================================
        # تمام تحلیل‌های امروز
        # =================================================

        if analysis_request == "TODAY":

            results = (
                get_today_analyses(
                    chat_id
                )
            )

            if not results:

                send_message(
                    chat_id,
                    "📊 امروز هنوز تحلیلی ثبت نشده است."
                )

                return "ok"


            # چون نتایج از جدید به قدیم هستند،
            # اولین مورد هر نماد = آخرین تحلیل آن نماد
            latest = {}

            for symbol, msg_id, msg_date in results:

                if symbol not in latest:

                    latest[
                        symbol
                    ] = msg_id


            reply = (
                "📊 تحلیل‌های امروز روی چارت\n\n"
            )


            for symbol, msg_id in latest.items():

                name = DISPLAY_NAMES.get(
                    symbol,
                    symbol
                )

                reply += (
                    f"• {name} #{symbol}\n"
                )


            send_message(
                chat_id,
                reply
            )

            return "ok"


        # =================================================
        # درخواست تحلیل یک ارز
        # =================================================

        if analysis_request:

            # ---------------------------------------------
            # حالت نماد مستقیم
            # ---------------------------------------------

            if isinstance(
                analysis_request,
                str
            ):

                symbol = analysis_request

                latest_message_id = (
                    get_latest_analysis(
                        chat_id,
                        symbol
                    )
                )

                if latest_message_id is None:

                    send_message(
                        chat_id,
                        f"❌ هنوز تحلیلی برای "
                        f"{DISPLAY_NAMES.get(symbol, symbol)} "
                        f"ثبت نشده است."
                    )

                    return "ok"


                name = DISPLAY_NAMES.get(
                    symbol,
                    symbol
                )

                send_message(
                    chat_id,
                    f"📊 آخرین تحلیل {name}:",
                    reply_to_message_id=
                        latest_message_id
                )

                return "ok"


            # ---------------------------------------------
            # حالت نام فارسی ناشناخته
            # ---------------------------------------------

            if isinstance(
                analysis_request,
                dict
            ):

                requested_name = (
                    analysis_request[
                        "NAME"
                    ]
                )

                result = (
                    get_latest_analysis_by_name(
                        chat_id,
                        requested_name
                    )
                )

                if result:

                    latest_message_id = (
                        result[0]
                    )

                    symbol = (
                        result[1]
                    )

                    name = DISPLAY_NAMES.get(
                        symbol,
                        requested_name
                    )

                    send_message(
                        chat_id,
                        f"📊 آخرین تحلیل {name}:",
                        reply_to_message_id=
                            latest_message_id
                    )

                    return "ok"


                send_message(
                    chat_id,
                    f"❌ تحلیلی برای "
                    f"{requested_name} "
                    f"پیدا نشد."
                )

                return "ok"


        # =================================================
        # فیلتر پیام‌های گروه
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
        # قیمت ارز
        # =================================================

        try:

            symbol = find_symbol(
                text
            )

            if not symbol:

                if chat_type in [
                    "group",
                    "supergroup"
                ]:

                    return "ok"

                send_message(
                    chat_id,
                    "❌ این ارز در بازار تومانی تبدیل پیدا نشد."
                )

                return "ok"


            # ---------------------------------------------
            # قیمت تومان
            # ---------------------------------------------

            toman_price = get_price(
                symbol,
                "IRT"
            )


            # ---------------------------------------------
            # قیمت تتر
            # ---------------------------------------------

            usdt_price = None

            if symbol != "USDTIRT":

                try:

                    usdt_price = get_price(
                        symbol,
                        "USDT"
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
                    "❌ قیمت این ارز در حال حاضر دریافت نشد."
                )

                return "ok"


            # ---------------------------------------------
            # نام نمایشی
            # ---------------------------------------------

            display_name = (
                normalize_text(
                    text
                )
            )

            # اگر کاربر نام فارسی داده،
            # همان نام خودش نمایش داده می‌شود.
            # اگر نماد انگلیسی داده،
            # نام فارسی شناخته‌شده نمایش داده می‌شود.

            lookup_compact = compact_text(
                display_name
            )

            resolved_symbol = None

            if display_name in ALIASES:

                resolved_symbol = ALIASES[
                    display_name
                ]

            else:

                for alias, alias_symbol in ALIASES.items():

                    if compact_text(alias) == lookup_compact:

                        resolved_symbol = alias_symbol
                        break

            if resolved_symbol:

                display_title = DISPLAY_NAMES.get(
                    resolved_symbol,
                    display_name
                )

            else:

                display_title = display_name


            reply = (
                f"🪙 {display_title}\n\n"
            )


            # ---------------------------------------------
            # قیمت تومان
            # ---------------------------------------------

            if toman_price is not None:

                reply += (
                    f"🇮🇷 تومان: "
                    f"{toman_price:,.0f}\n"
                )


            # ---------------------------------------------
            # قیمت تتر
            # ---------------------------------------------

            if resolved_symbol == "USDT":

                reply += (
                    "💵 تتر: 1 USDT"
                )

            elif display_name in [
                "تتر",
                "دلار"
            ]:

                reply += (
                    "💵 تتر: 1 USDT"
                )

            elif usdt_price is not None:

                usdt_display = (
                    f"{usdt_price:.8f}"
                    .rstrip("0")
                    .rstrip(".")
                )

                reply += (
                    f"💵 تتر: "
                    f"{usdt_display} USDT"
                )


            send_message(
                chat_id,
                reply
            )


        except Exception as e:

            print(
                "PRICE ERROR:",
                repr(e)
            )

            if chat_type in [
                "group",
                "supergroup"
            ]:

                return "ok"

            send_message(
                chat_id,
                "⚠️ خطا در دریافت قیمت. "
                "لطفاً دوباره امتحان کنید."
            )


    except Exception as e:

        print(
            "GENERAL WEBHOOK ERROR:",
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
