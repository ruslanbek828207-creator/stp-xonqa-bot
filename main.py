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

# Янги юборилган сплиттерлар ва абонентлар файл номлари
EXCEL_SPLITTERS = "2.3.1.6_Оборудование_сетей_ШПД_10.11.2026_12h12m40s_2.xlsx"
EXCEL_SUBSCRIBERS = "Xonqa.xlsx"

splitters_list = []
subscribers_list = []

# Сплиттерлар базасини ўқиш
try:
    if os.path.exists(EXCEL_SPLITTERS):
        df_raw = pd.read_excel(EXCEL_SPLITTERS, skiprows=11)
        if len(df_raw) > 0:
            for _, row in df_raw.iterrows():
                num = str(row.iloc[2] if len(row) > 2 else '').strip()
                splitter_type = str(row.iloc[5] if len(row) > 5 else '').strip()
                model = str(row.iloc[6] if len(row) > 6 else '').strip()
                address = str(row.iloc[25] if len(row) > 25 else '').strip()
                town = str(row.iloc[31] if len(row) > 31 else '').strip()
                real_sn = str(row.iloc[35] if len(row) > 35 else '').strip()
                
                if num and num != 'nan':
                    splitters_list.append({
                        "number": num,
                        "splitter": splitter_type,
                        "model": model,
                        "address": address,
                        "town": town,
                        "real_sn": real_sn
                    })
        print(f"✅ Сплиттерлар юкланди: {len(splitters_list)} та")
except Exception as e:
    print(f"❌ Сплиттер файлини ўқишда хатолик: {e}")

# Абонентлар базасини ўқиш
try:
    if os.path.exists(EXCEL_SUBSCRIBERS):
        xls = pd.ExcelFile(EXCEL_SUBSCRIBERS)
        for sheet_name in xls.sheet_names:
            df_sub = pd.read_excel(EXCEL_SUBSCRIBERS, sheet_name=sheet_name)
            for _, row in df_sub.iterrows():
                client_name = str(row.get('CLIENT', '') or row.get('Client', '') or '').strip()
                login_val = str(row.get('Login', '') or row.get('login', '') or '').strip()
                phone_num = str(row.get('PHONE', '') or row.get('Phone', '') or '-').strip()
                msisdn_val = str(row.get('MSISDN', '') or '').strip()
                address_val = str(row.get('Прописка', '') or row.get('Address', '') or '-').strip()
                balance_val = str(row.get('Баланс', '') or row.get('Balance', '0')).strip()
                rate_plan = str(row.get('RATE_PLAN', '') or '-').strip()
                status_val = str(row.get('RT_LC_STATES', '') or '-').strip()

                if (client_name and client_name != 'nan') or (login_val and login_val != 'nan'):
                    subscribers_list.append({
                        "client": client_name if client_name != 'nan' else 'Номаълум',
                        "login": login_val if login_val != 'nan' else '-',
                        "phone": phone_num if phone_num != 'nan' else '-',
                        "msisdn": msisdn_val if msisdn_val != 'nan' else '-',
                        "address": address_val if address_val != 'nan' else '-',
                        "balance": balance_val if balance_val != 'nan' else '0',
                        "rate_plan": rate_plan if rate_plan != 'nan' else '-',
                        "status": status_val if status_val != 'nan' else '-'
                    })
        print(f"✅ Абонентлар базаси юкланди: {len(subscribers_list)} та")
except Exception as e:
    print(f"❌ Абонентлар файлини ўқишда хатолик: {e}")

TOWNS_LIST = sorted(list(set(s['town'] for s in splitters_list if s['town'] and s['town'] != 'nan')))

UCHASKA_10_DATA = {
    "uch_1": {"name": "Ёрқин Юлдуз-2 берк кўчаси", "status": "Узлуксиз хизмат кўрсатишда", "signal": "Нормал (-19 dBm)"},
    "uch_2": {"name": "Олажа қишлоғи, Yorqin yulduz уй", "status": "Фаол", "signal": "Яхши (-20 dBm)"},
    "uch_3": {"name": "Олажа қишлоғи, Афсонавий кўчаси", "status": "Фаол", "signal": "Нормал (-22 dBm)"},
    "uch_4": {"name": "Олажа қишлоғи, Ахли диёр кўчаси", "status": "Фаол", "signal": "Яхши (-18 dBm)"},
    "uch_5": {"name": "Олажа қишлоғи, Барака кўчаси", "status": "Фаол", "signal": "Нормал (-21 dBm)"},
    "uch_6": {"name": "Олажа қишлоғи, Бахтли оила кўчаси", "status": "Фаол", "signal": "Яхши (-19 dBm)"},
    "uch_7": {"name": "Олажа қишлоғи, Бўстонлиқ кўчаси", "status": "Фаол", "signal": "Нормал (-23 dBm)"},
    "uch_8": {"name": "Олажа қишлоғи, Бухоро кўчаси", "status": "Фаол", "signal": "Яхши (-20 dBm)"},
    "uch_9": {"name": "Олажа қишлоғи, Буюк ипак йўли 3- йўлак кўчаси", "status": "Фаол", "signal": "Нормал (-22 dBm)"},
}

ELECTRICIANS_DATA = {
    "elect_1": {"name": "Шоназаров Достон Хайитбоевич", "phone": "+998995054885", "zone": "Хонқа тумани, Марказий МФЙ", "task": "Оптик тармоқларни тортиш, сварка қилиш ва абонентларни улаш."},
    "elect_2": {"name": "Отабоев Рамзиддин Рахматилло угли", "phone": "+998995603938", "zone": "Хонқа тумани, Пахтакор МФЙ", "task": "Бетон столбаларда ишлаш, drop кабель тортиш ва роутерларни созлаш."},
    "elect_3": {"name": "Юсупов Бобур Сапарбой ўғли", "phone": "+998995601312", "zone": "Хонқа тумани, Тинчлик МФЙ", "task": "1х16 сплиттерларда сигнални текшириш ва носозликларни бартараф этиш."},
    "elect_4": {"name": "Каримов Илхом Машарипович", "phone": "+998995606399", "zone": "Хонқа тумани, Гулистон МФЙ", "task": "Интернет линияларини таъмирлаш ва абонентлар мурожаатлари билан ишлаш."},
    "elect_5": {"name": "Абдурахмонов Хушнуд Ниёзметович", "phone": "+998995603001", "zone": "Хонқа тумани, Навоий МФЙ", "task": "Оптик толали кабелларни улаш ва сигнал даражасини ўлчаш."},
    "elect_6": {"name": "Жуманиёзов Жўшқин Шоназарович", "phone": "+998995608636", "zone": "Хонқа тумани, Бўстон МФЙ", "task": "ZTE ва TP-Link роутерларини созлаш, интернет тармоқларини тест қилиш."},
    "elect_7": {"name": "Атажанов Рустам Комоладдинович", "phone": "+998992797072", "zone": "Хонқа тумани, Истиқлол МФЙ", "task": "Янги абонентларни тармоққа улаш ва шартнома масалалари."},
    "elect_8": {"name": "Каримов Заир Авезметович", "phone": "+998995601310", "zone": "Хонқа тумани, Оқолтин МФЙ", "task": "Столбаларга чиқиш, ҳаво линияларини монтаж қилиш."},
    "elect_9": {"name": "Бабажанов Искандар Сапарбекович", "phone": "+998995603005", "zone": "Хонқа тумани, Қоратепа МФЙ", "task": "Магистрал оптик тармоқларга хизмат кўрсатиш."},
    "elect_10": {"name": "Каримов Дониёр Хаджибоевич", "phone": "+998995603171", "zone": "Хонқа тумани, Шихрезван МФЙ", "task": "Абонентлар уйига интернет кабелларини тортиш ва улаш."},
    "elect_11": {"name": "Жуманиёзов Руслан Рустамович", "phone": "+998995603937", "zone": "Хонқа тумани (Бошқарув ва техник назорат)", "task": "Техник ёрдам, тармоқ мониторинги, OSS портал ва бот бошқаруви."},
    "elect_12": {"name": "Саидов Хушнуд Матяқубович", "phone": "+998992797071", "zone": "Хонқа тумани, Ҳаётобод МФЙ", "task": "Оптик сварка ишлари ва таъмирлаш."},
    "elect_13": {"name": "Жаббаров Хамдам Рустамович", "phone": "+998995603936", "zone": "Хонқа тумани, Сарқипчоқ МФЙ", "task": "Авария ҳолатларини бартараф этиш ва тушган аризалар билан ишлаш."},
    "elect_14": {"name": "Хаитов Хаитбай Шоназарович", "phone": "+998995603934", "zone": "Хонқа тумани, Қипчоқ МФЙ", "task": "Интернет тармоқларини кенгайтириш ва янги нуқталарни улаш."},
    "elect_15": {"name": "Саидов Умарбек Шавкатович", "phone": "+998995603002", "zone": "Хонқа тумани, Заркент МФЙ", "task": "Сплиттерлар ва тақсимот қутиларини назорат қилиш."},
    "elect_16": {"name": "Эгамов Азизбек Озод угли", "phone": "+998977929525", "zone": "Хонқа тумани, Чармгар МФЙ", "task": "Абонент моделларини созлаш ва техник ёрдам кўрсатиш."},
    "elect_17": {"name": "Якубов Жасурбек Ахмеджонович", "phone": "+998995606787", "zone": "Хонқа тумани, Янги ҳаёт МФЙ", "task": "Оптик кабель узилишларини тезкор бартараф этиш."},
    "elect_18": {"name": "Машарипов Али Валиевич", "phone": "+998995603931", "zone": "Хонқа тумани, Дўстлик МФЙ", "task": "Тармоқ қурилмаларини ўрнатиш ва созлаш."},
    "elect_19": {"name": "Ваисов Рустам Юсуфбоевич", "phone": "+998995603935", "zone": "Хонқа тумани, Меҳнатобод МФЙ", "task": "Абонентларга сифатли интернет улаш ва линияларни текшириш."},
    "elect_20": {"name": "Юлдошов Кадамбой Атабоевич", "phone": "+998995603007", "zone": "Хонқа тумани, Олмазор МФЙ", "task": "Электр ва оптик тармоқларда профилактика ишлари."},
}

keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="🌐 Интернет тарифлари"),
            KeyboardButton(text="⚡ Сплиттер қидириш")
        ],
        [
            KeyboardButton(text="🔍 Абонент қидириш"),
            KeyboardButton(text="🏘 Қишлоқ ва шаҳарчалар")
        ],
        [
            KeyboardButton(text="🏢 10-учаска объектлари"),
            KeyboardButton(text="👷 Электрамонтёрлар")
        ],
        [
            KeyboardButton(text="🛠 Хизматлар ва мурожаат"),
            KeyboardButton(text="📞 Боғланиш")
        ],
        [
            KeyboardButton(text="📊 OSS Портал", web_app=WebAppInfo(url="https://oss.uztelecom.uz/dashboard/")),
            KeyboardButton(text="🗺 GeoWFM Харита", web_app=WebAppInfo(url="https://geowfm.uztelecom.uz/geoutr/equipments/filter"))
        ],
        [
            KeyboardButton(text="📱 MSMS Портал", web_app=WebAppInfo(url="https://msms.uztelecom.uz/"))
        ]
    ],
    resize_keyboard=True
)

@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    if message.from_user.id == ADMIN_ID or message.from_user.id in authorized_users:
        user_name = html.quote(message.from_user.first_name)
        await message.answer(
            f"Ассалому алайкум, {user_name}!\n"
            f"<b>@STP_Xonqa_bot</b> хизматингизга тайёр. Керакли бўлимни танланг:",
            reply_markup=keyboard
        )
    else:
        await message.answer("🔐 Ассалому алайкум! Ботдан фойдаланиш учун махфий паролни киритинг:")

@dp.message(Command("stats"))
async def stats_handler(message: Message) -> None:
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer(f"📊 Паролни киритиб уланган ходимлар: {len(authorized_users)} та\n📦 Сплиттерлар: {len(splitters_list)} та\n👥 Хонқа абонентлари: {len(subscribers_list)} та")

@dp.message()
async def text_handler(message: Message) -> None:
    user_id = message.from_user.id
    text = message.text.strip()

    if user_id == ADMIN_ID or user_id in authorized_users:
        if text == "🌐 Интернет тарифлари":
            await message.answer(
                "<b>UZTELECOM Home Интернет тарифлари (Ҳаммаси бирга):</b>\n\n"
                "🔥 <b>Ҳаммаси бирга 4</b> (500 Мбит/с) - 500 000 сўм/ой\n"
                "🔥 <b>Ҳаммаси бирга 3+</b> (350 Мбит/с) - 350 000 сўм/ой\n"
                "🔥 <b>Ҳаммаси бирга 3</b> (250 Мбит/с) - 215 000 сўм/ой\n"
                "🔥 <b>Ҳаммаси бирга 2+</b> (150 Мбит/с) - 175 000 сўм/ой\n\n"
                "📞 Масъул: +998995603937",
                parse_mode=ParseMode.HTML
            )
        elif text == "⚡ Сплиттер қидириш":
            search_state.add(user_id)
            await message.answer("🔍 Қидирмоқчи бўлган сплиттер номини киритинг (масалан: <code>Markaz 1/1/1</code> ёки <code>Toma 1/1/1</code>):", parse_mode=ParseMode.HTML)
        elif text == "🔍 Абонент қидириш":
            await message.answer("🔍 Абонент Логин (счёт), Ф.И.Ш., телефон рақами ёки манзилини ёзинг (масалан: <code>m897730</code>):", parse_mode=ParseMode.HTML)
        elif text == "🏘 Қишлоқ ва шаҳарчалар":
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
            await message.answer("<b>Хонқа туманидаги қишлоқ ва шаҳарчалар:</b>\nКеракли ҳудудни танланг:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
        elif text == "🏢 10-учаска объектлари":
            buttons = [[InlineKeyboardButton(text=f"📍 {val['name']}", callback_data=key)] for key, val in UCHASKA_10_DATA.items()]
            await message.answer("<b>10-учаска ҳудудлари ва манзиллари:</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
        elif text == "👷 Электрамонтёрлар":
            buttons = [[InlineKeyboardButton(text=f"👷 {val['name']}", callback_data=key)] for key, val in ELECTRICIANS_DATA.items()]
            await message.answer("Хонқа туманидаги электрамонтёрлар рўйхати:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
        elif text == "🛠 Хизматлар ва мурожаат":
            await message.answer("<b>Техник хизматлар ва ўрнатиш:</b>\n• Оптик фибер сварка\n• Бетон столбаларда ишлаш\nМурожаат: +998995603937")
        elif text == "📞 Боғланиш":
            await message.answer("📞 <b>Алоқа:</b> +998995603937 (Хонқа тумани)")
        else:
            # Сплиттер қидириш
            if user_id in search_state:
                search_state.remove(user_id)
                query = text.lower().strip()
                
                found = []
                for s in splitters_list:
                    num = s['number'].lower().strip()
                    addr = s['address'].lower().strip()
                    town = s['town'].lower().strip()
                    sn = s['real_sn'].lower().strip()
                    
                    if query in num or query in addr or query in town or query in sn:
                        found.append(s)

                if not found:
                    await message.answer("❌ Бундай сплиттер ёки манзил топилмади.")
                else:
                    response = f"🔍 <b>Сплиттер қидирув натижалари (Жами: {len(found)} та):</b>\n\n"
                    for item in found[:10]:
                        response += (
                            f"📍 <b>Ҳудуд:</b> {item['town']}\n"
                            f"🏷 <b>Номи:</b> {item['number']}\n"
                            f"⚙️ <b>Тури:</b> {item['splitter']} ({item['model']})\n"
                            f"🏠 <b>Манзил:</b> {item['address']}\n"
                            f"🔢 <b>S/N:</b> {item['real_sn']}\n"
                            f"-----------------------------------\n"
                        )
                    if len(found) > 10:
                        response += f"\n<i>Фақат дастлабки 10 таси кўрсатилди.</i>"
                    await message.answer(response, parse_mode=ParseMode.HTML)
                return

            # Абонентни қидириш
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
                response = f"👤 <b>Абонент қидирув натижалари (Жами: {len(found_subs)} та):</b>\n\n"
                for item in found_subs[:10]:
                    response += (
                        f"👨‍💼 <b>Ф.И.Ш:</b> {item['client']}\n"
                        f"🔑 <b>Логин:</b> <code>{item['login']}</code>\n"
                        f"📞 <b>Тел:</b> {item['phone']}\n"
                        f"📋 <b>Тариф:</b> {item['rate_plan']}\n"
                        f"🏠 <b>Манзил:</b> {item['address']}\n"
                        f"🟢 <b>Ҳолати:</b> {item['status']}\n"
                        f"💰 <b>Баланс:</b> {item['balance']} сўм\n"
                        f"-----------------------------------\n"
                    )
                if len(found_subs) > 10:
                    response += f"\n<i>Фақат дастлабки 10 таси кўрсатилди. Аниқроқ ёзинг.</i>"
                await message.answer(response, parse_mode=ParseMode.HTML)
            else:
                await message.answer("❌ Бундай абонент ёки сплиттер топилмади. Қайтадан текшириб ёзинг.")
    else:
        if text == SECRET_PASSWORD:
            authorized_users.add(user_id)
            await message.answer("✅ Парол тўғри! Хуш келибсиз. Қуйидаги менюдан фойдаланишингиз mumkin:", reply_markup=keyboard)
        else:
            await message.answer("❌ Нотўғри парол! Илтимос, тўғри паролни киритинг:")

@dp.callback_query()
async def callback_handler(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    if user_id != ADMIN_ID and user_id not in authorized_users:
        await callback.answer("Рухсат йўқ!", show_alert=True)
        return

    data_id = callback.data
    if data_id.startswith("town_"):
        town_name = data_id.replace("town_", "")
        found = [s for s in splitters_list if s['town'] == town_name]
        
        response = f"🏘 <b>{town_name} бўйича сплиттерлар (Жами: {len(found)} та):</b>\n\n"
        for item in found[:10]:
            response += (
                f"🏷 <b>Номи:</b> {item['number']}\n"
                f"⚙️ <b>Тури:</b> {item['splitter']} ({item['model']})\n"
                f"🏠 <b>Манзил:</b> {item['address']}\n"
                f"🔢 <b>S/N:</b> {item['real_sn']}\n"
                f"-----------------------------------\n"
            )
        if len(found) > 10:
            response += f"\n<i>Фақат дастлабки 10 таси кўрсатилди.</i>"
        await callback.message.answer(response, parse_mode=ParseMode.HTML)
    elif data_id.startswith("uch_"):
        data = UCHASKA_10_DATA.get(data_id)
        text = f"🏢 <b>{data['name']}</b>\n📌 Ҳолати: {data['status']}\n⚡ Сигнал: {data['signal']}" if data else "Топилмади."
        await callback.message.answer(text, parse_mode=ParseMode.HTML)
    elif data_id.startswith("elect_"):
        data = ELECTRICIANS_DATA.get(data_id)
        text = f"👷 <b>{data['name']}</b>\n📞 Тел: {data['phone']}\n📍 Зона: {data['zone']}\n🛠 Вазифа: {data['task']}" if data else "Топилмади."
        await callback.message.answer(text, parse_mode=ParseMode.HTML)
    await callback.answer()

async def handle_ping(request):
    return web.Response(text="Бот ишлаяпти!")

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
