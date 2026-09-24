from flask import Flask, request
import requests
import os

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")

COINS = {
    "تتر": "USDTIRT",
    "usdt": "USDTIRT",
    "بیت کوین": "BTCIRT",
    "بیتکوین": "BTCIRT",
    "btc": "BTCIRT",
    "اتریوم": "ETHIRT",
    "eth": "ETHIRT",
    "سولانا": "SOLIRT",
    "sol": "SOLIRT",
    "ترون": "TRXIRT",
    "trx": "TRXIRT",
    "دوج": "DOGEIRT",
    "دوج کوین": "DOGEIRT",
    "doge": "DOGEIRT",
    "ریپل": "XRPIRT",
    "xrp": "XRPIRT",
    "بی ان بی": "BNBIRT",
    "bnb": "BNBIRT",
    "تون": "TONIRT",
    "ton": "TONIRT",
    "کاردانو": "ADAIRT",
    "ada": "ADAIRT",
    "شیبا": "SHIBIRT",
    "شیبا اینو": "SHIBIRT",
    "shib": "SHIBIRT",
}


def get_price(symbol):
    url = "https://api.tabdeal.org/r/api/v1/depth"

    response = requests.get(
        url,
        params={"symbol": symbol},
        timeout=10
    )

    response.raise_for_status()

    data = response.json()

    asks = data.get("asks", [])

    if not asks:
        return None

    # ارزان‌ترین سفارش فروش
    price_rial = float(asks[0][0])

    # ریال → تومان
    return round(price_rial)


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
            "نام ارز را بنویسید.\n\n"
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

        except Exception as e:
            print("PRICE ERROR:", e)

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
