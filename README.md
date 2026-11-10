## رفع خطاهای انتشار — نسخه ۲.۱ (۱۰ نوامبر ۲۰۲۶)

پس از لاگ ۱۴ نرخ اصلی و ۸۲ نرخ تکمیلی، مشکلات شناسایی‌شده اصلاح شدند:

- پوشه `assets/generated/` هنگام تولید کارت اینستاگرام ساخته می‌شود؛ خطای `FileNotFoundError` مربوط به پوشه خروجی رفع شد.
- مرحله Git در `hourly_run.yml` فقط پوشه‌های موجود را Stage می‌کند و با نبودن تصویر شکست نمی‌خورد.
- `TELEGRAM_CHAT_ID` اکنون ابتدا از Secret، سپس از Variable و در نهایت از `@currencytel` خوانده می‌شود. نسخه قبلی همیشه مقدار ثابت `@currencytel` را اعمال می‌کرد.
- خطاهای API با توضیح‌های ایمن ثبت می‌شوند، بدون چاپ توکن.
- یک Workflow جدید **CurrencyTel | Check channel access (no posts)** وجود دارد؛ با `Run workflow` اجرا کنید. این Workflow پیام منتشر نمی‌کند و فقط به کمک `getMe` و `getChat`، شناسه ربات و دسترسی‌های کانال را بررسی می‌کند.
- در روبیکا، `RUBIKA_CHAT_ID` باید GUID کانال باشد. مقدار `@currencytel` به‌عنوان شناسه API رد می‌شود؛ این مقدار صرفاً آدرس عمومی است.

**مراحل رفع HTTP 403:** ربات تلگرام و بله را به‌عنوان مدیر کانال با مجوز انتشار اضافه کنید؛ مطمئن شوید توکن Secret متعلق به همان ربات است و `@currencytel` دقیقاً نام کاربری کانال در هر شبکه است. اگر کانال خصوصی باشد، شناسه واقعی کانال را استفاده کنید. ابتدا Workflow تشخیصی بدون انتشار را اجرا کنید. اجرای `Fetch & publish` پیام واقعی می‌فرستد و فقط پس از حل دسترسی‌ها مناسب است.

### نکته انتشار

این اصلاح‌ها مشکل محلی تولید تصویر و Git را برطرف می‌کند؛ **هیچ تست زنده‌ای با توکن‌های خصوصی انجام نشده است**. لازم است دسترسی واقعی هر بات در حساب‌های خودتان بررسی شود.

---

# CurrencyTel — نسخه ماژولار

داشبورد نصب‌شدنی PWA و انتشار خودکار **دقیقاً ۱۴ نرخ** به تلگرام، بله، روبیکا و (در دو مرحله) اینستاگرام. منبع موجود در مخزن ارسالی شما **alanchand.com** بود؛ همین منبع حفظ شده است. هیچ قیمت نمونه‌ای به‌جای قیمت زنده منتشر نمی‌شود.

## چرا این ساختار؟

```text
currencytel/
  catalog.py             # فهرست دقیق ۱۴ نرخ + بازارهای اضافی وب‌سایت
  models.py              # مدل‌های مشترک داده
  settings.py            # تنظیمات و فعال‌سازی شبکه‌ها
  browser.py             # درایور سریع Selenium
  sources/alanchand.py   # دریافت و تحلیل HTML؛ بدون API پولی
  report.py              # گزارش فقط ۱۴ نرخ
  storage.py             # market.json / history.json / market_log.txt
  dispatch.py            # مدیریت ارسال مستقل + جلوگیری از ارسال تکراری
  publishers/
    telegram.py
    bale.py
    rubika.py
    instagram.py
  media.py               # کارت تصویری ۱۴ نرخ اینستاگرام
main.py                  # اجرای یک‌مرحله‌ای بازار + شبکه‌های متنی
scripts/post_instagram.py  # انتشار دو‌مرحله‌ای اینستاگرام
assets/css/main.css      # رابط PWA
assets/js/               # اپ ماژولار بدون کتابخانه سنگین فرانت‌اند
assets/icons/            # آیکون نصب
sw.js                    # Service Worker
manifest.webmanifest     # تنظیمات PWA
data/market.json         # مرجع قیمت سایت
data/history.json        # تاریخچه گزارش‌های موفق
market_log.txt           # خروجی متنی با فرمت قدیمی برای سازگاری
.github/workflows/       # market / instagram / test
```

## ۱. نصب روی GitHub

1. پوشه‌های این ZIP را به **ریشه** مخزن GitHub منتقل و Commit کنید (نه داخل یک پوشه فرعی). نسخه قدیمی `Scraper.py`، `TelegramWebScraper.py`، `app.js`، `style.css`، `config.js` دیگر لازم نیست.
2. در **Settings → Secrets and variables → Actions → Secrets**، برای تلگرام `BOT_TOKEN` قبلی شما همچنان پذیرفته می‌شود. یا `TELEGRAM_BOT_TOKEN` تعریف کنید. مقدار توکن را در فایل عمومی وارد نکنید.
3. در همان صفحه، بخش **Variables** تنظیمات `ENABLE_TELEGRAM=1`، و در صورت آماده بودن بات‌ها `ENABLE_BALE=1` و `ENABLE_RUBIKA=1` را قرار دهید.
4. برای بله `BALE_BOT_TOKEN` و `BALE_CHAT_ID`، برای روبیکا `RUBIKA_BOT_TOKEN` و **شناسه واقعی چت کانال (GUID)** در `RUBIKA_CHAT_ID` را به Secrets اضافه کنید. هندل `currencytel` لزوماً Chat ID مورد پذیرش API روبیکا نیست.
5. هر بات باید به کانال مربوط **اضافه و ادمین** شده و مجوز ارسال داشته باشد.
6. در **Actions → CurrencyTel | Fetch & publish → Run workflow** یک‌بار دستی اجرا کنید. پس از اجرای موفق `data/market.json`، `data/history.json` و `market_log.txt` به‌روز می‌شوند.
7. در **Settings → Pages** منبع را `Deploy from a branch`، شاخه `main` و مسیر `/ (root)` قرار دهید. سایت با آدرس GitHub Pages خودتان باز می‌شود. اگر مخزن از قبل Pages فعال دارد، URL قبلی سایت حفظ می‌شود.

### زمان‌بندی با cron-job.org

نام فایل اصلی Workflow یعنی **`hourly_run.yml` حفظ شده است** تا آدرس Job قبلی cron-job.org در صورت استفاده از همان Workflow ID همچنان معتبر بماند. بااین‌حال یک بار Cron را بررسی کنید. این پروژه عمداً **GitHub Actions schedule** ندارد؛ می‌توانید همان cron-job.org فعلی را نگه دارید و در فاصله انتخابی `workflow_dispatch` یا `repository_dispatch` با نوع `market_update` را اجرا کنید. اگر برای مخزن تغییر کرده‌اید، نام مخزن و آدرس Dispatch را در Cron اصلاح کنید. GitHub API نیازمند توکن با مجوز Actions/Contents مناسب است؛ آن توکن را در مخزن عمومی نگذارید. اجرای کمتر از طول مدت یک نوبت باعث صف‌شدن اجراها می‌شود.

## ۲. شبکه‌های اجتماعی

همه ناشرها فقط گزارش **۱۴ نرخ** را می‌گیرند، به ترتیب ثابت: دلار، یورو، پوند، لیر، فرانک، یوان، سکه بهار، نیم، ربع، انس طلا، طلای ۱۸ عیار، برنت، بیت‌کوین و تتر؛ به‌علاوه یک سطر آدرس کانال `@currencytel`. **اطلاعات اضافه PWA به شبکه‌ها نمی‌روند.**

- **Telegram:** `https://api.telegram.org/bot…/sendMessage`، توکن `TELEGRAM_BOT_TOKEN` یا `BOT_TOKEN`، کانال `@currencytel`.
- **Bale:** `https://tapi.bale.ai/bot…/sendMessage`، توکن `BALE_BOT_TOKEN` و شناسه `BALE_CHAT_ID`.
- **Rubika:** `https://botapi.rubika.ir/v3/{token}/sendMessage`؛ توکن و `RUBIKA_CHAT_ID` واقعی.
- **Instagram:** چون پست فید نیازمند عکس است، HTML راست‌به‌چپ نرخ‌ها در Chromium به JPEG ۱۰۸۰×۱۳۵۰ تبدیل می‌شود. تصویر و گزارش در صف می‌مانند. در مرحله دوم و **پس از اینکه GitHub Pages تصویر را عمومی کرد**، Workflow `CurrencyTel | Publish prepared Instagram image` اجرا می‌شود.

### راه‌اندازی اینستاگرام

1. حساب اختصاصی CurrencyTel را از نوع **Professional (Business یا Creator)** کنید. مجوزهای لازم برای **Instagram API with Instagram Login** و `instagram_business_content_publish` را تنظیم کنید. برای حساب شخصی از این API نمی‌توان پست کرد.
2. `INSTAGRAM_ACCESS_TOKEN`، `INSTAGRAM_ACCOUNT_ID` در Secrets و `ENABLE_INSTAGRAM=1`، `PUBLIC_SITE_URL` در Variables را تعریف کنید. `PUBLIC_SITE_URL` باید **آدرس کامل سایت فعال** بدون اسلش انتهایی باشد؛ برای مثال `https://USERNAME.github.io/REPO`.
3. ابتدا Workflow بازار را اجرا کنید و مطمئن شوید فایل `assets/generated/post-XXXXXXXX.jpg` در Pages قابل دریافت است. **بعد** Workflow اینستاگرام را اجرا کنید.
4. برای اجرای منظم هر دو، دو Cron جدا داشته باشید: اول بازار، دوم انتشار اینستاگرام با تأخیری که برای به‌روزرسانی Pages کافی است. در صورت نرسیدن عکس به آدرس عمومی، پست اینستاگرام ارسال نمی‌شود.
5. در برخی انواع دسترسی، وضعیت اپ، تأیید Meta، تمدید Access Token و سیاست مجوزها محدودیت دارند. انتشار زنده قبل از اخذ مجوز و اجرای موفق تست تأیید نمی‌شود.

### نکات ایمنی انتشار

- به‌صورت پیش‌فرض در Workflow فقط تلگرام فعال است؛ بله و روبیکا تا زمان ورود Secrets و فعال‌کردن Variables خاموش هستند، اینستاگرام نیز مستقل است.
- هر قیمت ضروری اگر پیدا نشود، **هیچ قیمت ناقصی منتشر نمی‌شود** و اطلاعات قبلی دست‌نخورده می‌ماند.
- اگر محتوای ۱۴ نرخ با گزارش قبلی یکسان باشد، برای همان کانال دوباره ارسال نمی‌شود. `POST_UNCHANGED=1` این رفتار را تغییر می‌دهد.
- پس از ارسال موفق یک شبکه، شناسه/هش آن ذخیره می‌شود؛ شبکه‌ای که خطا داده، در نوبت بعد مستقل تکرار می‌شود. **تضمین دقیق یک‌بار ارسال در لحظه قطع ناگهانی runner وجود ندارد**؛ بدون پایگاه‌داده تراکنشی، ارسال دوباره در این حالت نادر ممکن است.
- اگر صفحه منبع تغییر کند یا دسترسی GitHub Runner به آن قطع شود، خطا ثبت می‌شود. سایت قیمت ساختگی دریافت نمی‌کند.

## ۳. PWA

به‌جای محدود کردن وب‌اپ به ۱۴ قیمت، صفحات فهرست ارز، طلا، رمزارز، فلزات پایه، کشاورزی و بازارهای جهانی بررسی می‌شوند. فقط ردیف‌هایی که نام و نرخشان به شکل معتبر در HTML شناسایی شوند به داده سایت اضافه می‌شوند. هر مورد دارای مسیر منبع و در صورت موجود بودن، تغییر روزانه، سقف/کف، قیمت خرید و داده جانبی است. برای سکه و طلا نیز در صورت وجود، درصد حباب ثبت می‌شود. جدول وب‌اپ دارای فیلتر، مرتب‌سازی، جستجو، علاقه‌مندی، نمودار مبتنی بر فایل تاریخچه، محاسبه‌گر، تم روشن/تیره و نصب PWA است.

**توجه:** `fetched_at` زمان *دریافت گزارش* است و الزاماً زمان تغییر آخرین قیمت در منبع نیست. نمونه اولیه مهاجرت از `market_log.txt` با نشان «زمان نامشخص/آرشیوی» نمایش داده می‌شود تا داده قدیمی به‌عنوان نرخ لحظه‌ای معرفی نشود. نمودار تنها پس از جمع شدن چند اجرای موفق شکل می‌گیرد. PWA روی HTTPS (GitHub Pages) قابلیت نصب و کش آفلاین دارد؛ آفلاین بودن به‌معنی زنده بودن قیمت‌های قبلی نیست.

## ۴. اجرای محلی و تست

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
# نیازمند Chromium/Chrome برای خواندن سایت
DRY_RUN=1 ENABLE_TELEGRAM=0 GENERATE_INSTAGRAM_CARD=0 python main.py
python -m http.server 8000
# http://localhost:8000
```

در Windows می‌توان مقدار متغیر محیط را از طریق PowerShell تنظیم کرد. برای استفاده تولیدی، اجرای `python main.py` به GitHub Actions سپرده می‌شود.

## منابع رسمی

- AlanChand: https://alanchand.com/en/media/api (API آن جداگانه دارای شرایط/هزینه است؛ در این پروژه استفاده نمی‌شود)
- Bale: https://bale.ai/dev
- Rubika: https://rubika.ir/botapi و https://rubika.ir/botapi/group-channel
- Meta: https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/content-publishing

این پروژه به‌صورت مستقل توسعه یافته و وابسته به API پولی منبع نیست. احترام به شرایط استفاده سایت، محدودیت درخواست و حقوق محتوایی منبع ضروری است.
