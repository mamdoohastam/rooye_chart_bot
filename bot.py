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


# =========================================================
# نام‌های قابل جستجوی تحلیلگران
# =========================================================

ANALYST_ALIASES = {
    "رضا": "REZA",
    "re​za": "REZA",

    "چراغی": "CHERAGHI",
    "رضا چراغی": "CHERAGHI",
    "reza ch": "CHERAGHI",

    "سلیمانی": "SOLEIMANI",
    "آقای سلیمانی": "SOLEIMANI",
    "ایرانمان": "SOLEIMANI",
    "iranman": "SOLEIMANI",
}


ANALYST_NAMES = {
    "REZA": "رضا",
    "CHERAGHI": "آقای چراغی",
    "SOLEIMANI": "آقای سلیمانی",
}


# =========================================================
# دیتابیس
# =========================================================

def get_db():

    connection = sqlite3.connect(
        DB_FILE,
        timeout=10
    )

    connection.row_factory = sqlite3.Row

    return connection


def init_database():

    connection = get_db()

    cursor = connection.cursor()

    # جدول تحلیل‌ها
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            message_id INTEGER NOT NULL,
            symbol TEXT NOT NULL,
            analyst TEXT NOT NULL,
            message_date INTEGER NOT NULL,
            date_text TEXT NOT NULL
        )
    """)

    # جدول تحلیلگران
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS analysts (
            user_id INTEGER PRIMARY KEY,
            analyst TEXT NOT NULL,
            registered_at INTEGER NOT NULL
        )
    """)

    connection.commit()
    connection.close()


init_database()


# =========================================================
# نرمال‌سازی
# =========================================================

def normalize_text(text):

    if not text:
        return ""

    text = text.strip()

    text = text.replace("ي", "ی")
    text = text.replace("ى", "ی")
    text = text.replace("ك", "ک")

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# =========================================================
# تشخیص هشتگ ارز
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
            r"[A-Z0-9]{2,15}",
            symbol
        ):

            symbols.append(symbol)

    return list(set(symbols))


# =========================================================
# ذخیره تحلیل
# =========================================================

def save_analysis(
    chat_id,
    message_id,
    symbol,
    analyst,
    message_date
):

    tehran_time = datetime.fromtimestamp(
        message_date,
        tz=ZoneInfo("Asia/Tehran")
    )

    date_text = tehran_time.strftime(
        "%Y-%m-%d"
    )

    connection = get_db()

    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO analyses
        (
            chat_id,
            message_id,
            symbol,
            analyst,
            message_date,
            date_text
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            chat_id,
            message_id,
            symbol,
            analyst,
            message_date,
            date_text
        )
    )

    connection.commit()
    connection.close()

    print(
        f"SAVED ANALYSIS: "
        f"{symbol} | "
        f"{analyst} | "
        f"chat={chat_id} | "
        f"message={message_id}"
    )


# =========================================================
# پیدا کردن تحلیلگر از روی User ID
# =========================================================

def get_registered_analyst(user_id):

    connection = get_db()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT analyst
        FROM analysts
        WHERE user_id = ?
        """,
        (user_id,)
    )

    result = cursor.fetchone()

    connection.close()

    if result:
        return result["analyst"]

    return None


# =========================================================
# ثبت تحلیلگر
# =========================================================

def register_analyst(
    user_id,
    analyst
):

    connection = get_db()

    cursor = connection.cursor()

    now = int(
        datetime.now().timestamp()
    )

    cursor.execute(
        """
        INSERT OR REPLACE INTO analysts
        (
            user_id,
            analyst,
            registered_at
        )
        VALUES (?, ?, ?)
        """,
        (
            user_id,
            analyst,
            now
        )
    )

    connection.commit()
    connection.close()


# =========================================================
# تشخیص نام تحلیلگر
# =========================================================

def find_analyst(text):

    normalized = normalize_text(
        text
    ).lower()

    # از طولانی‌ترین نام به کوتاه‌ترین
    names = sorted(
        ANALYST_ALIASES.keys(),
        key=len,
        reverse=True
    )

    for name in names:

        if name.lower() in normalized:

            return ANALYST_ALIASES[name]

    return None


# =========================================================
# تشخیص ارز در درخواست تحلیل
# =========================================================

def find_requested_symbol(text):

    normalized = normalize_text(
        text
    )

    # ابتدا نام‌های فارسی
    aliases = sorted(
        ALIASES.keys(),
        key=len,
        reverse=True
    )

    for alias in aliases:

        if alias in normalized:

            return ALIASES[alias]

    # سپس نماد انگلیسی
    words = re.findall(
        r"[A-Za-z0-9]{2,15}",
        normalized
    )

    # حذف کلمات مربوط به تحلیلگر
    ignored = {
        "تحلیل",
        "TODAY",
        "REZA",
        "CHERAGHI",
        "SOLEIMANI"
    }

    for word in words:

        upper = word.upper()

        if upper in ignored:
            continue

        if re.fullmatch(
            r"[A-Z0-9]{2,15}",
            upper
        ):

            return upper

    return None


# =========================================================
# آخرین تحلیل یک ارز و یک تحلیلگر
# =========================================================

def get_latest_analysis(
    chat_id,
    symbol,
    analyst=None
):

    connection = get_db()

    cursor = connection.cursor()

    if analyst:

        cursor.execute(
            """
            SELECT *
            FROM analyses
            WHERE chat_id = ?
            AND symbol = ?
            AND analyst = ?
            ORDER BY message_date DESC
            LIMIT 1
            """,
            (
                chat_id,
                symbol,
                analyst
            )
        )

    else:

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

    connection.close()

    return result


# =========================================================
# آخرین تحلیل هر سه تحلیلگر
# =========================================================

def get_latest_all_analysts(
    chat_id,
    symbol
):

    results = []

    for analyst in [
        "REZA",
        "CHERAGHI",
        "SOLEIMANI"
    ]:

        result = get_latest_analysis(
            chat_id,
            symbol,
            analyst
        )

        if result:
            results.append(result)

    return results


# =========================================================
# تمام تحلیل‌های امروز
# =========================================================

def get_today_analyses(chat_id):

    today = datetime.now(
        ZoneInfo("Asia/Tehran")
    ).strftime("%Y-%m-%d")

    connection = get_db()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT *
        FROM analyses
        WHERE chat_id = ?
        AND date_text = ?
        ORDER BY message_date ASC
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
# نام نمایشی ارز
# =========================================================

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
# تشخیص «تحلیل امروز»
# =========================================================

def is_today_request(text):

    normalized = normalize_text(
        text
    )

    normalized = normalized.replace(
        "‌",
        ""
    )

    return (
        normalized == "تحلیلهای امروز"
        or
        normalized == "تحلیل های امروز"
        or
        normalized == "تحلیل امروز"
    )


# =========================================================
# تشخیص درخواست تحلیل
# =========================================================

def is_analysis_request(text):

    normalized = normalize_text(
        text
    )

    return (
        "تحلیل" in normalized
    )


# =========================================================
# دریافت بازارها از تبدیل
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
# تشخیص پیام شبیه ارز
# =========================================================

def looks_like_coin(text):

    text = normalize_text(
        text
    )

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


# =========================================================
# پیدا کردن بازار تومانی
# =========================================================

def find_symbol(user_text):

    text = normalize_text(
        user_text
    )

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

            return market.get(
                "symbol"
            )

    return None


# =========================================================
# قیمت
# =========================================================

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


# =========================================================
# ارسال پیام
# =========================================================

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
        "text": text
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


# =========================================================
# صفحه اصلی
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

    sender = message.get(
        "from",
        {}
    )

    user_id = sender.get(
        "id"
    )


    # =====================================================
    # پیام متنی
    # =====================================================

    text = message.get(
        "text",
        ""
    ).strip()


    # =====================================================
    # ثبت تحلیلگر
    # =====================================================

    if text.startswith("/register"):

        # فقط در چت خصوصی
        if chat_type != "private":

            send_message(
                chat_id,
                "❌ ثبت تحلیلگر باید "
                "در چت خصوصی ربات انجام شود."
            )

            return "ok"


        parts = text.split(
            maxsplit=1
        )

        if len(parts) < 2:

            send_message(
                chat_id,
                "فرمت صحیح:\n\n"
                "/register رضا\n"
                "/register چراغی\n"
                "/register سلیمانی"
            )

            return "ok"


        requested_name = normalize_text(
            parts[1]
        ).lower()


        # تبدیل نام به شناسه داخلی
        analyst = None

        for name, code in ANALYST_ALIASES.items():

            if requested_name == name.lower():

                analyst = code
                break


        if analyst is None:

            send_message(
                chat_id,
                "❌ نام تحلیلگر شناخته نشد.\n\n"
                "یکی از این سه نام را وارد کنید:\n"
                "رضا\n"
                "چراغی\n"
                "سلیمانی"
            )

            return "ok"


        register_analyst(
            user_id,
            analyst
        )

        send_message(
            chat_id,
            "✅ ثبت شد.\n\n"
            f"شما به عنوان "
            f"«{ANALYST_NAMES[analyst]}» "
            f"ثبت شدید.\n\n"
            "از این به بعد برای ثبت تحلیل "
            "فقط هشتگ ارز را اضافه کنید.\n\n"
            "مثال:\n"
            "#SOL"
        )

        print(
            f"REGISTERED ANALYST: "
            f"user={user_id} "
            f"analyst={analyst}"
        )

        return "ok"


    # =====================================================
    # بررسی پیام عکس و ثبت تحلیل
    # =====================================================

    if "photo" in message:

        caption = message.get(
            "caption",
            ""
        )

        symbols = (
            extract_analysis_symbols(
                caption
            )
        )

        if symbols:

            analyst = get_registered_analyst(
                user_id
            )

            if analyst:

                for symbol in symbols:

                    save_analysis(
                        chat_id,
                        message_id,
                        symbol,
                        analyst,
                        message_date
                    )

            else:

                print(
                    "UNKNOWN ANALYST:",
                    user_id
                )

            return "ok"


    # =====================================================
    # پیام بدون متن
    # =====================================================

    if not text:

        return "ok"


    # =====================================================
    # /start
    # =====================================================

    if text.lower() == "/start":

        send_message(
            chat_id,

            "🤖 ربات روی چارت\n\n"
            "برای قیمت، نام یا نماد ارز را "
            "بنویسید.\n\n"
            "برای تحلیل:\n"
            "تحلیل سولانا\n"
            "تحلیل سولانا رضا\n"
            "تحلیل ریپل چراغی\n"
            "تحلیل بیت سلیمانی\n\n"
            "برای همه تحلیل‌های امروز:\n"
            "تحلیل های امروز"
        )

        return "ok"


    # =====================================================
    # درخواست تحلیل‌های امروز
    # =====================================================

    if is_today_request(text):

        results = get_today_analyses(
            chat_id
        )

        if not results:

            send_message(
                chat_id,
                "📊 امروز هنوز تحلیلی "
                "ثبت نشده است."
            )

            return "ok"


        reply = "📊 تحلیل‌های امروز\n\n"


        for result in results:

            symbol = result["symbol"]
            analyst = result["analyst"]

            name = DISPLAY_NAMES.get(
                symbol,
                symbol
            )

            analyst_name = ANALYST_NAMES.get(
                analyst,
                analyst
            )

            time_text = datetime.fromtimestamp(
                result["message_date"],
                tz=ZoneInfo("Asia/Tehran")
            ).strftime("%H:%M")


            reply += (
                f"• {time_text} — "
                f"{analyst_name} — "
                f"{name}\n"
            )


        send_message(
            chat_id,
            reply
        )

        return "ok"


    # =====================================================
    # درخواست تحلیل یک ارز
    # =====================================================

    if is_analysis_request(text):

        symbol = find_requested_symbol(
            text
        )

        if not symbol:

            send_message(
                chat_id,
                "❌ نتوانستم ارز موردنظر "
                "را تشخیص بدهم."
            )

            return "ok"


        analyst = find_analyst(
            text
        )


        # -------------------------------------------------
        # اگر تحلیلگر مشخص شده باشد
        # -------------------------------------------------

        if analyst:

            result = get_latest_analysis(
                chat_id,
                symbol,
                analyst
            )

            if not result:

                send_message(
                    chat_id,
                    "❌ هنوز تحلیلی از "
                    f"{ANALYST_NAMES[analyst]} "
                    f"درباره "
                    f"{DISPLAY_NAMES.get(symbol, symbol)} "
                    "ثبت نشده است."
                )

                return "ok"


            name = DISPLAY_NAMES.get(
                symbol,
                symbol
            )

            analyst_name = ANALYST_NAMES.get(
                analyst,
                analyst
            )


            send_message(
                chat_id,

                f"📊 آخرین تحلیل "
                f"{analyst_name} "
                f"درباره {name}",

                reply_to_message_id=
                    result["message_id"]
            )

            return "ok"


        # -------------------------------------------------
        # اگر تحلیلگر مشخص نشده:
        # آخرین تحلیل هر سه نفر
        # -------------------------------------------------

        results = get_latest_all_analysts(
            chat_id,
            symbol
        )

        if not results:

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


        # هر تحلیلگر را جداگانه Reply می‌کنیم
        send_message(
            chat_id,
            f"📊 آخرین تحلیل‌های {name}"
        )


        for result in results:

            analyst_name = ANALYST_NAMES.get(
                result["analyst"],
                result["analyst"]
            )

            send_message(
                chat_id,

                f"👤 {analyst_name}\n"
                f"آخرین تحلیل {name}",

                reply_to_message_id=
                    result["message_id"]
            )

        return "ok"


    # =====================================================
    # فیلتر پیام‌های گروه
    # =====================================================

    if chat_type in [
        "group",
        "supergroup"
    ]:

        if not looks_like_coin(text):

            return "ok"


    # =====================================================
    # قیمت
    # =====================================================

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
                "❌ این ارز در بازار "
                "تومانی تبدیل پیدا نشد."
            )

            return "ok"


        # قیمت تومان
        toman_price = get_price(
            symbol,
            "IRT"
        )


        # قیمت تتر
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
