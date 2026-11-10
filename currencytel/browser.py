"""Small Selenium lifecycle wrapper; one browser per pipeline run."""
import logging

LOG=logging.getLogger(__name__)

def create_browser(page_timeout=13):
    from selenium import webdriver
    options=webdriver.ChromeOptions()
    options.page_load_strategy='eager'
    for arg in ('--headless=new','--no-sandbox','--disable-dev-shm-usage','--disable-gpu','--window-size=1440,1000',
                '--blink-settings=imagesEnabled=false','--disable-background-networking',
                '--lang=en-US'):
        options.add_argument(arg)
    options.add_argument('--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36')
    browser=webdriver.Chrome(options=options)
    browser.set_page_load_timeout(page_timeout)
    return browser
