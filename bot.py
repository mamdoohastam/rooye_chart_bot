rom flask import Flask, request
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

    text = text.replace("ي", "ی")
    text = text.replace("ى", "ی")
    text = text.replace("ك", "ک")

    text = text.replace("@", "")
    text = text.replace("$", "")

    return text.strip()


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
# تشخیص اینکه پیام شبیه ارز است
# =========================

def looks_like_coin(text):

    text = normalize_text(text)

    if text in ALIASES:
        return True

    if len(text.split()) > 3:
        return False

    if re.fullmatch(r"[A-Za-z0-9]{2,15}", text):
        return True

    if re.fullmatch(r"[آ-ی‌]{2,20}", text):
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

def get_price(symbol, quote="IRT"):

    if quote == "USDT":

        if symbol.endswith("IRT"):
            market_symbol = symbol[:-3] + "USDT"
        else:
            market_symbol = symbol

    else:

        market_symbol = symbol

    url = "https://api1.tab
