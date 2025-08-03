import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
import requests
import ta
import pandas as pd

API_KEY = "cf26d86b345344cdad7a749724c072c8"
BOT_TOKEN = "8261487004:AAFEGgSK5QaiIJR8MOHFZmGA02ID4rZdv9g"
OWNER_ID = 746541964

logging.basicConfig(level=logging.INFO)

currency_pairs = [
    "EUR/USD", "USD/JPY", "GBP/USD", "USD/CHF", "AUD/USD",
    "USD/CAD", "NZD/USD", "EUR/GBP", "EUR/JPY", "GBP/JPY"
]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("⛔ Доступ заборонено.")
        return

    keyboard = [[InlineKeyboardButton(pair, callback_data=pair)] for pair in currency_pairs]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Вибери валютну пару для аналізу:", reply_markup=reply_markup)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    symbol = query.data.replace("/", "")

    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=1min&apikey={API_KEY}&outputsize=100"
    r = requests.get(url).json()

    if "values" not in r:
        await query.edit_message_text("Дані недоступні. Спробуй пізніше.")
        return

    df = pd.DataFrame(r["values"]).iloc[::-1]
    df = df.astype({"open": "float", "high": "float", "low": "float", "close": "float"})

    df["rsi"] = ta.momentum.RSIIndicator(df["close"]).rsi()
    df["ema"] = ta.trend.EMAIndicator(df["close"], window=10).ema_indicator()
    df["macd"] = ta.trend.MACD(df["close"]).macd()
    bb = ta.volatility.BollingerBands(df["close"])
    df["bb_upper"] = bb.bollinger_hband()
    df["bb_lower"] = bb.bollinger_lband()
    df["sma"] = ta.trend.SMAIndicator(df["close"]).sma_indicator()

    last = df.iloc[-1]

    signal = ""
    if (
        last["rsi"] < 30
        and last["close"] < last["bb_lower"]
        and last["close"] > last["ema"]
        and last["macd"] > 0
    ):
        signal = "📈 СИГНАЛ ВГОРУ"
    elif (
        last["rsi"] > 70
        and last["close"] > last["bb_upper"]
        and last["close"] < last["ema"]
        and last["macd"] < 0
    ):
        signal = "📉 СИГНАЛ ВНИЗ"
    else:
        signal = "❌ Немає чіткого сигналу"

    keyboard = [[InlineKeyboardButton("🔄 Новий аналіз", callback_data="restart")]]
    await query.edit_message_text(f"Результат для {query.data}:\n\n{signal}", reply_markup=InlineKeyboardMarkup(keyboard))

async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button, pattern="^(?!restart).+"))
    app.add_handler(CallbackQueryHandler(restart, pattern="^restart$"))
    app.run_polling()
