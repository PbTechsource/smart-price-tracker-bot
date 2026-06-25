from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes , MessageHandler, filters
from ml import fetch_and_predict
import asyncio
from database import add_product, get_products, get_product_url, add_price, get_price_history


TOKEN = "8577416971:AAH7NJa7ZvqPzY28ji8bADUB5zNCih0BT1g"

# ------------- COMMANDS -------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        " سلام!\n"
        "من بات ردیاب قیمت هستم\n\n"
        "برای دیدن دستورات:\n"
    )


async def add_product_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["add_mode"] = True
    await update.message.reply_text(
        "نام و لینک محصول رو بفرست\n"
        "مثال:\n"
        "نام: گوشی A54\n"
        "https://example.com/product/123"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("add_mode"):
        return
    
    text = update.message.text.split("\n")

    if len(text) < 2:
        await update.message.reply_text("فرمت اشتباهه. دوباره تلاش کن.")
        return
    
    name = text[0].replace("نام:", "").strip()
    url = text[1].strip()

    add_product(name, url)
    context.user_data["add_mode"] = False
    await update.message.reply_text(f"محصول '{name}' با موفقیت اضافه شد!")

# ------------- LIST PRODUCTS -------------
async def products_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    products = get_products()
    if not products:
        await update.message.reply_text("هیچ محصولی ثبت نشده.")
        return
    
    msg = "لیست محصولات:\n"
    for prod in products:
        msg += f"ID: {prod[0]} - نام: {prod[1]}\n"
    
    await update.message.reply_text(msg)

# ---------- ML CMD ----------
async def ml_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("id محصول رو بده")
        return

    product_id = int(context.args[0])
    url = get_product_url(product_id)
    if not url:
        await update.message.reply_text("محصول پیدا نشد")
        return

    await update.message.reply_text("در حال تحلیل قیمت واقعی...")

    history = get_price_history(product_id)
    result_text = await asyncio.to_thread(fetch_and_predict, url, history)

    if "❌" not in result_text:
        add_price(product_id, history[-1])

    await update.message.reply_text(result_text)

async def track_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("id محصول رو بده")
        return

    product_id = int(context.args[0])
    url = get_product_url(product_id)

    if not url:
        await update.message.reply_text("محصول پیدا نشد")
        return

    await update.message.reply_text("در حال گرفتن قیمت...")

    history = get_price_history(product_id)

    result_text = await asyncio.to_thread(fetch_and_predict, url, history)

    if "❌" not in result_text:
        add_price(product_id, history[-1])

    await update.message.reply_text(result_text)

# ---------- MAIN ----------
def main():
    app = (
    ApplicationBuilder()
    .token(TOKEN)
    .job_queue(None)
    .build()
)

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add_product", add_product_cmd))
    app.add_handler(CommandHandler("products", products_cmd))
    app.add_handler(CommandHandler("track", track_cmd))
    app.add_handler(CommandHandler("ml", ml_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
