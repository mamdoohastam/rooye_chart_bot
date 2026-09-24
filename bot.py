from flask import Flask, request
import requests
import os

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")

# نام‌های فارسی رایج
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


def get_markets():
    url = "https://api1.tabdeal.org/r/api/v1/exchangeInfo"

    response = requests.get(url, timeout=10)
    response.raise_for_status()

    data = response.json()

    if isinstance(data, list):
        return data

    return data.get("symbols", [])


def find_symbol(user_text):
    text = user_text.strip().upper()

    # اگر کاربر نام فارسی رایج نوشت
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


def get_price(symbol):
    url = "https://api1.tabdeal.org/r/api/v1/depth"

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

    asks = data.get("asks", [])

    if not asks:
        return None

    # قیمت به ریال/واحد API
    price = float(asks[0][0])

    # طبق تست قبلی ربات، مقدار API تبدیل را مستقیماً نمایش می‌دهیم
    return round(price)


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


@app.route("/")
def home():
    return "Rooye Chart Bot is running"


@app.route("/webhook", methods=["POST"])
def webhook():

    data = request.get_json()

    if not data or "message" not in data:
        return "ok"

    message = data["message"]

    chat_id = message["chat"]["id"]
    text = message.get("text", "").strip()

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

    try:

        symbol = find_symbol(text)

        if not symbol:
            send_message(
                chat_id,
                "❌ این ارز در بازار تومانی تبدیل پیدا نشد."
            )
            return "ok"

        price = get_price(symbol)

        if price is None:
            send_message(
                chat_id,
                "❌ قیمت این ارز در حال حاضر دریافت نشد."
            )
            return "ok"

        send_message(
            chat_id,
            f"💰 قیمت {text}\n\n"
            f"🇮🇷 {price:,} تومان"
        )

    except Exception as e:

        print("ERROR:", e)

        send_message(
            chat_id,
            "⚠️ خطا در دریافت قیمت. لطفاً دوباره امتحان کنید."
        )

    return "ok"


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 10000))
    )
