from playwright.async_api import async_playwright
import re


async def get_digikala_price(url: str) -> dict:
    """
    دریافت قیمت و وضعیت موجودی از دیجی‌کالا
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
            # عنوان محصول
            title_el = await page.query_selector("h1.js-product-page-title, h1[class*='product-title']")
            if title_el:
                result["title"] = (await title_el.inner_text()).strip()

            # قیمت (تومان)
            price_el = await page.query_selector(
                "[class*='price-box__price'], [data-testid='price-no-discount'], "
                "[class*='final-price'], span.price"
            )
            if price_el:
                raw = (await price_el.inner_text()).strip()
                digits = re.sub(r"[^\d]", "", raw)
                if digits:
                    result["price"] = int(digits)
                    result["available"] = True

            # بررسی ناموجود بودن
            unavailable = await page.query_selector("[class*='unavailable'], [class*='out-of-stock']")
            if unavailable:
                result["available"] = False

        except Exception as e:
            print(f"[Digikala] خطا در پارس: {e}")

        await browser.close()
        return result


def is_digikala_url(url: str) -> bool:
    return "digikala.com" in url
