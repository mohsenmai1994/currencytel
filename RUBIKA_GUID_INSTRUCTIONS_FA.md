# نمایش GUID کانال روبیکا در GitHub Actions

این نسخه فقط برای یافتن GUID یک مرحله خواندنی اضافه می‌کند. هیچ پیامی از این مرحله ارسال نمی‌شود.

1. کدهای ZIP را در مخزن GitHub جایگزین کنید.
2. به `Actions > CurrencyTel | Check channel access (no posts) > Run workflow` بروید.
3. مرحله `Print Rubika GUID candidates (read-only, no posts)` را باز کنید.
4. از خط `RUBIKA_CHAT_ID=c0...` شناسه را بردارید.
5. فقط اگر مطمئن هستید شناسه به کانال خودتان مربوط است، در `Settings > Secrets and variables > Actions > Secrets > RUBIKA_CHAT_ID` جایگزین کنید.

اگر `getChat: NOT VERIFIED` دیده شد، تعلق GUID به کانال هنوز تأیید نشده است؛ قبل از انتشار واقعی احتیاط کنید. لاگ ممکن است در مخزن عمومی برای دیگران قابل مشاهده باشد. پس از تغییر Secret، از صفحه Secrets مقدار آن را دوباره نمی‌توانید بخوانید و برای تغییر باید Update کنید.

در اجرای بعدی، اگر خواستید فقط روبیکا پست بگذارد، ENABLE_BALE و ENABLE_TELEGRAM را موقتاً صفر کنید. توجه: تنها در صورتی که Workflow واقعاً این Variables را بخواند اثر می‌کنند؛ نام فعال‌سازی را در workflow مربوطه بررسی کنید.
