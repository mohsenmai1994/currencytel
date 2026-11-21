"""RSS sources and deployment settings; keep credentials in GitHub secrets."""


FEEDS = {
    "مهر": "https://www.mehrnews.com/rss/tp/25",
    "ایسنا": "https://www.isna.ir/rss",
    "ایرنا": "https://www.irna.ir/rss",
    "باشگاه خبرنگاران": "https://www.yjc.ir/fa/rss/allnews",
}

# Kept for compatibility with feeds.py's is_economic().
ECONOMIC_WORDS = (
    "اقتصاد", "تورم", "دلار", "ارز", "طلا", "سکه", "بورس", "بانک", "وام",
    "تسهیلات", "مسکن", "اجاره", "حقوق", "دستمزد", "یارانه", "کالابرگ",
    "خودرو", "بنزین", "مالیات", "بودجه", "بیمه", "بازنشسته", "قیمت",
    "بازار", "تجارت", "صادرات", "واردات", "انرژی", "نفت", "گاز",
    "معیشت", "گمرک", "سپرده", "اقساط", "درآمد", "افزایش نرخ",
)


