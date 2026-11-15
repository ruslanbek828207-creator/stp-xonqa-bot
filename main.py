import asyncio
import logging
import os
import sys
from aiohttp import web
from aiogram import Bot, Dispatcher, html, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
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

# Foydalanuvchilar ro'yxatini xotirada saqlash uchun to'plam (Set)
active_users = set()

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
        ],
        [
            KeyboardButton(text="📱 MSMS Portal", web_app=WebAppInfo(url="https://msms.uztelecom.uz/"))
        ]
    ],
    resize_keyboard=True
)

@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    user = message.from_user
    user_info = f"👤 {user.full_name} (ID: <code>{user.id}</code>)"
    active_users.add(user_info)
    
    user_name = html.quote(user.first_name)
    await message.answer(
        f"Assalomu alaykum, {user_name}!\n"
        f"<b>@STP_Xonqa_bot</b> xizmatingizga tayyor. Kerakli bo'limni tanlang:",
        reply_markup=keyboard
    )

# Kimlar ulanganni ko'rish uchun maxfiy buyruq: /stats
@dp.message(Command("stats"))
async def stats_handler(message: Message) -> None:
    if not active_users:
        await message.answer("Hozircha botga ulangan foydalanuvchilar yo'q.")
        return
    
    users_list = "\n".join(active_users)
    await message.answer(
        f"📊 <b>Botga ulangan foydalanuvchilar (Jami: {len(active_users)} ta):</b>\n\n{users_list}",
        parse_mode=ParseMode.HTML
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
