import re
from playwright.sync_api import sync_playwright
import numpy as np
from sklearn.linear_model import LinearRegression


def fetch_price(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, timeout=15000)

        html = page.content()
        browser.close()

    match = re.search(r'(\d{1,3}(?:[.,]\d{3})+)', html)
    if not match:
        return None

    price = match.group(1).replace(",", "").replace(".", "")
    return int(price)


def fetch_and_predict(url, history):
    price = fetch_price(url)

    if price is None:
        return "قیمت پیدا نشد"

    history.append(price)

    if len(history) < 3:
        return f"""
محصول
قیمت امروز : {price:,}
داده کافی برای پیش‌بینی وجود ندارد
"""

    X = np.arange(len(history)).reshape(-1, 1)
    y = np.array(history)

    model = LinearRegression()
    model.fit(X, y)

    predicted_7 = int(model.predict([[len(history) + 7]])[0])

    suggestion = "صبر کنید" if predicted_7 < price else "الان زمان خریده"

    return f"""
محصول
قیمت امروز : {price:,}
پیش‌بینی 7 روز آینده : {predicted_7:,}
پیشنهاد : {suggestion}
"""
