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

# جلب بيانات السوق
def get_market_data(interval: str):
    url = f"https://api.twelvedata.com/time_series?symbol={SYMBOL}&interval={interval}&apikey={TD_API_KEY}&outputsize=50"
    response = requests.get(url)
    data = response.json()

    if "values" not in data:
        raise ValueError("📛 لا توجد بيانات. السوق ممكن يكون في عطلة.")

    df = pd.DataFrame(data["values"])
    # تحويل الأعمدة الرقمية فقط
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna().iloc[::-1].reset_index(drop=True)
    return df

# التحليل الفني - نفس الطريقة لكل من السكالب والسوينغ
def analyze_data(df, mode="scalp"):
    stoch = StochasticOscillator(close=df["close"], high=df["high"], low=df["low"], window=14, smooth_window=3)
    k = stoch.stoch()
    d = stoch.stoch_signal()
    last_k = k.iloc[-1]
    last_d = d.iloc[-1]

    trend = ""
    if last_k > 80 and last_d > 80:
        trend = "📉 Overbought: احتمال نزول"
    elif last_k < 20 and last_d < 20:
        trend = "📈 Oversold: احتمال صعود"
    else:
        trend = "⏸ لا توجد إشارة واضحة"

    # توصية بناءً على نوع الصفقة
    if mode == "scalp":
        recommendation = "💡 هذه إشارة قصيرة المدى (سكالبينغ)"
    else:
        recommendation = "📊 هذه إشارة طويلة المدى (سوينغ)"

    return f"{trend}\n{recommendation}"

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔁 تحليل اسكالبينغ", callback_data="scalp")],
        [InlineKeyboardButton("📈 تحليل سوينغ", callback_data="swing")]
    ]
    await update.message.reply_text("👋 اختر نوع التحليل:", reply_markup=InlineKeyboardMarkup(keyboard))

# عند الضغط على زر
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    mode = query.data
    interval = "15min" if mode == "scalp" else "1h"

    try:
        df = get_market_data(interval)
        signal = analyze_data(df, mode=mode)
        await query.edit_message_text(text=f"🔍 نوع التحليل: {mode.upper()}\n\n{signal}")
    except Exception as e:
        await query.edit_message_text(
            text=f"⚠️ السوق يبدو في عطلة أو حدث خطأ.\n📆 يُتوقع أن يفتح يوم الإثنين صباحًا.\n\n🔍 التفاصيل: {str(e)}"
        )

# Main
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.run_polling()

if __name__ == "__main__":
    main()
