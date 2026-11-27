import asyncio
import logging
import math
import os
import sys
import pandas as pd
from aiohttp import web
from aiogram import Bot, Dispatcher, F, html
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

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

TOKEN = os.getenv("BOT_TOKEN") or "9125362206:AAF4zONlkd5e81kfoZthNBTkwQ8TRa5-UQY"
dp = Dispatcher()

ADMIN_ID = 51975910
SECRET_PASSWORD = "3939"

authorized_users = set()

# Excel fayl nomlari
EXCEL_SPLITTERS = "2.3.1.6_Оборудование_сетей_ШПД_10.11.2026_12h12m40s.xlsx"
EXCEL_SUBSCRIBERS = "Xonqa.xlsx"
EXCEL_OLT_CANDIDATES = [
    "Tayanch OLT.xlsx",
    "Tayanch OLT_5.xlsx",
    "Tayanch OLT_4.xlsx",
    "Tayanch OLT_3.xlsx",
    "Tayanch OLT_2.xlsx",
]
EXCEL_TOMA_EQUIPMENT_CANDIDATES = [
    "Toma OLT_yangilangan_2.xlsx",
    "Toma OLT_yangilangan.xlsx",
    "Toma OLT.xlsx",
]
EXCEL_XONKOBOD_EQUIPMENT = "OLT_Xonkobod_tayyor.xlsx"
EXCEL_YOSH_KUCH_EQUIPMENT = "OLT Yosh kuch.xlsx"
EXCEL_NAVVOI_EQUIPMENT_CANDIDATES = [
    "Navoi_2.xlsx",
    "Navoi.xlsx",
]
EXCEL_MARKAZ2 = "Markaz 2.xlsx"
EXCEL_DURVADIK = "Durvadik.xlsx"
EXCEL_PAXTAKOR_CANDIDATES = [
    "OLT Paxtakor_3.xlsx",
    "OLT Paxtakor_2.xlsx",
    "OLT Paxtakor.xlsx",
]

# Qo‘shimcha OLT ro‘yxati (tugmalar uchun)
EXTRA_OLT_NAMES = [
    "Марказ",
    "Дурвадик",
    "Олажа",
    "Марказ2",
    "Нурафшон",
    "Навои",
    "Олтин сохил",
    "Пахтакор",
    "Дўстлик",
    "Дурман",
    "Хонкобод",
    "Ёш куч",
    "Туркистон",
    "Янги Турмуш",
    "Пахтагул",
]

# Har bir hudud / OLT uchun biriktirilgan montyorlar
ZONE_MONTYORS = {
    "tayanch": "Jumaniyazov Ruslan",
    "toma": "Jumaniyazov Ruslan",
    "xonkobod": "Юсупов Бобур Сапарбой ўғли",
    "yosh_kuch": "Юлдошов Кадамбой Атабоевич",
    "navoi": "Машарипов Али Валиевич",
    "durvadik": "Jumaniyazov Ruslan Рустамович",
    "paxtakor": "Iskandar Bobojonov",
    "markaz2": "Шоназаров Достон Хайитбоевич, Umar Xamdam",
}

splitters_list = []
subscribers_list = []

# Tayanch OLT ma'lumotlari va montyori
tayanch_olt_list = []
tayanch_splitters_order = []
tayanch_by_splitter = {}
tayanch_montyor = ZONE_MONTYORS["tayanch"]

# TOMA OLT ma'lumotlari va montyori
toma_olt_list = []
toma_splitters_order = []
toma_by_splitter = {}
toma_equipment_list = []
toma_source_file = EXCEL_TOMA_EQUIPMENT_CANDIDATES[0]
toma_montyor = ZONE_MONTYORS["toma"]

# OLT Xonkobod uskunalari va montyori
xonkobod_equipment_list = []
xonkobod_montyor = ZONE_MONTYORS["xonkobod"]

# OLT Yosh kuch uskunalari va montyori
yosh_kuch_equipment_list = []
yosh_kuch_montyor = ZONE_MONTYORS["yosh_kuch"]

# OLT Navoi uskunalari va montyori
navoi_equipment_list = []
navoi_source_file = EXCEL_NAVVOI_EQUIPMENT_CANDIDATES[0]
navoi_montyor = ZONE_MONTYORS["navoi"]

# OLT Markaz 2 ma'lumotlari va montyori
markaz2_olt_list = []
markaz2_splitters_order = []
markaz2_by_splitter = {}
markaz2_scheme_list = []
markaz2_montyor = ZONE_MONTYORS["markaz2"]

# OLT Durvadik ma'lumotlari va montyori
durvadik_list = []
durvadik_montyor = ZONE_MONTYORS["durvadik"]

# OLT Paxtakor ma'lumotlari va montyori
paxtakor_list = []
paxtakor_olt_list = []
paxtakor_splitters_order = []
paxtakor_by_splitter = {}
paxtakor_source_file = EXCEL_PAXTAKOR_CANDIDATES[-1]
paxtakor_montyor = ZONE_MONTYORS["paxtakor"]


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


def detect_montyor_by_address_and_splitter(address: str, splitter: str, olt_label: str, fallback: str) -> str:
    text = f"{address} {splitter} {olt_label}".lower()
    if any(k in text for k in ("paxtakor", "пахтакор", "қирқёп", "qirqyop", "сарапоён", "sarapoyon")):
        return ZONE_MONTYORS["paxtakor"]
    if any(k in text for k in ("xonkobod", "хонкобод", "тинчлик", "tinchlik")):
        return ZONE_MONTYORS["xonkobod"]
    if any(k in text for k in ("ёш куч", "yosh kuch", "yoshkuch", "олмазор", "olmazor")):
        return ZONE_MONTYORS["yosh_kuch"]
    if any(k in text for k in ("навои", "navoi", "навхос", "navxos", "дўстлик", "do'stlik")):
        return ZONE_MONTYORS["navoi"]
    if any(k in text for k in ("дурвадик", "durvadik", "сарқипчоқ", "sarqipchoq", "мадир", "madir")):
        return ZONE_MONTYORS["durvadik"]
    if "марказ2" in text or "markaz 2" in text or "markaz2" in text:
        return ZONE_MONTYORS["markaz2"]
    return fallback


def pick_column(df: pd.DataFrame, candidates: list[str], fallback_idx: int | None = None) -> str | None:
    cols_map = {str(c).strip().lower(): c for c in df.columns}
    for cand in candidates:
        key = cand.strip().lower()
        if key in cols_map:
            return cols_map[key]
    for cand in candidates:
        key = cand.strip().lower()
        for col_low, orig_col in cols_map.items():
            if key in col_low:
                return orig_col
    if fallback_idx is not None and 0 <= fallback_idx < len(df.columns):
        return df.columns[fallback_idx]
    return None


def short_splitter_label(full_name: str, prefixes: list[str]) -> str:
    cleaned = full_name
    for p in prefixes:
        cleaned = cleaned.replace(p, "").strip()
    return cleaned if cleaned else full_name


def parse_olt_sheet(df_sheet: pd.DataFrame, default_montyor: str = "") -> tuple[list[dict], list[str], dict[str, list[dict]], str]:
    df_sheet = df_sheet.copy()
    detected_montyor = default_montyor

    row0_vals = [str(x).strip().lower() for x in df_sheet.iloc[0, :7]] if len(df_sheet) > 0 else []
    if any(k in row0_vals for k in ("spllikter", "splitter", "сплиттер", "login")):
        new_cols = list(df_sheet.columns)
        for c_idx in range(min(len(new_cols), 7)):
            val_c = df_sheet.iloc[0, c_idx]
            if pd.notna(val_c) and str(val_c).strip():
                new_cols[c_idx] = str(val_c).strip()
        df_sheet.columns = new_cols
        df_sheet = df_sheet.iloc[1:].reset_index(drop=True)

    if len(df_sheet) > 0 and pd.isna(df_sheet.iloc[0, 0]):
        c1_str = str(df_sheet.iloc[0, 1]).strip() if len(df_sheet.columns) > 1 and pd.notna(df_sheet.iloc[0, 1]) else ""
        c2_str = str(df_sheet.iloc[0, 2]).strip() if len(df_sheet.columns) > 2 and pd.notna(df_sheet.iloc[0, 2]) else ""
        if c2_str and c1_str.lower() in ("olt paxtakor", "paxtakor", "tayanch olt", "toma olt", "markaz 2", "марказ2"):
            new_cols = list(df_sheet.columns)
            if len(new_cols) > 1:
                new_cols[1] = "Spllikter"
            if len(new_cols) > 2:
                new_cols[2] = "Login"
            if len(new_cols) > 3:
                new_cols[3] = "Manzil"
            if len(new_cols) > 4:
                new_cols[4] = "Telfon nomeri"
            if len(new_cols) > 5:
                new_cols[5] = "ip-telfon"
            if len(new_cols) > 6:
                new_cols[6] = "ip"
            df_sheet.columns = new_cols

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
        col1_val = row.get(sp_col)
        col2_val = row.get(login_col) if login_col else None
        address_val = row.get(addr_col) if addr_col else None
        phone_val = row.get(phone_col) if phone_col else None
        ip_phone_val = row.get(ip_phone_col) if ip_phone_col else None
        ip_val = row.get(ip_col) if ip_col else None

        if pd.isna(port_raw):
            c1_s = " ".join(str(col1_val).split()) if pd.notna(col1_val) and str(col1_val).strip().lower() != "nan" else ""
            c2_s = " ".join(str(col2_val).split()) if pd.notna(col2_val) and str(col2_val).strip().lower() != "nan" else ""

            if c1_s.lower() in ("spllikter", "splitter", "сплиттер"):
                continue

            if c2_s and c1_s.lower() in ("olt paxtakor", "paxtakor", "tayanch olt", "toma olt", "markaz 2", "марказ2"):
                current_splitter = f"{c1_s} {c2_s}".strip()
            elif c1_s:
                current_splitter = c1_s
            else:
                current_splitter = None
                continue

            if current_splitter not in by_sp_out:
                order_out.append(current_splitter)
                by_sp_out[current_splitter] = []
            continue

        if not current_splitter:
            continue

        try:
            port_num = str(int(float(port_raw)))
        except (ValueError, TypeError):
            port_num = str(port_raw).strip()

        raw_fio = " ".join(str(col1_val).replace("\xa0", " ").split()) if pd.notna(col1_val) else ""
        fio_str = "Бўш порт" if raw_fio in ("", "\\", "nan") else raw_fio

        login_str = str(col2_val).strip() if pd.notna(col2_val) and str(col2_val).strip() not in ("", "nan") else "-"
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


# 1. Splitters bazasini o'qish
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

# 2. Abonentlar bazasini o'qish
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

# 3. Tayanch OLT va TOMA OLT varaqlarini o'qish
try:
    olt_file = next((f for f in EXCEL_OLT_CANDIDATES if os.path.exists(f)), None)
    if olt_file:
        xls_olt = pd.ExcelFile(olt_file)
        sheet_names_clean = {name.strip(): name for name in xls_olt.sheet_names}

        if "Tayanch OLT" in sheet_names_clean:
            df_t_raw = pd.read_excel(olt_file, sheet_name=sheet_names_clean["Tayanch OLT"])
            tayanch_olt_list, tayanch_splitters_order, tayanch_by_splitter, _ = parse_olt_sheet(
                df_t_raw, default_montyor=tayanch_montyor
            )
            print(f"✅ Tayanch OLT юкланди: {len(tayanch_splitters_order)} та сплиттер, {len(tayanch_olt_list)} та порт (Монтёр: {tayanch_montyor})")

        if "TOMA OLT" in sheet_names_clean:
            df_m_raw = pd.read_excel(olt_file, sheet_name=sheet_names_clean["TOMA OLT"])
            toma_olt_list, toma_splitters_order, toma_by_splitter, _ = parse_olt_sheet(
                df_m_raw, default_montyor=toma_montyor
            )
            print(f"✅ TOMA OLT портлари юкланди: {len(toma_splitters_order)} та сплиттер, {len(toma_olt_list)} та порт (Монтёр: {toma_montyor})")
except Exception as e:
    print(f"❌ OLT файлини ўқишда хатолик: {e}")

# 3b. Toma OLT uskunalarini o'qish
try:
    toma_eq_file = next((f for f in EXCEL_TOMA_EQUIPMENT_CANDIDATES if os.path.exists(f)), None)
    if toma_eq_file:
        toma_source_file = toma_eq_file
        xls_teq = pd.ExcelFile(toma_eq_file)
        for s_name in xls_teq.sheet_names:
            df_teq = pd.read_excel(toma_eq_file, sheet_name=s_name)
            set_col = pick_column(df_teq, ["Set", "Hudud", "Set / Hudud"], 0)
            num_col = pick_column(df_teq, ["Nomer oborud.", "Kod / Port", "Kod porta", "Nomer"], 1)
            addr_col = pick_column(df_teq, ["Adres ustanovki", "Uy manzili", "Manzil", "Adres"], 2)
            ser_col = pick_column(df_teq, ["Seriyniy nomer", "Serial", "S/N"], None)

            for _, row in df_teq.iterrows():
                set_name = " ".join(str(row.get(set_col, "") if set_col else "").replace("\xa0", " ").split())
                eq_num = " ".join(str(row.get(num_col, "") if num_col else "").replace("\xa0", " ").split())
                addr = " ".join(str(row.get(addr_col, "") if addr_col else "").replace("\xa0", " ").split())
                serial = " ".join(str(row.get(ser_col, "") if ser_col else "").replace("\xa0", " ").split())

                if set_name.upper() == "JAMI OBYEKTLAR":
                    continue
                if eq_num and eq_num.lower() != "nan":
                    toma_equipment_list.append({
                        "set": set_name if set_name and set_name.lower() != "nan" else "OLT (Tomo)",
                        "number": eq_num,
                        "address": addr if addr and addr.lower() != "nan" else "-",
                        "serial": serial if serial and serial.lower() != "nan" else "-",
                        "montyor": toma_montyor
                    })
        print(f"✅ {toma_eq_file} юкланди: {len(toma_equipment_list)} та (Монтёр: {toma_montyor})")
except Exception as e:
    print(f"❌ Toma OLT файлини ўқишда хатолик: {e}")

# 3c. OLT_Xonkobod_tayyor.xlsx uskunalarini o'qish
try:
    if os.path.exists(EXCEL_XONKOBOD_EQUIPMENT):
        xls_xeq = pd.ExcelFile(EXCEL_XONKOBOD_EQUIPMENT)
        for s_name in xls_xeq.sheet_names:
            df_xeq = pd.read_excel(EXCEL_XONKOBOD_EQUIPMENT, sheet_name=s_name)
            for _, row in df_xeq.iterrows():
                set_name = " ".join(str(row.get("Set", "") or "").replace("\xa0", " ").split())
                eq_num = " ".join(str(row.get("Nomer oborud.", "") or "").replace("\xa0", " ").split())
                addr = " ".join(str(row.get("Adres ustanovki", "") or "").replace("\xa0", " ").split())
                serial = " ".join(str(row.get("Seriyniy nomer", "") or "").replace("\xa0", " ").split())

                if eq_num and eq_num.lower() != "nan":
                    xonkobod_equipment_list.append({
                        "set": set_name if set_name and set_name.lower() != "nan" else "OLT Xonkobod",
                        "number": eq_num,
                        "address": addr if addr and addr.lower() != "nan" else "-",
                        "serial": serial if serial and serial.lower() != "nan" else "-",
                        "montyor": xonkobod_montyor
                    })
        print(f"✅ OLT_Xonkobod_tayyor.xlsx юкланди: {len(xonkobod_equipment_list)} та (Монтёр: {xonkobod_montyor})")
except Exception as e:
    print(f"❌ OLT_Xonkobod_tayyor.xlsx файлини ўқишда хатолик: {e}")

# 3d. OLT Yosh kuch.xlsx uskunalarini o'qish
try:
    if os.path.exists(EXCEL_YOSH_KUCH_EQUIPMENT):
        xls_yk = pd.ExcelFile(EXCEL_YOSH_KUCH_EQUIPMENT)
        for s_name in xls_yk.sheet_names:
            df_yk = pd.read_excel(EXCEL_YOSH_KUCH_EQUIPMENT, skiprows=2, sheet_name=s_name)
            for _, row in df_yk.iterrows():
                set_name = " ".join(str(row.get("Set", "") or "").replace("\xa0", " ").split())
                port_code = " ".join(str(row.get("Kod porta", "") or "").replace("\xa0", " ").split())
                street = " ".join(str(row.get("Ko‘cha", "") or row.get("Ko'cha", "") or "").replace("\xa0", " ").split())
                addr = " ".join(str(row.get("Adres ustanovki", "") or "").replace("\xa0", " ").split())

                if set_name.upper() == "JAMI OBYEKTLAR":
                    continue
                if port_code and port_code.lower() != "nan":
                    yosh_kuch_equipment_list.append({
                        "set": set_name if set_name and set_name.lower() != "nan" else "OLT Yosh kuch",
                        "number": port_code,
                        "street": street if street and street.lower() != "nan" else "-",
                        "address": addr if addr and addr.lower() != "nan" else "-",
                        "montyor": yosh_kuch_montyor
                    })
        print(f"✅ OLT Yosh kuch.xlsx юкланди: {len(yosh_kuch_equipment_list)} та (Монтёр: {yosh_kuch_montyor})")
except Exception as e:
    print(f"❌ OLT Yosh kuch.xlsx файлини ўқишда хатолик: {e}")

# 3e. Navoi uskunalarini o'qish
try:
    nav_eq_file = next((f for f in EXCEL_NAVVOI_EQUIPMENT_CANDIDATES if os.path.exists(f)), None)
    if nav_eq_file:
        navoi_source_file = nav_eq_file
        xls_nav = pd.ExcelFile(nav_eq_file)
        for s_name in xls_nav.sheet_names:
            df_nav = pd.read_excel(nav_eq_file, sheet_name=s_name)
            code_col = pick_column(df_nav, ["Kod / Port", "Kod porta", "Nomer oborud.", "Kod"], 0)
            rep_col = pick_column(df_nav, ["Kod / Port (Takror)", "Takror"], None)
            hudud_col = pick_column(df_nav, ["Set / Hudud", "Set", "Hudud"], 2)
            addr_col = pick_column(df_nav, ["Uy manzili", "Adres ustanovki", "Manzil", "Adres"], 3)

            for _, row in df_nav.iterrows():
                code_port = " ".join(str(row.get(code_col, "") if code_col else "").replace("\xa0", " ").split())
                repeat_code = " ".join(str(row.get(rep_col, "") if rep_col else "").replace("\xa0", " ").split())
                hudud = " ".join(str(row.get(hudud_col, "") if hudud_col else "").replace("\xa0", " ").split())
                addr = " ".join(str(row.get(addr_col, "") if addr_col else "").replace("\xa0", " ").split())

                if code_port.upper() == "JAMI OBYEKTLAR":
                    continue
                if code_port and code_port.lower() != "nan":
                    navoi_equipment_list.append({
                        "set": hudud if hudud and hudud.lower() != "nan" else "(Navoi)",
                        "number": code_port,
                        "repeat_code": repeat_code if repeat_code and repeat_code.lower() != "nan" else "-",
                        "address": addr if addr and addr.lower() != "nan" else "-",
                        "montyor": navoi_montyor
                    })
        print(f"✅ {nav_eq_file} юкланди: {len(navoi_equipment_list)} та (Монтёр: {navoi_montyor})")
except Exception as e:
    print(f"❌ Navoi файлини ўқишда хатолик: {e}")

# 3f. Markaz 2.xlsx ma'lumotlarini o'qish
try:
    if os.path.exists(EXCEL_MARKAZ2):
        xls_m2 = pd.ExcelFile(EXCEL_MARKAZ2)
        m2_sheets = {name.strip(): name for name in xls_m2.sheet_names}

        if "Markaz 2 splitter" in m2_sheets:
            df_m2_sp = pd.read_excel(EXCEL_MARKAZ2, sheet_name=m2_sheets["Markaz 2 splitter"])
            markaz2_olt_list, markaz2_splitters_order, markaz2_by_splitter, _ = parse_olt_sheet(
                df_m2_sp, default_montyor=markaz2_montyor
            )
            for p in markaz2_olt_list:
                p["montyor"] = markaz2_montyor
            print(f"✅ Markaz 2 splitter юкланди: {len(markaz2_splitters_order)} та сплиттер, {len(markaz2_olt_list)} та порт (Монтёр: {markaz2_montyor})")

        if "Markaz 2" in m2_sheets:
            df_m2_main = pd.read_excel(EXCEL_MARKAZ2, sheet_name=m2_sheets["Markaz 2"])
            for _, row in df_m2_main.iterrows():
                set_val = " ".join(str(row.get("Set", "") or "").replace("\xa0", " ").split())
                sp_single = " ".join(str(row.get("Splitter (Bittadan)", "") or "").replace("\xa0", " ").split())
                orks_os = " ".join(str(row.get("ORKS / OS", "") or "").replace("\xa0", " ").split())
                sp_ur = " ".join(str(row.get("Splitter-UR", "") or "").replace("\xa0", " ").split())
                port_1xn = " ".join(str(row.get("Port / 1xN", "") or "").replace("\xa0", " ").split())
                addr_val = " ".join(str(row.get("Uy manzili", "") or "").replace("\xa0", " ").split())

                if any(v and v.lower() != "nan" for v in (sp_single, orks_os, sp_ur, port_1xn, addr_val)):
                    markaz2_scheme_list.append({
                        "set": set_val if set_val and set_val.lower() != "nan" else "Markaz 2",
                        "splitter_single": sp_single if sp_single and sp_single.lower() != "nan" else "-",
                        "orks_os": orks_os if orks_os and orks_os.lower() != "nan" else "-",
                        "splitter_ur": sp_ur if sp_ur and sp_ur.lower() != "nan" else "-",
                        "port_1xn": port_1xn if port_1xn and port_1xn.lower() != "nan" else "-",
                        "address": addr_val if addr_val and addr_val.lower() != "nan" else "-",
                    })
            print(f"✅ Markaz 2 схемаси юкланди: {len(markaz2_scheme_list)} та ёзув")
except Exception as e:
    print(f"❌ Markaz 2.xlsx файлини ўқишда хатолик: {e}")

# 3g. Durvadik.xlsx ma'lumotlarini o'qish
try:
    if os.path.exists(EXCEL_DURVADIK):
        xls_durv = pd.ExcelFile(EXCEL_DURVADIK)
        for s_name in xls_durv.sheet_names:
            df_durv = pd.read_excel(EXCEL_DURVADIK, sheet_name=s_name)
            tr_col = pick_column(df_durv, ["T/r", "№", "Nomer"], 0)
            set_col = pick_column(df_durv, ["Set", "Hudud"], 1)
            sp_col = pick_column(df_durv, ["Splitter (Bittadan)", "Splitter", "Spllikter", "Kod / Port"], 2)
            addr_col = pick_column(df_durv, ["Uy manzili", "Manzil", "Adres ustanovki"], 3)

            for _, row in df_durv.iterrows():
                tr_raw = row.get(tr_col) if tr_col else None
                tr_val = "-"
                if pd.notna(tr_raw) and str(tr_raw).strip() and str(tr_raw).strip().lower() != "nan":
                    try:
                        tr_val = str(int(float(tr_raw)))
                    except (ValueError, TypeError):
                        tr_val = " ".join(str(tr_raw).replace("\xa0", " ").split())

                set_val = " ".join(str(row.get(set_col, "") if set_col else "").replace("\xa0", " ").split())
                sp_val = " ".join(str(row.get(sp_col, "") if sp_col else "").replace("\xa0", " ").split())
                addr_val = " ".join(str(row.get(addr_col, "") if addr_col else "").replace("\xa0", " ").split())

                if sp_val and sp_val.lower() != "nan":
                    durvadik_list.append({
                        "tr": tr_val,
                        "set": set_val if set_val and set_val.lower() != "nan" else "(Durvadik)",
                        "number": sp_val,
                        "address": addr_val if addr_val and addr_val.lower() != "nan" else "-",
                        "montyor": durvadik_montyor
                    })
        print(f"✅ Durvadik.xlsx юкланди: {len(durvadik_list)} та (Монтёр: {durvadik_montyor})")
except Exception as e:
    print(f"❌ Durvadik.xlsx файлини ўқишда хатолик: {e}")

# 3h. OLT Paxtakor ma'lumotlarini o'qish ("OLT Paxtakor" va "Splitter" varaqlari)
try:
    paxt_eq_file = next((f for f in EXCEL_PAXTAKOR_CANDIDATES if os.path.exists(f)), None)
    if paxt_eq_file:
        paxtakor_source_file = paxt_eq_file
        xls_paxt = pd.ExcelFile(paxt_eq_file)
        paxt_sheets = {name.strip().lower(): name for name in xls_paxt.sheet_names}

        if "splitter" in paxt_sheets:
            df_paxt_sp = pd.read_excel(paxt_eq_file, sheet_name=paxt_sheets["splitter"])
            paxtakor_olt_list, paxtakor_splitters_order, paxtakor_by_splitter, _ = parse_olt_sheet(
                df_paxt_sp, default_montyor=paxtakor_montyor
            )
            for p in paxtakor_olt_list:
                p["montyor"] = paxtakor_montyor
            print(
                f"✅ {paxt_eq_file} [Splitter] юкланди: {len(paxtakor_splitters_order)} та сплиттер, "
                f"{len(paxtakor_olt_list)} та порт (Монтёр: {paxtakor_montyor})"
            )

        main_sheet_key = next((k for k in paxt_sheets if k != "splitter"), None)
        if main_sheet_key:
            df_paxt = pd.read_excel(paxt_eq_file, sheet_name=paxt_sheets[main_sheet_key])
            tr_col = pick_column(df_paxt, ["T/r", "№", "Nomer"], 0)
            set_col = pick_column(df_paxt, ["Set", "Hudud"], 1)
            sp_col = pick_column(df_paxt, ["Splitter (Bittadan)", "Splitter", "Spllikter", "Kod / Port"], 2)
            addr_col = pick_column(df_paxt, ["Uy manzili", "Manzil", "Adres ustanovki"], 3)

            for _, row in df_paxt.iterrows():
                tr_raw = row.get(tr_col) if tr_col else None
                tr_val = "-"
                if pd.notna(tr_raw) and str(tr_raw).strip() and str(tr_raw).strip().lower() != "nan":
                    try:
                        tr_val = str(int(float(tr_raw)))
                    except (ValueError, TypeError):
                        tr_val = " ".join(str(tr_raw).replace("\xa0", " ").split())

                set_val = " ".join(str(row.get(set_col, "") if set_col else "").replace("\xa0", " ").split())
                sp_val = " ".join(str(row.get(sp_col, "") if sp_col else "").replace("\xa0", " ").split())
                addr_val = " ".join(str(row.get(addr_col, "") if addr_col else "").replace("\xa0", " ").split())

                if sp_val and sp_val.lower() != "nan":
                    paxtakor_list.append({
                        "tr": tr_val,
                        "set": set_val if set_val and set_val.lower() != "nan" else "OLT Paxtakor",
                        "number": sp_val,
                        "address": addr_val if addr_val and addr_val.lower() != "nan" else "-",
                        "montyor": paxtakor_montyor
                    })
            print(f"✅ {paxt_eq_file} [{paxt_sheets[main_sheet_key]}] юкланди: {len(paxtakor_list)} та")
except Exception as e:
    print(f"❌ OLT Paxtakor файлини ўқишда хатолик: {e}")

ELECTRICIANS_DATA = {
    "elect_1": {"name": "Шоназаров Достон Хайитбоевич", "phone": "+998995054885", "zone": "Хонқа тумани, Марказий МФЙ (OLT Марказ / Марказ2)", "task": "Оптик тармоқларни тортиш, сварка қилиш ва абонентларни улаш."},
    "elect_2": {"name": "Отабоев Рамзиддин Рахматилло угли", "phone": "+998995603938", "zone": "Хонқа тумани, Пахтакор МФЙ", "task": "Бетон столбаларда ишлаш, drop кабель тортиш ва роутерларни созлаш."},
    "elect_3": {"name": "Юсупов Бобур Сапарбой ўғли", "phone": "+998995601312", "zone": "Хонқа тумани, Тинчлик МФЙ (OLT Xonkobod)", "task": "1х16 сплиттерларда сигнални текшириш ва носозликларни бартараф этиш."},
    "elect_4": {"name": "Каримов Илхом Машарипович", "phone": "+998995606399", "zone": "Хонқа тумани, Гулистон МФЙ", "task": "Интернет линияларини таъмирлаш ва абонентлар мурожаатлари билан ишлаш."},
    "elect_6": {"name": "Жуманиёзов Жўшқин Шоназарович", "phone": "+998995608636", "zone": "Хонқа тумани, Бўстон МФЙ", "task": "ZTE ва TP-Link роутерларини созлаш, интернет тармоқларини тест қилиш."},
    "elect_7": {"name": "Атажанов Рустам Комоладдинович", "phone": "+998992797072", "zone": "Хонқа тумани, Истиқлол МФЙ", "task": "Янги абонентларни тармоққа улаш ва шартнома масалалари."},
    "elect_8": {"name": "Каримов Заир Авезметович", "phone": "+998995601310", "zone": "Хонқа тумани, Оқолтин МФЙ", "task": "Столбаларга чиқиш, ҳаво линияларини монтаж қилиш."},
    "elect_9": {"name": "Бабажанов Искандар Сапарбекович", "phone": "+998995603005", "zone": "Хонқа тумани, Қоратепа МФЙ (OLT Пахтакор)", "task": "Магистрал оптик тармоқларга хизмат кўрсатиш."},
    "elect_10": {"name": "Каримов Дониёр Хаджибоевич", "phone": "+998995603171", "zone": "Хонқа тумани, Шихрезван МФЙ", "task": "Абонентлар уйига интернет кабелларини тортиш ва улаш."},
    "elect_11": {"name": "Жуманиёзов Руслан Рустамович", "phone": "+998995603937", "zone": "Хонқа тумани (Tayanch OLT / TOMA OLT / OLT Дурвадик)", "task": "Техник ёрдам, тармоқ мониторинги, OSS портал ва бот бошқаруви."},
    "elect_12": {"name": "Саидов Хушнуд Матяқубович", "phone": "+998992797071", "zone": "Хонқа тумани, Ҳаётобод МФЙ", "task": "Оптик сварка ишлари ва таъмирлаш."},
    "elect_13": {"name": "Жаббаров Хамдам Рустамович", "phone": "+998995603936", "zone": "Хонқа тумани, Сарқипчоқ МФЙ (OLT Марказ2)", "task": "Авария ҳолатларини бартараф этиш ва тушган аризалар билан ишлаш."},
    "elect_14": {"name": "Хаитов Хаитбай Шоназарович", "phone": "+998995603934", "zone": "Хонқа тумани, Қипчоқ МФЙ", "task": "Интернет тармоқларини кенгайтириш ва янги нуқталарни улаш."},
    "elect_15": {"name": "Саидов Умарбек Шавкатович", "phone": "+998995603002", "zone": "Хонқа тумани, Заркент МФЙ", "task": "Сплиттерлар ва тақсимот қутиларини назорат қилиш."},
    "elect_16": {"name": "Эгамов Азизбек Озод угли", "phone": "+998977929525", "zone": "Хонқа тумани, Чармгар МФЙ", "task": "Абонент моделларини созлаш ва техник ёрдам кўрсатиш."},
    "elect_17": {"name": "Якубов Жасурбек Ахмеджонович", "phone": "+998995606787", "zone": "Хонқа тумани, Янги ҳаёт МФЙ", "task": "Оптик кабель узилишларини тезкор бартараф этиш."},
    "elect_18": {"name": "Машарипов Али Валиевич", "phone": "+998995603931", "zone": "Хонқа тумани, Дўстлик МФЙ (OLT Навои)", "task": "Тармоқ қурилмаларини ўрнатиш ва созлаш."},
    "elect_19": {"name": "Ваисов Рустам Юсуфбоевич", "phone": "+998995603935", "zone": "Хонқа тумани, Меҳнатобод МФЙ", "task": "Абонентларга сифатли интернет улаш ва линияларни текшириш."},
    "elect_20": {"name": "Юлдошов Кадамбой Атабоевич", "phone": "+998995603007", "zone": "Хонқа тумани, Олмазор МФЙ (OLT Yosh kuch)", "task": "Электр ва оптик тармоқларда профилактика ишлари."},
}


def build_main_keyboard() -> ReplyKeyboardMarkup:
    rows = [
        [
            KeyboardButton(text="🌐 Интернет тарифлари"),
            KeyboardButton(text="🔍 Абонент қидириш")
        ],
        [
            KeyboardButton(text="🔌 Tayanch OLT"),
            KeyboardButton(text="📡 TOMA")
        ],
        [
            KeyboardButton(text="👷 Электрамонтёрлар")
        ]
    ]
    for i in range(0, len(EXTRA_OLT_NAMES), 2):
        pair = [KeyboardButton(text=f"🏢 OLT {EXTRA_OLT_NAMES[i]}")]
        if i + 1 < len(EXTRA_OLT_NAMES):
            pair.append(KeyboardButton(text=f"🏢 OLT {EXTRA_OLT_NAMES[i + 1]}"))
        rows.append(pair)
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


keyboard = build_main_keyboard()
EXTRA_OLT_BUTTON_MAP = {f"🏢 OLT {name}": name for name in EXTRA_OLT_NAMES}


def build_electricians_keyboard() -> InlineKeyboardMarkup:
    rows = []
    for key, info in ELECTRICIANS_DATA.items():
        rows.append([InlineKeyboardButton(text=f"👷 {info['name']}", callback_data=key)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


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


def format_splitter_ports_text(splitter_name: str, by_splitter: dict[str, list[dict]], montyor: str = "", olt_label: str = "") -> str:
    ports = by_splitter.get(splitter_name, [])
    busy_cnt = sum(1 for p in ports if p["client"] != "Бўш порт")
    free_cnt = len(ports) - busy_cnt

    lines = [f"🔌 <b>{html.quote(splitter_name)}</b>"]
    if ports:
        sample_m = detect_montyor_by_address_and_splitter(
            ports[0].get("address", ""), splitter_name, olt_label, montyor
        )
        if sample_m:
            lines.append(f"👷 Участка монтёри: <b>{html.quote(sample_m)}</b>")
    elif montyor:
        lines.append(f"👷 Участка монтёри: <b>{html.quote(montyor)}</b>")
    lines.append(f"📊 Портлар: <b>{busy_cnt} банд</b> / <b>{free_cnt} бўш</b> (Жами: {len(ports)} та)\n")

    for p in ports:
        if p["client"] == "Бўш порт":
            lines.append(f"<b>{html.quote(p['port'])}-порт:</b> ⚪ <i>Бўш порт</i>")
        else:
            extra = []
            if p["ip_phone"] != "-":
                extra.append(f"IP-тел: {html.quote(p['ip_phone'])}")
            if p["ip"] != "-":
                extra.append(f"IP: <code>{html.quote(p['ip'])}</code>")
            extra_str = f" | {' | '.join(extra)}" if extra else ""

            lines.append(
                f"<b>{html.quote(p['port'])}-порт:</b> 🟢 <b>{html.quote(p['client'])}</b>\n"
                f"   🔑 Логин: <code>{html.quote(p['login'])}</code> | 📞 Тел: {html.quote(p['phone'])}{extra_str}\n"
                f"   🏠 Манзил: {html.quote(p['address'])}"
            )

    return "\n".join(lines)


def build_toma_eq_page_keyboard(page: int, page_size: int = 15) -> InlineKeyboardMarkup:
    total_items = len(toma_equipment_list)
    total_pages = max(1, math.ceil(total_items / page_size))
    page = max(0, min(page, total_pages - 1))

    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️ Олдинги", callback_data=f"tomaeq_pg_{page - 1}"))
    nav_row.append(InlineKeyboardButton(text=f"📄 {page + 1}/{total_pages}", callback_data="tomaeq_noop"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton(text="Кейинги ➡️", callback_data=f"tomaeq_pg_{page + 1}"))

    return InlineKeyboardMarkup(inline_keyboard=[nav_row])


def format_toma_eq_page_text(page: int, page_size: int = 15) -> tuple[str, int]:
    total_items = len(toma_equipment_list)
    total_pages = max(1, math.ceil(total_items / page_size))
    page = max(0, min(page, total_pages - 1))

    start_idx = page * page_size
    end_idx = min(start_idx + page_size, total_items)

    lines = [
        f"📡 <b>TOMA OLT ускуналари</b> (Жами: <b>{total_items} та</b> | Саҳифа {page + 1}/{total_pages})\n"
        f"👷 Электромонтёр: <b>{html.quote(toma_montyor)}</b>\n"
    ]
    for item in toma_equipment_list[start_idx:end_idx]:
        serial_part = f" | 🔢 S/N: <code>{html.quote(item['serial'])}</code>" if item["serial"] != "-" else ""
        lines.append(
            f"• <b>{html.quote(item['number'])}</b> ({html.quote(item['set'])})\n"
            f"  🏠 {html.quote(item['address'])}{serial_part}"
        )
    return "\n".join(lines), page


def build_xonkobod_page_keyboard(page: int, page_size: int = 15) -> InlineKeyboardMarkup:
    total_items = len(xonkobod_equipment_list)
    total_pages = max(1, math.ceil(total_items / page_size))
    page = max(0, min(page, total_pages - 1))

    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️ Олдинги", callback_data=f"xonk_pg_{page - 1}"))
    nav_row.append(InlineKeyboardButton(text=f"📄 {page + 1}/{total_pages}", callback_data="xonk_noop"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton(text="Кейинги ➡️", callback_data=f"xonk_pg_{page + 1}"))

    return InlineKeyboardMarkup(inline_keyboard=[nav_row])


def format_xonkobod_page_text(page: int, page_size: int = 15) -> tuple[str, int]:
    total_items = len(xonkobod_equipment_list)
    total_pages = max(1, math.ceil(total_items / page_size))
    page = max(0, min(page, total_pages - 1))

    start_idx = page * page_size
    end_idx = min(start_idx + page_size, total_items)

    lines = [
        f"📡 <b>OLT Xonkobod ускуналари</b> (Жами: <b>{total_items} та</b> | Саҳифа {page + 1}/{total_pages})\n"
        f"👷 Электромонтёр: <b>{html.quote(xonkobod_montyor)}</b>\n"
    ]
    for item in xonkobod_equipment_list[start_idx:end_idx]:
        lines.append(
            f"• <b>{html.quote(item['number'])}</b> ({html.quote(item['set'])})\n"
            f"  🏠 {html.quote(item['address'])}"
        )
    return "\n".join(lines), page


def build_yosh_kuch_page_keyboard(page: int, page_size: int = 15) -> InlineKeyboardMarkup:
    total_items = len(yosh_kuch_equipment_list)
    total_pages = max(1, math.ceil(total_items / page_size))
    page = max(0, min(page, total_pages - 1))

    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️ Олдинги", callback_data=f"yk_pg_{page - 1}"))
    nav_row.append(InlineKeyboardButton(text=f"📄 {page + 1}/{total_pages}", callback_data="yk_noop"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton(text="Кейинги ➡️", callback_data=f"yk_pg_{page + 1}"))

    return InlineKeyboardMarkup(inline_keyboard=[nav_row])


def format_yosh_kuch_page_text(page: int, page_size: int = 15) -> tuple[str, int]:
    total_items = len(yosh_kuch_equipment_list)
    total_pages = max(1, math.ceil(total_items / page_size))
    page = max(0, min(page, total_pages - 1))

    start_idx = page * page_size
    end_idx = min(start_idx + page_size, total_items)

    lines = [
        f"📡 <b>OLT Yosh kuch объектлари</b> (Жами: <b>{total_items} та</b> | Саҳифа {page + 1}/{total_pages})\n"
        f"👷 Электромонтёр: <b>{html.quote(yosh_kuch_montyor)}</b>\n"
    ]
    for item in yosh_kuch_equipment_list[start_idx:end_idx]:
        lines.append(
            f"• <b>{html.quote(item['number'])}</b> ({html.quote(item['set'])})\n"
            f"  🏠 {html.quote(item['address'])}"
        )
    return "\n".join(lines), page


def build_navoi_page_keyboard(page: int, page_size: int = 15) -> InlineKeyboardMarkup:
    total_items = len(navoi_equipment_list)
    total_pages = max(1, math.ceil(total_items / page_size))
    page = max(0, min(page, total_pages - 1))

    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️ Олдинги", callback_data=f"nav_pg_{page - 1}"))
    nav_row.append(InlineKeyboardButton(text=f"📄 {page + 1}/{total_pages}", callback_data="nav_noop"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton(text="Кейинги ➡️", callback_data=f"nav_pg_{page + 1}"))

    return InlineKeyboardMarkup(inline_keyboard=[nav_row])


def format_navoi_page_text(page: int, page_size: int = 15) -> tuple[str, int]:
    total_items = len(navoi_equipment_list)
    total_pages = max(1, math.ceil(total_items / page_size))
    page = max(0, min(page, total_pages - 1))

    start_idx = page * page_size
    end_idx = min(start_idx + page_size, total_items)

    lines = [
        f"📡 <b>OLT Навои объектлари</b> (Жами: <b>{total_items} та</b> | Саҳифа {page + 1}/{total_pages})\n"
        f"👷 Электромонтёр: <b>{html.quote(navoi_montyor)}</b>\n"
    ]
    for item in navoi_equipment_list[start_idx:end_idx]:
        rep_part = f" (<code>{html.quote(item['repeat_code'])}</code>)" if item.get("repeat_code") and item["repeat_code"] != "-" else ""
        lines.append(
            f"• <b>{html.quote(item['number'])}</b>{rep_part} {html.quote(item['set'])}\n"
            f"  🏠 {html.quote(item['address'])}"
        )
    return "\n".join(lines), page


def build_durvadik_page_keyboard(page: int, page_size: int = 15) -> InlineKeyboardMarkup:
    total_items = len(durvadik_list)
    total_pages = max(1, math.ceil(total_items / page_size))
    page = max(0, min(page, total_pages - 1))

    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️ Олдинги", callback_data=f"durv_pg_{page - 1}"))
    nav_row.append(InlineKeyboardButton(text=f"📄 {page + 1}/{total_pages}", callback_data="durv_noop"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton(text="Кейинги ➡️", callback_data=f"durv_pg_{page + 1}"))

    return InlineKeyboardMarkup(inline_keyboard=[nav_row])


def format_durvadik_page_text(page: int, page_size: int = 15) -> tuple[str, int]:
    total_items = len(durvadik_list)
    total_pages = max(1, math.ceil(total_items / page_size))
    page = max(0, min(page, total_pages - 1))

    start_idx = page * page_size
    end_idx = min(start_idx + page_size, total_items)

    lines = [
        f"🏢 <b>OLT Дурвадик</b> (Жами: <b>{total_items} та</b> | Саҳифа {page + 1}/{total_pages})\n"
        f"👷 Электромонтёр: <b>{html.quote(durvadik_montyor)}</b>\n"
    ]
    for item in durvadik_list[start_idx:end_idx]:
        tr_part = f" [T/r: {html.quote(item['tr'])}]" if item.get("tr") and item["tr"] != "-" else ""
        lines.append(
            f"• <b>{html.quote(item['number'])}</b>{tr_part} {html.quote(item['set'])}\n"
            f"  🏠 {html.quote(item['address'])}"
        )
    return "\n".join(lines), page


def build_paxtakor_page_keyboard(page: int, page_size: int = 15) -> InlineKeyboardMarkup:
    total_items = len(paxtakor_list)
    total_pages = max(1, math.ceil(total_items / page_size))
    page = max(0, min(page, total_pages - 1))

    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️ Олдинги", callback_data=f"paxt_pg_{page - 1}"))
    nav_row.append(InlineKeyboardButton(text=f"📄 {page + 1}/{total_pages}", callback_data="paxt_noop"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton(text="Кейинги ➡️", callback_data=f"paxt_pg_{page + 1}"))

    return InlineKeyboardMarkup(inline_keyboard=[nav_row])


def format_paxtakor_page_text(page: int, page_size: int = 15) -> tuple[str, int]:
    total_items = len(paxtakor_list)
    total_pages = max(1, math.ceil(total_items / page_size))
    page = max(0, min(page, total_pages - 1))

    start_idx = page * page_size
    end_idx = min(start_idx + page_size, total_items)

    lines = [
        f"🏢 <b>OLT Пахтакор</b> (Жами: <b>{total_items} та</b> | Саҳифа {page + 1}/{total_pages})\n"
        f"👷 Электромонтёр: <b>{html.quote(paxtakor_montyor)}</b>\n"
    ]
    for item in paxtakor_list[start_idx:end_idx]:
        tr_part = f" [T/r: {html.quote(item['tr'])}]" if item.get("tr") and item["tr"] != "-" else ""
        lines.append(
            f"• <b>{html.quote(item['number'])}</b>{tr_part} {html.quote(item['set'])}\n"
            f"  🏠 {html.quote(item['address'])}"
        )
    return "\n".join(lines), page


def format_extra_olt_summary(olt_name: str) -> str:
    kw = olt_name.lower().strip()
    matched_ports = [
        p for p in (tayanch_olt_list + toma_olt_list + markaz2_olt_list + paxtakor_olt_list)
        if kw in f"{p['splitter']} {p['client']} {p['login']} {p['address']} {p.get('montyor', '')}".lower()
    ]
    matched_splitters = [
        s for s in splitters_list
        if kw in f"{s['number']} {s['splitter']} {s['model']} {s['address']} {s['town']} {s['real_sn']}".lower()
    ]
    matched_xonkobod = [
        e for e in xonkobod_equipment_list
        if kw in ("хонкобод", "xonkobod")
        or kw in f"{e['set']} {e['number']} {e['address']} {e['serial']} {e.get('montyor', '')}".lower()
    ]
    matched_yosh_kuch = [
        e for e in yosh_kuch_equipment_list
        if kw in ("ёш куч", "yosh kuch", "yoshkuch")
        or kw in f"{e['set']} {e['number']} {e.get('street', '')} {e['address']} {e.get('montyor', '')}".lower()
    ]
    matched_navoi = [
        e for e in navoi_equipment_list
        if kw in ("навои", "navoi", "навхос", "navxos")
        or kw in f"{e['set']} {e['number']} {e.get('repeat_code', '')} {e['address']} {e.get('montyor', '')}".lower()
    ]
    matched_durvadik = [
        e for e in durvadik_list
        if kw in ("дурвадик", "durvadik")
        or kw in f"{e['set']} {e['number']} {e['address']} {e.get('montyor', '')}".lower()
    ]
    matched_paxtakor = [
        e for e in paxtakor_list
        if kw in ("пахтакор", "paxtakor")
        or kw in f"{e['set']} {e['number']} {e['address']} {e.get('montyor', '')}".lower()
    ]

    lines = [f"🏢 <b>OLT: {html.quote(olt_name)}</b>"]
    if matched_ports:
        lines.append(f"🔌 OLT портларда топилди: <b>{len(matched_ports)} та</b>\n")
        for item in matched_ports[:8]:
            m_name = detect_montyor_by_address_and_splitter(
                item.get("address", ""), item.get("splitter", ""), olt_name, item.get("montyor", "")
            )
            mont_str = f" | 👷 {html.quote(m_name)}" if m_name else ""
            lines.append(
                f"🏷 <b>{html.quote(item['splitter'])}</b> (Порт: {html.quote(item['port'])}) — <b>{html.quote(item['client'])}</b>{mont_str}\n"
                f"   🔑 Логин: <code>{html.quote(item['login'])}</code> | 📞 Тел: {html.quote(item['phone'])}\n"
                f"   🏠 Манзил: {html.quote(item['address'])}"
            )
    if matched_splitters:
        lines.append(f"\n⚡ Сплиттерлар базасида топилди: <b>{len(matched_splitters)} та</b>\n")
        for s in matched_splitters[:5]:
            lines.append(
                f"📍 <b>{html.quote(s['town'])}</b> — <b>{html.quote(s['number'])}</b> ({html.quote(s['splitter'])} / {html.quote(s['model'])})\n"
                f"   🏠 Манзил: {html.quote(s['address'])} | S/N: <code>{html.quote(s['real_sn'])}</code>"
            )

    if matched_xonkobod and kw not in ("хонкобод", "xonkobod"):
        lines.append(
            f"\n📡 <b>OLT Xonkobod ускуналарида ({len(matched_xonkobod)} та)</b> "
            f"| 👷 Монтёр: <b>{html.quote(xonkobod_montyor)}</b>:\n"
        )
        for e in matched_xonkobod[:8]:
            lines.append(
                f"• <b>{html.quote(e['number'])}</b> ({html.quote(e['set'])})\n"
                f"  🏠 {html.quote(e['address'])}"
            )

    if matched_yosh_kuch and kw not in ("ёш куч", "yosh kuch", "yoshkuch"):
        lines.append(
            f"\n📡 <b>OLT Yosh kuch объектларида ({len(matched_yosh_kuch)} та)</b> "
            f"| 👷 Монтёр: <b>{html.quote(yosh_kuch_montyor)}</b>:\n"
        )
        for e in matched_yosh_kuch[:8]:
            lines.append(
                f"• <b>{html.quote(e['number'])}</b> ({html.quote(e['set'])})\n"
                f"  🏠 {html.quote(e['address'])}"
            )

    if matched_navoi and kw not in ("навои", "navoi"):
        lines.append(
            f"\n📡 <b>OLT Навои объектларида ({len(matched_navoi)} та)</b> "
            f"| 👷 Монтёр: <b>{html.quote(navoi_montyor)}</b>:\n"
        )
        for e in matched_navoi[:8]:
            lines.append(
                f"• <b>{html.quote(e['number'])}</b> {html.quote(e['set'])}\n"
                f"  🏠 {html.quote(e['address'])}"
            )

    if matched_durvadik and kw not in ("дурвадик", "durvadik"):
        lines.append(
            f"\n📡 <b>OLT Дурвадик объектларида ({len(matched_durvadik)} та)</b> "
            f"| 👷 Монтёр: <b>{html.quote(durvadik_montyor)}</b>:\n"
        )
        for e in matched_durvadik[:8]:
            lines.append(
                f"• <b>{html.quote(e['number'])}</b> {html.quote(e['set'])}\n"
                f"  🏠 {html.quote(e['address'])}"
            )

    if matched_paxtakor and kw not in ("пахтакор", "paxtakor"):
        lines.append(
            f"\n📡 <b>OLT Пахтакор объектларида ({len(matched_paxtakor)} та)</b> "
            f"| 👷 Монтёр: <b>{html.quote(paxtakor_montyor)}</b>:\n"
        )
        for e in matched_paxtakor[:8]:
            lines.append(
                f"• <b>{html.quote(e['number'])}</b> {html.quote(e['set'])}\n"
                f"  🏠 {html.quote(e['address'])}"
            )

    if (
        not matched_ports
        and not matched_splitters
        and not matched_xonkobod
        and not matched_yosh_kuch
        and not matched_navoi
        and not matched_durvadik
        and not matched_paxtakor
    ):
        lines.append("ℹ️ Базада ҳозирча бу OLT бўйича ёзув топилмади (тугма фаол).")

    return "\n".join(lines)


def search_all_databases(query: str) -> str:
    q = query.lower().strip()
    if len(q) < 2:
        return "⚠️ Абонент қидириш учун камида 2 та белги киритинг."

    # 1. OLT portlaridan faqat band abonentlar bo'yicha qidirish
    olt_sources = [
        ("Tayanch OLT", tayanch_olt_list, tayanch_montyor),
        ("TOMA OLT", toma_olt_list, toma_montyor),
        ("OLT Марказ2", markaz2_olt_list, markaz2_montyor),
        ("OLT Пахтакор", paxtakor_olt_list, paxtakor_montyor),
    ]

    olt_hits = []
    for olt_label, port_list, default_mont in olt_sources:
        for p in port_list:
            if p["client"] == "Бўш порт":
                continue
            mont_name = detect_montyor_by_address_and_splitter(
                p.get("address", ""), p.get("splitter", ""), olt_label, default_mont
            )
            haystack = (
                f"{p['client']} {p['login']} {p['phone']} {p['ip_phone']} {p['ip']} "
                f"{p['address']} {p['splitter']} {olt_label} {mont_name}"
            ).lower()
            if q in haystack:
                item_copy = dict(p)
                item_copy["olt_zone"] = olt_label
                item_copy["montyor_display"] = mont_name
                olt_hits.append(item_copy)

    # 2. Abonentlar bazasidan qidirish + OLT / montyor hududini aniqlash
    sub_hits = []
    for s in subscribers_list:
        haystack = f"{s['client']} {s['login']} {s['phone']} {s['msisdn']} {s['address']}".lower()
        if q in haystack:
            addr_low = s["address"].lower()
            matched_zones = []

            for p in olt_hits:
                if p["login"] != "-" and p["login"].lower() == s["login"].lower():
                    matched_zones.append(f"{p['olt_zone']} — {p['montyor_display']}")

            if any(k in addr_low for k in ("paxtakor", "пахтакор", "қирқёп", "qirqyop", "сарапоён", "sarapoyon")):
                matched_zones.append(f"OLT Пахтакор — {paxtakor_montyor}")
            if any(k in addr_low for k in ("xonkobod", "хонкобод", "тинчлик", "tinchlik")):
                matched_zones.append(f"OLT Xonkobod — {xonkobod_montyor}")
            if any(k in addr_low for k in ("ёш куч", "yosh kuch", "yoshkuch", "олмазор", "olmazor")):
                matched_zones.append(f"OLT Yosh kuch — {yosh_kuch_montyor}")
            if any(k in addr_low for k in ("навои", "navoi", "навхос", "navxos", "дўстлик", "do'stlik")):
                matched_zones.append(f"OLT Навои — {navoi_montyor}")
            if any(k in addr_low for k in ("дурвадик", "durvadik", "сарқипчоқ", "sarqipchoq", "мадир", "madir")):
                matched_zones.append(f"OLT Дурвадик — {durvadik_montyor}")

            unique_zones = list(dict.fromkeys(matched_zones))
            sub_copy = dict(s)
            sub_copy["zone_info"] = ", ".join(unique_zones) if unique_zones else f"Хонқа тумани — {tayanch_montyor}"
            sub_hits.append(sub_copy)

    if not olt_hits and not sub_hits:
        return f"❌ <b>«{html.quote(query)}»</b> бўйича абонент топилмади."

    out = [f"🔎 <b>Абонент қидируви натижалари («{html.quote(query)}»):</b>"]

    if olt_hits:
        out.append(f"\n🔌 <b>OLT абонентларида ({len(olt_hits)} та):</b>")
        for p in olt_hits[:10]:
            extra = []
            if p["ip_phone"] != "-":
                extra.append(f"IP-тел: {html.quote(p['ip_phone'])}")
            if p["ip"] != "-":
                extra.append(f"IP: <code>{html.quote(p['ip'])}</code>")
            extra_str = f" | {' | '.join(extra)}" if extra else ""

            out.append(
                f"• <b>{html.quote(p['client'])}</b> ({html.quote(p['splitter'])} — {html.quote(p['port'])}-порт)\n"
                f"  📍 Ҳудуд: <b>{html.quote(p['olt_zone'])}</b> | 👷 Монтёр: <b>{html.quote(p['montyor_display'])}</b>\n"
                f"  🔑 <code>{html.quote(p['login'])}</code> | 📞 Тел: {html.quote(p['phone'])}{extra_str}\n"
                f"  🏠 Манзил: {html.quote(p['address'])}"
            )

    if sub_hits:
        out.append(f"\n👥 <b>Абонентлар базасида ({len(sub_hits)} та):</b>")
        for s in sub_hits[:8]:
            out.append(
                f"• <b>{html.quote(s['client'])}</b> (<code>{html.quote(s['login'])}</code>)\n"
                f"  📍 Ҳудуд ва монтёр: <b>{html.quote(s['zone_info'])}</b>\n"
                f"  📞 Тел: {html.quote(s['phone'])} | Тариф: {html.quote(s['rate_plan'])} | Баланс: {html.quote(s['balance'])}\n"
                f"  🏠 Манзил: {html.quote(s['address'])}"
            )

    return "\n".join(out)


async def send_long_message(target_msg: Message, text: str, reply_markup=None):
    max_len = 4000
    if len(text) <= max_len:
        await target_msg.answer(text, reply_markup=reply_markup)
        return

    parts = []
    current = ""
    for line in text.split("\n"):
        if len(current) + len(line) + 1 > max_len:
            parts.append(current)
            current = line
        else:
            current = f"{current}\n{line}" if current else line
    if current:
        parts.append(current)

    for i, part in enumerate(parts):
        await target_msg.answer(part, reply_markup=reply_markup if i == len(parts) - 1 else None)


@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "👋 Ассалому алайкум!\n"
        "<b>Хонқа тумани</b> оптик тармоқ, OLT, сплиттер, абонент ва монтёрлар маълумот базаси ботига хуш келибсиз.\n\n"
        "Қуйидаги менюдан керакли бўлимни танланг ёки абонент қидириш учун Ф.И.Ш., логин, телефон ёки манзил ёзинг.",
        reply_markup=keyboard
    )


@dp.message(Command("stats"))
async def cmd_stats(message: Message):
    await message.answer(
        f"📊 <b>База статистикаси:</b>\n"
        f"• Сплиттерлар: <b>{len(splitters_list)} та</b>\n"
        f"• Абонентлар: <b>{len(subscribers_list)} та</b>\n"
        f"• Tayanch OLT сплиттерлар: <b>{len(tayanch_splitters_order)} та</b> ({len(tayanch_olt_list)} порт | Монтёр: <b>{html.quote(tayanch_montyor)}</b>)\n"
        f"• TOMA OLT сплиттерлар: <b>{len(toma_splitters_order)} та</b> ({len(toma_olt_list)} порт | Монтёр: <b>{html.quote(toma_montyor)}</b>)\n"
        f"• TOMA ускуналар ({html.quote(toma_source_file)}): <b>{len(toma_equipment_list)} та</b> (Монтёр: <b>{html.quote(toma_montyor)}</b>)\n"
        f"• OLT Xonkobod ускуналар: <b>{len(xonkobod_equipment_list)} та</b> (Монтёр: <b>{html.quote(xonkobod_montyor)}</b>)\n"
        f"• OLT Yosh kuch объектлар: <b>{len(yosh_kuch_equipment_list)} та</b> (Монтёр: <b>{html.quote(yosh_kuch_montyor)}</b>)\n"
        f"• OLT Навои объектлар ({html.quote(navoi_source_file)}): <b>{len(navoi_equipment_list)} та</b> (Монтёр: <b>{html.quote(navoi_montyor)}</b>)\n"
        f"• OLT Марказ2 сплиттерлар: <b>{len(markaz2_splitters_order)} та</b> ({len(markaz2_olt_list)} порт, {len(markaz2_scheme_list)} схема | Монтёр: <b>{html.quote(markaz2_montyor)}</b>)\n"
        f"• OLT Дурвадик объектлар: <b>{len(durvadik_list)} та</b> (Монтёр: <b>{html.quote(durvadik_montyor)}</b>)\n"
        f"• OLT Пахтакор сплиттерлар: <b>{len(paxtakor_splitters_order)} та</b> ({len(paxtakor_olt_list)} порт, {len(paxtakor_list)} объект | {html.quote(paxtakor_source_file)} | Монтёр: <b>{html.quote(paxtakor_montyor)}</b>)",
        reply_markup=keyboard
    )


@dp.message(F.text == "🌐 Интернет тарифлари")
async def show_tariffs(message: Message):
    await message.answer(
        "🌐 <b>UZTELECOM — Хонқа тумани уй интернети тарифлари:</b>\n\n"
        "⚡ <b>100 Мбит/с</b> — барқарор уй интернети\n"
        "🚀 <b>200 Мбит/с</b> — юқори тезлик ва HD/4K контент\n"
        "💎 <b>1 Гбит/с</b> — максимал тезлик ва кўп қурилмали уйлар учун\n\n"
        "🎁 Уланишда SIM-карта, Wi-Fi 5/6 роутер ва 100 метргача drop кабель имкониятлари мавжуд.\n"
        "📞 Уланиш ва техник ёрдам: <code>+998995603937</code>",
        reply_markup=keyboard
    )


@dp.message(F.text == "🔍 Абонент қидириш")
async def prompt_search(message: Message):
    await message.answer(
        "🔍 <b>Абонент қидириш учун маълумот киритинг:</b>\n"
        "• Абонент Ф.И.Ш. ёки логини\n"
        "• Телефон рақами ёки IP-манзил\n"
        "• Кўча / маҳалла / уй манзили",
        reply_markup=keyboard
    )


@dp.message(F.text == "🔌 Tayanch OLT")
async def show_tayanch_olt(message: Message):
    if not tayanch_splitters_order:
        await message.answer("⚠️ <b>Tayanch OLT</b> маълумотлари топилмади.", reply_markup=keyboard)
        return

    mk = build_olt_page_keyboard(
        splitters_order=tayanch_splitters_order,
        by_splitter=tayanch_by_splitter,
        prefixes=["Tayanch OLT", "Tayanch"],
        cb_prefix="tolt",
        page=0
    )
    await message.answer(
        f"🔌 <b>Tayanch OLT</b> сплиттерлари (Жами: <b>{len(tayanch_splitters_order)} та</b>)\n"
        f"👷 Монтёр: <b>{html.quote(tayanch_montyor)}</b>\n"
        "Сплиттерни танланг:",
        reply_markup=mk
    )


@dp.message(F.text == "📡 TOMA")
async def show_toma_olt(message: Message):
    if not toma_splitters_order and not toma_equipment_list:
        await message.answer("⚠️ <b>TOMA</b> маълумотлари топилмади.", reply_markup=keyboard)
        return

    if toma_splitters_order:
        mk = build_olt_page_keyboard(
            splitters_order=toma_splitters_order,
            by_splitter=toma_by_splitter,
            prefixes=["TOMA OLT", "TOMA", "Tomo"],
            cb_prefix="molt",
            page=0
        )
        await message.answer(
            f"📡 <b>TOMA OLT</b> сплиттерлари (Жами: <b>{len(toma_splitters_order)} та</b>)\n"
            f"👷 Монтёр: <b>{html.quote(toma_montyor)}</b>\n"
            "Сплиттерни танланг:",
            reply_markup=mk
        )
    else:
        text, page = format_toma_eq_page_text(0)
        mk = build_toma_eq_page_keyboard(page)
        await message.answer(text, reply_markup=mk)


@dp.message(F.text == "👷 Электрамонтёрлар")
async def show_electricians(message: Message):
    await message.answer(
        "👷 <b>Хонқа тумани электрамонтёрлари:</b>\nМаълумот олиш учун ходимни танланг:",
        reply_markup=build_electricians_keyboard()
    )


@dp.callback_query(F.data.startswith("elect_"))
async def cb_electrician_detail(callback: CallbackQuery):
    info = ELECTRICIANS_DATA.get(callback.data)
    if not info:
        await callback.answer("Маълумот топилмади", show_alert=True)
        return

    text = (
        f"👷 <b>{html.quote(info['name'])}</b>\n"
        f"📞 Телефон: <code>{html.quote(info['phone'])}</code>\n"
        f"📍 Ҳудуд: {html.quote(info['zone'])}\n"
        f"🛠 Вазифаси: {html.quote(info['task'])}"
    )
    await callback.message.answer(text, reply_markup=build_electricians_keyboard())
    await callback.answer()


@dp.callback_query(F.data.startswith(("tolt_", "molt_", "m2olt_", "pxolt_")))
async def cb_olt_pagination_and_ports(callback: CallbackQuery):
    data = callback.data
    if data.startswith("tolt_"):
        prefix = "tolt"
        sp_order = tayanch_splitters_order
        by_sp = tayanch_by_splitter
        sp_prefixes = ["Tayanch OLT", "Tayanch"]
        montyor = tayanch_montyor
        title = "Tayanch OLT"
    elif data.startswith("molt_"):
        prefix = "molt"
        sp_order = toma_splitters_order
        by_sp = toma_by_splitter
        sp_prefixes = ["TOMA OLT", "TOMA", "Tomo"]
        montyor = toma_montyor
        title = "TOMA OLT"
    elif data.startswith("m2olt_"):
        prefix = "m2olt"
        sp_order = markaz2_splitters_order
        by_sp = markaz2_by_splitter
        sp_prefixes = ["OLT Markaz 2", "Markaz 2", "Markaz"]
        montyor = markaz2_montyor
        title = "OLT Марказ2"
    else:
        prefix = "pxolt"
        sp_order = paxtakor_splitters_order
        by_sp = paxtakor_by_splitter
        sp_prefixes = ["OLT Paxtakor", "Paxtakor"]
        montyor = paxtakor_montyor
        title = "OLT Пахтакор"

    if data.endswith("_noop"):
        await callback.answer()
        return

    parts = data.split("_")
    if len(parts) >= 3 and parts[1] == "pg":
        try:
            page = int(parts[2])
        except ValueError:
            page = 0
        mk = build_olt_page_keyboard(sp_order, by_sp, sp_prefixes, prefix, page)
        await callback.message.edit_reply_markup(reply_markup=mk)
        await callback.answer()
        return

    if len(parts) >= 4 and parts[1] == "sp":
        try:
            sp_idx = int(parts[2])
        except ValueError:
            await callback.answer("Сплиттер индекси нотўғри", show_alert=True)
            return

        if 0 <= sp_idx < len(sp_order):
            sp_name = sp_order[sp_idx]
            formatted = format_splitter_ports_text(sp_name, by_sp, montyor=montyor, olt_label=title)
            await send_long_message(callback.message, formatted)
            await callback.answer()
        else:
            await callback.answer(f"{title} сплиттери топилмади", show_alert=True)
        return

    await callback.answer()


@dp.callback_query(F.data.startswith("tomaeq_"))
async def cb_toma_eq_pagination(callback: CallbackQuery):
    if callback.data == "tomaeq_noop":
        await callback.answer()
        return

    if callback.data.startswith("tomaeq_pg_"):
        try:
            page = int(callback.data.split("_")[2])
        except ValueError:
            page = 0
        text, current_page = format_toma_eq_page_text(page)
        mk = build_toma_eq_page_keyboard(current_page)
        await callback.message.edit_text(text, reply_markup=mk)
        await callback.answer()
        return

    await callback.answer()


@dp.callback_query(F.data.startswith("xonk_"))
async def cb_xonkobod_pagination(callback: CallbackQuery):
    if callback.data == "xonk_noop":
        await callback.answer()
        return

    if callback.data.startswith("xonk_pg_"):
        try:
            page = int(callback.data.split("_")[2])
        except ValueError:
            page = 0
        text, current_page = format_xonkobod_page_text(page)
        mk = build_xonkobod_page_keyboard(current_page)
        await callback.message.edit_text(text, reply_markup=mk)
        await callback.answer()
        return

    await callback.answer()


@dp.callback_query(F.data.startswith("yk_"))
async def cb_yosh_kuch_pagination(callback: CallbackQuery):
    if callback.data == "yk_noop":
        await callback.answer()
        return

    if callback.data.startswith("yk_pg_"):
        try:
            page = int(callback.data.split("_")[2])
        except ValueError:
            page = 0
        text, current_page = format_yosh_kuch_page_text(page)
        mk = build_yosh_kuch_page_keyboard(current_page)
        await callback.message.edit_text(text, reply_markup=mk)
        await callback.answer()
        return

    await callback.answer()


@dp.callback_query(F.data.startswith("nav_"))
async def cb_navoi_pagination(callback: CallbackQuery):
    if callback.data == "nav_noop":
        await callback.answer()
        return

    if callback.data.startswith("nav_pg_"):
        try:
            page = int(callback.data.split("_")[2])
        except ValueError:
            page = 0
        text, current_page = format_navoi_page_text(page)
        mk = build_navoi_page_keyboard(current_page)
        await callback.message.edit_text(text, reply_markup=mk)
        await callback.answer()
        return

    await callback.answer()


@dp.callback_query(F.data.startswith("durv_"))
async def cb_durvadik_pagination(callback: CallbackQuery):
    if callback.data == "durv_noop":
        await callback.answer()
        return

    if callback.data.startswith("durv_pg_"):
        try:
            page = int(callback.data.split("_")[2])
        except ValueError:
            page = 0
        text, current_page = format_durvadik_page_text(page)
        mk = build_durvadik_page_keyboard(current_page)
        await callback.message.edit_text(text, reply_markup=mk)
        await callback.answer()
        return

    await callback.answer()


@dp.callback_query(F.data.startswith("paxt_"))
async def cb_paxtakor_pagination(callback: CallbackQuery):
    if callback.data == "paxt_noop":
        await callback.answer()
        return

    if callback.data.startswith("paxt_pg_"):
        try:
            page = int(callback.data.split("_")[2])
        except ValueError:
            page = 0
        text, current_page = format_paxtakor_page_text(page)
        mk = build_paxtakor_page_keyboard(current_page)
        await callback.message.edit_text(text, reply_markup=mk)
        await callback.answer()
        return

    await callback.answer()


@dp.message(F.text)
async def handle_text(message: Message):
    txt = message.text.strip()

    if txt in EXTRA_OLT_BUTTON_MAP:
        olt_name = EXTRA_OLT_BUTTON_MAP[txt]
        if olt_name.lower() in ("марказ2", "марказ 2", "markaz2", "markaz 2") and markaz2_splitters_order:
            mk = build_olt_page_keyboard(
                splitters_order=markaz2_splitters_order,
                by_splitter=markaz2_by_splitter,
                prefixes=["OLT Markaz 2", "Markaz 2", "Markaz"],
                cb_prefix="m2olt",
                page=0
            )
            await message.answer(
                f"🏢 <b>OLT Марказ2</b> сплиттерлари (Жами: <b>{len(markaz2_splitters_order)} та</b>)\n"
                f"👷 Монтёр: <b>{html.quote(markaz2_montyor)}</b>\n"
                "Сплиттерни танланг:",
                reply_markup=mk
            )
            return

        if olt_name.lower() in ("дурвадик", "durvadik") and durvadik_list:
            text, page = format_durvadik_page_text(0)
            mk = build_durvadik_page_keyboard(page)
            await message.answer(text, reply_markup=mk)
            return

        if olt_name.lower() in ("пахтакор", "paxtakor"):
            if paxtakor_splitters_order:
                mk = build_olt_page_keyboard(
                    splitters_order=paxtakor_splitters_order,
                    by_splitter=paxtakor_by_splitter,
                    prefixes=["OLT Paxtakor", "Paxtakor"],
                    cb_prefix="pxolt",
                    page=0
                )
                await message.answer(
                    f"🏢 <b>OLT Пахтакор</b> сплиттерлари (Жами: <b>{len(paxtakor_splitters_order)} та</b>)\n"
                    f"👷 Монтёр: <b>{html.quote(paxtakor_montyor)}</b>\n"
                    "Сплиттерни танланг:",
                    reply_markup=mk
                )
                return
            if paxtakor_list:
                text, page = format_paxtakor_page_text(0)
                mk = build_paxtakor_page_keyboard(page)
                await message.answer(text, reply_markup=mk)
                return

        if olt_name.lower() in ("хонкобод", "xonkobod") and xonkobod_equipment_list:
            text, page = format_xonkobod_page_text(0)
            mk = build_xonkobod_page_keyboard(page)
            await message.answer(text, reply_markup=mk)
            return

        if olt_name.lower() in ("ёш куч", "yosh kuch", "yoshkuch") and yosh_kuch_equipment_list:
            text, page = format_yosh_kuch_page_text(0)
            mk = build_yosh_kuch_page_keyboard(page)
            await message.answer(text, reply_markup=mk)
            return

        if olt_name.lower() in ("навои", "navoi") and navoi_equipment_list:
            text, page = format_navoi_page_text(0)
            mk = build_navoi_page_keyboard(page)
            await message.answer(text, reply_markup=mk)
            return

        summary = format_extra_olt_summary(olt_name)
        await send_long_message(message, summary, reply_markup=keyboard)
        return

    result = search_all_databases(txt)
    await send_long_message(message, result, reply_markup=keyboard)


async def health_handler(request: web.Request) -> web.Response:
    return web.Response(text="OK")


async def start_web_server():
    app = web.Application()
    app.router.add_get("/", health_handler)
    app.router.add_get("/health", health_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", "8080"))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logging.info(f"🌐 Web health server started on 0.0.0.0:{port}")


async def main():
    await start_web_server()
    bot = Bot(
        token=TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    logging.info("🤖 Telegram bot starting polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("🛑 Bot stopped.")
        sys.exit(0)
