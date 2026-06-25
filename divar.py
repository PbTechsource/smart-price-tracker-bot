from playwright.async_api import async_playwright
import re


async def get_divar_price(url: str) -> dict:
    """
    دریافت قیمت از دیوار
    Returns: {"price": int, "available": bool, "title": str}
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        await page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })

        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)

        result = {"price": None, "available": False, "title": "نامشخص"}

        try:
            # عنوان آگهی
            title_el = await page.query_selector("h1.kt-page-title__title, h1[class*='title']")
            if title_el:
                result["title"] = (await title_el.inner_text()).strip()

            # قیمت
            price_el = await page.query_selector(
                "[class*='price'] strong, [class*='kt-unexpandable-row__value'], "
                "p.kt-unexpandable-row__value"
            )
            if price_el:
                raw = (await price_el.inner_text()).strip()

                # توافقی یا رایگان
                if any(w in raw for w in ["توافقی", "رایگان", "مجانی"]):
                    result["price"] = 0
                    result["available"] = True
                else:
                    digits = re.sub(r"[^\d]", "", raw)
                    if digits:
                        result["price"] = int(digits)
                        result["available"] = True

            # بررسی منقضی شدن آگهی
            expired = await page.query_selector("[class*='expired'], [class*='inactive']")
            if expired:
                result["available"] = False

        except Exception as e:
            print(f"[Divar] خطا در پارس: {e}")

        await browser.close()
        return result


def is_divar_url(url: str) -> bool:
    return "divar.ir" in url
