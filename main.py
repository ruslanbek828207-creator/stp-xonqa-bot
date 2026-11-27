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
    "Toma OLT_yangilangan.xlsx",
    "Toma OLT.xlsx",
]
EXCEL_XONKOBOD_EQUIPMENT = "OLT_Xonkobod_tayyor.xlsx"
EXCEL_YOSH_KUCH_EQUIPMENT = "OLT Yosh kuch.xlsx"

MUFTA_FILES = [
    "Shodiyona ko’chasi Mufta.xlsx",
    "А.Қаҳҳор кўчаси 47-уй Муфта.xlsx",
    "Гайрат махалласи Узумзор 59-уй.xlsx",
    "Гулобод Муфта сарапаён.xlsx",
    "Дала шипон Муфма.xlsx",
    "Дўрмон кўчаси, 1 уй.xlsx",
    "Дўстлик кўчаси 23-уй Муфта.xlsx",
    "Жайхун қуёши болалар оромгоҳига олиб борувчи йўл.xlsx",
    "Кутлткадам муфта.xlsx",
    "Қорақош 9-мактаб Наврўз кўчаси дом. 45.xlsx",
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

# Kod ichidagi tayyor muftalar bazasi (qidiruv va OLT ma'lumotlari uchun)
DEFAULT_MUFTALAR_LIST = [
    {
        "title": "Shodiyona ko'chasi Mufta",
        "sheets": ["Shodiyona ko’chasi"],
        "addresses": [
            "Xonqa tumani Istiqlol maxallasi Shodiyona ko’chasi 36-uy",
            "Shodiyona ko’chasi 10-uy",
            "Shodiyona ko’chasi 76-uy",
            "Shodiyona ko’chasi 38-uy"
        ],
        "cables": ["Mavjud FIG-8 Aerial Loose Tube Cable G.652D 8F"],
        "meta": ["Паспорт 2024 йилнинг 29 март куни тузилган"]
    },
    {
        "title": "А.Қаҳҳор кўчаси 47-уй Муфта",
        "sheets": ["Хонқобод махалласи"],
        "addresses": [
            "Хонқа туман Порлоқ махалласи А.Қаҳҳор кўчаси 47-уй",
            "А.Қаҳҳор кўчаси 47-уй"
        ],
        "cables": [
            "FIG-8 Aerial Loose Tube Cable G.652D 6F 6.6*12.7",
            "NXTС8S-8B1.3 138 м"
        ],
        "meta": [
            "Паспорт 2024 йилнинг 02 апрел куни тузилган",
            "№ 1-муфта (переходная), 12.01.2024 йилда пайвандланган"
        ]
    },
    {
        "title": "Ғайрат махалласи Узумзор 59-уй",
        "sheets": ["Гайрат махалласи Узумзор 59-уй"],
        "addresses": [
            "Хонқа туман Гайрат махалласи Узумзор кўчаси 59-уй",
            "Хонқа туман Гайрат махалласи Узумзор кўчаси 96-уй",
            "Умид ниҳоллари кўчаси, 28 уй Қорақош (Ленин) қишлоғи"
        ],
        "cables": ["NXTС8S-8B1.3 1.7mm"],
        "meta": [
            "Паспорт 2024 йилнинг 02 апрел куни тузилган",
            "№ 1-муфта (переходная), 12.01.2024 йилда пайвандланган"
        ]
    },
    {
        "title": "Гулобод Муфта (Сарапаён)",
        "sheets": ["Гулобод Муфта", "Гулобод Муфта 2"],
        "addresses": [
            "Хонқа туман Истиқлол махалласи Гулобод кўчаси 37-уй",
            "Хонқа туман Истиқлол махалласи Гулзор кўчаси 4-уй",
            "Хонқа тумани Сарапаян қишлоғи Истиқлол махалласи Дўстлик кўчаси 23-уй",
            "Гулобод кўчаси 43-уй, 79-уй"
        ],
        "cables": [
            "NJXTA-32B1.3",
            "FIG-8 Aerial Loose Tube Cable G.652D 12F",
            "NJXTW-8B1.3",
            "NXTC8S-12B1.3 ОКТцМ-П-8Е (1х8)-1.5 kH"
        ],
        "meta": ["Паспорт 2024 йилнинг 29 март куни тузилган"]
    },
    {
        "title": "Дала шипон Муфта (1 ва 2)",
        "sheets": ["Дала шипон Муфма 1", "Дала шипон Муфта 2"],
        "addresses": [
            "Қутлуғқадам 1-уй, Томадурвадик қишлоғи",
            "Қутлиқадам кўчаси 1-уй"
        ],
        "cables": [
            "NXTC8S-48B1.3",
            "ВОК-48 воздушный (FIG-8 Aerial Armored Optical Fiber Cable G.652D 48F 9.6*15.7)"
        ],
        "meta": ["Паспорт 2024 йилнинг 29 март куни тузилган"]
    },
    {
        "title": "Дўрмон кўчаси, 1-уй Муфта",
        "sheets": ["Дўрмон кўчаси, 1 уй", "4-5-6"],
        "addresses": [
            "Дўрмон кўчаси, 1 уй Қирқёп қишлоғи",
            "Дўрмон кўчаси, 7 уй Қирқёп қишлоғи",
            "Хонка Темирчилар кўчаси, 6 уй Қирқёп қишлоғи",
            "Юксалиш кўчаси, 49 уй Қирқёп қишлоғи"
        ],
        "cables": [
            "NJXTA-48B1.3",
            "FIG-8 Aerial Tube Cable G.652D 6F",
            "ОКНСМ-10-01-0,22-12"
        ],
        "meta": [
            "Паспорт 2024 йилнинг 02 апрел куни тузилган",
            "№ 1-муфта (переходная), 12.01.2024 йилда пайвандланган"
        ]
    },
    {
        "title": "Дўстлик кўчаси 23-уй Муфта",
        "sheets": ["Гулобод Муфта"],
        "addresses": [
            "Хонқа туман Истиқлол махалласи Гулобод кўчаси 23-уй",
            "Хоразм вилояти, Хонқа тумани, Сарапоён қишлоғи, Дўстлик кўчаси дом 76"
        ],
        "cables": ["NJXTW-8B1.3"],
        "meta": ["Паспорт 2024 йилнинг 29 март куни тузилган"]
    },
    {
        "title": "Жайхун қуёши болалар оромгоҳи йўли",
        "sheets": ["Жайхун қуёши болалар оромгоҳига"],
        "addresses": [
            "Хонқа туман Томадургадик қишлоғи Жайхун қуёши болалар оромгоҳига олиб борувчи йўл"
        ],
        "cables": [
            "NXTC8S-12B1.3",
            "FIG-8 Aerial Loose Tube Cable 6F 546 м"
        ],
        "meta": ["Паспорт 2024 йилнинг 29 март куни тузилган"]
    },
    {
        "title": "Қутлуғқадам муфта",
        "sheets": ["Лист1"],
        "addresses": [
            "Қутлуғқадам кўчаси, 62 уй Томадурвадик қишлоғи",
            "Қутлиқадам кўчаси 1-уй",
            "Мустақиллик кўчаси 45"
        ],
        "cables": [
            "NXTA-32B1.3",
            "NXTC8S-24B1.3",
            "ОКТ-П-48Е- (4х12)-6кН"
        ],
        "meta": ["Паспорт 2024 йилнинг 29 март куни тузилган"]
    },
    {
        "title": "Қорақош 9-мактаб Наврўз кўчаси дом 45",
        "sheets": ["Лист1"],
        "addresses": [
            "Хоразм вилояти, Хонқа тумани, Қорақош (Ленин) қишлоғи, Наврўз кўчаси дом 45",
            "Наврўз кўчаси, 44 уй Қорақош (Ленин) қишлоғи"
        ],
        "cables": [
            "NXTС8S-48B1.3 1.7mm",
            "NXTC8S-48B1.3"
        ],
        "meta": ["Паспорт 2024 йилнинг Апрел куни тузилган"]
    }
]

splitters_list = []
subscribers_list = []
muftalar_list = []

# Tayanch OLT ma'lumotlari va montyori
tayanch_olt_list = []
tayanch_splitters_order = []
tayanch_by_splitter = {}
tayanch_montyor = "Jumaniyazov Ruslan"

# TOMA OLT ma'lumotlari va montyori
toma_olt_list = []
toma_splitters_order = []
toma_by_splitter = {}
toma_equipment_list = []
toma_source_file = EXCEL_TOMA_EQUIPMENT_CANDIDATES[0]
toma_montyor = "Jumaniyazov Ruslan"

# OLT Xonkobod uskunalari va montyori
xonkobod_equipment_list = []
xonkobod_montyor = "Yusupov Bobur"

# OLT Yosh kuch uskunalari va montyori
yosh_kuch_equipment_list = []
yosh_kuch_montyor = "Yo'ldashov Qadamboy"


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
    detected_montyor = default_montyor

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


def parse_mufta_workbook(fpath: str) -> dict | None:
    try:
        xls = pd.ExcelFile(fpath)
        addresses = []
        cables = []
        meta = []
        sheets = [s.strip() for s in xls.sheet_names]
        for s in xls.sheet_names:
            df = pd.read_excel(fpath, sheet_name=s, header=None)
            for r in range(df.shape[0]):
                for c in range(df.shape[1]):
                    v = df.iat[r, c]
                    if pd.isna(v):
                        continue
                    sv = " ".join(str(v).split())
                    low = sv.lower()
                    if "манзил:" in low or "қишлоғ" in low or "кўчаси" in low or "махалласи" in low:
                        val = sv.split(":", 1)[1].strip() if ":" in sv else sv
                        if val and val not in addresses:
                            addresses.append(val)
                    elif "маркаси:" in low or "cable" in low or "nx" in low or "вок-" in low or "окт" in low or "окнсм" in low:
                        val = sv.split(":", 1)[1].strip() if ":" in sv else sv
                        if val and len(val) > 3 and val not in cables:
                            cables.append(val)
                    elif "паспорт 20" in low or "муфтанинг техник" in low or "пайвандланган" in low:
                        if sv not in meta:
                            meta.append(sv)
        title = os.path.splitext(os.path.basename(fpath))[0]
        return {
            "title": title,
            "sheets": sheets,
            "addresses": addresses,
            "cables": cables,
            "meta": meta
        }
    except Exception as e:
        print(f"❌ Муфта файлини ўқишда хатолик ({fpath}): {e}")
        return None


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

# 3b. Toma OLT_yangilangan.xlsx / Toma OLT.xlsx uskunalarini o'qish
try:
    toma_eq_file = next((f for f in EXCEL_TOMA_EQUIPMENT_CANDIDATES if os.path.exists(f)), None)
    if toma_eq_file:
        toma_source_file = toma_eq_file
        xls_teq = pd.ExcelFile(toma_eq_file)
        for s_name in xls_teq.sheet_names:
            df_teq = pd.read_excel(toma_eq_file, sheet_name=s_name)
            for _, row in df_teq.iterrows():
                set_name = " ".join(str(row.get("Set", "") or "").replace("\xa0", " ").split())
                eq_num = " ".join(str(row.get("Nomer oborud.", "") or "").replace("\xa0", " ").split())
                addr = " ".join(str(row.get("Adres ustanovki", "") or "").replace("\xa0", " ").split())
                serial = " ".join(str(row.get("Seriyniy nomer", "") or "").replace("\xa0", " ").split())

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

# 4. Muftalar bazasini yuklash
existing_mufta_files = [f for f in MUFTA_FILES if os.path.exists(f)]
if existing_mufta_files:
    for mf in existing_mufta_files:
        parsed = parse_mufta_workbook(mf)
        if parsed:
            muftalar_list.append(parsed)
    print(f"✅ Муфталар файллардан юкланди: {len(muftalar_list)} та")
else:
    muftalar_list = list(DEFAULT_MUFTALAR_LIST)
    print(f"✅ Муфталар захира базадан юкланди: {len(muftalar_list)} та")

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


def build_main_keyboard() -> ReplyKeyboardMarkup:
    rows = [
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


def format_splitter_ports_text(splitter_name: str, by_splitter: dict[str, list[dict]], montyor: str = "") -> str:
    ports = by_splitter.get(splitter_name, [])
    busy_cnt = sum(1 for p in ports if p["client"] != "Бўш порт")
    free_cnt = len(ports) - busy_cnt

    lines = [f"🔌 <b>{html.quote(splitter_name)}</b>"]
    if montyor:
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


def format_extra_olt_summary(olt_name: str) -> str:
    kw = olt_name.lower().strip()
    matched_ports = [
        p for p in (tayanch_olt_list + toma_olt_list)
        if kw in f"{p['splitter']} {p['client']} {p['login']} {p['address']} {p.get('montyor', '')}".lower()
    ]
    matched_splitters = [
        s for s in splitters_list
        if kw in f"{s['number']} {s['splitter']} {s['model']} {s['address']} {s['town']} {s['real_sn']}".lower()
    ]
    matched_muftalar = [
        m for m in muftalar_list
        if kw in f"{m['title']} {' '.join(m['addresses'])} {' '.join(m['cables'])}".lower()
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

    lines = [f"🏢 <b>OLT: {html.quote(olt_name)}</b>"]
    if matched_ports:
        lines.append(f"🔌 OLT портларда топилди: <b>{len(matched_ports)} та</b>\n")
        for item in matched_ports[:8]:
            mont_str = f" | 👷 {html.quote(item['montyor'])}" if item.get("montyor") else ""
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
    if matched_muftalar:
        lines.append(f"\n🧵 Муфталар базасида топилди: <b>{len(matched_muftalar)} та</b>\n")
        for m in matched_muftalar[:3]:
            lines.append(f"   • <b>{html.quote(m['title'])}</b> — {html.quote(', '.join(m['addresses'][:2]))}")

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

    if not matched_ports and not matched_splitters and not matched_muftalar and not matched_xonkobod and not matched_yosh_kuch:
        lines.append("ℹ️ Базада ҳозирча бу OLT бўйича ёзув топилмади (тугма фаол).")

    return "\n".join(lines)


def search_all_databases(query: str) -> str:
    q = query.lower().strip()
    if len(q) < 2:
        return "⚠️ Қидирув учун камида 2 та белги киритинг."

    # 1. Tayanch va TOMA OLT portlaridan qidirish
    olt_hits = [
        p for p in (tayanch_olt_list + toma_olt_list)
        if q in f"{p['splitter']} {p['client']} {p['login']} {p['phone']} {p['ip_phone']} {p['ip']} {p['address']} {p.get('montyor', '')}".lower()
    ]

    # 2. Abonentlar bazasidan qidirish
    sub_hits = [
        s for s in subscribers_list
        if q in f"{s['client']} {s['login']} {s['phone']} {s['msisdn']} {s['address']}".lower()
    ]

    # 3. Umumiy splitterlar bazasidan qidirish
    sp_hits = [
        sp for sp in splitters_list
        if q in f"{sp['number']} {sp['splitter']} {sp['model']} {sp['address']} {sp['town']} {sp['real_sn']}".lower()
    ]

    # 3b. Toma OLT_yangilangan.xlsx / Toma OLT.xlsx uskunalaridan qidirish
    toma_sp_hits = [
        e for e in toma_equipment_list
        if q in f"{e['set']} {e['number']} {e['address']} {e['serial']} {e.get('montyor', '')}".lower()
    ]

    # 3c. OLT_Xonkobod_tayyor.xlsx uskunalaridan qidirish
    xonkobod_sp_hits = [
        e for e in xonkobod_equipment_list
        if q in f"{e['set']} {e['number']} {e['address']} {e['serial']} {e.get('montyor', '')}".lower()
    ]

    # 3d. OLT Yosh kuch.xlsx uskunalaridan qidirish
    yosh_kuch_sp_hits = [
        e for e in yosh_kuch_equipment_list
        if q in f"{e['set']} {e['number']} {e.get('street', '')} {e['address']} {e.get('montyor', '')}".lower()
    ]

    # 4. Muftalardan qidirish
    mufta_hits = [
        m for m in muftalar_list
        if q in f"{m['title']} {' '.join(m['addresses'])} {' '.join(m['cables'])}".lower()
    ]

    if not olt_hits and not sub_hits and not sp_hits and not toma_sp_hits and not xonkobod_sp_hits and not yosh_kuch_sp_hits and not mufta_hits:
        return f"❌ <b>«{html.quote(query)}»</b> бўйича ҳеч нарса топилмади."

    out = [f"🔎 <b>Қидирув натижалари («{html.quote(query)}»):</b>"]

    if olt_hits:
        out.append(f"\n🔌 <b>OLT портларида ({len(olt_hits)} та):</b>")
        for p in olt_hits[:10]:
            extra = []
            if p["ip_phone"] != "-":
                extra.append(f"IP-тел: {html.quote(p['ip_phone'])}")
            if p["ip"] != "-":
                extra.append(f"IP: <code>{html.quote(p['ip'])}</code>")
            if p.get("montyor"):
                extra.append(f"👷 {html.quote(p['montyor'])}")
            extra_str = f" | {' | '.join(extra)}" if extra else ""
            out.append(
                f"• <b>{html.quote(p['splitter'])}</b> ({html.quote(p['port'])}-порт) — <b>{html.quote(p['client'])}</b>\n"
                f"  🔑 <code>{html.quote(p['login'])}</code> | 📞 {html.quote(p['phone'])}{extra_str}\n"
                f"  🏠 {html.quote(p['address'])}"
            )

    if sub_hits:
        out.append(f"\n👥 <b>Абонентлар базасида ({len(sub_hits)} та):</b>")
        for s in sub_hits[:6]:
            out.append(
                f"• <b>{html.quote(s['client'])}</b> (<code>{html.quote(s['login'])}</code>)\n"
                f"  📞 {html.quote(s['phone'])} | Тариф: {html.quote(s['rate_plan'])} | Баланс: {html.quote(s['balance'])}\n"
                f"  🏠 {html.quote(s['address'])}"
            )

    if sp_hits:
        out.append(f"\n⚡ <b>Сплиттерлар базасида ({len(sp_hits)} та):</b>")
        for sp in sp_hits[:5]:
            out.append(
                f"• <b>{html.quote(sp['number'])}</b> ({html.quote(sp['splitter'])} / {html.quote(sp['model'])})\n"
                f"  📍 {html.quote(sp['town'])}, {html.quote(sp['address'])} | S/N: <code>{html.quote(sp['real_sn'])}</code>"
            )

    if toma_sp_hits:
        out.append(
            f"\n📡 <b>TOMA ускуналарида ({len(toma_sp_hits)} та)</b> "
            f"| 👷 Монтёр: <b>{html.quote(toma_montyor)}</b>:"
        )
        for e in toma_sp_hits[:8]:
            serial_part = f"🔢 S/N: <code>{html.quote(e['serial'])}</code> | " if e["serial"] != "-" else ""
            out.append(
                f"• <b>{html.quote(e['number'])}</b> ({html.quote(e['set'])})\n"
                f"  {serial_part}🏠 {html.quote(e['address'])}"
            )

    if xonkobod_sp_hits:
        out.append(
            f"\n📡 <b>OLT Xonkobod ускуналарида ({len(xonkobod_sp_hits)} та)</b> "
            f"| 👷 Монтёр: <b>{html.quote(xonkobod_montyor)}</b>:"
        )
        for e in xonkobod_sp_hits[:8]:
            out.append(
                f"• <b>{html.quote(e['number'])}</b> ({html.quote(e['set'])})\n"
                f"  🏠 {html.quote(e['address'])}"
            )

    if yosh_kuch_sp_hits:
        out.append(
            f"\n📡 <b>OLT Yosh kuch объектларида ({len(yosh_kuch_sp_hits)} та)</b> "
            f"| 👷 Монтёр: <b>{html.quote(yosh_kuch_montyor)}</b>:"
        )
        for e in yosh_kuch_sp_hits[:8]:
            out.append(
                f"• <b>{html.quote(e['number'])}</b> ({html.quote(e['set'])})\n"
                f"  🏠 {html.quote(e['address'])}"
            )

    if mufta_hits:
        out.append(f"\n🧵 <b>Муфталарда ({len(mufta_hits)} та):</b>")
        for m in mufta_hits[:5]:
            out.append(
                f"• <b>{html.quote(m['title'])}</b>\n"
                f"  🏠 {html.quote(', '.join(m['addresses'][:3]))}"
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
        "Қуйидаги менюдан керакли бўлимни танланг ёки қидирув сўзини (Ф.И.Ш., логин, телефон, манзил ёки порт/ускуна рақами) ёзинг.",
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
        f"• Муфталар: <b>{len(muftalar_list)} та</b>",
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


@dp.message(F.text == "🔍 Абонент ва сплиттер қидириш")
async def prompt_search(message: Message):
    await message.answer(
        "🔍 <b>Қидирув учун сўз киритинг:</b>\n"
        "• Абонент Ф.И.Ш. ёки логини\n"
        "• Телефон ёки IP-манзил\n"
        "• Кўча / маҳалла / уй манзили\n"
        "• Сплиттер ёки ускуна рақами (масалан: <code>1/1 1x4</code>, <code>1/11/3</code>, <code>Miskin</code>)",
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


@dp.callback_query(F.data.startswith(("tolt_", "molt_")))
async def cb_olt_pagination_and_ports(callback: CallbackQuery):
    data = callback.data
    is_tayanch = data.startswith("tolt_")
    prefix = "tolt" if is_tayanch else "molt"
    sp_order = tayanch_splitters_order if is_tayanch else toma_splitters_order
    by_sp = tayanch_by_splitter if is_tayanch else toma_by_splitter
    sp_prefixes = ["Tayanch OLT", "Tayanch"] if is_tayanch else ["TOMA OLT", "TOMA", "Tomo"]
    montyor = tayanch_montyor if is_tayanch else toma_montyor
    title = "Tayanch OLT" if is_tayanch else "TOMA OLT"

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
            formatted = format_splitter_ports_text(sp_name, by_sp, montyor=montyor)
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


@dp.message(F.text)
async def handle_text(message: Message):
    txt = message.text.strip()

    if txt in EXTRA_OLT_BUTTON_MAP:
        olt_name = EXTRA_OLT_BUTTON_MAP[txt]
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
