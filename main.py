import os
import logging
import requests
import pandas as pd
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
)
from ta.momentum import StochasticOscillator

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ["BOT_TOKEN"]
TD_API_KEY = os.environ["TD_API_KEY"]
SYMBOL = "XAU/USD"

def get_market_data(interval: str):
    url = f"https://api.twelvedata.com/time_series?symbol={SYMBOL}&interval={interval}&apikey={TD_API_KEY}&outputsize=50"
    response = requests.get(url)
    data = response.json()

    if "values" not in data:
        raise ValueError("📛 لا توجد بيانات.")

    df = pd.DataFrame(data["values"])
    for col in ["open", "high", "low", "close"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna().iloc[::-1].reset_index(drop=True)
    return df

def analyze_data(df, mode="scalp"):
    result = []
    close, high, low = df["close"], df["high"], df["low"]

    stoch = StochasticOscillator(close=close, high=high, low=low, window=14, smooth_window=3)
    k = stoch.stoch()
    d = stoch.stoch_signal()
    last_k, last_d = k.iloc[-1], d.iloc[-1]

    is_buy = False
    is_sell = False
    signals = []

    # Stochastic
    if last_k < 20 and last_d < 20:
        result.append("📈 Stochastic: Oversold - احتمال صعود")
        is_buy = True
        signals.append("stochastic")
    elif last_k > 80 and last_d > 80:
        result.append("📉 Stochastic: Overbought - احتمال هبوط")
        is_sell = True
        signals.append("stochastic")
    else:
        result.append("⏸ Stochastic: لا توجد إشارة واضحة")

    # Support/Resistance
    support = low.rolling(window=10).min().iloc[-1]
    resistance = high.rolling(window=10).max().iloc[-1]
    current_price = close.iloc[-1]

    if current_price <= support * 1.01:
        result.append("🟢 قريب من الدعم")
        is_buy = True
        signals.append("support_resistance")
    elif current_price >= resistance * 0.99:
        result.append("🔴 قريب من المقاومة")
        is_sell = True
        signals.append("support_resistance")

    # Order Block
    if (low.iloc[-2] > high.iloc[-3]) and (df["open"].iloc[-1] > df["close"].iloc[-1]):
        result.append("🟤 Order Block بيعي")
        is_sell = True
        signals.append("order_block")
    elif (high.iloc[-2] < low.iloc[-3]) and (df["open"].iloc[-1] < df["close"].iloc[-1]):
        result.append("🟢 Order Block شرائي")
        is_buy = True
        signals.append("order_block")

    # FVG
    if abs(high.iloc[-2] - low.iloc[-1]) > (high.iloc[-1] - low.iloc[-1]) * 1.5:
        result.append("🟨 FVG موجود - احتمال ارتداد")
        signals.append("fvg")

    # SMC
    if high.iloc[-1] > high.iloc[-2] > high.iloc[-3]:
        result.append("📉 SMC: كسر قمة")
        is_sell = True
        signals.append("smc")
    elif low.iloc[-1] < low.iloc[-2] < low.iloc[-3]:
        result.append("📈 SMC: كسر قاع")
        is_buy = True
        signals.append("smc")

    # Dynamic confidence calculation
    weights = {
        "stochastic": 1,
        "support_resistance": 1,
        "order_block": 1,
        "fvg": 0.5,
        "smc": 0.5
    }
    max_score = sum(weights.values())
    active_score = sum(weights.get(sig, 0) for sig in signals)
    confidence = int((active_score / max_score) * 100)

    # Always show a trade suggestion
    direction = "🔼 شراء" if is_buy else "🔽 بيع" if is_sell else "❓ غير واضح"
    result.append(f"\n📊 القرار النهائي: {direction}")
    result.append(f"📉 نسبة النجاح المتوقعة: {confidence}%")

    sl = current_price * (0.995 if is_buy else 1.005)
    tp = current_price * (1.01 if is_buy else 0.99)
    result.append(f"🎯 نقطة الدخول: {current_price:.2f}")
    result.append(f"🛑 وقف الخسارة: {sl:.2f}")
    result.append(f"🎯 الهدف (TP): {tp:.2f}")

    result.append("💡 سكالبينغ (صفقة قصيرة)" if mode == "scalp" else "📈 سوينغ (صفقة طويلة)")
    return "\n".join(result)

# Telegram handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔁 تحليل اسكالبينغ", callback_data="scalp")],
        [InlineKeyboardButton("📈 تحليل سوينغ", callback_data="swing")]
    ]
    await update.message.reply_text("👋 اختر نوع التحليل:", reply_markup=InlineKeyboardMarkup(keyboard))

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
            text=f"⚠️ حدث خطأ أثناء التحليل.\n\n🔍 التفاصيل: {str(e)}"
        )

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.run_polling()

if __name__ == "__main__":
    main()
