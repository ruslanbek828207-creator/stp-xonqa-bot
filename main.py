import asyncio
import logging
import os
import sys
from aiohttp import web
from aiogram import Bot, Dispatcher, html, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
    WebAppInfo
)

TOKEN = "9125362206:AAGSRlOCTy_vJRU7t5VGJyLZ3ArmdfAWtZs"
dp = Dispatcher()

# Splitterlar bazasi
SPLITTERS_DATA = {
    "split_1x2_1": {
        "name": "Splitter 1x2 №1 (Markaz)",
        "info": "Signal darajasi: Normal (-18 dBm)\n\n"
                "<b>Ulangan abonentlar:</b>\n"
                "1. Ismoilov Anvar - 15-uy (Tel: +998901234567)\n"
                "2. Matyakubov Baxtiyor - 18-uy (Tel: +998919876543)"
    },
    "split_1x16_1": {
        "name": "Splitter 1x16 №1 (Xonqa ko'cha)",
        "info": "Signal darajasi: Yaxshi (-21 dBm)\n\n"
                "<b>Ulangan abonentlar:</b>\n"
                "1. Jumaniyozov Jasur - 4-uy (Tel: +998931112233)\n"
                "2. Raximov Farhod - 12-uy (Tel: +998974445566)\n"
                "3. Bobojonov Rustam - 25-uy (Tel: +998997778899)"
    },
    "split_1x16_2": {
        "name": "Splitter 1x16 №2 (Paxtakor)",
        "info": "Signal darajasi: O'rtacha (-24 dBm)\n\n"
                "<b>Ulangan abonentlar:</b>\n"
                "1. Sobirov Sherzod - 7-uy (Tel: +998905554433)\n"
                "2. Yusupov Dilshod - 19-uy (Tel: +998912223344)"
    }
}

# Elektramontyorlar ma'lumotlari
ELECTRICIANS_DATA = {
    "elect_1": {"name": "Шоназаров Достон Хайитбоевич", "phone": "+998995054885"},
    "elect_2": {"name": "Отабоев Рамзиддин Рахматилло угли", "phone": "+998995603938"},
    "elect_3": {"name": "Юсупов Бобур Сапарбой ўғли", "phone": "+998995601312"},
    "elect_4": {"name": "Каримов Илхом Машарипович", "phone": "+998995606399"},
    "elect_5": {"name": "Абдурахмонов Хушнуд Ниёзметович", "phone": "+998995603001"},
    "elect_6": {"name": "Жуманиёзов Жўшқин Шоназарович", "phone": "+998995608636"},
    "elect_7": {"name": "Атажанов Рустам Комоладдинович", "phone": "+998992797072"},
    "elect_8": {"name": "Каримов Заир Авезметович", "phone": "+998995601310"},
    "elect_9": {"name": "Бабажанов Искандар Сапарбекович", "phone": "+998995603005"},
    "elect_10": {"name": "Каримов Дониёр Хаджибоевич", "phone": "+998995603171"},
    "elect_11": {"name": "Жуманиёзов Руслан Рустамович", "phone": "+998995603937"},
    "elect_12": {"name": "Саидов Хушнуд Матяқубович", "phone": "+998992797071"},
    "elect_13": {"name": "Жаббаров Хамдам Рустамович", "phone": "+998995603936"},
    "elect_14": {"name": "Хаитов Хаитбай Шоназарович", "phone": "+998995603934"},
    "elect_15": {"name": "Саидов Умарбек Шавкатович", "phone": "+998995603002"},
    "elect_16": {"name": "Эгамов Азизбек Озод угли", "phone": "+998977929525"},
    "elect_17": {"name": "Якубов Жасурбек Ахмеджонович", "phone": "+998995606787"},
    "elect_18": {"name": "Машарипов Али Валиевич", "phone": "+998995603931"},
    "elect_19": {"name": "Ваисов Рустам Юсуфбоевич", "phone": "+998995603935"},
    "elect_20": {"name": "Юлдошов Кадамбой Атабоевич", "phone": "+998995603007"},
}

# Asosiy menyu tugmalari
keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="🌐 Internet tariflari"),
            KeyboardButton(text="⚡ Splitterlar va abonentlar")
        ],
        [
            KeyboardButton(text="👷 Elektramontyorlar"),
            KeyboardButton(text="🛠 Xizmatlar va murojaat")
        ],
        [
            KeyboardButton(text="📊 OSS Portal", web_app=WebAppInfo(url="https://oss.uztelecom.uz/dashboard/")),
            KeyboardButton(text="🗺 Geowfm Xarita", web_app=WebAppInfo(url="https://geofm.uztelecom.uz/geoutr/equipments/list"))
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

@dp.message(F.text == "🌐 Internet tariflari")
async def internet_handler(message: Message) -> None:
    await message.answer(
        "<b>UZTELECOM Home Internet tariflari (Xonqa):</b>\n\n"
        "• 100 Mb/s - Yuqori tezlikdagi optik internet\n"
        "• 200 Mb/s - Qulay paket\n"
        "• 1 Gbit/s - Super tezlik!\n\n"
        "Ulanish uchun operator bilan bog'laning: +998995603937"
    )

@dp.message(F.text == "⚡ Splitterlar va abonentlar")
async def splitters_menu(message: Message) -> None:
    inline_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔹 Splitter 1x2 №1 (Markaz)", callback_data="split_1x2_1")],
            [InlineKeyboardButton(text="🔸 Splitter 1x16 №1 (Xonqa)", callback_data="split_1x16_1")],
            [InlineKeyboardButton(text="🔸 Splitter 1x16 №2 (Paxtakor)", callback_data="split_1x16_2")]
        ]
    )
    await message.answer("Tekshirmoqchi bo'lgan splitter yoki muftani tanlang:", reply_markup=inline_kb)

@dp.callback_query(F.data.startswith("split_"))
async def process_splitter_callback(callback: CallbackQuery) -> None:
    splitter_id = callback.data
    data = SPLITTERS_DATA.get(splitter_id)
    
    if data:
        text = f"📍 <b>{data['name']}</b>\n\n{data['info']}"
    else:
        text = "Ma'lumot topilmadi."
        
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML)
    await callback.answer()

@dp.message(F.text == "👷 Elektramontyorlar")
async def electricians_handler(message: Message) -> None:
    buttons = []
    for key, val in ELECTRICIANS_DATA.items():
        buttons.append([InlineKeyboardButton(text=f"👷 {val['name']}", callback_data=key)])
    
    inline_kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer("Xonqa tumanidagi elektramontyorlar ro'yxati. Kerakli xodimni tanlang:", reply_markup=inline_kb)

@dp.callback_query(F.data.startswith("elect_"))
async def process_electrician_callback(callback: CallbackQuery) -> None:
    elect_id = callback.data
    data = ELECTRICIANS_DATA.get(elect_id)
    
    if data:
        text = f"👷 <b>Elektramontyor:</b> {data['name']}\n📞 <b>Telefon raqami:</b> {data['phone']}"
    else:
        text = "Ma'lumot topilmadi."
        
    await callback.message.answer(text, parse_mode=ParseMode.HTML)
    await callback.answer()

@dp.message(F.text == "🛠 Xizmatlar va murojaat")
async def services_handler(message: Message) -> None:
    await message.answer(
        "<b>Texnik xizmatlar va o'rnatish:</b>\n"
        "• Optik fiber svarka\n"
        "• Beton stalbalarda ishlash va drop kabel tortish\n"
        "• 1x2 va 1x16 splitterlarda signalni tekshirish\n"
        "• ZTE ZXHN F6600P va TP-Link routerlarini sozlash\n\n"
        "Murojaat uchun tel: +998995603937"
    )

@dp.message(F.text == "📞 Bog'lanish")
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
