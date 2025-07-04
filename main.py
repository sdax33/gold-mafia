import os
import logging
import requests
import pandas as pd
from ta.momentum import StochasticOscillator
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
)

# إعدادات التسجيل
logging.basicConfig(level=logging.INFO)

# متغيرات البيئة
BOT_TOKEN = os.environ["BOT_TOKEN"]
TD_API_KEY = os.environ["TD_API_KEY"]

# إعدادات السوق
SYMBOL = "XAU/USD"
INTERVAL = "1h"

# استدعاء بيانات من Twelve Data
def get_market_data():
    url = f"https://api.twelvedata.com/time_series?symbol={SYMBOL}&interval={INTERVAL}&apikey={TD_API_KEY}&outputsize=50"
    response = requests.get(url)
    data = response.json()
    df = pd.DataFrame(data["values"])
    df = df.astype(float)
    return df[::-1]

# تحليل بسيط باستخدام Stochastic Oscillator
def analyze_data(df):
    stoch = StochasticOscillator(close=df["close"], high=df["high"], low=df["low"], window=14, smooth_window=3)
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

# زر البوت
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("📊 تحليل السوق", callback_data="analyze")]]
    await update.message.reply_text("مرحبًا! اضغط الزر لبدء التحليل:", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "analyze":
        try:
            df = get_market_data()
            signal = analyze_data(df)
            await query.edit_message_text(text=f"نتيجة التحليل:\n{signal}")
        except Exception as e:
            await query.edit_message_text(text=f"⚠️ حصل خطأ: {str(e)}")

# Main
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.run_polling()

if __name__ == "__main__":
    main()
