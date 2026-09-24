from flask import Flask, request
import requests
import os

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")

COINS = {
    "تتر": "usdt",
    "usdt": "usdt",
    "بیت کوین": "btc",
    "بیتکوین": "btc",
    "btc": "btc",
    "اتریوم": "eth",
    "eth": "eth",
    "سولانا": "sol",
    "sol": "sol",
    "ترون": "trx",
    "trx": "trx",
    "دوج": "doge",
    "دوج کوین": "doge",
    "doge": "doge",
    "ریپل": "xrp",
    "xrp": "xrp",
    "bnb": "bnb",
    "بی ان بی": "bnb",
    "تون": "ton",
    "ton": "ton",
    "کاردانو": "ada",
    "ada": "ada",
    "شیبا": "shib",
    "شیبا اینو": "shib",
    "shib": "shib",
}

def get_price(symbol):
    url = "https://apiv2.nobitex.ir/v3/orderbook/" + symbol + "IRT"

    response = requests.get(url, timeout=10)

    print("NOBITEX STATUS:", response.status_code)
    print("NOBITEX RESPONSE:", response.text)

    data = response.json()

    asks = data.get("asks", [])

    if not asks:
        return None

    price_rial = float(asks[0][0])
    return round(price_rial / 10)


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
    text = message.get("text", "").strip().lower()

    if text == "/start":
        send_message(
            chat_id,
            "🤖 ربات قیمت روی چارت\n\n"
            "برای دریافت قیمت، نام ارز را بنویسید.\n\n"
            "مثال:\n"
            "تتر\n"
            "بیت کوین\n"
            "اتریوم\n"
            "سولانا"
        )
        return "ok"

    if text in COINS:

        symbol = COINS[text]

        try:
            price = get_price(symbol)

            if price:
                send_message(
                    chat_id,
                    f"💰 قیمت {text}\n\n"
                    f"🇮🇷 {price:,} تومان"
                )
            else:
                send_message(
                    chat_id,
                    "❌ قیمت این ارز در حال حاضر دریافت نشد."
                )

        except Exception:
            send_message(
                chat_id,
                "⚠️ خطا در دریافت قیمت. لطفاً چند لحظه بعد دوباره امتحان کنید."
            )

    return "ok"


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 10000))
    )
