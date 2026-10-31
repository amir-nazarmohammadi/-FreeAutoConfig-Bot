import asyncio
import time
import threading
from bot import main as config_main
from proxy_bot import main_proxy

INTERVAL = 10 * 60

def runner(label, function):
    while True:
        try:
            asyncio.run(function())
        except Exception as exc:
            print(f"❌ {label}: {exc}")
        time.sleep(INTERVAL)

if __name__ == "__main__":
    print("🤖 Auto-bot-tel started: configs + MTProto every 10 minutes")
    threading.Thread(target=runner, args=("configs", config_main), daemon=True).start()
    runner("MTProto", main_proxy)
