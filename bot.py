import requests
import pandas as pd
import time
from telegram import Bot
from datetime import datetime, timezone

# === CONFIGURATION ===
ALPHA_VANTAGE_API_KEY = 'PGE9CDZQ450JLVZI'  # Put your API key here
TELEGRAM_TOKEN = '7671201734:AAFtIqONreZHpEplcfZSC06g6h8L3BjOLuE'             # Put your Telegram Bot token here
TELEGRAM_CHAT_ID = '6740908804'             # Put your Telegram Chat ID here
SYMBOL = 'EURUSD'  # Example trading pair

# Moving Averages settings
FAST_MA = 5
SLOW_MA = 20
RSI_PERIOD = 14
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

# Setup Telegram bot
bot = Bot(token=TELEGRAM_TOKEN)

# === FUNCTIONS ===

def get_forex_data(symbol):
    url = f"https://www.alphavantage.co/query?function=FX_DAILY&from_symbol={symbol[:3]}&to_symbol={symbol[3:]}&apikey={ALPHA_VANTAGE_API_KEY}"
    response = requests.get(url)
    data = response.json()

    if "Time Series FX (Daily)" not in data:
        print("Error fetching data:", data)
        return None

    time_series = data['Time Series FX (Daily)']
    df = pd.DataFrame.from_dict(time_series, orient='index').astype(float)
    df.rename(columns={
        '1. open': 'open',
        '2. high': 'high',
        '3. low': 'low',
        '4. close': 'close'
    }, inplace=True)
    df.index = pd.to_datetime(df.index)
    df = df.sort_index()
    return df

def calculate_indicators(df):
    # Moving Averages
    df['MA_fast'] = df['close'].rolling(window=FAST_MA).mean()
    df['MA_slow'] = df['close'].rolling(window=SLOW_MA).mean()

    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=RSI_PERIOD).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=RSI_PERIOD).mean()
    RS = gain / loss
    df['RSI'] = 100 - (100 / (1 + RS))

    # MACD
    exp1 = df['close'].ewm(span=MACD_FAST, adjust=False).mean()
    exp2 = df['close'].ewm(span=MACD_SLOW, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['MACD_signal'] = df['MACD'].ewm(span=MACD_SIGNAL, adjust=False).mean()

    return df

def check_trade_signal(df):
    last = df.iloc[-1]
    
    now = datetime.now(timezone.utc)
    if now.weekday() >= 5:  # Saturday(5) or Sunday(6)
        return None

    # Strategy rules
    if (last['MA_fast'] > last['MA_slow']) and (last['RSI'] < 70) and (last['MACD'] > last['MACD_signal']):
        return "BUY"
    elif (last['MA_fast'] < last['MA_slow']) and (last['RSI'] > 30) and (last['MACD'] < last['MACD_signal']):
        return "SELL"
    else:
        return None

def send_alert(message):
    bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)

# === MAIN LOOP ===

while True:
    try:
        df = get_forex_data(SYMBOL)
        if df is not None:
            df = calculate_indicators(df)
            signal = check_trade_signal(df)

            if signal:
                current_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
                send_alert(f"{signal} signal for {SYMBOL} at {current_time} UTC")
                print(f"{current_time}: Sent {signal} signal!")

    except Exception as e:
        print("Error:", e)

    # Wait 24 hours
    time.sleep(86400)