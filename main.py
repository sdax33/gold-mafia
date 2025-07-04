import os
import logging
import requests
import pandas as pd
from ta.momentum import StochasticOscillator
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler

# ✅ إعدادات
logging.basicConfig(level=logging.INFO)
API_KEY = os.getenv("TD_API_KEY")  # Twelve Data API Key
SYMBOL = "XAU/USD"
INTERVAL = "1h"

# ✅ جلب بيانات السوق من Twelve Data
def fetch_market_data():
    url = f"https://api.twelvedata.com/time_series?symbol={SYMBOL}&interval={INTERVAL}&outputsize=100&apikey={API_KEY}"
    response = requests.get(url).json()
    if "values" not in response:
        raise Exception(f"خطأ في جلب البيانات: {response}")

    df = pd.DataFrame(response["values"])
    df.rename(columns={
        "datetime": "timestamp",
        "open": "open",
        "high": "high",
        "low": "low",
        "close": "close",
        "volume": "volume"
    }, inplace=True)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp")
    df[["open", "high", "low", "close", "volume"]] = df[["open", "high", "low", "close", "volume"]].astype(float)
    return df

# ✅ كشف FVG (فجوات القيمة العادلة)
def detect_fvg(df):
    for i in range(2, len(df)):
        prev_high = df["high"].iloc[i - 2]
        curr_low = df["low"].iloc[i]
        if prev_high < curr_low:
            return f"📈 FVG صاعد عند {df['timestamp'].iloc[i]}"
        prev_low = df["low"].iloc[i - 2]
        curr_high = df["high"].iloc[i]
        if prev_low > curr_high:
            return f"📉 FVG هابط عند {df['timestamp'].iloc[i]}"
    return "❌ لا توجد FVG حالياً"

# ✅ كشف Order Block
def detect_order_block(df):
    bearish_candles = df[df["close"] < df["open"]]
    if bearish_candles.empty:
        return "❌ لا يوجد Order Block"
    last_ob = bearish_candles.iloc[-1]
    return f"🧱 OB هابط عند {last_ob['timestamp']} (Open={last_ob['open']:.2f}, Close={last_ob['close']:.2f})"

# ✅ تحليل كامل للسوق
def analyze_market(df):
    # Stochastic
    stoch = StochasticOscillator(df["high"], df["low"], df["close"], window=14, smooth_window=3)
    df["stoch_k"] = stoch.stoch()
    df["stoch_d"] = stoch.stoch_signal()
    st_k = df["stoch_k"].iloc[-1]
    st_d = df["stoch_d"].iloc[-1]

    # إشارات Stochastic
    if st_k > 80 and st_d > 80:
        signal = "✅ توصية: ادخل بيع (تشبع شراء)"
    elif st_k < 20 and st_d < 20:
        signal = "✅ توصية: ادخل شراء (تشبع بيع)"
    else:
        signal = "⏳ توصية: انتظر (لا توجد إشارة واضحة)"

    # FVG و OB
    fvg = detect_fvg(df)
    ob = detect_order_block(df)

    # النص النهائي
    final = f"{signal}\n\n📊 Stoch K: {st_k:.2f}\n📊 Stoch D: {st_d:.2f}\n\n{fvg}\n{ob}"
    return final

# ✅ أوامر Telegram
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔸 سكالب", callback_data="scalp")],
        [InlineKeyboardButton("🔹 سوينغ", callback_data="swing")]
    ]
    await update.message.reply_text("ابدأ تحليلك مع بوت S A (gold mafia)", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text("🔍 جاري تحليل السوق الحقيقي...")

    try:
        df = fetch_market_data()
        result = analyze_market(df)
        await q.message.reply_text(result)
    except Exception as e:
        await q.message.reply_text(f"❌ حصل خطأ أثناء التحليل:\n{str(e)}")

# ✅ تشغيل البوت
def main():
    token = os.getenv("BOT_TOKEN")
    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.run_polling()

if __name__ == "__main__":
    main()
