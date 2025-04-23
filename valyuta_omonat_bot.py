import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,  # Qo'shilgan import
)
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io

# Omonat hisoblash bosqichlari
SUMMA, FOIZ, OY, VALYUTA = range(4)

# MB'dan valyuta kurslarini olish
def get_exchange_rates():
    try:
        url = "https://nbu.uz/uz/exchange-rates/json/"
        response = requests.get(url)
        response.raise_for_status()  # Agar so'rov muvaffaqiyatsiz bo'lsa, xato
        data = response.json()

        rates = {}
        for item in data:
            code = item["code"]
            rate = float(item["cb_price"].replace(",", ""))
            rates[code] = rate
        return rates
    except requests.RequestException as e:
        print(f"API xatosi: {e}")
        return {}

# /kurs komandasi uchun funksiya
async def kurs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rates = get_exchange_rates()
    if not rates:
        await update.message.reply_text("❌ Valyuta kurslarini olishda xato yuz berdi.")
        return

    keyboard = [
        [
            InlineKeyboardButton("USD", callback_data="USD"),
            InlineKeyboardButton("EUR", callback_data="EUR"),
            InlineKeyboardButton("RUB", callback_data="RUB"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("💱 Valyutani tanlang:", reply_markup=reply_markup)

# Kursni tanlagan valyutaga ko‘ra ko‘rsatish
async def kurs_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    rates = get_exchange_rates()
    valyuta = query.data
    kurs = rates.get(valyuta, "Noma'lum")
    await query.answer()
    await query.edit_message_text(f"{valyuta} kursi: {kurs} so‘m")

# /omonat komandasi – boshlanish
async def omonat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("💰 Omonat summasini kiriting (so‘m):")
    return SUMMA

# Omonat summasini qabul qilish
async def summa_qabul(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data["summa"] = float(update.message.text)
        await update.message.reply_text("Yillik foiz stavkasini kiriting (masalan: 14):")
        return FOIZ
    except ValueError:
        await update.message.reply_text("Iltimos, to‘g‘ri summa kiriting (raqam):")
        return SUMMA

# Foiz stavkasini qabul qilish
async def foiz_qabul(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data["foiz"] = float(update.message.text)
        await update.message.reply_text("Muddatni kiriting (oylarda):")
        return OY
    except ValueError:
        await update.message.reply_text("Iltimos, to‘g‘ri foiz stavkasini kiriting (raqam):")
        return FOIZ

# Muddatni qabul qilish va hisoblash
async def oy_qabul(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        oy = int(update.message.text)
        summa = context.user_data["summa"]
        foiz = context.user_data["foiz"]

        # Hisoblash formulasi (oddiy foiz)
        yillik = foiz / 100
        jami = summa * (1 + yillik * oy / 12)

        # Natijani PDF formatida yaratish
        pdf_file = io.BytesIO()
        c = canvas.Canvas(pdf_file, pagesize=letter)
        c.drawString(100, 750, "📊 Omonat hisoboti:")
        c.drawString(100, 730, f"Summa: {summa:,.2f} so‘m")
        c.drawString(100, 710, f"Foiz stavkasi: {foiz}%")
        c.drawString(100, 690, f"Muddat: {oy} oy")
        c.drawString(100, 670, f"Yakuni: {round(jami, 2):,.2f} so‘m")
        c.save()

        pdf_file.seek(0)
        await update.message.reply_text("📊 Hisobot tayyor! Omonat hisoboti:")
        await update.message.reply_document(pdf_file, filename="Omonat_hisoboti.pdf")

        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("Iltimos, to‘g‘ri muddat kiriting (raqam):")
        return OY

# Bekor qilish
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bekor qilindi.")
    return ConversationHandler.END

# Asosiy ishga tushirish
if __name__ == "__main__":
    app = ApplicationBuilder().token("7992280278:AAHUVQmNfKc7s9Np-HstUiX6qTY44GXNJrQ").build()  # Tokenni o'zgartiring

    # Komandalar
    app.add_handler(CommandHandler("kurs", kurs))
    app.add_handler(CommandHandler("omonat", omonat))

    # Omonat funksiyasi (multi-step)
    omonat_handler = ConversationHandler(
        entry_points=[CommandHandler("omonat", omonat)],
        states={
            SUMMA: [MessageHandler(filters.TEXT & ~filters.COMMAND, summa_qabul)],
            FOIZ: [MessageHandler(filters.TEXT & ~filters.COMMAND, foiz_qabul)],
            OY: [MessageHandler(filters.TEXT & ~filters.COMMAND, oy_qabul)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(omonat_handler)

    # Valyuta kursini tanlash uchun callback
    app.add_handler(CallbackQueryHandler(kurs_callback))

    print("Bot ishga tushdi...")
    app.run_polling()
