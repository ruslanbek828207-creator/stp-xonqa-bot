import asyncio
import logging
import os
import sys
from aiohttp import web
from aiogram import Bot, Dispatcher, html
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    WebAppInfo
)

TOKEN = "9125362206:AAFzP3W9w9cfHSqa0ymoZpW0mpKP6eISpj8"
dp = Dispatcher()

# Asosiy menyu tugmalari (OSS Portal va Geowfm Telegram ichida ochiladi)
keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="🌐 Internet tariflari"),
            KeyboardButton(text="📊 OSS Portal", web_app=WebAppInfo(url="https://oss.uztelecom.uz/dashboard/"))
        ],
        [
            KeyboardButton(text="🗺 Geowfm Xarita", web_app=WebAppInfo(url="https://geofm.uztelecom.uz/geoutr/equipments/list")),
            KeyboardButton(text="🛠 Xizmatlar va murojaat")
        ],
        [
            KeyboardButton(text="📞 Bog'lanish")
        ]
    ],
    resize_keyboard=True
)

@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    user_name = html.quote(message.from_user.first_name)
    await message.answer(
        f"Assalomu alaykum, {user_name}!\n"
        f"<b>@STP_Xonqa_bot</b> xizmatingizga tayyor. Kerakli bo'limni tanlang:",
        reply_markup=keyboard
    )

@dp.message(lambda message: message.text == "🌐 Internet tariflari")
async def internet_handler(message: Message) -> None:
    await message.answer(
        "<b>UZTELECOM Home Internet tariflari (Xonqa):</b>\n\n"
        "• 100 Mb/s - Yuqori tezlikdagi optik internet\n"
        "• 200 Mb/s - Qulay paket\n"
        "• 1 Gbit/s - Super tezlik!\n\n"
        "Ulanish uchun operator bilan bog'laning: +998995603937"
    )

@dp.message(lambda message: message.text == "🛠 Xizmatlar va murojaat")
async def services_handler(message: Message) -> None:
    await message.answer(
        "<b>Texnik xizmatlar va o'rnatish:</b>\n"
        "• Optik fiber svarka\n"
        "• Beton stalbalarda ishlash va drop kabel tortish\n"
        "• 1x2 va 1x16 splitterlarda signalni tekshirish\n"
        "• ZTE ZXHN F6600P va TP-Link routerlarini sozlash\n\n"
        "Murojaat uchun tel: +998995603937"
    )

@dp.message(lambda message: message.text == "📞 Bog'lanish")
async def contact_handler(message: Message) -> None:
    await message.answer(
        "📞 <b>Aloqa ma'lumotlari:</b>\n"
        "• Mas'ul: Elektramontyor\n"
        "• Telefon: +998995603937\n"
        "• Hudud: Xonqa tumani, Xorazm"
    )

@dp.message()
async def echo_handler(message: Message) -> None:
    await message.answer("Tushunarsiz buyruq. Iltimos, menyudagi tugmalardan foydalaning.")

# Render.com va UptimeRobot uchun kichik veb-server
async def handle_ping(request):
    return web.Response(text="Bot ishlayapti!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

async def main() -> None:
    await start_web_server()
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
