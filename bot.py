
from flask import Flask, request
import requests
import os

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
    "اتریوم": "ETH",
    "سولانا": "SOL",
    "ترون": "TRX",
    "دوج": "DOGE",
    "دوج کوین": "DOGE",
    "ریپل": "XRP",
    "بی ان بی": "BNB",
    "تون": "TON",
    "کاردانو": "ADA",
    "شیبا": "SHIB",
}


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
# پیدا کردن بازار تومانی ارز
# =========================

def find_symbol(user_text):

    text = user_text.strip().upper()

    if user_text.strip() in ALIASES:
        asset = ALIASES[user_text.strip()]
    else:
        asset = text

    markets = get_markets()

    for market in markets:

        if market.get("status") != "TRADING":
            continue

        if market.get("quoteAsset") != "IRT":
            continue

        if market.get("baseAsset", "").upper() == asset:

            return market.get("symbol")

    return None


# =========================
# دریافت قیمت
# quote = IRT یا USDT
# =========================

def get_price(symbol, quote="IRT"):

    # مثال:
    # BTCIRT  -> BTCIRT
    # BTCIRT  -> BTCUSDT

    if quote == "USDT":

        if symbol.endswith("IRT"):
            market_symbol = symbol[:-3] + "USDT"
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
# ارسال پیام به تلگرام
# =========================

def send_message(chat_id, text):

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

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
# Webhook تلگرام
# =========================

@app.route("/webhook", methods=["POST"])
def webhook():

    data = request.get_json()

    if not data or "message" not in data:
        return "ok"

    message = data["message"]

    chat_id = message["chat"]["id"]

    text = message.get("text", "").strip()


    # =========================
    # دستور /start
    # =========================

    if text.lower() == "/start":

        send_message(
            chat_id,

            "🤖 ربات قیمت روی چارت\n\n"

            "نام یا نماد هر ارز را بنویسید.\n\n"

            "مثال:\n"

            "تتر\n"
            "بیت کوین\n"
            "BTC\n"
            "PEPE\n"
            "APT"
        )

        return "ok"


    # =========================
    # دریافت قیمت
    # =========================

    try:

        # پیدا کردن بازار تومانی
        symbol = find_symbol(text)


        if not symbol:

            send_message(
                chat_id,

                "❌ این ارز در بازار تومانی تبدیل پیدا نشد."
            )

            return "ok"


        # قیمت تومانی
        toman_price = get_price(
            symbol,
            "IRT"
        )


        # قیمت تتری
        usdt_price = None

        # برای خود تتر بازار USDT/USDT وجود ندارد
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


        # اگر هیچ قیمتی پیدا نشد
        if toman_price is None and usdt_price is None:

            send_message(
                chat_id,

                "❌ قیمت این ارز در حال حاضر دریافت نشد."
            )

            return "ok"


        # =========================
        # ساخت پاسخ
        # =========================

        reply = f"🪙 {text}\n\n"


        if toman_price is not None:

            reply += (
                f"🇮🇷 تومان: "
                f"{toman_price:,.0f}\n"
            )


        if text.strip() in ["تتر", "دلار"]:

            reply += (
                f"💵 تتر: "
                f"1 USDT"
            )

        elif usdt_price is not None:

            reply += (
                f"💵 تتر: "
                f"{usdt_price:,.8f} USDT"
            )


        # ارسال پاسخ
        send_message(
            chat_id,
            reply
        )


    except Exception as e:

        print(
            "ERROR:",
            e
        )

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
