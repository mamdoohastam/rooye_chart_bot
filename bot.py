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

def get_markets():
    response = requests.get(
        "https://api1.tabdeal.org/r/api/v1/exchangeInfo",
        timeout=10
    )
    response.raise_for_status()
    data = response.json()
    return data if isinstance(data,list) else data.get("symbols",[])

def looks_like_coin(text):
    text = normalize_text(text)
    if text in ALIASES:
        return True
    if len(text.split()) > 3:
        return False
    return bool(
        re.fullmatch(r"[A-Za-z0-9]{2,15}",text) or
        re.fullmatch(r"[آ-ی‌]{2,20}",text)
    )

def find_symbol(user_text):
    text = normalize_text(user_text)
    asset = ALIASES.get(text,text.upper())

    for market in get_markets():
        if market.get("status") != "TRADING":
            continue
        if market.get("quoteAsset") != "IRT":
            continue
        if market.get("baseAsset","").upper() == asset:
            return market.get("symbol")
    return None

def get_price(symbol, quote="IRT"):
    market_symbol = symbol
    if quote == "USDT" and symbol.endswith("IRT"):
        market_symbol = symbol[:-3] + "USDT"

    response = requests.get(
        "https://api1.tabdeal.org/r/api/v1/depth",
        params={"symbol":market_symbol,"limit":1},
        timeout=10
    )
    response.raise_for_status()
    asks = response.json().get("asks",[])
    return float(asks[0][0]) if asks else None

def keyboard():
    base_keyboard = {
        "inline_keyboard": [[
            {"text":"📢 کانال روی چارت","url":CHANNEL_URL},
            {"text":"💬 گروه روی چارت","url":GROUP_URL}
        ]]
    }

    exchange_menu = exchange_keyboard()

    base_keyboard["inline_keyboard"].extend(
        exchange_menu["inline_keyboard"]
    )

    return base_keyboard

    exchange_menu = exchange_keyboard()

    base_keyboard["inline_keyboard"].extend(
        exchange_menu["inline_keyboard"]
    )

    return base_keyboard

def send_message(chat_id,text,reply_to_message_id=None):
    payload = {
        "chat_id":chat_id,
        "text":text,
        "reply_markup":keyboard()
    }
    if reply_to_message_id is not None:
        payload["reply_parameters"]={"message_id":reply_to_message_id}

    response = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json=payload, timeout=10
    )
    print("SEND:",response.status_code,response.text[:300])
    return response.ok

def copy_analysis_message(target_chat_id,source_chat_id,source_message_id):
    payload = {
        "chat_id":target_chat_id,
        "from_chat_id":source_chat_id,
        "message_id":source_message_id,
        "reply_markup":keyboard()
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
    if not data or "message" not in data:
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
            "برای قیمت، نام یا نماد ارز را بنویسید.\n\n"
            "برای تحلیل:\n"
            "• تحلیل سولانا\n"
            "• تحلیل XRP\n"
            "• تحلیل FET\n\n"
            "برای همه تحلیل‌های امروز:\n"
            "• تحلیل های امروز\n\n"
            "مثال قیمت:\n"
            "بیت کوین\nسولانا\nلیسک\nBTC\nSOL\nLSK"
        )
        return "ok"

    if chat_type in {"group","supergroup"} and not looks_like_coin(text):
        return "ok"

    # =========================
    # قیمت
    # =========================
    try:
        symbol = find_symbol(text)

        if not symbol:
            if chat_type in {"group","supergroup"}:
                return "ok"
            send_message(
                chat_id,
                "❌ این ارز در بازار تومانی تبدیل پیدا نشد."
            )
            return "ok"

        toman_price = get_price(symbol,"IRT")
        usdt_price = None

        if symbol != "USDTIRT":
            try:
                usdt_price = get_price(symbol,"USDT")
            except Exception as e:
                print("USDT PRICE ERROR:",e)

        if toman_price is None and usdt_price is None:
            if chat_type in {"group","supergroup"}:
                return "ok"
            send_message(chat_id,"❌ قیمت این ارز در حال حاضر دریافت نشد.")
            return "ok"

        display_name = normalize_text(text)
        reply = f"🪙 {display_name}\n\n"

        if toman_price is not None:
            reply += f"🇮🇷 تومان: {toman_price:,.0f}\n"

        if display_name in {"تتر","دلار"}:
            reply += "💵 تتر: 1 USDT"
        elif usdt_price is not None:
            value = f"{usdt_price:.8f}".rstrip("0").rstrip(".")
            reply += f"💵 تتر: {value} USDT"

        send_message(chat_id,reply)

    except Exception as e:
        print("ERROR:",e)
        if chat_type in {"group","supergroup"}:
            return "ok"
        send_message(chat_id,"⚠️ خطا در دریافت قیمت. لطفاً دوباره امتحان کنید.")

    return "ok"

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT",10000))
    )
