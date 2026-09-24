import os
import requests
from flask import Flask, request

app = Flask(__name__)

BOT_TOKEN = os.environ["BOT_TOKEN"]

NOBITEX_URL = "https://api.nobitex.ir/market/stats"

COINS = {
    "btc": "بیت‌کوین",
    "eth": "اتریوم",
    "sol": "سولانا",
    "trx": "ترون",
    "doge": "دوج‌کوین",
    "xrp": "ریپل",
    "bnb": "BNB",
    "ton": "TON",
    "ada": "کاردانو",
    "shib": "شیبا",
    "usdt": "تتر"
}


def get_price(symbol):
    response = requests.get(
        NOBITEX_URL,
        params={
            "srcCurrency": symbol,
            "dstCurrency": "rls"
        },
        timeout=10
    )

    data = response.json()

    if data.get("status") != "ok":
        return None

    market = data["stats"].get(f"{symbol}-rls")

    if not market:
        return None

    price_rial = float(market["latest"])
    price_toman = price_rial / 10

    change = float(market.get("dayChange", 0))

    return price_toman, change


def format_number(number):
    return f"{number:,.0f}"


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


@app.route("/", methods=["GET"])
def home():
    return "Rooye Chart Bot is running."


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(silent=True)

    if not data or "message" not in data:
        return "OK"

    message = data["message"]

    chat_id = message["chat"]["id"]

    text = message.get("text", "").strip().lower()

    if not text:
        return "OK"

    if text == "/start":
        send_message(
            chat_id,
            "📊 ربات قیمت «روی چارت»\n\n"
            "قیمت تومانی ارزها را دریافت کنید.\n\n"
            "/btc\n"
            "/eth\n"
            "/sol\n"
            "/trx\n"
            "/doge\n"
            "/xrp\n"
            "/bnb\n"
            "/ton\n"
            "/ada\n"
            "/shib\n"
            "/usdt\n\n"
            "برای مشاهده همه قیمت‌ها:\n"
            "/prices"
        )

        return "OK"

    if text == "/prices":
        lines = ["📊 قیمت ارزها در نوبیتکس\n"]

        for symbol, name in COINS.items():
            result = get_price(symbol)

            if result:
                price, change = result

                emoji = "🟢" if change >= 0 else "🔴"

                lines.append(
                    f"{emoji} {name}\n"
                    f"💰 {format_number(price)} تومان\n"
                    f"📊 24h: {change:+.2f}%\n"
                )

        send_message(chat_id, "\n".join(lines))

        return "OK"

    if text.startswith("/"):
        symbol = text[1:].split("@")[0]

        if symbol in COINS:
            result = get_price(symbol)

            if result:
                price, change = result

                name = COINS[symbol]

                emoji = "🟢" if change >= 0 else "🔴"

                reply = (
                    f"💰 {name}\n\n"
                    f"قیمت: {format_number(price)} تومان\n"
                    f"{emoji} تغییر ۲۴ ساعته: {change:+.2f}%"
                )

            else:
                reply = "❌ قیمت این ارز در حال حاضر در دسترس نیست."

            send_message(chat_id, reply)

        else:
            send_message(
                chat_id,
                "❌ ارز موردنظر پیدا نشد.\n"
                "مثلاً /btc یا /usdt را امتحان کنید."
            )

    return "OK"


if name == "main":
    port = int(os.environ.get("PORT", 10000))

    app.run(
        host="0.0.0.0",
        port=port
    )
