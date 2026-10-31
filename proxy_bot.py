import asyncio
import aiohttp
import re
import random
import os
import html
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse, parse_qs

BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
TARGET_CHANNEL = os.environ.get("TARGET_CHANNEL", "@FreeAutoConfig").strip()
CHANNEL_NAME = TARGET_CHANNEL
SENT_PROXY_FILE = "sent_proxies.txt"
MAX_SENT_HISTORY = 3000
MAX_PROXIES_PER_POST = 12

IRAN_TZ = timezone(timedelta(hours=3, minutes=30))

# منابع تلگرامی؛ نام کانال بدون @
PROXY_SOURCES = [
    "chat_nakoni",
    "v2ryNG01",
    "ProxyDotNet",
]

# فهرست‌های عمومی لینک MTProto؛ فرمت هر منبع ممکن است با تغییر upstream عوض شود.
PROXY_SOURCE_URLS = [
    "https://raw.githubusercontent.com/tgmtproxy/telegram-mtproto-proxy-list/main/proxies.txt",
    "https://raw.githubusercontent.com/iwizard7/MTProxy_list/data/working.txt",
    "https://raw.githubusercontent.com/Grim1313/mtproto-for-telegram/master/all_proxies.txt",
]

FLAGS = ["🇺🇸","🇬🇧","🇩🇪","🇫🇷","🇯🇵","🇰🇷","🇨🇦","🇳🇱","🇸🇬","🇫🇮","🇸🇪","🇳🇴","🇩🇰","🇨🇭","🇦🇺","🇳🇿","🇧🇷","🇮🇳","🇵🇱","🇺🇦","🇹🇷","🇦🇪","🇪🇸","🇮🇹"]

def load_sent_proxies():
    if os.path.exists(SENT_PROXY_FILE):
        with open(SENT_PROXY_FILE, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def save_sent_proxies(sent_set):
    items = sorted(sent_set)[-MAX_SENT_HISTORY:]
    with open(SENT_PROXY_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(items) + ("\n" if items else ""))

def extract_proxies(text):
    text = html.unescape(text).replace("&amp;", "&")
    pattern = r'(?:https?://t\.me/proxy\?[^\s<>"\']+|tg://proxy\?[^\s<>"\']+)'
    matches = re.findall(pattern, text, flags=re.I)
    cleaned = []
    for match in matches:
        match = match.rstrip(".,;:)\\]")
        if "server=" in match and "port=" in match and "secret=" in match:
            cleaned.append(match)
    # از متن‌های خام سرور/پورت/secret هم پشتیبانی کن.
    if not cleaned:
        for line in text.splitlines():
            line = line.strip()
            if line.startswith(("https://t.me/proxy?", "http://t.me/proxy?", "tg://proxy?")) and "secret=" in line:
                cleaned.append(line.rstrip(".,;:)"))
    return list(dict.fromkeys(cleaned))

async def fetch_text(session, url, label):
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; FreeAutoConfigBot/2.0)"}
        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=20)) as resp:
            if resp.status == 200:
                text = await resp.text(errors="ignore")
                found = extract_proxies(text)
                print(f"✅ منبع پروکسی {label}: {len(found)}")
                return found
            print(f"⚠️ منبع پروکسی {label}: HTTP {resp.status}")
    except Exception as exc:
        print(f"⚠️ منبع پروکسی {label}: {exc}")
    return []

async def fetch_channel(session, channel):
    return await fetch_text(session, f"https://t.me/s/{channel}", f"@{channel}")

def proxy_key(proxy):
    try:
        query = parse_qs(urlparse(proxy.replace("tg://", "https://t.me/")).query)
        server = query.get("server", [""])[0].lower()
        port = query.get("port", [""])[0]
        secret = query.get("secret", [""])[0]
        return f"{server}:{port}:{secret}"
    except Exception:
        return proxy.strip()

async def send_to_channel(session, text):
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN تنظیم نشده است.")
        return False
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": TARGET_CHANNEL, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
    try:
        async with session.post(url, json=data, timeout=aiohttp.ClientTimeout(total=20)) as resp:
            result = await resp.json()
            if not result.get("ok"):
                print(f"❌ Telegram API: {result}")
            return result.get("ok", False)
    except Exception as exc:
        print(f"❌ خطا در ارسال: {exc}")
        return False

async def main_proxy():
    print(f"\n🔌 شروع جمع‌آوری پروکسی: {datetime.now(IRAN_TZ).strftime('%Y-%m-%d %H:%M:%S')}")
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN تنظیم نشده است.")
        return
    sent = load_sent_proxies()
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_channel(session, ch) for ch in PROXY_SOURCES]
        tasks += [fetch_text(session, url, url.split("/")[3] if len(url.split("/")) > 3 else url) for url in PROXY_SOURCE_URLS]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        all_proxies = []
        for result in results:
            if isinstance(result, list):
                all_proxies.extend(result)

        unique = {}
        for proxy in all_proxies:
            key = proxy_key(proxy)
            if key not in unique and key and key != "::":
                unique[key] = proxy
        new = [p for p in unique.values() if proxy_key(p) not in sent]
        pool = new if new else list(unique.values())
        print(f"📊 پروکسی یکتا: {len(unique)} | جدید: {len(new)}")
        if not pool:
            print("❌ پروکسی قابل‌انتشار پیدا نشد.")
            return

        random.shuffle(pool)
        selected = pool[:MAX_PROXIES_PER_POST]
        now = datetime.now(IRAN_TZ).strftime("%H:%M")
        rows = []
        for index, proxy in enumerate(selected):
            flag = FLAGS[index % len(FLAGS)]
            rows.append(f'{flag} <a href="{html.escape(proxy, quote=True)}">اتصال به پروکسی</a>')
        message = (
            f"🔌 <b>MTProto Proxy | {html.escape(CHANNEL_NAME)}</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"⏰ <b>آپدیت:</b> <code>{now}</code> (به وقت ایران)\n"
            f"📦 <b>تعداد پروکسی:</b> <code>{len(selected)}</code>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n" + "\n".join(rows) +
            "\n\n━━━━━━━━━━━━━━━━━━━━\n"
            "🔄 بررسی و انتشار خودکار هر ۱۰ دقیقه"
        )
        if await send_to_channel(session, message):
            sent.update(proxy_key(p) for p in selected)
            save_sent_proxies(sent)
            print(f"✅ پست پروکسی ارسال شد: {len(selected)}")
        else:
            print("❌ ارسال پست پروکسی ناموفق بود.")

if __name__ == "__main__":
    asyncio.run(main_proxy())
