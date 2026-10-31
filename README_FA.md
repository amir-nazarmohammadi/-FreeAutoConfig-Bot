# Auto-bot-tel — enhanced version

ربات جمع‌آوری کانفیگ‌های عمومی سازگار با V2RayNG و پروکسی‌های عمومی MTProto و انتشار آن‌ها در کانال تلگرام.

## راه‌اندازی روی GitHub Actions

1. تمام فایل‌های این پروژه را در ریشهٔ repository خودت آپلود کن؛ پوشهٔ `.github/workflows` هم باید حفظ شود.
2. در BotFather یک ربات بساز یا از ربات فعلی استفاده کن. توکن را در کد ننویس.
3. ربات را به کانال مقصد اضافه کن و دسترسی **Post Messages** بده.
4. در GitHub repository برو به **Settings → Secrets and variables → Actions → New repository secret** و secret زیر را بساز:
   - Name: `BOT_TOKEN`
   - Secret: توکن BotFather
5. (اختیاری) در **Settings → Secrets and variables → Actions → Variables** یک variable بساز:
   - Name: `TARGET_CHANNEL`
   - Value: `@FreeAutoConfig`
   اگر این variable را نسازی، همین کانال پیش‌فرض استفاده می‌شود.
6. در **Settings → Actions → General → Workflow permissions** گزینهٔ **Read and write permissions** را انتخاب کن تا تاریخچهٔ کانفیگ‌ها ذخیره شود.
7. از تب **Actions** workflow با نام `Auto Config and MTProto Bot` را باز کن و **Run workflow** را بزن.
8. لاگ هر اجرا را بررسی کن. اگر منبعی 404 داد، حذف یا با فید معتبر دیگری جایگزینش کن.

## زمان‌بندی

GitHub Actions طبق cron هر ۱۰ دقیقه تلاش می‌کند اجرا شود؛ زمان‌بندی دقیق تضمین‌شده نیست و GitHub ممکن است اجرا را با تأخیر شروع کند. هر اجرای موفق می‌تواند یک پست کانفیگ و یک پست MTProto منتشر کند؛ بنابراین ممکن است دو پست در هر چرخه داشته باشی.

## افزودن منابع

- منابع کانال تلگرام را به `SOURCE_CHANNELS` در `bot.py` اضافه کن؛ فقط نام کانال بدون `@`.
- فیدهای متنی یا subscription URL را به `SOURCE_URLS` اضافه کن.
- منابع پروکسی را به `PROXY_SOURCES` یا `PROXY_SOURCE_URLS` در `proxy_bot.py` اضافه کن.
- فیدهای عمومی ممکن است حذف شوند یا آدرس‌شان تغییر کند. لاگ Actions را بررسی کن.

## نکات امنیتی و کیفیت

- هیچ توکنی را داخل فایل کد یا commit عمومی قرار نده؛ فقط GitHub Secret.
- کانفیگ‌های عمومی شخص ثالث هستند؛ بررسی ساختاری به معنی تست اتصال واقعی یا امن بودن سرویس نیست.
- ربات فقط از منابع عمومی می‌خواند؛ به منابع فشار بیش از حد وارد نکن.
- GitHub Actions ممکن است اجرا را به تأخیر بیندازد. برای اجرای پیوستهٔ دقیق‌تر، یک VPS مناسب‌تر است.
