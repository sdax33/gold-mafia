import os
import logging
import requests
import pandas as pd
from ta.momentum import StochasticOscillator
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
)
import asyncio

# إعدادات التسجيل
logging.basicConfig(level=logging.INFO)

# مفاتيح البيئة
BOT_TOKEN = os.environ["BOT_TOKEN"]
TD_API_KEY = os.environ["TD_API_KEY"]

# إعدادات السوق
SYMBOL = "XAU/USD"
INTERVAL = "1h"

# استدعاء بيانات السوق
def get_market_data():
    url = f"https://api.twelvedata.com/time_series?symbol={SYMBOL}&interval={INTERVAL}&apikey={TD_API_KEY}&outputsize=50"
    response = requests.get(url)
    data = response.json()

    if "values" not in data:
        raise Exception(data.get("message", "البيانات غير متوفرة"))

    df = pd.DataFrame(data["values"])
    
    # تحويل الأعمدة الرقمية فقط
    numeric_columns = ["open", "high", "low", "close", "volume"]
    df[numeric_columns] = df[numeric_columns].astype(float)

    return df[::-1]  # عكس الترتيب ليكون الأحدث في الآخر

# تحليل Stochastic Oscillator
def analyze_data(df):
    stoch = StochasticOscillator(
        close=df["close"], high=df["high"], low=df["low"],
        window=14, smooth_window=3
    )
    k = stoch.stoch()
    d = stoch.stoch_signal()
    last_k = k.iloc[-1]
    last_d = d.iloc[-1]

    if last_k > 80 and last_d > 80:
        return "📉 Overbought: احتمال نزول"
    elif last_k < 20 and last_d < 20:
        return "📈 Oversold: احتمال صعود"
    else:
        return "⏸ لا توجد إشارة واضحة"

# زر البدء
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("⚡️ سكالبينغ", callback_data="scalp")],
        [InlineKeyboardButton("📈 سوينغ", callback_data="swing")]
    ]
    await update.message.reply_text(
        "مرحبًا بك في بوت تحليل السوق!\nاختر نوع التحليل:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# عند الضغط على زر
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data in ["scalp", "swing"]:
        try:
            df = get_market_data()
            signal = analyze_data(df)
            await query.edit_message_text(text=f"📊 نتيجة تحليل {query.data}:\n\n{signal}")
        except Exception as e:
            await query.edit_message_text(
                text=f"⚠️ السوق يبدو في عطلة أو حدث خطأ.\n"
                     f"📆 يُتوقع أن يفتح يوم الإثنين صباحًا.\n\n"
                     f"🔍 التفاصيل: {str(e)}"
            )

# تشغيل البوت
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    await app.bot.delete_webhook(drop_pending_updates=True)  # منع التعارض
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
