import os, logging, asyncio
import pandas as pd
import ccxt
from smartmoneyconcepts import smc
from ta.momentum import StochasticOscillator
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler

logging.basicConfig(level=logging.INFO)

# جلب داتا من Binance
exchange = ccxt.binance({
    'enableRateLimit': True,
})

async def fetch_ohlc(symbol="XAU/USDT", timeframe="1h", limit=200):
    bars = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(bars, columns=["timestamp","open","high","low","close","volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    return df

def analyze(df):
    df2 = df.copy()
    fvg = smc.fvg(df2, join_consecutive=False)
    swings = smc.swing_highs_lows(df2)
    bos = smc.bos_choch(df2, swings)
    obs = smc.ob(df2, swings)
    st = StochasticOscillator(df2["high"], df2["low"], df2["close"], window=14, smooth_window=3)
    df2["stoch_k"] = st.stoch()
    df2["stoch_d"] = st.stoch_signal()
    return df2, fvg, obs, df2["stoch_k"].iloc[-1], df2["stoch_d"].iloc[-1], bos["BOS"].iloc[-1]

async def generate_signal(mode):
    df, fvg, obs, st_k, st_d, bos = await asyncio.get_event_loop().run_in_executor(None, analyze, await fetch_ohlc())
    last_fvg = fvg.iloc[-1]
    last_ob = obs.iloc[-1]
    trend = "شراء" if bos == 1 else "بيع"
    st_signal = ""
    if st_k > 80 and st_d > 80: st_signal = "تشبع شراء"
    elif st_k < 20 and st_d < 20: st_signal = "تشبع بيع"
    
    reason = f"FVG={last_fvg:.0f}, OrderBlock={last_ob:.0f}, Stochastic={st_signal}"
    # السكالب: توصية فورية
    if mode == "scalp":
        action = "ادخل شراء" if bos == 1 else "ادخل بيع"
        return (action, reason, "Stop Loss عند سعر قريب", "Take Profit: نسبه قصيرة")
    # السوينغ: توصية أطول
    else:
        sl = df["low"].iloc[-1] if bos==1 else df["high"].iloc[-1]
        tp = df["close"].iloc[-1] + (df["close"].iloc[-1] - sl)*2 if bos==1 else df["close"].iloc[-1] - (sl - df["close"].iloc[-1])*2
        return (trend, reason, sl, tp)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [[InlineKeyboardButton("🔸 سكالب", callback_data="scalp")],
          [InlineKeyboardButton("🔹 سوينغ", callback_data="swing")]]
    await update.message.reply_text("ابدأ تحليلك مع بوت S A (gold mafia)", reply_markup=InlineKeyboardMarkup(kb))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    mode = q.data
    await q.edit_message_text(f"📊 جاري تحليل السوق لوضع {mode}...")
    action, reason, sl, tp = await generate_signal(mode)
    text = f"📌 *{ 'سكالب' if mode=='scalp' else 'سُوينغ'} توصية:*\n" \
           f"{action}\n" \
           f"🔍 السبب: {reason}\n" \
           f"🛑 Stop Loss: {sl}\n" \
           f"🏁 Take Profit: {tp}"
    await q.message.reply_text(text, parse_mode="Markdown")

def main():
    token = os.getenv("BOT_TOKEN")
    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.run_polling()

if __name__ == "__main__":
    main()
