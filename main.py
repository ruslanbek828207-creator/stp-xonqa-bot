import asyncio
import logging
import math
import os
import sys
import pandas as pd
from aiohttp import web
from aiogram import Bot, Dispatcher, html
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery
)

TOKEN = "9125362206:AAF4zONlkd5e81kfoZthNBTkwQ8TRa5-UQY"
dp = Dispatcher()

ADMIN_ID = 51975910
SECRET_PASSWORD = "3939"

authorized_users = set()

# Excel файл номлари
EXCEL_SPLITTERS = "2.3.1.6_Оборудование_сетей_ШПД_10.11.2026_12h12m40s.xlsx"
EXCEL_SUBSCRIBERS = "Xonqa.xlsx"
EXCEL_OLT_CANDIDATES = [
    "Tayanch OLT_5.xlsx",
    "Tayanch OLT_4.xlsx",
    "Tayanch OLT_3.xlsx",
    "Tayanch OLT_2.xlsx",
    "Tayanch OLT.xlsx"
]

splitters_list = []
subscribers_list = []

# Tayanch OLT маълумотлари
tayanch_olt_list = []
tayanch_splitters_order = []
tayanch_by_splitter = {}
tayanch_montyor = "JUMANIYAZOV RUSLAN"

# TOMA OLT маълумотлари
toma_olt_list = []
toma_splitters_order = []
toma_by_splitter = {}

def clean_phone(val) -> str:
    if pd.isna(val):
        return "-"
    s = str(val).replace("\xa0", "").strip()
    if not s or s.lower() == "nan":
        return "-"
    try:
        return str(int(float(s)))
    except (ValueError, TypeError):
        return s

def short_splitter_label(full_name: str, prefixes: list[str]) -> str:
    cleaned = full_name
    for p in prefixes:
        cleaned = cleaned.replace(p, "").strip()
    return cleaned if cleaned else full_name

def parse_olt_sheet(df_sheet: pd.DataFrame, default_montyor: str = "") -> tuple[list[dict], list[str], dict[str, list[dict]], str]:
    df_sheet = df_sheet.copy()
    first_col_header = str(df_sheet.columns[1]).strip() if len(df_sheet.columns) > 1 else ""
    detected_montyor = default_montyor
    if "ELEKTRAMANTYORI" in first_col_header.upper():
        detected_montyor = " ".join(first_col_header.split())

    # Агар 0-қаторда "Spllikter" сарлавҳаси турган бўлса, уни устун номи сифатида қўллаш
    row0_col1 = str(df_sheet.iloc[0, 1]).strip() if len(df_sheet) > 0 and len(df_sheet.columns) > 1 and pd.notna(df_sheet.iloc[0, 1]) else ""
    if row0_col1.lower() in ("spllikter", "splitter", "сплиттер"):
        new_cols = list(df_sheet.columns)
        for c_idx in range(1, min(len(new_cols), 7)):
            val_c = df_sheet.iloc[0, c_idx]
            if pd.notna(val_c) and str(val_c).strip():
                new_cols[c_idx] = str(val_c).strip()
        df_sheet.columns = new_cols
        df_sheet = df_sheet.iloc[1:].reset_index(drop=True)

    df_sheet.columns = [
        str(col).strip() if not str(col).startswith("Unnamed") else str(col)
        for col in df_sheet.columns
    ]

    port_col = df_sheet.columns[0]
    sp_col = "Spllikter" if "Spllikter" in df_sheet.columns else df_sheet.columns[1]
    login_col = "Login" if "Login" in df_sheet.columns else (df_sheet.columns[2] if len(df_sheet.columns) > 2 else None)
    addr_col = "Manzil" if "Manzil" in df_sheet.columns else (df_sheet.columns[3] if len(df_sheet.columns) > 3 else None)
    phone_col = "Telfon nomeri" if "Telfon nomeri" in df_sheet.columns else (df_sheet.columns[4] if len(df_sheet.columns) > 4 else None)
    ip_phone_col = "ip-telfon" if "ip-telfon" in df_sheet.columns else (df_sheet.columns[5] if len(df_sheet.columns) > 5 else None)
    ip_col = "ip" if "ip" in df_sheet.columns else (df_sheet.columns[6] if len(df_sheet.columns) > 6 else None)

    ports_out = []
    order_out = []
    by_sp_out = {}
    current_splitter = None

    for _, row in df_sheet.iterrows():
        port_raw = row.get(port_col)
        splitter_or_fio = row.get(sp_col)
        login_val = row.get(login_col) if login_col else None
        address_val = row.get(addr_col) if addr_col else None
        phone_val = row.get(phone_col) if phone_col else None
        ip_phone_val = row.get(ip_phone_col) if ip_phone_col else None
        ip_val = row.get(ip_col) if ip_col else None

        if pd.isna(port_raw):
            if pd.notna(splitter_or_fio) and str(splitter_or_fio).strip():
                current_splitter = " ".join(str(splitter_or_fio).split())
                if current_splitter not in by_sp_out:
                    order_out.append(current_splitter)
                    by_sp_out[current_splitter] = []
            else:
                current_splitter = None
            continue

        if not current_splitter:
            continue

        try:
            port_num = str(int(float(port_raw)))
        except (ValueError, TypeError):
            port_num = str(port_raw).strip()

        raw_fio = " ".join(str(splitter_or_fio).replace("\xa0", " ").split()) if pd.notna(splitter_or_fio) else ""
        fio_str = "Бўш порт" if raw_fio in ("", "\\", "nan") else raw_fio

        login_str = str(login_val).strip() if pd.notna(login_val) and str(login_val).strip() not in ("", "nan") else "-"
        addr_str = " ".join(str(address_val).replace("\xa0", " ").split()) if pd.notna(address_val) and str(address_val).strip() not in ("", "nan") else "-"
        phone_str = clean_phone(phone_val)
        ip_phone_str = clean_phone(ip_phone_val)
        ip_str = str(ip_val).strip() if pd.notna(ip_val) and str(ip_val).strip() not in ("", "nan") else "-"

        entry = {
            "splitter": current_splitter,
            "port": port_num,
            "client": fio_str,
            "login": login_str,
            "address": addr_str,
            "phone": phone_str,
            "ip_phone": ip_phone_str,
            "ip": ip_str,
            "montyor": detected_montyor
        }
        ports_out.append(entry)
        by_sp_out[current_splitter].append(entry)

    return ports_out, order_out, by_sp_out, detected_montyor

# 1. Сплиттерлар базасини ўқиш
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

# 2. Абонентлар базасини ўқиш
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

# 3. Tayanch OLT ва TOMA OLT варақларини ўқиш
try:
    olt_file = next((f for f in EXCEL_OLT_CANDIDATES if os.path.exists(f)), None)
    if olt_file:
        xls_olt = pd.ExcelFile(olt_file)
        sheet_names_clean = {name.strip(): name for name in xls_olt.sheet_names}

        if "Tayanch OLT" in sheet_names_clean:
            df_t_raw = pd.read_excel(olt_file, sheet_name=sheet_names_clean["Tayanch OLT"])
            tayanch_olt_list, tayanch_splitters_order, tayanch_by_splitter, tayanch_montyor = parse_olt_sheet(
                df_t_raw, default_montyor="ELEKTRAMANTYORI JUMANIYAZOV RUSLAN"
            )
            print(f"✅ Tayanch OLT юкланди: {len(tayanch_splitters_order)} та сплиттер, {len(tayanch_olt_list)} та порт")

        if "TOMA OLT" in sheet_names_clean:
            df_m_raw = pd.read_excel(olt_file, sheet_name=sheet_names_clean["TOMA OLT"])
            toma_olt_list, toma_splitters_order, toma_by_splitter, _ = parse_olt_sheet(
                df_m_raw, default_montyor=""
            )
            print(f"✅ TOMA OLT юкланди: {len(toma_splitters_order)} та сплиттер, {len(toma_olt_list)} та порт")
except Exception as e:
    print(f"❌ OLT файлини ўқишда хатолик: {e}")

ELECTRICIANS_DATA = {
    "elect_1": {"name": "Шоназаров Достон Хайитбоевич", "phone": "+998995054885", "zone": "Хонқа тумани, Марказий МФЙ", "task": "Оптик тармоқларни тортиш, сварка қилиш ва абонентларни улаш."},
    "elect_2": {"name": "Отабоев Рамзиддин Рахматилло угли", "phone": "+998995603938", "zone": "Хонқа тумани, Пахтакор МФЙ", "task": "Бетон столбаларда ишлаш, drop кабель тортиш ва роутерларни созлаш."},
    "elect_3": {"name": "Юсупов Бобур Сапарбой ўғли", "phone": "+998995601312", "zone": "Хонқа тумани, Тинчлик МФЙ", "task": "1х16 сплиттерларда сигнални текшириш ва носозликларни бартараф этиш."},
    "elect_4": {"name": "Каримов Илхом Машарипович", "phone": "+998995606399", "zone": "Хонқа тумани, Гулистон МФЙ", "task": "Интернет линияларини таъмирлаш ва абонентлар мурожаатлари билан ишлаш."},
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
            KeyboardButton(text="🔍 Абонент ва сплиттер қидириш")
        ],
        [
            KeyboardButton(text="🔌 Tayanch OLT"),
            KeyboardButton(text="📡 TOMA")
        ],
        [
            KeyboardButton(text="👷 Электрамонтёрлар")
        ]
    ],
    resize_keyboard=True
)

def build_olt_page_keyboard(
    splitters_order: list[str],
    by_splitter: dict[str, list[dict]],
    prefixes: list[str],
    cb_prefix: str,
    page: int,
    page_size: int = 20
) -> InlineKeyboardMarkup:
    total_items = len(splitters_order)
    total_pages = max(1, math.ceil(total_items / page_size))
    page = max(0, min(page, total_pages - 1))

    start_idx = page * page_size
    end_idx = min(start_idx + page_size, total_items)

    rows = []
    row = []
    for idx in range(start_idx, end_idx):
        sp_name = splitters_order[idx]
        ports_cnt = len(by_splitter.get(sp_name, []))
        busy_cnt = sum(1 for p in by_splitter.get(sp_name, []) if p["client"] != "Бўш порт")
        label = f"{short_splitter_label(sp_name, prefixes)} ({busy_cnt}/{ports_cnt})"
        row.append(InlineKeyboardButton(text=label, callback_data=f"{cb_prefix}_sp_{idx}_{page}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)

    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️ Олдинги", callback_data=f"{cb_prefix}_pg_{page - 1}"))
    nav_row.append(InlineKeyboardButton(text=f"📄 {page + 1}/{total_pages}", callback_data=f"{cb_prefix}_noop"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton(text="Кейинги ➡️", callback_data=f"{cb_prefix}_pg_{page + 1}"))
    rows.append(nav_row)

    return InlineKeyboardMarkup(inline_keyboard=rows)

def format_splitter_ports_text(splitter_name: str, by_splitter: dict[str, list[dict]], montyor: str = "") -> str:
    ports = by_splitter.get(splitter_name, [])
    busy_cnt = sum(1 for p in ports if p["client"] != "Бўш порт")
    free_cnt = len(ports) - busy_cnt

    lines = [f"🔌 <b>{splitter_name}</b>"]
    if montyor:
        lines.append(f"👷 Участка монтёри: <b>{montyor}</b>")
    lines.append(f"📊 Портлар: <b>{busy_cnt} банд</b> / <b>{free_cnt} бўш</b> (Жами: {len(ports)} та)\n")

    for p in ports:
        if p["client"] == "Бўш порт":
            lines.append(f"<b>{p['port']}-порт:</b> ⚪ <i>Бўш порт</i>")
        else:
            extra = []
            if p["ip_phone"] != "-":
                extra.append(f"IP-тел: {p['ip_phone']}")
            if p["ip"] != "-":
                extra.append(f"IP: <code>{p['ip']}</code>")
            extra_str = f" | {' | '.join(extra)}" if extra else ""

            lines.append(
                f"<b>{p['port']}-порт:</b> 🟢 <b>{p['client']}</b>\n"
                f"   🔑 Логин: <code>{p['login']}</code> | 📞 Тел: {p['phone']}{extra_str}\n"
                f"   🏠 Манзил: {p['address']}"
            )

    return "\n".join(lines)

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
    t_busy = sum(1 for x in tayanch_olt_list if x["client"] != "Бўш порт")
    m_busy = sum(1 for x in toma_olt_list if x["client"] != "Бўш порт")
    await message.answer(
        f"📊 Паролни киритиб уланган ходимлар: {len(authorized_users)} та\n"
        f"📦 Сплиттерлар: {len(splitters_list)} та\n"
        f"🔌 Tayanch OLT: {len(tayanch_splitters_order)} та сплиттер, {len(tayanch_olt_list)} та порт (Банд: {t_busy} та)\n"
        f"📡 TOMA OLT: {len(toma_splitters_order)} та сплиттер, {len(toma_olt_list)} та порт (Банд: {m_busy} та)\n"
        f"👥 Хонқа абонентлари: {len(subscribers_list)} та"
    )

@dp.message()
async def text_handler(message: Message) -> None:
    if not message.text:
        return
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
        elif text == "🔍 Абонент ва сплиттер қидириш":
            await message.answer("🔍 Қидирмоқчи бўлган абонент логини, Ф.И.Ш., телефон рақами, IP ёки сплиттер номини киритинг (масалан: <code>m1382825</code>, <code>2/16/4</code> ёки <code>Навқирон</code>):", parse_mode=ParseMode.HTML)
        elif text == "🔌 Tayanch OLT":
            if not tayanch_splitters_order:
                await message.answer("❌ Tayanch OLT базаси бўш ёки файл топилмади.")
                return
            t_busy = sum(1 for x in tayanch_olt_list if x["client"] != "Бўш порт")
            await message.answer(
                f"🔌 <b>Tayanch OLT сплиттерлари</b>\n"
                f"👷 Участка монтёри: <b>{tayanch_montyor}</b>\n"
                f"📊 Жами: {len(tayanch_splitters_order)} та сплиттер, {t_busy}/{len(tayanch_olt_list)} порт банд\n"
                f"Керакли сплиттерни танланг:",
                reply_markup=build_olt_page_keyboard(
                    tayanch_splitters_order, tayanch_by_splitter, ["OLT Таянч"], "tolt", 0
                ),
                parse_mode=ParseMode.HTML
            )
        elif text == "📡 TOMA":
            if not toma_splitters_order:
                await message.answer("❌ TOMA OLT базаси бўш ёки файл топилмади.")
                return
            m_busy = sum(1 for x in toma_olt_list if x["client"] != "Бўш порт")
            await message.answer(
                f"📡 <b>TOMA OLT сплиттерлари</b>\n"
                f"📊 Жами: {len(toma_splitters_order)} та сплиттер, {m_busy}/{len(toma_olt_list)} порт банд\n"
                f"Керакли сплиттерни танланг:",
                reply_markup=build_olt_page_keyboard(
                    toma_splitters_order, toma_by_splitter, ["OLT ТOMA", "OLT TOMA"], "molt", 0
                ),
                parse_mode=ParseMode.HTML
            )
        elif text == "👷 Электрамонтёрлар":
            buttons = [[InlineKeyboardButton(text=f"👷 {val['name']}", callback_data=key)] for key, val in ELECTRICIANS_DATA.items()]
            await message.answer("Хонқа туманидаги электрамонтёрлар рўйхати:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
        else:
            query = text.lower().strip()
            keywords = query.split()

            # 1. Абонентларни қидириш
            found_subs = []
            for sub in subscribers_list:
                log = sub['login'].lower()
                cli = sub['client'].lower()
                ph = sub['phone'].lower()
                msisdn = sub['msisdn'].lower()
                adr = sub['address'].lower()
                if query in log or query in cli or query in ph or query in msisdn or query in adr:
                    found_subs.append(sub)

            # 2. Tayanch OLT ва TOMA OLT портларини қидириш
            found_olt_ports = []
            for item in (tayanch_olt_list + toma_olt_list):
                combined_olt = (
                    f"{item['splitter']} порт {item['port']} {item['client']} "
                    f"{item['login']} {item['address']} {item['phone']} "
                    f"{item['ip_phone']} {item['ip']} {item.get('montyor', '')}"
                ).lower()
                if all(kw in combined_olt for kw in keywords):
                    found_olt_ports.append(item)

            # 3. Сплиттерларни қидириш
            found_splitters = []
            for s in splitters_list:
                combined_text = f"{s['number']} {s['splitter']} {s['model']} {s['address']} {s['town']} {s['real_sn']}".lower()
                if all(kw in combined_text for kw in keywords):
                    found_splitters.append(s)

            # Натижаларни чиқариш
            if found_subs or found_olt_ports or found_splitters:
                response = ""
                
                if found_subs:
                    response += f"👤 <b>Абонентлар (Жами: {len(found_subs)} та):</b>\n\n"
                    for item in found_subs[:5]:
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

                if found_olt_ports:
                    response += f"🔌 <b>OLT Портлар (Жами: {len(found_olt_ports)} та):</b>\n\n"
                    for item in found_olt_ports[:8]:
                        extra_info = ""
                        if item['ip_phone'] != '-':
                            extra_info += f"☎️ <b>IP-тел:</b> {item['ip_phone']}\n"
                        if item['ip'] != '-':
                            extra_info += f"🌐 <b>IP:</b> <code>{item['ip']}</code>\n"
                        if item.get('montyor'):
                            extra_info += f"👷 <b>Монтёр:</b> {item['montyor']}\n"

                        response += (
                            f"🏷 <b>Сплиттер:</b> {item['splitter']} (Порт: {item['port']})\n"
                            f"👨‍💼 <b>Ф.И.Ш:</b> {item['client']}\n"
                            f"🔑 <b>Логин:</b> <code>{item['login']}</code>\n"
                            f"🏠 <b>Манзил:</b> {item['address']}\n"
                            f"📞 <b>Тел:</b> {item['phone']}\n"
                            f"{extra_info}"
                            f"-----------------------------------\n"
                        )
                
                if found_splitters:
                    response += f"⚡ <b>Сплиттерлар (Жами: {len(found_splitters)} та):</b>\n\n"
                    for item in found_splitters[:5]:
                        response += (
                            f"📍 <b>Ҳудуд:</b> {item['town']}\n"
                            f"🏷 <b>Номи:</b> {item['number']}\n"
                            f"⚙️ <b>Тури:</b> {item['splitter']} ({item['model']})\n"
                            f"🏠 <b>Манзил:</b> {item['address']}\n"
                            f"🔢 <b>S/N:</b> {item['real_sn']}\n"
                            f"-----------------------------------\n"
                        )
                
                await message.answer(response, parse_mode=ParseMode.HTML)
            else:
                await message.answer("❌ Бундай абонент ёки сплиттер топилмади. Қайтадан текшириб ёзинг.")
    else:
        if text == SECRET_PASSWORD:
            authorized_users.add(user_id)
            await message.answer("✅ Парол тўғри! Хуш келибсиз. Қуйидаги менюдан фойдаланишингиз мумкин:", reply_markup=keyboard)
        else:
            await message.answer("❌ Нотўғри парол! Илтимос, тўғри паролни киритинг:")

@dp.callback_query()
async def callback_handler(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    if user_id != ADMIN_ID and user_id not in authorized_users:
        await callback.answer("Рухсат йўқ!", show_alert=True)
        return

    data_id = callback.data

    # Tayanch OLT callbacklari
    if data_id == "tolt_noop":
        await callback.answer()
        return
    elif data_id.startswith("tolt_pg_"):
        page = int(data_id.replace("tolt_pg_", ""))
        await callback.message.edit_reply_markup(
            reply_markup=build_olt_page_keyboard(
                tayanch_splitters_order, tayanch_by_splitter, ["OLT Таянч"], "tolt", page
            )
        )
        await callback.answer()
    elif data_id.startswith("tolt_back_"):
        page = int(data_id.replace("tolt_back_", ""))
        t_busy = sum(1 for x in tayanch_olt_list if x["client"] != "Бўш порт")
        await callback.message.edit_text(
            f"🔌 <b>Tayanch OLT сплиттерлари</b>\n"
            f"👷 Участка монтёри: <b>{tayanch_montyor}</b>\n"
            f"📊 Жами: {len(tayanch_splitters_order)} та сплиттер, {t_busy}/{len(tayanch_olt_list)} порт банд\n"
            f"Керакли сплиттерни танланг:",
            reply_markup=build_olt_page_keyboard(
                tayanch_splitters_order, tayanch_by_splitter, ["OLT Таянч"], "tolt", page
            ),
            parse_mode=ParseMode.HTML
        )
        await callback.answer()
    elif data_id.startswith("tolt_sp_"):
        parts = data_id.replace("tolt_sp_", "").split("_")
        sp_idx = int(parts[0])
        ret_page = int(parts[1]) if len(parts) > 1 else 0
        if 0 <= sp_idx < len(tayanch_splitters_order):
            sp_name = tayanch_splitters_order[sp_idx]
            ports_text = format_splitter_ports_text(sp_name, tayanch_by_splitter, tayanch_montyor)
            back_kb = InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="⬅️ Сплиттерларга қайтиш", callback_data=f"tolt_back_{ret_page}")]]
            )
            await callback.message.edit_text(ports_text, reply_markup=back_kb, parse_mode=ParseMode.HTML)
        else:
            await callback.answer("Сплиттер топилмади.", show_alert=True)
            return
        await callback.answer()

    # TOMA OLT callbacklari
    elif data_id == "molt_noop":
        await callback.answer()
        return
    elif data_id.startswith("molt_pg_"):
        page = int(data_id.replace("molt_pg_", ""))
        await callback.message.edit_reply_markup(
            reply_markup=build_olt_page_keyboard(
                toma_splitters_order, toma_by_splitter, ["OLT ТOMA", "OLT TOMA"], "molt", page
            )
        )
        await callback.answer()
    elif data_id.startswith("molt_back_"):
        page = int(data_id.replace("molt_back_", ""))
        m_busy = sum(1 for x in toma_olt_list if x["client"] != "Бўш порт")
        await callback.message.edit_text(
            f"📡 <b>TOMA OLT сплиттерлари</b>\n"
            f"📊 Жами: {len(toma_splitters_order)} та сплиттер, {m_busy}/{len(toma_olt_list)} порт банд\n"
            f"Керакли сплиттерни танланг:",
            reply_markup=build_olt_page_keyboard(
                toma_splitters_order, toma_by_splitter, ["OLT ТOMA", "OLT TOMA"], "molt", page
            ),
            parse_mode=ParseMode.HTML
        )
        await callback.answer()
    elif data_id.startswith("molt_sp_"):
        parts = data_id.replace("molt_sp_", "").split("_")
        sp_idx = int(parts[0])
        ret_page = int(parts[1]) if len(parts) > 1 else 0
        if 0 <= sp_idx < len(toma_splitters_order):
            sp_name = toma_splitters_order[sp_idx]
            ports_text = format_splitter_ports_text(sp_name, toma_by_splitter)
            back_kb = InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="⬅️ Сплиттерларга қайтиш", callback_data=f"molt_back_{ret_page}")]]
            )
            await callback.message.edit_text(ports_text, reply_markup=back_kb, parse_mode=ParseMode.HTML)
        else:
            await callback.answer("Сплиттер топилмади.", show_alert=True)
            return
        await callback.answer()

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
