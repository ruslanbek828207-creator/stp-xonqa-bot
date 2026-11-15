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

# 10-uchaska manzillari bazasi
UCHASKA_10_DATA = {
    "uch_1": {"name": "Ёрқин Юлдуз-2 берк кўчаси", "status": "Uzluksiz xizmat ko'rsatishda", "signal": "Normal (-19 dBm)"},
    "uch_2": {"name": "Олажа қишлоғи, Yorqin yulduz уй", "status": "Faol", "signal": "Yaxshi (-20 dBm)"},
    "uch_3": {"name": "Олажа қишлоғи, Афсонавий кўчаси", "status": "Faol", "signal": "Normal (-22 dBm)"},
    "uch_4": {"name": "Олажа қишлоғи, Ахли диёр кўчаси", "status": "Faol", "signal": "Yaxshi (-18 dBm)"},
    "uch_5": {"name": "Олажа қишлоғи, Барака кўчаси", "status": "Faol", "signal": "Normal (-21 dBm)"},
    "uch_6": {"name": "Олажа қишлоғи, Бахтли оила кўчаси", "status": "Faol", "signal": "Yaxshi (-19 dBm)"},
    "uch_7": {"name": "Олажа қишлоғи, Бўстонлиқ кўчаси", "status": "Faol", "signal": "Normal (-23 dBm)"},
    "uch_8": {"name": "Олажа қишлоғи, Бухоро кўчаси", "status": "Faol", "signal": "Yaxshi (-20 dBm)"},
    "uch_9": {"name": "Олажа қишлоғи, Буюк ипак йўли 3- йўлак кўчаси", "status": "Faol", "signal": "Normal (-22 dBm)"},
}

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
    }
}

# Elektramontyorlar bazasi
ELECTRICIANS_DATA = {
    "elect_1": {"name": "Шоназаров Достон Хайитбоевич", "phone": "+998995054885", "zone": "Xonqa tumani, Markaziy MFY", "task": "Optik tarmoqlarni tortish, svarka qilish va abonentlarni ulash."},
    "elect_2": {"name": "Отабоев Рамзиддин Рахматилло угли", "phone": "+998995603938", "zone": "Xonqa tumani, Paxtakor MFY", "task": "Beton stalbalarda ishlash, drop kabel tortish va routerlarni sozlash."},
    "elect_3": {"name": "Юсупов Бобур Сапарбой ўғли", "phone": "+998995601312", "zone": "Xonqa tumani, Tinchlik MFY", "task": "1x16 splitterlarda signalni tekshirish va nosozliklarni bartaraf etish."},
    "elect_4": {"name": "Каримов Илхом Машарипович", "phone": "+998995606399", "zone": "Xonqa tumani, Guliston MFY", "task": "Internet liniyalarini ta'mirlash va abonentlar murojaatlari bilan ishlash."},
    "elect_5": {"name": "Абдурахмонов Хушнуд Ниёзметович", "phone": "+998995603001", "zone": "Xonqa tumani, Navoiy MFY", "task": "Optik tolali kabellarni ulash va signal darajasini o'lchash."},
    "elect_6": {"name": "Жуманиёзов Жўшқин Шоназарович", "phone": "+998995608636", "zone": "Xonqa tumani, Bo'ston MFY", "task": "ZTE va TP-Link routerlarini sozlash, internet tarmoqlarini test qilish."},
    "elect_7": {"name": "Атажанов Рустам Комоладдинович", "phone": "+998992797072", "zone": "Xonqa tumani, Istiqlol MFY", "task": "Yangi abonentlarni tarmoqqa ulash va shartnoma masalalari."},
    "elect_8": {"name": "Каримов Заир Авезметович", "phone": "+998995601310", "zone": "Xonqa tumani, Oqoltin MFY", "task": "Stalbalarga chiqish, havo liniyalarini montaj qilish."},
    "elect_9": {"name": "Бабажанов Искандар Сапарбекович", "phone": "+998995603005", "zone": "Xonqa tumani, Qoratepa MFY", "task": "Magistral optik tarmoqlarga xizmat ko'rsatish."},
    "elect_10": {"name": "Каримов Дониёр Хаджибоевич", "phone": "+998995603171", "zone": "Xonqa tumani, Shixrezvan MFY", "task": "Abonentlar uyiga internet kabellarini tortish va ulash."},
    "elect_11": {"name": "Жуманиёзов Руслан Рустамович", "phone": "+998995603937", "zone": "Xonqa tumani (Boshqaruv va texnik nazorat)", "task": "Texnik yordam, tarmoq monitoringi, OSS portal va bot boshqaruvi."},
    "elect_12": {"name": "Саидов Хушнуд Матяқубович", "phone": "+998992797071", "zone": "Xonqa tumani, Hayotobod MFY", "task": "Optik svarka ishlari va ta'mirlash."},
    "elect_13": {"name": "Жаббаров Хамдам Рустамович", "phone": "+998995603936", "zone": "Xonqa tumani, Sarqipchoq MFY", "task": "Avariya holatlarini bartaraf etish va tushgan arizalar bilan ishlash."},
    "elect_14": {"name": "Хаитов Хаитбай Шоназарович", "phone": "+998995603934", "zone": "Xonqa tumani, Qipchoq MFY", "task": "Internet tarmoqlarini kengaytirish va yangi nuqtalarni ulash."},
    "elect_15": {"name": "Саидов Умарбек Шавкатович", "phone": "+998995603002", "zone": "Xonqa tumani, Zarkent MFY", "task": "Splitterlar va taqsimot qutilarini nazorat qilish."},
    "elect_16": {"name": "Эгамов Азизбек Озод угли", "phone": "+998977929525", "zone": "Xonqa tumani, Charmgar MFY", "task": "Abonent modellarini sozlash va texnik yordam ko'rsatish."},
    "elect_17": {"name": "Якубов Жасурбек Ахмеджонович", "phone": "+998995606787", "zone": "Xonqa tumani, Yangi hayot MFY", "task": "Optik kabel uzilishlarini tezkor bartaraf etish."},
    "elect_18": {"name": "Машарипов Али Валиевич", "phone": "+998995603931", "zone": "Xonqa tumani, Do'stlik MFY", "task": "Tarmoq qurilmalarini o'rnatish va sozlash."},
    "elect_19": {"name": "Ваисов Рустам Юсуфбоевич", "phone": "+998995603935", "zone": "Xonqa tumani, Mehnatobod MFY", "task": "Abonendlarga sifatli internet ulash va liniyalarni tekshirish."},
    "elect_20": {"name": "Юлдошов Кадамбой Атабоевич", "phone": "+998995603007", "zone": "Xonqa tumani, Olmazor MFY", "task": "Elektr va optik tarmoqlarda profilaktika ishlari."},
}

# Asosiy menyu tugmalari
keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="🌐 Internet tariflari"),
            KeyboardButton(text="⚡ Splitterlar va abonentlar")
        ],
        [
            KeyboardButton(text="🏢 10-uchaska obyektlari"),
            KeyboardButton(text="👷 Elektramontyorlar")
        ],
        [
            KeyboardButton(text="🛠 Xizmatlar va murojaat"),
            KeyboardButton(text="📞 Bog'lanish")
        ],
        [
            KeyboardButton(text="📊 OSS Portal", web_app=WebAppInfo(url="https://oss.uztelecom.uz/dashboard/")),
            KeyboardButton(text="🗺 Geowfm Xarita", web_app=WebAppInfo(url="https://geofm.uztelecom.uz/geoutr/equipments/list"))
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
    text = (
        "<b>UZTELECOM Home Internet tariflari (Hammasi birga):</b>\n\n"
        "🔥 <b>Hammasi birga 4</b>\n"
        "• Internet tezligi: 500 Mbit/s\n"
        "• IP-telefoniya abonent to'lovi: 25 000 so'm/oyiga\n"
        "• Trafik: Cheksiz\n"
        "💰 <b>Narxi: 500 000 so'm/oyiga</b>\n\n"
        "🔥 <b>Hammasi birga 3+</b>\n"
        "• Internet tezligi: 350 Mbit/s\n"
        "• IP-telefoniya abonent to'lovi: 25 000 so'm/oyiga\n"
        "• Trafik: Cheksiz\n"
        "💰 <b>Narxi: 350 000 so'm/oyiga</b>\n\n"
        "🔥 <b>Hammasi birga 3</b>\n"
        "• Internet tezligi: 250 Mbit/s\n"
        "• IP-telefoniya abonent to'lovi: 25 000 so'm/oyiga\n"
        "• Trafik: Cheksiz\n"
        "💰 <b>Narxi: 215 000 so'm/oyiga</b>\n\n"
        "🔥 <b>Hammasi birga 2+</b>\n"
        "• Internet tezligi: 150 Mbit/s\n"
        "• IP-telefoniya abonent to'lovi: 25 000 so'm/oyiga\n"
        "• Trafik: Cheksiz\n"
        "💰 <b>Narxi: 175 000 so'm/oyiga</b>\n\n"
        "📞 Ulanish uchun mas'ul: +998995603937"
    )
    await message.answer(text, parse_mode=ParseMode.HTML)

@dp.message(F.text == "⚡ Splitterlar va abonentlar")
async def splitters_menu(message: Message) -> None:
    inline_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔹 Splitter 1x2 №1 (Markaz)", callback_data="split_1x2_1")],
            [InlineKeyboardButton(text="🔸 Splitter 1x16 №1 (Xonqa)", callback_data="split_1x16_1")]
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

@dp.message(F.text == "🏢 10-uchaska obyektlari")
async def uchaska_menu(message: Message) -> None:
    buttons = []
    for key, val in UCHASKA_10_DATA.items():
        buttons.append([InlineKeyboardButton(text=f"📍 {val['name']}", callback_data=key)])
    inline_kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer("<b>10-uchaska hududlari va manzillari:</b>\nKerakli manzilni tanlang:", reply_markup=inline_kb)

@dp.callback_query(F.data.startswith("uch_"))
async def process_uchaska_callback(callback: CallbackQuery) -> None:
    uch_id = callback.data
    data = UCHASKA_10_DATA.get(uch_id)
    if data:
        text = (
            f"🏢 <b>Obyekt / Manzil:</b> {data['name']}\n"
            f"📌 <b>Holati:</b> {data['status']}\n"
            f"⚡ <b>Signal darajasi:</b> {data['signal']}"
        )
    else:
        text = "Ma'lumot topilmadi."
    await callback.message.answer(text, parse_mode=ParseMode.HTML)
    await callback.answer()

@dp.message(F.text == "👷 Elektramontyorlar")
async def electricians_handler(message: Message) -> None:
    buttons = []
    for key, val in ELECTRICIANS_DATA.items():
        buttons.append([InlineKeyboardButton(text=f"👷 {val['name']}", callback_data=key)])
    inline_kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer("Xonqa tumanidagi elektramontyorlar ro'yxati. Xodim haqida ma'lumot olish uchun uning ustiga bosing:", reply_markup=inline_kb)

@dp.callback_query(F.data.startswith("elect_"))
async def process_electrician_callback(callback: CallbackQuery) -> None:
    elect_id = callback.data
    data = ELECTRICIANS_DATA.get(elect_id)
    if data:
        text = (
            f"👷 <b>Elektramontyor:</b> {data['name']}\n"
            f"📞 <b>Telefon raqami:</b> {data['phone']}\n"
            f"📍 <b>Xizmat ko'rsatish zonasi:</b> {data['zone']}\n"
            f"🛠 <b>Vazifasi / Qiladigan ishi:</b> {data['task']}"
        )
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

async def handle_ping(request):
    return web.Response(text="Bot ishlayapti!")

async def web_server_runner():
    app = web.Application()
    app.router.add_get("/", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

async def main() -> None:
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    await web_server_runner()
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
