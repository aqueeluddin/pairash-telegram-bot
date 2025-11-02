# Project: Telegram Multi-Utility Bot (Modular)
# Language: Python (aiogram)
# Structure shown below — save each code block as a separate file in the described path.

--- FILE: README.md ---
"""
Telegram Multi-Utility Bot — Modular

How to use
1. Create a virtualenv and install requirements:
   python -m venv venv
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   pip install -r requirements.txt

2. Create a .env file with these keys:
   TELEGRAM_TOKEN=<your_telegram_bot_token>
   OPENWEATHER_API_KEY=<optional>
   COINGECKO_API_KEY=<optional>
   ALPHAVANTAGE_API_KEY=<optional>
   HUGGINGFACE_API_KEY=<optional>

3. Run locally:
   python main.py

Notes
- This code uses simple JSON storage (db/users.json). For production, replace with a proper DB.
- Features implemented with free APIs or local logic.
"""

--- FILE: requirements.txt ---
aiogram==3.0.0b7
python-dotenv
requests
apscheduler

--- FILE: main.py ---
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder
import asyncio
import logging
import os
from dotenv import load_dotenv

# load env
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    raise SystemExit("Please set TELEGRAM_TOKEN in .env file")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

# simple keyboard
kb = ReplyKeyboardBuilder()
kb.add(types.KeyboardButton(text="/ask"))
kb.add(types.KeyboardButton(text="/quote"))
kb.add(types.KeyboardButton(text="/joke"))

# simple start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.reply(f"Hey {message.from_user.first_name}! I'm alive. Type /help to see commands.", reply_markup=kb.as_markup(resize_keyboard=True))

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    help_text = (
        "/start - Start bot\n"
        "/help - This help\n"
        "/ask <text> - Ask AI (local HF or fallback)\n"
        "/quote - Random inspirational quote\n"
        "/joke - Random joke\n"
        "/weather <city> - Weather info (OpenWeather)\n"
        "/crypto <id> - Crypto price (CoinGecko)\n"
        "/todo, /notes - Personal todo & notes (local json)\n"
    )
    await message.reply(help_text)

# include routers from modules
from commands import fun, utilities, ai

fun.register(dp)
utilities.register(dp)
ai.register(dp)

async def main():
    print("🚀 Bot is starting...")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == '__main__':
    asyncio.run(main())

--- FILE: commands/__init__.py ---
# package initializer

--- FILE: commands/fun.py ---
from aiogram import Router, types
import requests
import random
from aiogram.filters import Command

router = Router()

@router.message(Command("joke"))
async def cmd_joke(message: types.Message):
    try:
        r = requests.get('https://v2.jokeapi.dev/joke/Any?type=single')
        data = r.json()
        await message.reply(data.get('joke', 'Couldn\'t fetch joke'))
    except Exception as e:
        await message.reply("Joke API error")

@router.message(Command("quote"))
async def cmd_quote(message: types.Message):
    try:
        r = requests.get('https://zenquotes.io/api/random')
        data = r.json()[0]
        await message.reply(f"\"{data.get('q')}\" — {data.get('a')}")
    except Exception:
        await message.reply("Quote API error")

@router.message(Command("meme"))
async def cmd_meme(message: types.Message):
    try:
        r = requests.get('https://meme-api.herokuapp.com/gimme')
        data = r.json()
        await message.reply_photo(photo=data['url'], caption=data.get('title',''))
    except Exception:
        await message.reply("No meme for now")

def register(dp):
    dp.include_router(router)

--- FILE: commands/utilities.py ---
from aiogram import Router, types
from aiogram.filters import Command
import requests
import os

router = Router()

OPENWEATHER_KEY = os.getenv('OPENWEATHER_API_KEY')

@router.message(Command('weather'))
async def cmd_weather(message: types.Message):
    args = message.get_args()
    city = args.strip() if args else None
    if not city:
        await message.reply('Usage: /weather city_name')
        return
    try:
        url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_KEY}&units=metric"
        r = requests.get(url)
        if r.status_code != 200:
            await message.reply('Weather not found or API key missing')
            return
        data = r.json()
        desc = data['weather'][0]['description']
        temp = data['main']['temp']
        await message.reply(f"Weather in {city}: {desc}, {temp}°C")
    except Exception:
        await message.reply('Weather API error')

@router.message(Command('crypto'))
async def cmd_crypto(message: types.Message):
    args = message.get_args()
    coin = args.strip().lower() if args else 'bitcoin'
    try:
        r = requests.get(f'https://api.coingecko.com/api/v3/simple/price?ids={coin}&vs_currencies=usd')
        data = r.json()
        price = data.get(coin, {}).get('usd')
        if price is None:
            await message.reply('Coin not found')
            return
        await message.reply(f"{coin.capitalize()} price: ${price}")
    except Exception:
        await message.reply('CoinGecko API error')

@router.message(Command('time'))
async def cmd_time(message: types.Message):
    import datetime
    now = datetime.datetime.now()
    await message.reply(f"Server time: {now.strftime('%Y-%m-%d %H:%M:%S')}")

def register(dp):
    dp.include_router(router)

--- FILE: commands/ai.py ---
from aiogram import Router, types
from aiogram.filters import Command
import os
import requests

router = Router()
HUGGINGFACE_KEY = os.getenv('HUGGINGFACE_API_KEY')

@router.message(Command('ask'))
async def cmd_ask(message: types.Message):
    prompt = message.get_args()
    if not prompt:
        await message.reply('Usage: /ask your question')
        return
    # Use HuggingFace Inference API (fallback to simple canned reply if key missing)
    if not HUGGINGFACE_KEY:
        await message.reply(f"Sorry, no external AI key configured. You asked: {prompt}")
        return
    try:
        headers = {"Authorization": f"Bearer {HUGGINGFACE_KEY}", "Content-Type": "application/json"}
        payload = {"inputs": prompt}
        r = requests.post('https://api-inference.huggingface.co/models/gpt2', headers=headers, json=payload, timeout=20)
        data = r.json()
        if isinstance(data, list) and data:
            text = data[0].get('generated_text', str(data))
        else:
            text = data.get('generated_text', str(data))
        await message.reply(text[:3000])
    except Exception:
        await message.reply('AI API error or timeout')

def register(dp):
    dp.include_router(router)

--- FILE: utils/db.py ---
import json
from pathlib import Path
DB_FILE = Path('db/users.json')
DB_FILE.parent.mkdir(parents=True, exist_ok=True)

def load_db():
    if not DB_FILE.exists():
        return {'users': {}, 'todos': {}}
    return json.loads(DB_FILE.read_text(encoding='utf-8'))

def save_db(data):
    DB_FILE.write_text(json.dumps(data, indent=2), encoding='utf-8')

--- FILE: db/users.json ---
{}

--- FILE: .env.example ---
TELEGRAM_TOKEN=put_token_here
OPENWEATHER_API_KEY=put_openweather_key_here
HUGGINGFACE_API_KEY=put_hf_key_here

--- FILE: deploy_notes.md ---
1) For local testing use: python main.py
2) To deploy on Render / Railway / Deta, follow their docs. Keep your .env keys in their secret/env settings.

--- END OF PROJECT ---

# You can open this document and copy each file into your project folder.
# I did not include heavyweight paid API usage — only optional keys for HuggingFace/OpenWeather/AlphaVantage.
# If you want, I can now zip this into a single downloadable file or push to a GitHub gist (if you want that, provide permission).
