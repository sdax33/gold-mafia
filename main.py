import os
import logging
import requests
import pandas as pd
from ta.momentum import StochasticOscillator
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
)

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ["BOT_TOKEN"]
TD_API_KEY = os.environ["TD_API_KEY"]

SYMBOL = "XAU/USD"

# جلب البيانات من TwelveData حسب الفاصل الزمني
def get_market_data(interval: str):
    url = f"https://api.twelvedata.com/time_series?symbol={SYMBOL}&interval={interval}&apikey={TD_API_KEY}&outputsize=50"
    response = requests.get(url)
    data = response.json()
    if "values" not in data:
        raise ValueError("📛 لا توجد بيانات. السوق ممكن يكون في عطلة.")
    
    df = pd.DataFrame(data["values"])
    df = df.astype(float)
    return df[::-1]

# التحليل باستخدام Stochastic
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

# رسالة البدء مع أزرار التحليل
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔁 تحليل اسكالبينغ", callback_data="scalp")],
        [InlineKeyboardButton("📈 تحليل سوينغ", callback_data="swing")]
    ]
    await update.message.reply_text("اختار نوع التحليل:", reply_markup=InlineKeyboardMarkup(keyboard))

# التعامل مع الأزرار
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    interval = "15min" if query.data == "scalp" else "1h"

    try:
        df = get_market_data(interval)
        signal = analyze_data(df)
        await query.edit_message_text(text=f"🔍 نوع التحليل: {query.data.upper()}\n📊 نتيجة:\n{signal}")
    except Exception as e:
        await query.edit_message_text(
            text=f"⚠️ السوق يبدو في عطلة أو حدث خطأ.\n📆 يُتوقع أن يفتح يوم الإثنين صباحًا.\n\n🔍 التفاصيل: {str(e)}"
        )

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.run_polling()

if __name__ == "__main__":
    main()
