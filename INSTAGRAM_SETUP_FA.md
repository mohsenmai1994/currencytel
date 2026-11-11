# راه‌اندازی خودکار اینستاگرام با فقط دو Secret — CurrencyTel v2.8

این نسخه روش غیررسمی `instagrapi` را استفاده می‌کند و **برای شروع Meta App، توکن Graph API، کلید سشن، بارگذاری دستی فایل سشن یا اجرای کد روی کامپیوتر نیاز ندارد**؛ به شرطی که اینستاگرام ورود اولیه از GitHub را بدون Challenge بپذیرد.

## تنظیمات فقط یک‌بار

در GitHub به `Settings → Secrets and variables → Actions → Secrets` بروید و این دو مقدار را بسازید:

| Secret | مقدار |
|---|---|
| `INSTAGRAM_USERNAME` | نام کاربری حساب مستقل CurrencyTel، بدون `@` |
| `INSTAGRAM_PASSWORD` | رمز همان حساب |

در تب `Variables` مقدار `ENABLE_INSTAGRAM=1` و `GENERATE_INSTAGRAM_CARD=1` را ثبت کنید. به‌صورت اختیاری، `INSTAGRAM_MAX_DAILY_POSTS=3` و `INSTAGRAM_MIN_HOURS=4` را تعیین کنید.

**از `INSTAGRAM_SESSION_KEY` استفاده نکنید**؛ نیازی به آن نیست. فایل قدیمی `data/instagram_session.enc` نیز دیگر استفاده نمی‌شود.

## اجرای اولیه

1. پس از آپلود کامل پروژه، Workflow `CurrencyTel | Fetch & publish` را برای آماده‌سازی تصویر اجرا کنید.
2. بعد Workflow `CurrencyTel | Instagram auto-post (two Secrets)` را اجرا کنید. فایل تصویر از `assets/generated/` خوانده می‌شود.
3. اولین ورود موفق به Instagram، فایل رمزگذاری‌شده نشست را در `.github/state/instagram_session.enc` می‌سازد. Workflow آن را با مجوز `contents: write` **به‌طور خودکار** Commit می‌کند و برای اجراهای بعدی به‌کار می‌برد.
4. کلید AES-256 در هر بار ذخیره، با KDF `scrypt` از نام کاربری و رمز GitHub Secret و یک salt تصادفی ساخته می‌شود؛ کلید به‌صورت مستقل ذخیره نمی‌شود. **به هیچ Secret سومی نیاز نیست.**

**امنیت:** نشست فقط رمزگذاری‌شده ذخیره می‌شود، اما در مخزن عمومی، فایل رمزگذاری‌شده در تاریخچه Git قابل مشاهده است. از رمز قوی و منحصربه‌فرد برای CurrencyTel و احراز هویت دومرحله‌ای استفاده کنید. رمز ساده خطر حدس‌زدن آفلاین دارد. هیچ فایل JSON خام نشست یا کد ورود را Commit نکنید.

## اگر اولین ورود Challenge یا کد ایمیل خواست

کد نمی‌تواند ایمیل شما را بخواند یا کد تأیید را فقط با نام کاربری و رمز حدس بزند؛ بنابراین Workflow با خطای واضح متوقف می‌شود. **این محدودیت واقعی است.** ابتدا ورود را در خود اپ اینستاگرام تأیید کنید؛ اگر باز هم لازم بود، از اسکریپت اختیاری `scripts/setup_instagram.py` روی رایانه شخصی استفاده کنید و فقط فایل `.github/state/instagram_session.enc` را آپلود کنید. همچنان **تنها دو Secret** کافی است. این روش غیررسمی ممکن است باعث محدودیت حساب شود و ورود در IPهای متغیر GitHub ممکن است دوباره Challenge ایجاد کند.

## اگر پیام موفق بود ولی فایل نشست در GitHub ذخیره نشد

در `Settings → Actions → General → Workflow permissions`، دسترسی `Read and write permissions` را بررسی کنید؛ اگر شعبه محافظت‌شده باشد یا قوانین push مانع باشند، Commit نشست شکست می‌خورد. فایل و کلید را داخل لاگ GitHub چاپ نکنید.
