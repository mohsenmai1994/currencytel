# CurrencyTel v2.9 — کانال‌های قیمت + اپلیکیشن PWA

نسخه ماژولار قابل استقرار روی GitHub Actions و GitHub Pages. قالب کانال‌ها تنها **۱۴ قیمت اصلی** را نشان می‌دهد؛ PWA با بازارهای تکمیلی، جستجو، فیلتر، علاقه‌مندی، نمودار گزارش‌های ذخیره‌شده و محاسبه‌گر عرضه می‌شود. داده واقعی از صفحات عمومی `alanchand.com` خوانده می‌شود؛ هیچ قیمت نمونه‌ای برای انتشار استفاده نمی‌شود.

## رفع مشکلات نسخه قبل

- خطای `name 'TITLE' is not defined`: قالب پیام در `currencytel/report.py` با `HEADER_HASHTAGS` و `SIGNATURE` ثابت و تست‌شده ساخته می‌شود؛ تست ذخیره گزارش هم اضافه شده است.
- بیت‌کوین: استخراج **قیمت دلاری** از ستون مشخص `Price (USD)` و کنترل مجدد با صفحه `/en/crypto-price/btc`؛ هیچ‌وقت قیمت ریالی را به‌عنوان دلار منتشر نکنید.
- فرمت دقیق پیام شبکه‌ها:

  ```text
  #نرخ_ارز #سکه #طلا #دلار #بیتکوین

  ☸️دلار آمریکا: 263,100 تومان
  ... ۱۲ نرخ دیگر در همان ترتیب قبلی ...
  ✴️ تتر: 261,566 تومان

  ID: @currencytel
  ```
  اعداد بالا **صرفاً مثال قالب** هستند و توسط برنامه جایگزین قیمت‌های واقعی می‌شوند.
- PWA: منوی کناری دسکتاپ، ناوبری پایین موبایل، کارت‌های شاخص، جدول/کارت‌های واکنش‌گرا، جزئیات با لمس هر دارایی، زمان‌سنج وضعیت داده، ابزارهای قبلی و وضعیت بازارها.
- جمع‌آوری بیشتر از سایت منبع: صفحه انرژی، بورس ایران، فارکس و اوراق (در صورت دسترسی و واحد قابل تشخیص) علاوه بر ارز، طلا، رمزارز، کشاورزی، فلزات و بازارهای جهانی. فیلدهایی مثل تغییر درصد، کمینه/بیشینه، وضعیت بازار، قیمت دلاری/تومانی فقط با وجود مقدار قابل‌استناد در منبع ثبت می‌شوند. تعداد آیتم‌ها ثابت نیست.

## استقرار در GitHub

1. پیش از جایگزینی، از مخزن فعلی نسخه پشتیبان بگیرید و ترجیحاً نسخه جدید را ابتدا در branch آزمایشی قرار دهید.
2. **همه فایل‌های داخل ZIP** (از جمله پوشه مخفی `.github`) را در ریشه مخزن قرار دهید. جایگزینی یک فایل ZIP در GitHub باعث استخراج خودکار نمی‌شود؛ آن را روی رایانه استخراج کنید.
3. GitHub Secrets و Variables فعلی شما نیاز به تغییر ندارند. متغیرهای `ENABLE_TELEGRAM`, `ENABLE_BALE`, `ENABLE_RUBIKA` صرفاً برای کانال‌هایی `1` باشند که می‌خواهید واقعاً پیام بگیرند. قالب همه آنها از `report.py` می‌آید. برای تست فقط روبیکا، دو کانال دیگر را موقتاً `0` کنید.
4. ابتدا `Actions → CurrencyTel | Tests` را اجرا کنید. سپس `Actions → CurrencyTel | Fetch & publish` را اجرا کنید؛ این Workflow ممکن است **پیام واقعی** منتشر کند.
5. برای PWA، از `Settings → Pages` انتشار GitHub Pages از root شاخه اصلی را فعال کنید (یا تنظیم Pages موجود را حفظ کنید). `index.html` در ریشه است؛ نام فایل Workflow اصلی `hourly_run.yml` تغییر نکرده است.
6. اگر اینستاگرام با روش غیررسمی قبلی فعال است، دو Secret `INSTAGRAM_USERNAME`, `INSTAGRAM_PASSWORD` حفظ شده‌اند؛ تغییر جدیدی در احراز هویت Instagram اعمال نشده است. راهنما در `INSTAGRAM_SETUP_FA.md` قرار دارد.

## معماری

| مسیر | کاربرد |
|---|---|
| `currencytel/sources/alanchand.py` | دریافت و استخراج و اعتبارسنجی بازار و بیت‌کوین USD |
| `currencytel/catalog.py` | فهرست ثابت ۱۴ نرخ و دارایی‌های اختیاری |
| `currencytel/report.py` | قالب یکسان پیام تلگرام، بله و روبیکا |
| `currencytel/storage.py` | داده PWA، تاریخچه و خلاصه گزارش |
| `currencytel/media.py` | تصویر مخصوص اینستاگرام (جدا از قالب متنی کانال‌ها) |
| `currencytel/publishers/` | ارسال‌کننده‌های مجزا |
| `index.html`, `assets/css/main.css`, `assets/js/` | رابط کاربری PWA |
| `.github/workflows/hourly_run.yml` | دریافت، انتشار و commit داده |
| `.github/workflows/instagram.yml` | انتشار اختیاری Instagram |

## نکات مهم

- `Loaded /en` یعنی صفحه خوانده شده، نه اینکه انتشار در کانال‌ها موفق بوده باشد. موفقیت هر کانال را در `Publisher outcomes` بررسی کنید.
- افزایش داده PWA مشروط به در دسترس بودن صفحه و واحد قیمت معتبر است؛ اطلاعات غایب حدس زده نمی‌شوند.
- وضعیت «قدیمی / آرشیوی» در سایت روشن نمایش داده می‌شود؛ دریافت قیمت توسط GitHub Actions لزوماً لحظه‌ای نیست.
- PWA در مرورگر سبک و قابل نصب است؛ نمودار آن بر مبنای **تاریخچه ثبت‌شده همین پروژه** است نه آرشیو کامل سایت منبع.
- انتشار اینستاگرام با `instagrapi` غیررسمی است و ممکن است درخواست تأیید حساب یا محدودیت داشته باشد. نشست را فقط پس از ورود موفق ذخیره کنید؛ هرگز رمز/توکن را در کد یا چت منتشر نکنید.
- این نسخه با تست‌های آفلاین و بررسی نحوی JavaScript آزموده شده است؛ استخراج از سایت زنده، انتشار واقعی در کانال‌ها، و رندر گرافیکی در مرورگر کاربر بعد از استقرار باید تأیید شوند.


## v3.0: Instagram email/SMS verification in GitHub Actions

Workflow `CurrencyTel | Instagram verification and posting` has a `Run workflow` form: `mode=verify_login` (does **not** publish), optional `verification_code` (6–8 digits), and `mode=publish`. Normal scheduled publication uses the stored encrypted session. See `INSTAGRAM_SETUP_FA.md`.

Security note: GitHub `workflow_dispatch` inputs are **not secrets**. For sensitive codes, use a **temporary** `INSTAGRAM_ONE_TIME_CODE` repository Secret, leave the form input blank, run `verify_login`, then delete that temporary Secret. Only `INSTAGRAM_USERNAME` and `INSTAGRAM_PASSWORD` remain permanent.
