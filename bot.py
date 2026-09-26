from flask import Flask, request
import requests
import os
import re
import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo
import ccxt

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
DB_FILE = "analyses.db"

CHANNEL_URL = "https://t.me/rooye_chart"
GROUP_URL = "https://t.me/rooye_chart_gap"

# =========================
# موتور استعلام قیمت صرافی‌ها
# =========================
# قیمت نمایش‌داده‌شده «آخرین معامله» (last trade) است.
# فقط این ۴ صرافی در منوی قیمت نمایش داده می‌شوند.
EXCHANGES = {
    "nobitex": {"name": "نوبیتکس", "ccxt_id": "nobitex"},
    "tabdeal": {"name": "تبدیل", "ccxt_id": "tabdeal"},
    "bitpin": {"name": "بیت‌پین", "ccxt_id": "bitpin"},
    "abantether": {"name": "آبان‌تتر", "ccxt_id": "abantether"},
}

EXCHANGE_ALIASES = {
    "نوبیتکس": "nobitex",
    "نوبی تکس": "nobitex",
    "نوبی‌تکس": "nobitex",
    "nobitex": "nobitex",
    "تبدیل": "tabdeal",
    "tabdeal": "tabdeal",
    "بیت پین": "bitpin",
    "بیت‌پین": "bitpin",
    "bitpin": "bitpin",
    "آبان تتر": "abantether",
    "آبان‌تتر": "abantether",
    "آبانتتر": "abantether",
    "abantether": "abantether",
}

_exchange_clients = {}

# =========================
# نام‌های فارسی رایج
# =========================
ALIASES = {
    "تتر":"USDT","دلار":"USDT","بیت کوین":"BTC","بیتکوین":"BTC",
    "بیت‌کوین":"BTC","اتریوم":"ETH","سولانا":"SOL","ترون":"TRX",
    "دوج":"DOGE","دوج کوین":"DOGE","دوج‌کوین":"DOGE","ریپل":"XRP",
    "بی ان بی":"BNB","بی‌ان‌بی":"BNB","تون":"TON","کاردانو":"ADA",
    "شیبا":"SHIB","پپه":"PEPE","آپتوس":"APT","نات":"NOT",
    "چین لینک":"LINK","چین‌لینک":"LINK","پولکادات":"DOT",
    "آوالانچ":"AVAX","لایت کوین":"LTC","لایت‌کوین":"LTC",
    "تون کوین":"TON","نات کوین":"NOT","لیسک":"LSK","فت":"FET",
    "آربیتروم":"ARB","آپتیمیسم":"OP","سویی":"SUI","نیر":"NEAR",
    "اینجکتیو":"INJ","اوندو":"ONDO","مانترا":"OM","استکس":"STX",
    "فایل کوین":"FIL","گالا":"GALA","سندباکس":"SAND","مانا":"MANA",
    "یونی سواپ":"UNI","یونی‌سواپ":"UNI","آوه":"AAVE","میکر":"MKR",
    "لیدو":"LDO","پنکیک سواپ":"CAKE","پنکیک‌سواپ":"CAKE",
    "کازماس":"ATOM","هدرا":"HBAR","استلار":"XLM","الگوراند":"ALGO",
    "تزوس":"XTZ","کاسپا":"KAS","رندر":"RENDER","رندر توکن":"RENDER",
    "ورلد کوین":"WLD","بیت تنسور":"TAO","بیتنسر":"TAO","پایت":"PYTH",
    "جیتو":"JTO","جاپیتر":"JUP","سلستیا":"TIA","مانتا":"MANTA",
    "پندل":"PENDLE","تورچین":"RUNE","سینتتیکس":"SNX","فلوکی":"FLOKI",
    "بونک":"BONK","داگز":"DOGS","همستر":"HMSTR","وتور توکن":"VTHO",
    "تراست والت توکن":"TWT","توکو توکن":"TKO","استارک نت":"STRK",
    "استارک‌نت":"STRK","بایکو":"BICO","ولوت":"VELVET","هیما":"HEI",
}

DISPLAY_NAMES = {
    "BTC":"بیت‌کوین","ETH":"اتریوم","SOL":"سولانا","TRX":"ترون",
    "DOGE":"دوج‌کوین","XRP":"ریپل","BNB":"BNB","TON":"TON",
    "ADA":"کاردانو","SHIB":"شیبا","PEPE":"PEPE","APT":"APT",
    "NOT":"NOT","LINK":"چین‌لینک","DOT":"پولکادات","AVAX":"آوالانچ",
    "LTC":"لایت‌کوین","USDT":"تتر",
}

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

def normalize_text(text):
    text = (text or "").strip()
    text = text.replace("ي","ی").replace("ى","ی").replace("ك","ک")
    return text.replace("@","").replace("$","").strip()

def extract_analysis_symbols(caption):
    hashtags = re.findall(r"#([A-Za-z0-9_]+)", caption or "")
    symbols = set()

    for h in hashtags:
        symbol = h.upper().strip()
        if re.fullmatch(r"[A-Z0-9]{2,15}", symbol):
            symbols.add(symbol)

    return list(symbols)

def save_analysis(chat_id, message_id, symbol, message_date):
    date_text = datetime.fromtimestamp(
        message_date, tz=ZoneInfo("Asia/Tehran")
    ).strftime("%Y-%m-%d")
    connection = sqlite3.connect(DB_FILE)
    connection.execute("""
        INSERT INTO analyses
        (chat_id,message_id,symbol,message_date,date_text)
        VALUES (?,?,?,?,?)
    """, (chat_id,message_id,symbol,date_text and message_date,date_text))
    connection.commit()
    connection.close()

def get_latest_analysis(symbol, chat_id=None):
    # آخرین تحلیل هیچ محدودیت روزانه‌ای ندارد.
    # فقط جدیدترین رکورد همان ارز را بر اساس زمان پیام برمی‌گرداند.
    symbol = (symbol or "").strip().upper()

    connection = sqlite3.connect(DB_FILE)
    try:
        if chat_id is None:
            row = connection.execute("""
                SELECT chat_id,message_id
                FROM analyses
                WHERE UPPER(TRIM(symbol))=?
                ORDER BY message_date DESC,id DESC
                LIMIT 1
            """,(symbol,)).fetchone()
        else:
            row = connection.execute("""
                SELECT chat_id,message_id
                FROM analyses
                WHERE chat_id=? AND UPPER(TRIM(symbol))=?
                ORDER BY message_date DESC,id DESC
                LIMIT 1
            """,(chat_id,symbol)).fetchone()
    finally:
        connection.close()

    return row

def get_latest_analysis_info(symbol, chat_id=None):
    symbol = (symbol or "").strip().upper()

    connection = sqlite3.connect(DB_FILE)
    try:
        if chat_id is None:
            row = connection.execute("""
                SELECT chat_id,message_id,message_date
                FROM analyses
                WHERE UPPER(TRIM(symbol))=?
                ORDER BY message_date DESC,id DESC
                LIMIT 1
            """,(symbol,)).fetchone()
        else:
            row = connection.execute("""
                SELECT chat_id,message_id,message_date
                FROM analyses
                WHERE chat_id=? AND UPPER(TRIM(symbol))=?
                ORDER BY message_date DESC,id DESC
                LIMIT 1
            """,(chat_id,symbol)).fetchone()
    finally:
        connection.close()

    return row


def get_today_analyses(chat_id=None):
    today = datetime.now(ZoneInfo("Asia/Tehran")).strftime("%Y-%m-%d")
    connection = sqlite3.connect(DB_FILE)
    if chat_id is None:
        rows = connection.execute("""
            SELECT symbol,message_id,chat_id,message_date
            FROM analyses WHERE date_text=?
            ORDER BY message_date ASC,id ASC
        """,(today,)).fetchall()
    else:
        rows = connection.execute("""
            SELECT symbol,message_id,chat_id,message_date
            FROM analyses
            WHERE chat_id=? AND date_text=?
            ORDER BY message_date ASC,id ASC
        """,(chat_id,today)).fetchall()
    connection.close()
    return rows

def extract_analysis_request(text):
    normalized = normalize_text(text)

    if normalized in {
        "تحلیل های امروز","تحلیل‌های امروز","تحلیل امروز",
        "تحلیلهای امروز","تحلیل‌های امروزم"
    }:
        return "TODAY"

    if "تحلیل" not in normalized:
        return None

    remaining = normalized.replace("تحلیل","").strip()
    remaining = remaining.replace("های","").strip()
    remaining = remaining.replace("آخرین","").strip()

    if remaining in ALIASES:
        return ALIASES[remaining]

    upper = remaining.upper()
    if re.fullmatch(r"[A-Z0-9]{2,15}", upper):
        return upper
    return None

def get_exchange_client(exchange_id):
    if exchange_id not in EXCHANGES:
        raise ValueError("صرافی نامعتبر است.")

    if exchange_id not in _exchange_clients:
        ccxt_id = EXCHANGES[exchange_id]["ccxt_id"]
        exchange_class = getattr(ccxt, ccxt_id)
        _exchange_clients[exchange_id] = exchange_class({
            "enableRateLimit": True,
            "timeout": 10000,
        })

    return _exchange_clients[exchange_id]


def find_exchange_market(exchange_id, asset):
    """بازار تومانی/ریالی مناسب را برای ارز پیدا می‌کند."""
    exchange = get_exchange_client(exchange_id)
    markets = exchange.load_markets()
    asset = asset.upper()

    preferred = []
    for symbol, market in markets.items():
        if (market.get("base") or "").upper() != asset:
            continue
        if market.get("active") is False:
            continue
        if market.get("spot") is False and market.get("type") not in (None, "spot"):
            continue

        quote = (market.get("quote") or "").upper()
        if quote in {"IRT", "TMN", "IRR"}:
            preferred.append((symbol, quote))

    if not preferred:
        return None, None

    preferred.sort(key=lambda item: 0 if item[1] in {"IRT", "TMN"} else 1)
    return preferred[0]


def get_exchange_last_price(exchange_id, asset):
    """آخرین معامله را از صرافی مشخص می‌گیرد."""
    symbol, quote = find_exchange_market(exchange_id, asset)
    if not symbol:
        raise LookupError(
            f"بازار {asset} در {EXCHANGES[exchange_id]['name']} پیدا نشد."
        )

    exchange = get_exchange_client(exchange_id)
    ticker = exchange.fetch_ticker(symbol)
    last = ticker.get("last")

    if last is None:
        raise LookupError("آخرین قیمت معامله از صرافی دریافت نشد.")

    value = float(last)

    # IRR ریال است؛ خروجی ربات را به تومان نمایش می‌دهیم.
    if quote == "IRR":
        value /= 10

    return value, symbol


def looks_like_coin(text):
    text = normalize_text(text)
    if text in ALIASES:
        return True
    return bool(
        re.fullmatch(r"[A-Za-z0-9]{2,15}", text)
        or re.fullmatch(r"[آ-ی‌]{2,20}(?: [آ-ی‌]{2,20})?", text)
    )


def parse_price_request(text):
    """
    نمونه‌ها:
      سولانا             -> (SOL, None)
      سولانا تبدیل       -> (SOL, tabdeal)
      سولانا نوبیتکس     -> (SOL, nobitex)
      SOL بیت‌پین        -> (SOL, bitpin)
    """
    normalized = normalize_text(text)
    if not normalized:
        return None, None

    exchange_id = None
    coin_text = normalized

    aliases = sorted(EXCHANGE_ALIASES.items(), key=lambda x: len(x[0]), reverse=True)
    for alias, ex_id in aliases:
        if normalized == alias:
            return None, ex_id
        if normalized.endswith(" " + alias):
            coin_text = normalized[:-(len(alias) + 1)].strip()
            exchange_id = ex_id
            break

    if exchange_id is None:
        for alias, ex_id in aliases:
            prefix = alias + " "
            if normalized.startswith(prefix):
                coin_text = normalized[len(prefix):].strip()
                exchange_id = ex_id
                break

    if not coin_text:
        return None, exchange_id

    asset = ALIASES.get(coin_text, coin_text.upper())
    if not re.fullmatch(r"[A-Z0-9]{2,15}", asset):
        return None, exchange_id

    return asset, exchange_id


def exchange_keyboard(asset):
    return {
        "inline_keyboard": [
            [
                {"text": "🟢 نوبیتکس", "callback_data": f"price:{asset}:nobitex"},
                {"text": "🔵 تبدیل", "callback_data": f"price:{asset}:tabdeal"},
            ],
            [
                {"text": "🟣 بیت‌پین", "callback_data": f"price:{asset}:bitpin"},
                {"text": "🟠 آبان‌تتر", "callback_data": f"price:{asset}:abantether"},
            ],
        ]
    }


def send_exchange_menu(chat_id, asset):
    name = DISPLAY_NAMES.get(asset, asset)
    send_message(
        chat_id,
        f"💰 قیمت آخرین معامله {name}\n\nصرافی را انتخاب کنید:",
        reply_markup=exchange_keyboard(asset),
    )


def answer_callback(callback_id, text=None):
    payload = {"callback_query_id": callback_id}
    if text:
        payload["text"] = text
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery",
        json=payload,
        timeout=10,
    )


def send_exchange_price(chat_id, asset, exchange_id, reply_to_message_id=None):
    exchange_name = EXCHANGES[exchange_id]["name"]
    display_name = DISPLAY_NAMES.get(asset, asset)

    try:
        price, market_symbol = get_exchange_last_price(exchange_id, asset)
        text = (
            f"🪙 {display_name}\n\n"
            f"🏦 {exchange_name}\n"
            f"💰 آخرین معامله: {price:,.0f} تومان\n"
            f"📌 بازار: {market_symbol}"
        )
        send_message(chat_id, text, reply_to_message_id=reply_to_message_id)
    except Exception as e:
        print(f"EXCHANGE PRICE ERROR [{exchange_id}][{asset}]:", e)
        send_message(
            chat_id,
            f"⚠️ قیمت {display_name} در {exchange_name} در حال حاضر دریافت نشد.\n\n"
            "ممکن است بازار این ارز در این صرافی فعال نباشد.",
            reply_to_message_id=reply_to_message_id,
        )


def keyboard():
    # فقط لینک‌های کانال و گروه؛ منوی صرافی فقط هنگام درخواست قیمت نمایش داده می‌شود.
    return {
        "inline_keyboard": [[
            {"text":"📢 کانال روی چارت","url":CHANNEL_URL},
            {"text":"💬 گروه روی چارت","url":GROUP_URL}
        ]]
    }


def send_message(chat_id, text, reply_to_message_id=None, reply_markup=None):
    payload = {
        "chat_id": chat_id,
        "text": text,
    }

    if reply_markup is not None:
        payload["reply_markup"] = reply_markup

    if reply_to_message_id is not None:
        payload["reply_parameters"] = {"message_id": reply_to_message_id}

    response = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json=payload, timeout=10
    )
    print("SEND:", response.status_code, response.text[:300])
    return response.ok


def copy_analysis_message(target_chat_id,source_chat_id,source_message_id):
    payload = {
        "chat_id":target_chat_id,
        "from_chat_id":source_chat_id,
        "message_id":source_message_id,
    }
    response = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/copyMessage",
        json=payload, timeout=10
    )
    print("COPY:",response.status_code,response.text[:500])
    return response.ok

@app.route("/")
def home():
    return "Rooye Chart Bot is running"


def get_db_status():
    try:
        db_exists = os.path.exists(DB_FILE)
        db_size = os.path.getsize(DB_FILE) if db_exists else 0

        connection = sqlite3.connect(DB_FILE)
        try:
            total = connection.execute(
                "SELECT COUNT(*) FROM analyses"
            ).fetchone()[0]

            by_symbol = connection.execute("""
                SELECT symbol, COUNT(*), MAX(message_date)
                FROM analyses
                GROUP BY symbol
                ORDER BY MAX(message_date) DESC
                LIMIT 20
            """).fetchall()
        finally:
            connection.close()

        return db_exists, db_size, total, by_symbol
    except Exception as e:
        print("DB STATUS ERROR:", e)
        return None


def get_symbol_db_status(symbol):
    symbol = (symbol or "").strip().upper()
    connection = sqlite3.connect(DB_FILE)
    try:
        rows = connection.execute("""
            SELECT chat_id,message_id,symbol,message_date,date_text
            FROM analyses
            WHERE UPPER(TRIM(symbol))=?
            ORDER BY message_date DESC,id DESC
            LIMIT 10
        """,(symbol,)).fetchall()
    finally:
        connection.close()
    return rows

@app.route("/webhook",methods=["POST"])
def webhook():
    data = request.get_json()
    if not data:
        return "ok"

    # =========================
    # کلیک روی دکمه صرافی
    # =========================
    if "callback_query" in data:
        callback = data["callback_query"]
        callback_id = callback.get("id")
        callback_data = callback.get("data", "")

        if callback_data.startswith("price:"):
            parts = callback_data.split(":")
            if len(parts) == 3:
                asset = parts[1].upper()
                exchange_id = parts[2]

                if exchange_id in EXCHANGES:
                    answer_callback(callback_id, "در حال دریافت قیمت...")
                    callback_message = callback.get("message", {})
                    callback_chat = callback_message.get("chat", {})
                    callback_chat_id = callback_chat.get("id")
                    callback_message_id = callback_message.get("message_id")

                    if callback_chat_id is not None:
                        send_exchange_price(
                            callback_chat_id,
                            asset,
                            exchange_id,
                            reply_to_message_id=callback_message_id,
                        )
                    return "ok"

        answer_callback(callback_id)
        return "ok"

    if "message" not in data:
        return "ok"

    message = data["message"]
    chat_id = message["chat"]["id"]
    chat_type = message["chat"].get("type","private")
    message_id = message.get("message_id")
    message_date = message.get("date")

    # =========================
    # تشخیص وضعیت دیتابیس
    # فقط با دستورهای مخفی و در چت خصوصی
    # =========================
    text_for_command = message.get("text","").strip()

    if chat_type == "private" and text_for_command == "/dbstatus":
        status = get_db_status()
        if status is None:
            send_message(chat_id, "❌ خطا در خواندن دیتابیس.")
            return "ok"

        db_exists, db_size, total, by_symbol = status
        reply = (
            "🗄 وضعیت دیتابیس ربات\n\n"
            f"وجود فایل: {'✅' if db_exists else '❌'}\n"
            f"حجم: {db_size:,} bytes\n"
            f"تعداد کل تحلیل‌های ثبت‌شده: {total}\n\n"
            "آخرین رکوردهای ارزها:\n"
        )

        if by_symbol:
            for symbol, count, latest_ts in by_symbol:
                latest = datetime.fromtimestamp(
                    latest_ts, tz=ZoneInfo("Asia/Tehran")
                ).strftime("%Y-%m-%d %H:%M")
                reply += f"• {symbol}: {count} رکورد | {latest}\n"
        else:
            reply += "هیچ تحلیلی در دیتابیس وجود ندارد."

        send_message(chat_id, reply)
        return "ok"

    if chat_type == "private" and text_for_command.startswith("/dbsymbol"):
        parts = text_for_command.split(maxsplit=1)
        if len(parts) != 2:
            send_message(chat_id, "مثال: /dbsymbol NEAR")
            return "ok"

        symbol = parts[1].strip().upper()
        rows = get_symbol_db_status(symbol)

        if not rows:
            send_message(
                chat_id,
                f"🔎 برای {symbol} هیچ رکوردی در دیتابیس پیدا نشد."
            )
            return "ok"

        reply = f"🔎 رکوردهای {symbol}\n\n"
        for db_chat_id, db_message_id, db_symbol, ts, date_text in rows:
            dt = datetime.fromtimestamp(
                ts, tz=ZoneInfo("Asia/Tehran")
            ).strftime("%Y-%m-%d %H:%M")
            reply += (
                f"• {dt}\n"
                f"  chat_id: {db_chat_id}\n"
                f"  message_id: {db_message_id}\n"
                f"  date_text: {date_text}\n\n"
            )

        send_message(chat_id, reply)
        return "ok"

    # ثبت تحلیل عکس + هشتگ
    if "photo" in message:
        symbols = extract_analysis_symbols(message.get("caption",""))
        for symbol in symbols:
            save_analysis(chat_id,message_id,symbol,message_date)
        if symbols:
            return "ok"

    text = message.get("text","").strip()
    if not text:
        return "ok"

    analysis_request = extract_analysis_request(text)

    # =========================
    # تحلیل‌های امروز
    # =========================
    if analysis_request == "TODAY":
        search_chat_id = chat_id if chat_type in {"group","supergroup"} else None
        rows = get_today_analyses(search_chat_id)

        if not rows:
            send_message(chat_id,"📊 امروز هنوز تحلیلی ثبت نشده است.")
            return "ok"

        latest = {}
        for symbol,msg_id,source_chat,msg_date in rows:
            if symbol not in latest or msg_date >= latest[symbol][3]:
                latest[symbol]=(symbol,msg_id,source_chat,msg_date)

        reply = "📊 تحلیل‌های امروز روی چارت\n\n"
        for symbol in latest:
            reply += f"• {DISPLAY_NAMES.get(symbol,symbol)}  #{symbol}\n"

        send_message(chat_id,reply)

        # در خصوصی، خود آخرین تحلیل هر ارز را هم نمایش بده
        if chat_type == "private":
            for symbol,(_,msg_id,source_chat,_) in latest.items():
                copy_analysis_message(chat_id,source_chat,msg_id)

        return "ok"

    # =========================
    # آخرین تحلیل یک ارز
    # =========================
    if analysis_request:
        symbol = analysis_request
        search_chat_id = chat_id if chat_type in {"group","supergroup"} else None
        row = get_latest_analysis_info(symbol,search_chat_id)

        if not row:
            send_message(
                chat_id,
                f"❌ هنوز تحلیلی برای {DISPLAY_NAMES.get(symbol,symbol)} ثبت نشده است."
            )
            return "ok"

        source_chat_id,source_message_id,analysis_date = row
        name = DISPLAY_NAMES.get(symbol,symbol)

        analysis_time = datetime.fromtimestamp(
            analysis_date, tz=ZoneInfo("Asia/Tehran")
        ).strftime("%Y-%m-%d | %H:%M")

        if chat_type in {"group","supergroup"}:
            # هر بار درخواست شود، همان آخرین پیام اصلی را ریپلای می‌کند.
            send_message(
                chat_id,
                f"📊 آخرین تحلیل {name}\n🕐 {analysis_time}",
                reply_to_message_id=source_message_id
            )
        else:
            # در خصوصی، آخرین تحلیل گروه را واقعاً به خصوصی کپی می‌کند.
            send_message(
                chat_id,
                f"📊 آخرین تحلیل {name}\n🕐 {analysis_time}"
            )

            if not copy_analysis_message(
                chat_id,source_chat_id,source_message_id
            ):
                send_message(
                    chat_id,
                    f"⚠️ پیام تحلیل پیدا شد ولی Telegram اجازه کپی آن را نداد."
                )
        return "ok"

    # =========================
    # /start
    # =========================
    if text.lower() == "/start":
        send_message(
            chat_id,
            "🤖 ربات روی چارت\n\n"
            "برای قیمت، فقط نام یا نماد ارز را بنویسید.\n"
            "مثال: سولانا یا SOL\n\n"
            "اگر نام صرافی را هم بنویسید، قیمت همان صرافی مستقیم نمایش داده می‌شود.\n"
            "مثال: سولانا تبدیل\n"
            "یا: سولانا نوبیتکس\n\n"
            "برای تحلیل:\n"
            "• تحلیل سولانا\n"
            "• تحلیل XRP\n"
            "• تحلیل FET\n\n"
            "برای همه تحلیل‌های امروز:\n"
            "• تحلیل های امروز"
        )
        return "ok"

    if chat_type in {"group","supergroup"} and not looks_like_coin(text):
        return "ok"

    # =========================
    # قیمت چند صرافی
    # =========================
    asset, requested_exchange = parse_price_request(text)

    if asset:
        # فقط نام ارز: منوی انتخاب صرافی
        if requested_exchange is None:
            send_exchange_menu(chat_id, asset)
            return "ok"

        # نام ارز + نام صرافی: استعلام مستقیم
        if requested_exchange in EXCHANGES:
            send_exchange_price(chat_id, asset, requested_exchange)
            return "ok"

    if chat_type in {"group","supergroup"}:
        return "ok"

    send_message(
        chat_id,
        "❌ درخواست قیمت قابل تشخیص نیست.\n\n"
        "مثال:\n"
        "• سولانا\n"
        "• SOL\n"
        "• سولانا تبدیل\n"
        "• سولانا نوبیتکس"
    )
    return "ok"

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT",10000))
    )
