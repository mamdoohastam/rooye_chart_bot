
from flask import Flask, request
import requests
import os
import re

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")


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

    "ترون": "TRX",

    "چین لینک": "LINK",
    "چین‌لینک": "LINK",

    "پولکادات": "DOT",

    "آوالانچ": "AVAX",

    "لایت کوین": "LTC",
    "لایت‌کوین": "LTC",
}


# =========================
# نرمال‌سازی متن
# =========================

def normalize_text(text):

    text = text.strip()

    # حروف عربی به فارسی
    text = text.replace("ي", "ی")
    text = text.replace("ى", "ی")
    text = text.replace("ك", "ک")

    # حذف @ و $
    text = text.replace("@", "")
    text = text.replace("$", "")

    # حذف فاصله‌های ابتدا و انتها
    text = text.strip()

    return text


# =========================
# دریافت لیست بازارها
# =========================

def get_markets():

    url = "https://api1.tabdeal.org/r/api/v1/exchangeInfo"

    response = requests.get(
        url,
        timeout=10
    )

    response.raise_for_status()

    data = response.json()

    if isinstance(data, list):
        return data

    return data.get("symbols", [])


# =========================
# تشخیص اینکه پیام احتمالاً ارز است
# =========================

def looks_like_coin(text):

    text = normalize_text(text)

    # نام فارسی که در لیست ماست
    if text in ALIASES:
        return True

    # اگر شامل فاصله زیاد باشد، احتمالاً جمله معمولی است
    if len(text.split()) > 3:
        return False

    # نماد انگلیسی ارز
    # BTC
    # PEPE
    # BTCUSDT
    if re.fullmatch(r"[A-Za-z0-9]{2,15}", text):
        return True

    # متن‌های کوتاه فارسی
    # برای نام‌هایی مثل پپه، تتر، شیبا
    if re.fullmatch(r"[آ-ی‌]{2,20}", text):
        return True

    return False


# =========================
# پیدا کردن بازار تومانی
# =========================

def find_symbol(user_text):

    text = normalize_text(user_text)

    upper_text = text.upper()

    # اگر نام فارسی بود
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

def get_price(symbol, quote="IRT"):

    if quote == "USDT":

        if symbol.endswith("IRT"):

            market_symbol = (
                symbol[:-3] + "USDT"
            )

        else:

            market_symbol = symbol

    else:

        market_symbol = symbol


    url = "https://api1.tabdeal.org/r/api/v1/depth"

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

    asks = data.get("asks", [])

    if not asks:
        return None

    price = float(asks[0][0])

    return price


# =========================
# ارسال پیام تلگرام
# =========================

def send_message(chat_id, text):

    url = (
        f"https://api.telegram.org/"
        f"bot{BOT_TOKEN}/sendMessage"
    )

    requests.post(
        url,
        json={
            "chat_id": chat_id,
            "text": text
        },
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

@app.route("/webhook", methods=["POST"])
def webhook():

    data = request.get_json()

    if not data or "message" not in data:
        return "ok"

    message = data["message"]

    chat_id = message["chat"]["id"]

    chat_type = message["chat"].get(
        "type",
        "private"
    )

    text = message.get(
        "text",
        ""
    ).strip()


    if not text:
        return "ok"


    # =========================
    # دستور /start
    # =========================

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


    # =========================
    # در گروه فقط پیام‌هایی
    # که شبیه نام ارز هستند
    # پردازش شوند
    # =========================

    if chat_type in [
        "group",
        "supergroup"
    ]:

        if not looks_like_coin(text):

            # پیام معمولی گروه → هیچ پاسخی نده
            return "ok"


    # =========================
    # دریافت قیمت
    # =========================

    try:

        symbol = find_symbol(text)


        # اگر در گروه بود و ارز پیدا نشد:
        # هیچ پاسخی نده
        if not symbol:

            if chat_type in [
                "group",
                "supergroup"
            ]:

                return "ok"

            # در چت خصوصی اطلاع بده
            send_message(
                chat_id,

                "❌ این ارز در بازار تومانی "
                "تبدیل پیدا نشد."
            )

            return "ok"


        # =========================
        # قیمت تومانی
        # =========================

        toman_price = get_price(
            symbol,
            "IRT"
        )


        # =========================
        # قیمت تتری
        # =========================

        usdt_price = None


        # برای خود تتر بازار USDT/USDT نداریم
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

                usdt_price = None


        # =========================
        # هیچ قیمتی پیدا نشد
        # =========================

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


        # =========================
        # ساخت پاسخ
        # =========================

        display_name = normalize_text(text)

        reply = (
            f"🪙 {display_name}\n\n"
        )


        # قیمت تومان

        if toman_price is not None:

            reply += (
                f"🇮🇷 تومان: "
                f"{toman_price:,.0f}\n"
            )


        # قیمت تتر

        if display_name in [
            "تتر",
            "دلار"
        ]:

            reply += (
                "💵 تتر: 1 USDT"
            )

        elif usdt_price is not None:

            reply += (
                f"💵 تتر: "
                f"{usdt_price:,.8f} USDT"
            )


        # =========================
        # ارسال پاسخ
        # =========================

        send_message(
            chat_id,
            reply
        )


    except Exception as e:

        print(
            "ERROR:",
            e
        )

        # خطاهای فنی را در گروه به کاربران نشان نده
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
