from playwright.sync_api import sync_playwright
import time
import json

def get_unexpandable_value(page, label: str):
    row = page.locator(
        "div.kt-base-row:has(p.kt-base-row__title:has-text('%s'))" % label
    )
    if row.count() == 0:
        return None
    try:
        value = row.nth(0).locator(".kt-unexpandable-row__value").inner_text()
        return value.strip()
    except Exception:
        return None

LIMIT = 10

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    list_page = browser.new_page()
    list_page.set_default_timeout(60000)

    # لیست ماشین‌های تهران
    list_page.goto("https://divar.ir/s/tehran/car")
    list_page.wait_for_selector('a[href^="/v/"]')
    time.sleep(5)

    cards = list_page.locator('a[href^="/v/"]')
    total = cards.count()
    print("Total cards on list page:", total)

    # جمع‌آوری لینک‌های یکتا
    links = []
    seen = set()
    for i in range(total):
        href = cards.nth(i).get_attribute("href")
        if not href:
            continue
        if href.startswith("/"):
            href = "https://divar.ir" + href
        if href not in seen:
            seen.add(href)
            links.append(href)
        if len(links) >= LIMIT:
            break

    print("Links to scrape:", links)

    data = []

    detail_page = browser.new_page()
    for idx, link in enumerate(links, start=1):
        print(f"[{idx}/{len(links)}] visiting:", link)
        detail_page.goto(link)
        time.sleep(4)

        try:
            title = detail_page.locator("h1").first.inner_text().strip()
        except Exception:
            title = ""

        # اینجا می‌تونی بعداً info مثل سال ساخت، کارکرد و قیمت رو اضافه کنی
        data.append({"title": title, "link": link})

    with open("divar_tehran_cars.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    print(f"{len(data)} ads saved with details.")
    browser.close()
