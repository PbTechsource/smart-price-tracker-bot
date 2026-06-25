from scrapers.digikala import get_digikala_price, is_digikala_url
from scrapers.divar import get_divar_price, is_divar_url


def detect_source(url: str) -> str | None:
    if is_digikala_url(url):
        return "digikala"
    if is_divar_url(url):
        return "divar"
    return None


async def fetch_price(url: str, source: str) -> dict:
    if source == "digikala":
        return await get_digikala_price(url)
    elif source == "divar":
        return await get_divar_price(url)
    return {"price": None, "available": False, "title": "نامشخص"}
