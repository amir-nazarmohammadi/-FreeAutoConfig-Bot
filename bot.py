import asyncio
import aiohttp
import re
import random
import base64
import json
import os
import html
from datetime import datetime, timezone, timedelta

BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
TARGET_CHANNEL = os.environ.get("TARGET_CHANNEL", "@FreeAutoConfig").strip()
CHANNEL_NAME = TARGET_CHANNEL
SENT_FILE = "sent_configs.txt"
MAX_SENT_HISTORY = 5000
MAX_CONFIGS_PER_POST = 8

IRAN_TZ = timezone(timedelta(hours=3, minutes=30))

# منابع تلگرامی؛ نام کانال بدون @
SOURCE_CHANNELS = [
    "filembad",
    "icv2ray",
    "vpns",
    "HoosheMasnui",
    "Farah_VPN",
    # برای اضافه‌کردن منبع جدید، نام کانال را در خط جداگانه اضافه کن.
]

# فیدهای عمومی متنی/اشتراکی که کانفیگ‌های سازگار با V2RayNG منتشر می‌کنند.
# بعضی از فیدها Base64 هستند؛ کد در صورت نیاز آن‌ها را decode می‌کند.
SOURCE_URLS = [
    "https://raw.githubusercontent.com/0xRadikal/Free-v2ray-Configs/main/top100.txt",
    "https://raw.githubusercontent.com/0xRadikal/Free-v2ray-Configs/main/verified/configs.txt",
    "https://raw.githubusercontent.com/Alirewa/V2ray-Configs/main/config.txt",
    "https://raw.githubusercontent.com/morpheusadam/v2ray-config/main/subs/bundles/best.txt",
    "https://raw.githubusercontent.com/Delta-Kronecker/V2ray-Config/refs/heads/main/config/tcp-pass/batch_013.txt",
    "https://raw.githubusercontent.com/coldwater-10/V2ray-Config/main/Sub7.txt",
]

EMOJIS = [
    "🦁","🐯","🦊","🐺","🐻","🐉","🦅","🦋","🌟","⚡",
    "🔥","💎","🚀","🎯","🏆","👑","🍀","🌸","🌊","⭐"
]

CONFIG_PATTERNS = [
    r'(?<![A-Za-z0-9])vmess://[A-Za-z0-9+/=_-]+',
    r'(?<![A-Za-z0-9])vless://[^\s<>"\'`]+',
    r'(?<![A-Za-z0-9])trojan://[^\s<>"\'`]+',
    r'(?<![A-Za-z0-9])ss://[^\s<>"\'`]+',
    r'(?<![A-Za-z0-9])ssr://[A-Za-z0-9+/=_-]+',
    r'(?<![A-Za-z0-9])hysteria2?://[^\s<>"\'`]+',
    r'(?<![A-Za-z0-9])hy2://[^\s<>"\'`]+',
    r'(?<![A-Za-z0-9])tuic://[^\s<>"\'`]+',
    r'(?<![A-Za-z0-9])wireguard://[^\s<>"\'`]+',
    r'(?<![A-Za-z0-9])anytls://[^\s<>"\'`]+',
]

def load_sent_configs():
    if os.path.exists(SENT_FILE):
        with open(SENT_FILE, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def save_sent_configs(sent_set):
    # مرتب‌سازی باعث می‌شود فایل تاریخچه پایدار و قابل مقایسه بماند.
    items = sorted(sent_set)[-MAX_SENT_HISTORY:]
    with open(SENT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(items) + ("\n" if items else ""))

def config_key(config):
    # نام بعد از # را از کلید حذف می‌کنیم تا تغییر اسم باعث تکرار نشود.
    return config.split("#", 1)[0].strip()

def decode_subscription_if_needed(text):
    """اگر فید شامل URI خام نبود، تلاش می‌کند محتوای Base64 را باز کند."""
    if re.search(r'(?:vmess|vless|trojan|ss|ssr|hysteria2?|hy2|tuic|wireguard|anytls)://', text, re.I):
        return text
    compact = re.sub(r'\s+', '', text)
    if len(compact) < 20 or not re.fullmatch(r'[A-Za-z0-9+/=_-]+', compact):
        return text
    try:
        padded = compact + "=" * ((4 - len(compact) % 4) % 4)
        decoded = base64.b64decode(padded).decode("utf-8", errors="ignore")
        if re.search(r'(?:vmess|vless|trojan|ss|ssr|hysteria2?|hy2|tuic|wireguard|anytls)://', decoded, re.I):
            return decoded
    except Exception:
        pass
    return text

def is_valid_config(config):
    try:
        config = config.strip().rstrip(".,;)")
        if config.startswith("vmess://"):
            encoded = config[8:]
            padded = encoded + "=" * ((4 - len(encoded) % 4) % 4)
            decoded = base64.urlsafe_b64decode(padded).decode("utf-8")
            data = json.loads(decoded)
            return bool(data.get("add")) and str(data.get("port", "")).isdigit() and 0 < int(data["port"]) < 65536
        scheme, rest = config.split("://", 1)
        if scheme.lower() == "ss":
            # SS ممکن است به صورت base64-method:password@host:port یا SIP002 باشد.
            if "@" not in rest:
                padded = rest.split("#", 1)[0].split("?", 1)[0]
                padded += "=" * ((4 - len(padded) % 4) % 4)
                decoded = base64.urlsafe_b64decode(padded).decode("utf-8", errors="ignore")
                rest = decoded
            host_port = rest.split("@", 1)[-1].split("#", 1)[0].split("?", 1)[0]
        else:
            rest = rest.split("#", 1)[0].split("?", 1)[0]
            if "@" in rest:
                host_port = rest.rsplit("@", 1)[1]
            else:
                host_port = rest
            host_port = host_port.split("/", 1)[0]
        # IPv6:port یا host:port
        match = re.search(r'(\[[0-9a-fA-F:]+\]|[^:/?#@]+):(\d{1,5})$', host_port)
        if match:
            port = int(match.group(2))
            return bool(match.group(1)) and 0 < port < 65536
    except Exception:
        return False
    return False

def extract_configs(text):
    text = html.unescape(text).replace("\\/", "/")
    text = decode_subscription_if_needed(text)
    found = set()
    for pattern in CONFIG_PATTERNS:
        for match in re.findall(pattern, text, re.IGNORECASE):
            cleaned = match.strip().rstrip(".,;)")
            if cleaned:
                found.add(cleaned)
    return list(found)

def rename_config(config, channel_name, emoji):
    new_name = f"{emoji} {channel_name}"
    try:
        if config.startswith("vmess://"):
            encoded = config[8:]
            padded = encoded + "=" * ((4 - len(encoded) % 4) % 4)
            data = json.loads(base64.urlsafe_b64decode(padded).decode("utf-8"))
            data["ps"] = new_name
            new_encoded = base64.b64encode(json.dumps(data, ensure_ascii=False).encode()).decode()
            return f"vmess://{new_encoded}"
        # در لینک‌های URI نام فقط در fragment تغییر می‌کند.
        return config.split("#", 1)[0] + "#" + __import__("urllib.parse").parse.quote(new_name)
    except Exception:
        return config

async def fetch_text(session, url, label):
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; FreeAutoConfigBot/2.0)"}
        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=25)) as resp:
            if resp.status == 200:
                text = await resp.text(errors="ignore")
                configs = extract_configs(text)
                print(f"✅ منبع {label}: {len(configs)} کانفیگ خام")
                return configs
            print(f"⚠️ منبع {label}: HTTP {resp.status}")
    except Exception as exc:
        print(f"⚠️ منبع {label}: {exc}")
    return []

async def fetch_channel_configs(session, channel):
    return await fetch_text(session, f"https://t.me/s/{channel}", f"@{channel}")

async def send_to_channel(session, text):
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN":
        print("❌ BOT_TOKEN تنظیم نشده است؛ در GitHub Secrets مقدار BOT_TOKEN را اضافه کن.")
        return False
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": TARGET_CHANNEL,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    try:
        async with session.post(url, json=data, timeout=aiohttp.ClientTimeout(total=20)) as resp:
            result = await resp.json()
            if not result.get("ok"):
                print(f"❌ Telegram API: {result}")
            return result.get("ok", False)
    except Exception as exc:
        print(f"❌ خطا در ارسال: {exc}")
        return False

def make_message(configs):
    now = datetime.now(IRAN_TZ).strftime("%H:%M")
    # HTML escape جلوی خراب‌شدن parse_mode را می‌گیرد.
    safe_configs = "\n".join(html.escape(c) for c in configs)
    return (
        f"🔥 <b>{html.escape(CHANNEL_NAME)}</b> 🔥\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"⏰ <b>آپدیت:</b> <code>{now}</code> (به وقت ایران)\n"
        f"📦 <b>تعداد کانفیگ:</b> <code>{len(configs)}</code>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"<pre>{safe_configs}</pre>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"📢 <b>{html.escape(CHANNEL_NAME)}</b>\n"
        "🔄 بروزرسانی خودکار هر ۱۰ دقیقه"
    )

async def main():
    print(f"\n{'='*45}\n🚀 شروع اجرا: {datetime.now(IRAN_TZ).strftime('%Y-%m-%d %H:%M:%S')}\n{'='*45}")
    if not BOT_TOKEN:
        print("❌ متغیر BOT_TOKEN تنظیم نشده است.")
        return

    sent_configs = load_sent_configs()
    timeout = aiohttp.ClientTimeout(total=30)
    connector = aiohttp.TCPConnector(limit=12, ttl_dns_cache=300)
    async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
        tasks = [fetch_channel_configs(session, ch) for ch in SOURCE_CHANNELS]
        tasks += [fetch_text(session, url, url.split("/")[3] if len(url.split("/")) > 3 else url) for url in SOURCE_URLS]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_configs = []
        for result in results:
            if isinstance(result, list):
                all_configs.extend(result)

        unique = {}
        for config in all_configs:
            key = config_key(config)
            if key not in unique and is_valid_config(config):
                unique[key] = config

        new_configs = [c for c in unique.values() if config_key(c) not in sent_configs]
        print(f"📊 کل یکتا و معتبر از نظر ساختار: {len(unique)} | جدید: {len(new_configs)}")

        # اولویت با مواردی است که قبلاً منتشر نشده‌اند.
        pool = new_configs if new_configs else list(unique.values())
        if not pool:
            print("❌ از هیچ منبعی کانفیگ قابل‌استفاده پیدا نشد.")
            return

        random.shuffle(pool)
        selected = pool[:MAX_CONFIGS_PER_POST]
        renamed = [rename_config(c, CHANNEL_NAME, random.choice(EMOJIS)) for c in selected]
        message = make_message(renamed)

        if await send_to_channel(session, message):
            sent_configs.update(config_key(c) for c in selected)
            save_sent_configs(sent_configs)
            print(f"✅ پست شد: {len(selected)} کانفیگ")
        else:
            print("❌ پست ارسال نشد؛ تاریخچه تغییر نکرد.")

if __name__ == "__main__":
    asyncio.run(main())
