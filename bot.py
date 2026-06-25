import os
import re
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

from db.database import (
    init_db,
    add_product,
    get_user_products,
    get_product,
    save_price,
    get_price_history,
)
from scrapers.router import detect_source, fetch_price
from ml.analyzer import analyze_price

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ─── Conversation States ───────────────────────────────────────
WAIT_URL, WAIT_NAME = range(2)


# ══════════════════════════════════════════════════════════════
# /start
# ══════════════════════════════════════════════════════════════
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "👋 سلام! به ربات ردیاب قیمت خوش اومدی!\n\n"
        "🤖 این ربات بهت کمک می‌کنه قیمت محصولات رو از "
        "دیجی‌کالا و دیوار دنبال کنی و با تحلیل هوشمند بفهمی "
        "الان زمان خرید هست یا نه.\n\n"
        "📋 دستورات:\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "➕ /add\\_product — افزودن محصول جدید\n"
        "📦 /products — لیست محصولات من\n"
        "🔍 /track <id> — بررسی قیمت فعلی\n"
        "🧠 /ml <id> — تحلیل هوشمند ML\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "برای شروع /add\\_product رو بزن 🚀"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


# ══════════════════════════════════════════════════════════════
# /add_product (Conversation)
# ══════════════════════════════════════════════════════════════
async def add_product_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔗 لینک محصول از دیجی‌کالا یا دیوار رو برام بفرست:\n\n"
        "مثال:\n"
        "• https://www.digikala.com/product/...\n"
        "• https://divar.ir/v/...\n\n"
        "برای لغو /cancel بزن"
    )
    return WAIT_URL


async def received_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    source = detect_source(url)

    if not source:
        await update.message.reply_text(
            "❌ لینک معتبر نیست!\n"
            "فقط لینک‌های دیجی‌کالا و دیوار پشتیبانی می‌شن.\n"
            "دوباره امتحان کن یا /cancel بزن."
        )
        return WAIT_URL

    context.user_data["pending_url"] = url
    context.user_data["pending_source"] = source

    source_name = "دیجی‌کالا" if source == "digikala" else "دیوار"
    await update.message.reply_text(
        f"✅ لینک {source_name} دریافت شد!\n\n"
        "📝 حالا یه اسم دلخواه برای این محصول بنویس:\n"
        "(مثلاً: لپ‌تاپ ایسوس، آیفون ۱۵)"
    )
    return WAIT_NAME


async def received_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    url = context.user_data.get("pending_url")
    source = context.user_data.get("pending_source")
    user_id = update.effective_user.id

    product_id = add_product(user_id, name, url, source)

    await update.message.reply_text(
        f"🎉 محصول با موفقیت اضافه شد!\n\n"
        f"📌 نام: {name}\n"
        f"🆔 شناسه: `{product_id}`\n\n"
        f"برای بررسی قیمت: /track {product_id}\n"
        f"برای تحلیل ML: /ml {product_id}",
        parse_mode="Markdown"
    )
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ عملیات لغو شد.")
    return ConversationHandler.END


# ══════════════════════════════════════════════════════════════
# /products
# ══════════════════════════════════════════════════════════════
async def products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    items = get_user_products(user_id)

    if not items:
        await update.message.reply_text(
            "📭 هنوز محصولی اضافه نکردی!\n"
            "با /add\\_product شروع کن.",
            parse_mode="Markdown"
        )
        return

    source_emoji = {"digikala": "🔴", "divar": "🟢"}
    lines = ["📦 *محصولات من:*\n━━━━━━━━━━━━━━━━━━━━"]

    for item in items:
        emoji = source_emoji.get(item["source"], "⚪️")
        lines.append(
            f"{emoji} *{item['name']}*\n"
            f"   🆔 ID: `{item['id']}` | 🕐 {item['created_at'][:10]}\n"
            f"   🔍 /track {item['id']} | 🧠 /ml {item['id']}"
        )
        lines.append("━━━━━━━━━━━━━━━━━━━━")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


# ══════════════════════════════════════════════════════════════
# /track <product_id>
# ══════════════════════════════════════════════════════════════
async def track(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not context.args:
        await update.message.reply_text("⚠️ استفاده: `/track <id>`\nمثلاً: /track 1", parse_mode="Markdown")
        return

    try:
        product_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ شناسه باید عدد باشه.")
        return

    product = get_product(product_id, user_id)
    if not product:
        await update.message.reply_text("❌ محصول پیدا نشد یا مال تو نیست.")
        return

    msg = await update.message.reply_text(
        f"⏳ در حال بررسی قیمت *{product['name']}*...\n"
        "این کار چند ثانیه طول می‌کشه ⌛",
        parse_mode="Markdown"
    )

    try:
        data = await fetch_price(product["url"], product["source"])
    except Exception as e:
        logger.error(f"Scrape error: {e}")
        await msg.edit_text("❌ خطا در دریافت قیمت. ممکنه سایت موقتاً در دسترس نباشه.")
        return

    if data["price"] is None:
        await msg.edit_text(
            f"⚠️ قیمت *{product['name']}* پیدا نشد.\n"
            "ممکنه محصول ناموجود باشه یا لینک تغییر کرده باشه.",
            parse_mode="Markdown"
        )
        return

    save_price(product_id, data["price"], data["available"])

    status = "✅ موجود" if data["available"] else "❌ ناموجود"
    price_text = f"{data['price']:,}" if data["price"] > 0 else "توافقی"

    await msg.edit_text(
        f"📊 *{product['name']}*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 قیمت: *{price_text} تومان*\n"
        f"📦 وضعیت: {status}\n"
        f"🏷️ عنوان: {data.get('title', '—')}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🧠 برای تحلیل ML: /ml {product_id}",
        parse_mode="Markdown"
    )


# ══════════════════════════════════════════════════════════════
# /ml <product_id>
# ══════════════════════════════════════════════════════════════
async def ml(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not context.args:
        await update.message.reply_text("⚠️ استفاده: `/ml <id>`\nمثلاً: /ml 1", parse_mode="Markdown")
        return

    try:
        product_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ شناسه باید عدد باشه.")
        return

    product = get_product(product_id, user_id)
    if not product:
        await update.message.reply_text("❌ محصول پیدا نشد یا مال تو نیست.")
        return

    history = get_price_history(product_id)

    if not history:
        await update.message.reply_text(
            f"📭 هنوز هیچ قیمتی برای *{product['name']}* ثبت نشده.\n"
            f"اول /track {product_id} بزن تا قیمت ثبت بشه.",
            parse_mode="Markdown"
        )
        return

    analysis = analyze_price(history)
    stats = analysis["stats"]

    signal_emoji = {"buy": "🟢", "wait": "🔴", "neutral": "🟡"}.get(analysis["signal"], "⚪️")

    stats_text = ""
    if stats:
        stats_text = (
            f"\n📈 *آمار قیمت:*\n"
            f"• میانگین: {stats['mean']:,} تومان\n"
            f"• انحراف معیار: {stats['std']:,} تومان\n"
            f"• کمترین: {stats['min']:,} تومان\n"
            f"• بیشترین: {stats['max']:,} تومان\n"
            f"• روند اخیر: {stats['trend_pct']:+.1f}%\n"
            f"• تعداد داده: {stats['count']} نقطه\n"
        )

    await update.message.reply_text(
        f"🧠 *تحلیل ML — {product['name']}*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{signal_emoji} {analysis['reason']}\n"
        f"━━━━━━━━━━━━━━━━━━━━"
        f"{stats_text}",
        parse_mode="Markdown"
    )


# ══════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════
def main():
    token = os.environ.get("")
    if not token:
        raise ValueError("Environment variable  Not set!")

    init_db()

    app = ApplicationBuilder().token(token).build()

    # Conversation handler برای add_product
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("add_product", add_product_start)],
        states={
            WAIT_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_url)],
            WAIT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_name)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("products", products))
    app.add_handler(CommandHandler("track", track))
    app.add_handler(CommandHandler("ml", ml))

    logger.info("ربات شروع به کار کرد ✅")
    app.run_polling()


if __name__ == "__main__":
    main()
