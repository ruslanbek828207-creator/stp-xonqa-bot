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

ADMIN_ID = 51975910
SECRET_PASSWORD = "3939"

authorized_users = set()
search_state = set()

EXCEL_SPLITTERS = "2.3.1.6_Оборудование_сетей_ШПД_10.11.2026_12h12m40s.xlsx"
EXCEL_SUBSCRIBERS = "Xonqa.xlsx"

splitters_list = []
subscribers_list = []

# Splitterlar bazasini o'qish
try:
    if os.path.exists(EXCEL_SPLITTERS):
        df_raw = pd.read_excel(EXCEL_SPLITTERS, skiprows=11)
        if len(df_raw) > 1:
            col_names = df_raw.iloc[0].values
            df_data = df_raw.iloc[1:].copy()
            df_data.columns = col_names
            for _, row in df_data.iterrows():
                splitters_list.append({
                    "number": str(row.get('Номер оборуд.', '')),
                    "splitter": str(row.get('Вид оборуд.', '')),
                    "model": str(row.get('Марка', '')),
                    "address": str(row.get('Адрес установки', '')),
                    "town": str(row.get('Населенный пункт', '')),
                    "real_sn": str(row.get('Серийный номер', ''))
                })
        print(f"✅ Splitterlar yuklandi: {len(splitters_list)} ta")
except Exception as e:
    print(f"❌ Splitter faylini o'qishda xatolik: {e}")

# Abonentlar bazasini o'qish (Barcha varaqlarni va Login ustunini to'liq qo'llab-quvvatlash)
try:
    if os.path.exists(EXCEL_SUBSCRIBERS):
        xls = pd.ExcelFile(EXCEL_SUBSCRIBERS)
        for sheet_name in xls.sheet_names:
            df_sub = pd.read_excel(EXCEL_SUBSCRIBERS, sheet_name=sheet_name)
            for _, row in df_sub.iterrows():
                client_name = str(row.get('CLIENT', '') or row.get('Client', '') or '')
                login_val = str(row.get('Login', '') or row.get('login', '') or '')
                phone_num = str(row.get('PHONE', '') or row.get('Phone', '') or '-')
                msisdn_val = str(row.get('MSISDN', '') or '')
                address_val = str(row.get('Прописка', '') or row.get('Address', '') or '-')
                balance_val = str(row.get('Баланс', '') or row.get('Balance', '0'))
                rate_plan = str(row.get('RATE_PLAN', '') or '-')
                status_val = str(row.get('RT_LC_STATES', '') or '-')

                if (client_name and client_name != 'nan') or (login_val and login_val != 'nan'):
                    subscribers_list.append({
                        "client": client_name if client_name != 'nan' else 'Nomaʼlum',
                        "login": login_val if login_val != 'nan' else '-',
                        "phone": phone_num if phone_num != 'nan' else '-',
                        "msisdn": msisdn_val if msisdn_val != 'nan' else '-',
                        "address": address_val if address_val != 'nan' else '-',
                        "balance": balance_val if balance_val != 'nan' else '0',
                        "rate_plan": rate_plan if rate_plan != 'nan' else '-',
                        "status": status_val if status_val != 'nan' else '-'
                    })
        print(f"✅ Abonentlar bazasi yuklandi: {len(subscribers_list)} ta")
except Exception as e:
    print(f"❌ Abonentlar faylini o'qishda xatolik: {e}")

TOWNS_LIST = sorted(list(set(s['town'] for s in splitters_list if s['town'] and s['town'] != 'nan')))

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

keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="🌐 Internet tariflari"),
            KeyboardButton(text="⚡ Splitter qidirish")
        ],
        [
            KeyboardButton(text="🔍 Abonent qidirish"),
            KeyboardButton(text="🏘 Qishloq va shaharchalar")
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
            KeyboardButton(text="🗺 GeoWFM Xarita", web_app=WebAppInfo(url="https://geowfm.uztelecom.uz/geoutr/equipments/filter"))
        ],
        [
            KeyboardButton(text="📱 MSMS Portal", web_app=WebAppInfo(url="https://msms.uztelecom.uz/"))
        ]
    ],
    resize_keyboard=True
)

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
    await message.answer(f"📊 Parolni kiritib ulangan xodimlar: {len(authorized_users)} ta\n📦 Splitterlar: {len(splitters_list)} ta\n👥 Xonqa abonentlari: {len(subscribers_list)} ta")

@dp.message()
async def text_handler(message: Message) -> None:
    user_id = message.from_user.id
    text = message.text.strip()

    if user_id == ADMIN_ID or user_id in authorized_users:
        if text == "🌐 Internet tariflari":
            await message.answer(
                "<b>UZTELECOM Home Internet tariflari (Hammasi birga):</b>\n\n"
                "🔥 <b>Hammasi birga 4</b> (500 Mbit/s) - 500 000 so'м/oy\n"
                "🔥 <b>Hammasi birga 3+</b> (350 Mbit/s) - 350 000 so'м/oy\n"
                "🔥 <b>Hammasi birga 3</b> (250 Mbit/s) - 215 000 so'м/oy\n"
                "🔥 <b>Hammasi birga 2+</b> (150 Mbit/s) - 175 000 so'м/oy\n\n"
                "📞 Mas'ul: +998995603937",
                parse_mode=ParseMode.HTML
            )
        elif text == "⚡ Splitter qidirish":
            search_state.add(user_id)
            await message.answer("🔍 Qidirmoqchi bo'lgan qishloq nomini yoki raqamni kiriting (masalan: <code>Олажа</code> yoki <code>1/1</code>):", parse_mode=ParseMode.HTML)
        elif text == "🔍 Abonent qidirish":
            await message.answer("🔍 Abonent Login (schot), F.I.Sh., telefon raqami yoki manzilini yozing (masalan: <code>m897730</code>):", parse_mode=ParseMode.HTML)
        elif text == "🏘 Qishloq va shaharchalar":
            buttons = []
            row = []
            for t in TOWNS_LIST:
                short_name = t.replace(" қишлоғи", "").replace(" шаҳарчаси", "")
                row.append(InlineKeyboardButton(text=f"🏘 {short_name}", callback_data=f"town_{t}"))
                if len(row) == 2:
                    buttons.append(row)
                    row = []
            if row:
                buttons.append(row)
            await message.answer("<b>Xonqa tumanidagi qishloq va shaharchalar:</b>\nKerakli hududni tanlang:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
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
            # Agar foydalanuvchi "⚡ Splitter qidirish" rejimida bo'lsa
            if user_id in search_state:
                search_state.remove(user_id)
                query = text.lower()
                keywords = [k.strip() for k in query.split(',')]
                
                found = []
                for s in splitters_list:
                    num = s['number'].lower()
                    splitter_info = s['splitter'].lower()
                    addr = s['address'].lower()
                    town = s['town'].lower()
                    sn = s['real_sn'].lower()
                    
                    match_any = True
                    for kw in keywords:
                        if not (kw in num or kw in splitter_info or kw in addr or kw in town or kw in sn):
                            match_any = False
                            break
                    if match_any:
                        found.append(s)

                if not found:
                    await message.answer("❌ Bunday splitter yoki manzil topilmadi.")
                else:
                    response = f"🔍 <b>Splitter qidiruv natijalari (Jami: {len(found)} ta):</b>\n\n"
                    for item in found[:10]:
                        response += (
                            f"📍 <b>Hudud:</b> {item['town']}\n"
                            f"🏷 <b>Nomi:</b> {item['number']}\n"
                            f"⚙️ <b>Turi:</b> {item['splitter']} ({item['model']})\n"
                            f"🏠 <b>Manzil:</b> {item['address']}\n"
                            f"🔢 <b>S/N:</b> {item['real_sn']}\n"
                            f"-----------------------------------\n"
                        )
                    if len(found) > 10:
                        response += f"\n<i>Faqat dastlabki 10 tasi ko'rsatildi.</i>"
                    await message.answer(response, parse_mode=ParseMode.HTML)
                return

            # Abonentni Login, F.I.Sh, Telefon, MSISDN yoki Manzil bo'yicha qidirish
            query = text.lower().strip()
            found_subs = []
            for sub in subscribers_list:
                log = sub['login'].lower()
                cli = sub['client'].lower()
                ph = sub['phone'].lower()
                msisdn = sub['msisdn'].lower()
                adr = sub['address'].lower()
                if query in log or query in cli or query in ph or query in msisdn or query in adr:
                    found_subs.append(sub)

            if found_subs:
                response = f"👤 <b>Abonent qidiruv natijalari (Jami: {len(found_subs)} ta):</b>\n\n"
                for item in found_subs[:10]:
                    response += (
                        f"👨‍💼 <b>F.I.Sh:</b> {item['client']}\n"
                        f"🔑 <b>Login:</b> <code>{item['login']}</code>\n"
                        f"📞 <b>Tel:</b> {item['phone']}\n"
                        f"📋 <b>Tarif:</b> {item['rate_plan']}\n"
                        f"🏠 <b>Manzil:</b> {item['address']}\n"
                        f"🟢 <b>Holati:</b> {item['status']}\n"
                        f"💰 <b>Balans:</b> {item['balance']} so'м\n"
                        f"-----------------------------------\n"
                    )
                if len(found_subs) > 10:
                    response += f"\n<i>Faqat dastlabki 10 tasi ko'rsatildi. Aniqroq yozing.</i>"
                await message.answer(response, parse_mode=ParseMode.HTML)
            else:
                await message.answer("❌ Bunday abonent yoki splitter topilmadi. Qaytadan tekshirib yozing.")
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
    if data_id.startswith("town_"):
        town_name = data_id.replace("town_", "")
        found = [s for s in splitters_list if s['town'] == town_name]
        
        response = f"🏘 <b>{town_name} bo'yicha splitterlar (Jami: {len(found)} ta):</b>\n\n"
        for item in found[:10]:
            response += (
                f"🏷 <b>Nomi:</b> {item['number']}\n"
                f"⚙️ <b>Turi:</b> {item['splitter']} ({item['model']})\n"
                f"🏠 <b>Manzil:</b> {item['address']}\n"
                f"🔢 <b>S/N:</b> {item['real_sn']}\n"
                f"-----------------------------------\n"
            )
        if len(found) > 10:
            response += f"\n<i>Faqat dastlabki 10 tasi ko'rsatildi.</i>"
        await callback.message.answer(response, parse_mode=ParseMode.HTML)
    elif data_id.startswith("uch_"):
        data = UCHASKA_10_DATA.get(data_id)
        text = f"🏢 <b>{data['name']}</b>\n📌 Holati: {data['status']}\n⚡ Signal: {data['signal']}" if data else "Topilmadi."
        await callback.message.answer(text, parse_mode=ParseMode.HTML)
    elif data_id.startswith("elect_"):
        data = ELECTRICIANS_DATA.get(data_id)
        text = f"👷 <b>{data['name']}</b>\n📞 Tel: {data['phone']}\n📍 Zona: {data['zone']}\n🛠 Vazifa: {data['task']}" if data else "Topilmadi."
        await callback.message.answer(text, parse_mode=ParseMode.HTML)
    await callback.answer()

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
