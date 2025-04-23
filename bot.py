import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io

# Omonat hisoblash bosqichlari
SUMMA, FOIZ, OY, VALYUTA = range(4)

# MB'dan valyuta kurslarini olish
def get_exchange_rates():
    url = "https://nbu.uz/uz/exchange-rates/json/"
    response = requests.get(url)
    data = response.json()

    rates = {}
    for item in data:
        code = item['code']
        rate = float(item['cb_price'].replace(',', ''))
        rates[code] = rate
    return rates

# /kurs komandasi uchun funksiya
async def kurs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rates = get_exchange_rates()
    keyboard = [
        [InlineKeyboardButton("USD", callback_data="USD"),
         InlineKeyboardButton("EUR", callback_data="EUR"),
         InlineKeyboardButton("RUB", callback_data="RUB")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("💱 Valyutani tanlang:", reply_markup=reply_markup)

# Kursni tanlagan valyutaga ko‘ra ko‘rsatish
async def kurs_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    rates = get_exchange_rates()
    valyuta = query.data
    kurs = rates.get(valyuta, "Noma’lum")
    await query.answer()
    await query.edit_message_text(f"{valyuta} kursi: {kurs} so‘m")

# /omonat komandasi – boshlanish
async def omonat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("💰 Omonat summasini kiriting (so‘m):")
    return SUMMA

async def summa_qabul(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['summa'] = float(update.message.text)
    await update.message.reply_text("Yillik foiz stavkasini kiriting (masalan: 14):")
    return FOIZ

async def foiz_qabul(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['foiz'] = float(update.message.text)
    await update.message.reply_text("Muddatni kiriting (oylarda):")
    return OY

async def oy_qabul(update: Update, context: ContextTypes.DEFAULT_TYPE):
    oy = int(update.message.text)
    summa = context.user_data['summa']
    foiz = context.user_data['foiz']

    # Hisoblash formulasi (oddiy foiz)
    yillik = foiz / 100
    jami = summa * (1 + yillik * oy / 12)

    # Natijani PDF formatida yaratish
    pdf_file = io.BytesIO()
    c = canvas.Canvas(pdf_file, pagesize=letter)
    c.drawString(100, 750, f"📊 Omonat hisoboti:")
    c.drawString(100, 730, f"Summa: {summa} so‘m")
    c.drawString(100, 710, f"Foiz stavkasi: {foiz}%")
    c.drawString(100, 690, f"Muddat: {oy} oy")
    c.drawString(100, 670, f"Yakuni: {round(jami, 2):,} so‘m")
    c.save()

    pdf_file.seek(0)
    await update.message.reply_text(f"📊 Hisobot tayyor! Omonat hisoboti:")
    await update.message.reply_document(pdf_file, filename="Omonat_hisoboti.pdf")

    return ConversationHandler.END

# Bekor qilish
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bekor qilindi.")
    return ConversationHandler.END

# Asosiy ishga tushirish
app = ApplicationBuilder().token("YOUR_BOT_TOKEN_HERE").build()

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
