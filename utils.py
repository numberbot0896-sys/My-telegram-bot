import random
from datetime import datetime

COUNTRIES = {
    "ET": ("🇪🇹", "Ethiopia", "+251"),
    "BD": ("🇧🇩", "Bangladesh", "+880"),
    "US": ("🇺🇸", "United States", "+1"),
    "IN": ("🇮🇳", "India", "+91"),
}

SERVICES = ["Facebook", "Telegram", "WhatsApp", "Google", "IMO", "Instagram"]

OTP_TYPES = {
    "new_account": "নতুন একাউন্ট কোড",
    "login": "লগইন কোড",
    "password_reset": "পাসওয়ার্ড রিকভারি",
}

def generate_otp(length: int = 5) -> str:
    range_start = 10**(length - 1)
    range_end = (10**length) - 1
    return str(random.randint(range_start, range_end))

def generate_virtual_number(country_code: str) -> dict:
    info = COUNTRIES.get(country_code, COUNTRIES["ET"])
    flag, country_name, code = info
    rand_number = "".join([str(random.randint(0, 9)) for _ in range(9)])
    masked = f"{code[1:]}{rand_number[:3]}***{rand_number[-4:]}"
    return {
        "flag": flag,
        "country": country_name,
        "masked": masked
    }

def build_message(masked: str, flag: str, country: str, otp: str, service: str) -> str:
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return (
        "╔═  🔐 otp king 👑  🔐  ═╗\n"
        "     ✨ OTP RECEIVED ✨\n"
        "╚═══════════════╝\n\n"
        f"📱 `{masked}`   |   {flag} {country}\n\n"
        "╭─🔑 OTP CODE 🔑 ─╮\n"
        f"│      `{otp}`      │\n"
        "╰─────────────╯\n\n"
        f"🧩 Service   ◈   {service}\n"
        f"🕒 Time      ◈   {current_time}\n\n"
        "╔═════ ✦ MESSAGE ✦ ═════╗\n"
        f"💬 # {otp} est votre code {service}nH29QFsn4Sr\n"
        "╚═════════════════════╝"
    )

