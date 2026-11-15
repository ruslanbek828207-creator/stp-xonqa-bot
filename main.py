import asyncio
import logging
import os
import sys
import pandas as pd
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

TOKEN = "9125362206:AAF4zONlkd5e81kfoZthNBTkwQ8TRa5-UQY"
dp = Dispatcher()

# Admin Telegram ID raqami va parol
ADMIN_ID = 51975910
SECRET_PASSWORD = "3939"

# Tasdiqlangan (parolni kiritgan) foydalanuvchilar bazasi
authorized_users = set()

# Excel fayldan Xonqa (Ханкинский УТ) splitterlarini yuklab olish
EXCEL_FILE = "ХОРЕЗМСКИЙ ФИЛИАЛ Splitter 01.02.2024 5 (1).xlsx"
splitters_list = []

try:
    if os.path.exists(EXCEL_FILE):
        xls = pd.ExcelFile(EXCEL_FILE)
        for sheet in xls.sheet_names:
            temp_df = pd.read_excel(EXCEL_FILE, sheet_name=sheet)
            xonqa_df = temp_df[temp_df['uzel'].astype(str).str.contains('Ханкинский', case=False, na=False)]
            for _, row in xonqa_df.iterrows():
                splitters_list.append({
                    "splitter": str(row.get('splitter', '')),
                    "model": str(row.get('model', '')),
                    "fict_sn": str(row.get('fict s/n', '')),
                    "real_sn": str(row.get('real s/n', ''))
                })
        print(f"✅ Exceldan {len(splitters_list)} ta Xonqa splitterlari yuklandi.")
except Exception as e:
    print(f"❌ Excel faylni o'qishda xatolik: {e}")

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
            KeyboardButton(text="⚡ Splitter qidirish")
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
            KeyboardButton(text="🗺 GeoWFM Xarita", web_app=WebAppInfo(url="https://geowfm.uztelecom.uz/geowfm/#/map/employee/search"))
        ],
        [
            KeyboardButton(text="📱 MSMS Portal", web_app=WebAppInfo(url="https://msms.uztelecom.uz/"))
        ]
    ],
    resize_keyboard=True
)

# Foydalanuvchilar qidiruv holatini saqlash uchun
search_state = set()

@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    if message.from_user.id == ADMIN_ID or message.from_user.id in authorized_users:
        user_name = html.quote(message.from_user.first_name)
        await message.answer(
            f"Assalomu alaykum, {user_name}!\n"
            f"<b>@STP_Xonqa_bot</b> xizmatingizga tayyor. Kerakli bo'limni tanlang:",
            reply_markup=keyboard
        )
    else:
        await message.answer("🔐 Assalomu alaykum! Botdan foydalanish uchun maxfiy parolni kiriting:")

@dp.message(Command("stats"))
async def stats_handler(message: Message) -> None:
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer(f"📊 Parolni kiritib ulangan xodimlar: {len(authorized_users)} ta\n📦 Bazadagi Xonqa splitterlari: {len(splitters_list)} ta")

@dp.message()
async def text_handler(message: Message) -> None:
    user_id = message.from_user.id
    text = message.text.strip()

    if user_id == ADMIN_ID or user_id in authorized_users:
        if user_id in search_state:
            # Splitter qidirish jarayoni
            search_state.remove(user_id)
            query = text.lower()
            found = [s for s in splitters_list if query in s['splitter'].lower() or query in s['real_sn'].lower() or query in s['fict_sn'].lower()]
            
            if not found:
                await message.answer("❌ Bunday splitter topilmadi. Qaytadan urinib ko'rish uchun '⚡ Splitter qidirish' tugmasini bosing.")
            else:
                response = f"🔍 <b>Qidiruv natijalari ({len(found)} ta):</b>\n\n"
                for item in found[:10]: # Ko'pi bilan 10 tasini ko'rsatish
                    response += (
                        f"📍 <b>Splitter:</b> {item['splitter']}\n"
                        f"⚙️ <b>Model:</b> {item['model']}\n"
                        f"📋 <b>Fict S/N:</b> {item['fict_sn']}\n"
                        f"🔢 <b>Real S/N:</b> {item['real_sn']}\n"
                        f"-----------------------------------\n"
                    )
                if len(found) > 10:
                    response += "\n<i>Natijalar ko'p, faqat dastlabki 10 tasi ko'rsatildi. Aniqroq yozing.</i>"
                await message.answer(response, parse_mode=ParseMode.HTML)
            return

        if text == "🌐 Internet tariflari":
            await message.answer(
                "<b>UZTELECOM Home Internet tariflari (Hammasi birga):</b>\n\n"
                "🔥 <b>Hammasi birga 4</b> (500 Mbit/s) - 500 000 so'm/oy\n"
                "🔥 <b>Hammasi birga 3+</b> (350 Mbit/s) - 350 000 so'm/oy\n"
                "🔥 <b>Hammasi birga 3</b> (250 Mbit/s) - 215 000 so'm/oy\n"
                "🔥 <b>Hammasi birga 2+</b> (150 Mbit/s) - 175 000 so'm/oy\n\n"
                "📞 Mas'ul: +998995603937",
                parse_mode=ParseMode.HTML
            )
        elif text == "⚡ Splitter qidirish":
            search_state.add(user_id)
            await message.answer("🔍 Qidirmoqchi bo'lgan splitter raqamini yoki nomini kiriting (masalan: <code>1/1/2</code> yoki <code>3/6/3</code>):", parse_mode=ParseMode.HTML)
        elif text == "🏢 10-uchaska obyektlari":
            buttons = [[InlineKeyboardButton(text=f"📍 {val['name']}", callback_data=key)] for key, val in UCHASKA_10_DATA.items()]
            await message.answer("<b>10-uchaska hududlari va manzillari:</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
        elif text == "👷 Elektramontyorlar":
            buttons = [[InlineKeyboardButton(text=f"👷 {val['name']}", callback_data=key)] for key, val in ELECTRICIANS_DATA.items()]
            await message.answer("Xonqa tumanidagi elektramontyorlar ro'yxati:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
        elif text == "🛠 Xizmatlar va murojaat":
            await message.answer("<b>Texnik xizmatlar va o'rnatish:</b>\n• Optik fiber svarka\n• Beton stalbalarda ishlash\nMurojaat: +998995603937")
        elif text == "📞 Bog'lanish":
            await message.answer("📞 <b>Aloqa:</b> +998995603937 (Xonqa tumani)")
        else:
            await message.answer("Tushunarsiz buyruq. Menyudagi tugmalardan foydalaning.")
    else:
        if text == SECRET_PASSWORD:
            authorized_users.add(user_id)
            await message.answer("✅ Parol to'g'ri! Xush kelibsiz. Quyidagi menyudan foydalanishingiz mumkin:", reply_markup=keyboard)
        else:
            await message.answer("❌ Noto'g'ri parol! Iltimos, to'g'ri parolni kiriting:")

@dp.callback_query()
async def callback_handler(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    if user_id != ADMIN_ID and user_id not in authorized_users:
        await callback.answer("Ruxsat yo'q!", show_alert=True)
        return

    data_id = callback.data
    if data_id.startswith("uch_"):
        data = UCHASKA_10_DATA.get(data_id)
        text = f"🏢 <b>{data['name']}</b>\n📌 Holati: {data['status']}\n⚡ Signal: {data['signal']}" if data else "Topilmadi."
        await callback.message.answer(text, parse_mode=ParseMode.HTML)
    elif data_id.startswith("elect_"):
        data = ELECTRICIANS_DATA.get(data_id)
        text = f"👷 <b>{data['name']}</b>\n📞 Tel: {data['phone']}\n📍 Zona: {data['zone']}\n🛠 Vazifa: {data['task']}" if data else "Topilmadi."
        await callback.message.answer(text, parse_mode=ParseMode.HTML)
    await callback.answer()

# Render uchun veb-server
async def handle_ping(request):
    return web.Response(text="Bot ishlayapti!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

async def main() -> None:
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    await start_web_server()
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
