from playwright.sync_api import sync_playwright
import time
import json
import re

LIMIT = 15  # چند تا آگهی از صفحه لیست

def fa_to_en_digits(s: str) -> str:
    mapping = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")
    return s.translate(mapping)

def extract_int(text, default=None):
    if not text:
        return default
    text = fa_to_en_digits(text)
    text = re.sub(r"[^\d]", "", text)
    return int(text) if text.isdigit() else default

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

def parse_price(text, default=None):
    if not text:
        return default
    t = fa_to_en_digits(text)
    total = 0
    m_b = re.search(r"([\d,]+)\s*میلیارد", t)
    if m_b:
        n = int(re.sub(r"[^\d]", "", m_b.group(1)))
        total += n * 1_000_000_000
    m_m = re.search(r"([\d,]+)\s*میلیون", t)
    if m_m:
        n = int(re.sub(r"[^\d]", "", m_m.group(1)))
        total += n * 1_000_000
    if total > 0:
        return total
    m = re.search(r"([\d,]+)", t)
    if m:
        return int(re.sub(r"[^\d]", "", m.group(1)))
    return default

def parse_detail_page(page):
    # ---------- Car-specific fields ----------
    year = mileage = fuel = None

    year_text = get_unexpandable_value(page, "سال ساخت")
    year = extract_int(year_text)

    mileage_text = get_unexpandable_value(page, "کارکرد")
    mileage = extract_int(mileage_text)

    fuel = get_unexpandable_value(page, "سوخت")

    total_price_text = get_unexpandable_value(page, "قیمت")
    total_price = parse_price(total_price_text)

    return {
        "year": year,
        "mileage": mileage,
        "fuel": fuel,
        "total_price": total_price,
    }

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    list_page = browser.new_page()
    list_page.set_default_timeout(60000)

    # Tehran car listings
    list_page.goto("https://divar.ir/s/tehran/car")
    time.sleep(5)
    list_page.wait_for_selector('a[href^="/v/"]')

    cards = list_page.locator('a[href^="/v/"]')
    total = cards.count()
    print("Total cards on list page:", total)

    # Unique links
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

    print("Unique listing links to scrape:", len(links))

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

        info = parse_detail_page(detail_page)
        data.append({"title": title, "link": link, **info})

    with open("divar_tehran_cars.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    print(f"{len(data)} ads saved with details.")
    browser.close()
