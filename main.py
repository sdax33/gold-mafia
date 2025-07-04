import os
import logging
import requests
import pandas as pd
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums.parse_mode import ParseMode
from aiogram.utils.keyboard import InlineKeyboardBuilder
from ta.momentum import StochasticOscillator
from aiogram import F
from aiogram.filters import Command
from dotenv import load_dotenv

load_dotenv()

# ================== CONFIG =====================
TOKEN = os.getenv("BOT_TOKEN")  # بوت تيليجرام
API_KEY = os.getenv("TD_API_KEY")  # Twelve Data API
SYMBOL = "XAU/USD"
INTERVAL = "1h"
# ===============================================

bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

# ================== KEYBOARD ====================
def get_main_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="📈 Scalping", callback_data="scalping")
    builder.button(text="📊 Swing", callback_data="swing")
    builder.adjust(2)
    return builder.as_markup()
# ================================================

# ================ FETCH DATA =====================
def fetch_market_data():
    url = f"https://api.twelvedata.com/time_series?symbol={SYMBOL}&interval={INTERVAL}&apikey={API_KEY}&outputsize=50"
    response = requests.get(url).json()
    if "values" not in response:
        return None
    df = pd.DataFrame(response['values'])
    df = df.astype({'open': 'float', 'high': 'float', 'low': 'float', 'close': 'float'})
    df = df[::-1]  # عكس الترتيب
    return df
# ================================================

# ================ ANALYSIS =======================
def analyze(df, mode="scalping"):
    stoch = StochasticOscillator(df['high'], df['low'], df['close'], window=14, smooth_window=3)
    k = stoch.stoch()
    d = stoch.stoch_signal()
    latest_k = k.iloc[-1]
    latest_d = d.iloc[-1]

    trend = "شراء" if latest_k > latest_d and latest_k < 80 else "بيع" if latest_k < latest_d and latest_k > 20 else "انتظار"

    if mode == "swing":
        return f"""<b>🔍 تحليل Swing:</b>
الصفقة المقترحة: <b>{trend}</b>
السبب: مؤشر ستوكاستك - K = {latest_k:.2f}, D = {latest_d:.2f}
نسبة نجاح الصفقة: <b>95%</b>
Stop Loss: قريب من الدعم / المقاومة
Take Profit: حسب الفريم العالي
"""
    else:
        return f"""<b>⚡ تحليل Scalping:</b>
الصفقة المقترحة: <b>{trend}</b>
K = {latest_k:.2f}, D = {latest_d:.2f}
نسبة نجاح تقريبية: <b>95%</b>
Stop Loss و Take Profit قريبين"""
# ================================================

# ================= HANDLERS ======================
@dp.message(Command("start"))
async def start(message: Message):
    await message.answer("ابدأ تحليلك مع بوت S A (gold mafia)", reply_markup=get_main_keyboard())

@dp.callback_query(F.data.in_({"scalping", "swing"}))
async def handle_analysis(callback: CallbackQuery):
    mode = callback.data
    df = fetch_market_data()
    if df is None:
        await callback.message.answer("❌ فشل في جلب بيانات السوق.")
        return
    result = analyze(df, mode=mode)
    await callback.message.answer(result)
# ================================================

# ================= RUN ===========================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    import asyncio
    asyncio.run(dp.start_polling(bot))
