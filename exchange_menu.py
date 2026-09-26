# exchange_menu.py

EXCHANGES = [
    ("🟡 Binance", "https://www.binance.com"),
    ("🔵 Tabdeal", "https://tabdeal.org"),
    ("🟣 KCEX", "https://www.kcex.com"),
    ("🟢 Nobitex", "https://nobitex.ir"),
    ("🟠 Wallex", "https://wallex.ir"),
]


def exchange_keyboard():
    return {
        "inline_keyboard": [
            [
                {"text": name, "url": url}
            ]
            for name, url in EXCHANGES
        ]
    }
