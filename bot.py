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

CHANNEL_URL = "https://t.me/rooye_chart"
GROUP_URL = "https://t.me/rooye_chart_gap"


# =========================
# نام‌های فارسی رایج
# =========================

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
    "کاردانو": "ADA",

    "شیبا": "SHIB",
    "پپه": "PEPE",
    "آپتوس": "APT",
    "نات": "NOT",

    "چین لینک": "LINK",
    "چین‌لینک": "LINK",

    "پولکادات": "DOT",
    "آوالانچ": "AVAX",

    "لایت کوین": "LTC",
    "لایت‌کوین": "LTC",
}


# =========================
# ساخت دیتابیس
# =========================

def init_database():

    connection = sqlite3.connect(DB_FILE)

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

    connection.commit()
    connection.close()


init_database()


# =========================
# نرمال‌سازی متن
# =========================

def normalize_text(text):

    text = text.strip()

    text = text.replace("ي", "ی")
    text = text.replace("ى", "ی")
    text = text.replace("ك", "ک")

    text = text.replace("@", "")
    text = text.replace("$", "")

    return text.strip()


# =========================
# تشخیص هشتگ
# =========================

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
            r"[A-Z0-9]{2,15}",
            symbol
        ):

            symbols.append(symbol)

    return list(set(symbols))


# =========================
# ذخیره تحلیل
# =========================

def save_analysis(
    chat_id,
    message_id,
    symbol,
    message_date
):

    tehran_time = datetime.fromtimestamp(
        message_date,
        tz=ZoneInfo("Asia/Tehran")
    )

    date_text = tehran_time.strftime(
        "%Y-%m-%d"
    )

    connection = sqlite3.connect(
        DB_FILE
    )

    cursor = connection.cursor()

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

    connection.commit()
    connection.close()

    print(
        f"SAVED ANALYSIS: "
        f"{symbol} | "
        f"chat={chat_id} | "
        f"message={message_id}"
    )


# =========================
# آخرین تحلیل یک ارز
# =========================

def get_latest_analysis(
    chat_id,
    symbol
):

    connection = sqlite3.connect(
        DB_FILE
    )

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


# =========================
# تحلیل‌های امروز
# =========================

def get_today_analyses(chat_id):

    tehran_today = datetime.now(
        ZoneInfo("Asia/Tehran")
    ).strftime("%Y-%m-%d")

    connection = sqlite3.connect(
        DB_FILE
    )

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT symbol, message_id
        FROM analyses
        WHERE chat_id = ?
        AND date_text = ?
        ORDER BY message_date ASC
        """,
        (
            chat_id,
            tehran_today
        )
    )

    results = cursor.fetchall()

    connection.close()

    return results


# =========================
# نام ارز برای نمایش
# =========================

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


# =========================
# تشخیص درخواست تحلیل
# =========================

def extract_analysis_request(text):

    normalized = normalize_text(text)

    # همه شکل‌های رایج «تحلیل های امروز»
    today_patterns = [
        "تحلیل های امروز",
        "تحلیل‌های امروز",
        "تحلیل امروز",
        "تحلیلهای امروز",
        "تحلیل‌های امروزم"
    ]

    for pattern in today_patterns:

        if normalized == pattern:
            return "TODAY"


    # -----------------------------------------------------
    # مهم:
    # درخواست تحلیل باید با خود کلمه «تحلیل» شروع شود.
    #
    # بنابراین:
    # «آقا رضا تحلیل سولانا برای دوستمون بذار»
    # دیگر درخواست تحلیل محسوب نمی‌شود.
    # -----------------------------------------------------

    if not normalized.startswith("تحلیل"):
        return None


    # حذف فقط «تحلیل» از ابتدای پیام
    remaining = normalized[
        len("تحلیل"):
    ].strip()


    # عبارت‌های ساده مثل:
    # تحلیل سولانا
    # تحلیل XRP
    # تحلیل آخرین سولانا
    # تحلیل های سولانا
    # را قبول می‌کنیم.
    remaining = remaining.replace(
        "های",
        "",
        1
    ).strip()

    remaining = remaining.replace(
        "آخرین",
        "",
        1
    ).strip()


    if not remaining:
        return None


    # نام فارسی
    if remaining in ALIASES:
        return ALIASES[remaining]


    # نماد انگلیسی
    upper = remaining.upper()

    if re.fullmatch(
        r"[A-Z0-9]{2,15}",
        upper
    ):
        return upper


    return None


# =========================
# دریافت لیست بازارها
# =========================

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


# =========================
# تشخیص پیام شبیه ارز
# =========================

def looks_like_coin(text):

    text = normalize_text(text)

    if text in ALIASES:
        return True

    if len(text.split()) > 3:
        return False

    if re.fullmatch(
        r"[A-Za-z0-9]{2,15}",
        text
    ):
        return True

    if re.fullmatch(
        r"[آ-ی‌]{2,20}",
        text
    ):
        return True

    return False


# =========================
# پیدا کردن بازار تومانی
# =========================

def find_symbol(user_text):

    text = normalize_text(user_text)

    upper_text = text.upper()

    if text in ALIASES:
        asset = ALIASES[text]
    else:
        asset = upper_text

    markets = get_markets()

    for market in markets:

        if market.get("status") != "TRADING":
            continue

        if market.get("quoteAsset") != "IRT":
            continue

        base_asset = market.get(
            "baseAsset",
            ""
        ).upper()

        if base_asset == asset:
            return market.get("symbol")

    return None


# =========================
# دریافت قیمت
# =========================

def get_price(
    symbol,
    quote="IRT"
):

    if quote == "USDT":

        if symbol.endswith("IRT"):

            market_symbol = (
                symbol[:-3] + "USDT"
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


# =========================
# ارسال پیام
# =========================

def send_message(
    chat_id,
    text,
    reply_to_message_id=None
):

    url = (
        f"https://api.telegram.org/"
        f"bot{BOT_TOKEN}/sendMessage"
    )

    payload = {
        "chat_id": chat_id,
        "text": text,
        "reply_markup": {
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
    }


    if reply_to_message_id is not None:

        payload["reply_parameters"] = {
            "message_id":
                reply_to_message_id
        }


    requests.post(
        url,
        json=payload,
        timeout=10
    )


# =========================
# صفحه اصلی
# =========================

@app.route("/")
def home():

    return "Rooye Chart Bot is running"


# =========================
# Webhook
# =========================

@app.route(
    "/webhook",
    methods=["POST"]
)
def webhook():

    data = request.get_json()

    if not data:
        return "ok"

    if "message" not in data:
        return "ok"

    message = data["message"]

    chat_id = message["chat"]["id"]

    chat_type = message["chat"].get(
        "type",
        "private"
    )

    message_id = message.get(
        "message_id"
    )

    message_date = message.get(
        "date"
    )


    # ==================================================
    # ثبت تحلیل‌های تصویری
    # ==================================================

    if "photo" in message:

        caption = message.get(
            "caption",
            ""
        )

        analysis_symbols = (
            extract_analysis_symbols(
                caption
            )
        )

        if analysis_symbols:

            for symbol in analysis_symbols:

                save_analysis(
                    chat_id,
                    message_id,
                    symbol,
                    message_date
                )

            return "ok"


    # ==================================================
    # پیام متنی
    # ==================================================

    text = message.get(
        "text",
        ""
    ).strip()

    if not text:
        return "ok"


    # ==================================================
    # درخواست تحلیل
    # ==================================================

    analysis_request = (
        extract_analysis_request(text)
    )

    if analysis_request == "TODAY":

        results = get_today_analyses(
            chat_id
        )

        if not results:

            send_message(
                chat_id,
                "📊 امروز هنوز تحلیلی ثبت نشده است."
            )

            return "ok"


        # -------------------------------------------------
        # هر پیام تحلیل فقط یک بار نمایش داده شود.
        # اگر یک پیام چند هشتگ داشته باشد، همه نمادها
        # کنار همان تحلیل ثبت می‌شوند.
        # -------------------------------------------------

        grouped = {}

        for symbol, msg_id in results:

            if msg_id not in grouped:
                grouped[msg_id] = []

            if symbol not in grouped[msg_id]:
                grouped[msg_id].append(symbol)


        reply = (
            "📊 تمام تحلیل‌های امروز "
            "روی چارت\n\n"
        )


        for index, (msg_id, symbols) in enumerate(
            grouped.items(),
            start=1
        ):

            names = []

            for symbol in symbols:

                name = DISPLAY_NAMES.get(
                    symbol,
                    symbol
                )

                names.append(
                    f"{name} #{symbol}"
                )

            reply += (
                f"{index}. "
                f"{' | '.join(names)}\n"
            )


        send_message(
            chat_id,
            reply
        )


        # -------------------------------------------------
        # حالا خود تمام پیام‌های تحلیل امروز را به صورت
        # ریپلای نمایش بده.
        # -------------------------------------------------

        for msg_id in grouped:

            symbols = grouped[msg_id]

            names = []

            for symbol in symbols:

                name = DISPLAY_NAMES.get(
                    symbol,
                    symbol
                )

                names.append(name)


            send_message(
                chat_id,
                f"📊 تحلیل {' | '.join(names)}:",
                reply_to_message_id=msg_id
            )


        return "ok"


    if analysis_request:

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
            reply_to_message_id=latest_message_id
        )

        return "ok"


    # ==================================================
    # /start
    # ==================================================

    if text.lower() == "/start":

        send_message(
            chat_id,

            "🤖 ربات قیمت روی چارت\n\n"
            "نام یا نماد ارز را بنویسید.\n\n"
            "مثال:\n"
            "تتر\n"
            "بیت کوین\n"
            "BTC\n"
            "PEPE\n"
            "APT"
        )

        return "ok"


    # ==================================================
    # فیلتر پیام‌های گروه
    # ==================================================

    if chat_type in [
        "group",
        "supergroup"
    ]:

        if not looks_like_coin(text):

            return "ok"


    # ==================================================
    # قیمت ارز
    # ==================================================

    try:

        symbol = find_symbol(text)

        if not symbol:

            if chat_type in [
                "group",
                "supergroup"
            ]:

                return "ok"

            send_message(
                chat_id,
                "❌ این ارز در بازار تومانی "
                "تبدیل پیدا نشد."
            )

            return "ok"


        # قیمت تومان
        toman_price = get_price(
            symbol,
            "IRT"
        )


        # قیمت USDT
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
                "❌ قیمت این ارز در حال حاضر "
                "دریافت نشد."
            )

            return "ok"


        # ==================================================
        # ساخت پاسخ قیمت
        # ==================================================

        display_name = normalize_text(
            text
        )

        reply = (
            f"🪙 {display_name}\n\n"
        )


        if toman_price is not None:

            reply += (
                f"🇮🇷 تومان: "
                f"{toman_price:,.0f}\n"
            )


        if display_name in [
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
            "ERROR:",
            e
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


    return "ok"


# =========================
# اجرای برنامه
# =========================

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
