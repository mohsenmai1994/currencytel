# CurrencyTel v2.8 — پروژه کامل چندسکویی و PWA

نسخه ماژولار برای قیمت ارز، طلا و بازار، با استخراج از alanchand.com، ۱۴ نرخ ثابت برای کانال‌های تلگرام/بله/روبیکا، وب‌اپ PWA شامل قیمت‌های تکمیلی و کارت اینستاگرام. متن خروجی کانال‌ها بدون تغییر و مطابق درخواست: `قیمت #ارز، #طلا و #بازار`، ۱۴ نرخ و `🆔 @currencytel`.

## شروع سریع

1. همه فایل‌ها و پوشه‌های ZIP را در **ریشه** مخزن GitHub آپلود کنید. از نسخه فعلی مخزن نسخه پشتیبان داشته باشید.
2. Secrets شبکه‌ها را مطابق نمونه `.env.example` نگه دارید. برای اینستاگرام **فقط** این دو Secret لازم است: `INSTAGRAM_USERNAME` و `INSTAGRAM_PASSWORD`. Secret `INSTAGRAM_SESSION_KEY` از نسخه پیشین لازم نیست.
3. در GitHub Variables مقدارهای `GENERATE_INSTAGRAM_CARD=1` و `ENABLE_INSTAGRAM=1` را تنظیم کنید؛ برای جلوگیری از انتشار پرتکرار، `INSTAGRAM_MAX_DAILY_POSTS=3` و `INSTAGRAM_MIN_HOURS=4` را استفاده کنید.
4. `Actions → CurrencyTel | Fetch & publish` برای دریافت قیمت، تولید تصویر و ارسال به کانال‌های فعال اجرا می‌شود.
5. `Actions → CurrencyTel | Instagram auto-post (two Secrets)` تصویر را با روش غیررسمی `instagrapi` به اینستاگرام می‌فرستد. اولین نشست موفق **خودکار** در `.github/state/instagram_session.enc` به‌صورت AES-256-GCM رمزگذاری می‌شود و توسط GitHub Actions ثبت می‌شود.

**نکته:** کلید رمزگذاری با `scrypt` از رمز حساب و salt تصادفی مشتق می‌شود و نیازی به ثبت/ذخیره Secret سوم نیست. فایل سشن قدیمی `data/instagram_session.enc` دیگر استفاده نمی‌شود و در صورت وجود، Workflow آن را از مخزن حذف می‌کند. اگر اینستاگرام تأیید ایمیل/SMS/2FA تعاملی بخواهد، GitHub نمی‌تواند با فقط دو Secret آن را انجام دهد؛ راهنمای بازیابی در `INSTAGRAM_SETUP_FA.md` است.

## ساختار

- `currencytel/sources/`: دریافت بازار
- `currencytel/report.py`: قالب یکسان ۱۴ نرخ شبکه‌ها
- `currencytel/media.py`: کارت تصویری اینستاگرام
- `currencytel/publishers/`: ماژول‌های مستقل Telegram / Bale / Rubika / Instagram
- `.github/workflows/hourly_run.yml`: دریافت و انتشار قیمت
- `.github/workflows/instagram.yml`: انتشار اختیاری اینستاگرام + ذخیره نشست بدون Secret سوم
- `scripts/post_instagram.py`: محدودیت دفعات انتشار، حذف تکراری‌ها، پست تصویر
- `assets/`, `index.html`, `manifest.webmanifest`, `sw.js`: PWA
- `tests/`: تست‌های آفلاین

این API اینستاگرام رسمی نیست؛ موفقیت ورود/انتشار در GitHub تضمین نمی‌شود و IP متغیر GitHub ممکن است باعث چالش امنیتی یا محدودشدن حساب شود. **توکن‌ها/رمز را در کد، README یا لاگ ننویسید.**
