import statistics
from typing import Optional


def analyze_price(history: list) -> dict:
    """
    تحلیل هوشمند قیمت بر اساس تاریخچه
    
    Returns:
        signal: "buy" | "wait" | "neutral"
        reason: توضیح فارسی
        stats: آمار
    """
    prices = [h["price"] for h in history if h["price"] and h["price"] > 0]

    if not prices:
        return {
            "signal": "neutral",
            "reason": "اطلاعات کافی برای تحلیل وجود ندارد.",
            "stats": {}
        }

    current_price = prices[-1]
    stats = _calc_stats(prices)

    signal, reason = _make_decision(prices, current_price, stats)

    return {
        "signal": signal,
        "reason": reason,
        "stats": stats
    }


def _calc_stats(prices: list) -> dict:
    mean = statistics.mean(prices)
    std = statistics.stdev(prices) if len(prices) > 1 else 0
    min_p = min(prices)
    max_p = max(prices)
    current = prices[-1]

    # موقعیت قیمت فعلی نسبت به بازه
    price_range = max_p - min_p
    position = (current - min_p) / price_range if price_range > 0 else 0.5

    # روند اخیر (۳ نقطه آخر)
    recent = prices[-3:]
    if len(recent) >= 2:
        trend = (recent[-1] - recent[0]) / recent[0] * 100
    else:
        trend = 0.0

    return {
        "mean": int(mean),
        "std": int(std),
        "min": min_p,
        "max": max_p,
        "current": current,
        "position": round(position, 2),
        "trend_pct": round(trend, 1),
        "count": len(prices)
    }


def _make_decision(prices: list, current: int, stats: dict) -> tuple[str, str]:
    mean = stats["mean"]
    std = stats["std"]
    position = stats["position"]
    trend = stats["trend_pct"]
    count = stats["count"]

    reasons = []

    # ─── نیاز به داده بیشتر ───
    if count < 3:
        return "neutral", (
            f"⚪️ داده کافی نیست\n"
            f"فقط {count} نقطه قیمتی داریم. بیشتر track کن تا تحلیل دقیق‌تر بشه."
        )

    # ─── محاسبه سیگنال ───
    lower_band = mean - 0.5 * std
    upper_band = mean + 0.5 * std

    is_cheap = current <= lower_band
    is_expensive = current >= upper_band
    is_falling = trend < -3
    is_rising = trend > 3
    is_near_min = position < 0.2
    is_near_max = position > 0.8

    # تصمیم‌گیری ترکیبی
    buy_score = 0
    wait_score = 0

    if is_cheap:
        buy_score += 2
        reasons.append("قیمت زیر میانگین تاریخی است")
    if is_near_min:
        buy_score += 2
        reasons.append("قیمت نزدیک کمترین مقدار ثبت‌شده است")
    if is_falling:
        wait_score += 1
        reasons.append("روند قیمت نزولی است (شاید بیشتر کاهش یابد)")
    if is_rising:
        wait_score += 1
        reasons.append("روند قیمت صعودی است")
    if is_expensive:
        wait_score += 2
        reasons.append("قیمت بالاتر از میانگین تاریخی است")
    if is_near_max:
        wait_score += 2
        reasons.append("قیمت نزدیک بیشترین مقدار ثبت‌شده است")

    reason_text = " | ".join(reasons) if reasons else "قیمت در محدوده نرمال"

    if buy_score > wait_score and buy_score >= 2:
        return "buy", (
            f"🟢 زمان خرید مناسبه!\n"
            f"{reason_text}\n\n"
            f"قیمت فعلی {_fmt(current)} تومان در مقابل میانگین {_fmt(mean)} تومان"
        )
    elif wait_score > buy_score and wait_score >= 2:
        return "wait", (
            f"🔴 هنوز زمان خرید نیست\n"
            f"{reason_text}\n\n"
            f"قیمت فعلی {_fmt(current)} تومان، میانگین {_fmt(mean)} تومان"
        )
    else:
        return "neutral", (
            f"🟡 قیمت معقوله، نه ارزان نه گران\n"
            f"میانگین تاریخی: {_fmt(mean)} | فعلی: {_fmt(current)}\n"
            f"اگر نیاز داری بخری، الان بدم نیست."
        )


def _fmt(price: int) -> str:
    return f"{price:,}"
