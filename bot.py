import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import requests
import sqlite3
import os
import threading
import time

# =============================================
# KONFIGURASI
# =============================================
TOKEN = os.environ.get("BOT_TOKEN", "8647699255:AAG1ZO_AIjAZvSCYeoeqE0s3VxUo21hCgd0")
bot = telebot.TeleBot(TOKEN)

API_BASE = "https://smsbower.page/stubs/handler_api.php"
DB_PATH = os.environ.get("DB_PATH", "database.db")

MAX_ORDER = 20         # Maksimal order sekaligus
OTP_TIMEOUT = 300      # Timeout 5 menit (300 detik)
CHECK_INTERVAL = 5     # Cek OTP setiap 5 detik
COUNTRY_CODE = "84"    # Vietnam country code
COUNTRY_ID = "10"      # Vietnam country ID di SMSBower
SERVICE = "wa"         # WhatsApp service

# =============================================
# DATABASE
# =============================================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        api_key TEXT
    )''')
    conn.commit()
    conn.close()

def get_user_api(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT api_key FROM users WHERE user_id = ?", (user_id,))
    res = c.fetchone()
    conn.close()
    return res[0] if res else None

def set_user_api(user_id, api_key):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO users (user_id, api_key) VALUES (?, ?)", (user_id, api_key))
    conn.commit()
    conn.close()

# =============================================
# API HELPER
# =============================================
def req_api(api_key, action, **kwargs):
    params = {'api_key': api_key, 'action': action}
    params.update(kwargs)
    try:
        r = requests.get(API_BASE, params=params, timeout=15)
        return r.text.strip()
    except Exception as e:
        return f"ERROR: {str(e)}"

def strip_country_code(number):
    """Hapus country code +84 dari nomor Vietnam, sisakan nomor lokal saja"""
    number = number.strip()
    if number.startswith("+"):
        number = number[1:]
    if number.startswith(COUNTRY_CODE):
        number = number[len(COUNTRY_CODE):]
    return number

# =============================================
# FORMAT PESAN ORDER
# =============================================
def format_order_message(orders, title=""):
    """Format pesan daftar order dengan status OTP"""
    lines = []
    if title:
        lines.append(title)
        lines.append("")

    done_count = 0
    total = len(orders)

    for i, order in enumerate(orders, 1):
        number_local = strip_country_code(order['number'])
        status = order.get('status', 'waiting')

        if status == 'waiting':
            lines.append(f"{i}. `{number_local}` — ⏳ Menunggu OTP...")
        elif status == 'got_otp':
            code = order.get('code', '???')
            lines.append(f"{i}. `{number_local}` — ✅ OTP: `{code}`")
            done_count += 1
        elif status == 'cancelled':
            lines.append(f"{i}. `{number_local}` — 🚫 Dibatalkan")
            done_count += 1
        elif status == 'timeout':
            lines.append(f"{i}. `{number_local}` — ⏰ Timeout")
            done_count += 1
        elif status == 'error':
            lines.append(f"{i}. `{number_local}` — ❌ Error")
            done_count += 1

    lines.append("")
    lines.append(f"📊 Progress: {done_count}/{total}")

    if done_count >= total:
        lines.append("\n✅ *Semua order selesai!*")

    return "\n".join(lines)

# =============================================
# AUTO-CHECK OTP (BACKGROUND THREAD)
# =============================================
def auto_check_otp(chat_id, message_id, orders, api_key):
    """Background thread yang otomatis cek OTP untuk semua order"""
    start_time = time.time()

    while True:
        # Cek apakah semua order sudah selesai
        active_orders = [o for o in orders if o['status'] == 'waiting']
        if not active_orders:
            break

        # Cek timeout
        elapsed = time.time() - start_time
        if elapsed > OTP_TIMEOUT:
            # Timeout semua yang masih waiting
            for o in orders:
                if o['status'] == 'waiting':
                    o['status'] = 'timeout'
                    # Cancel di API (status 8 = cancel)
                    try:
                        req_api(api_key, 'setStatus', status='8', id=o['id'])
                    except:
                        pass
            # Update pesan terakhir
            try:
                text = format_order_message(orders, "🛒 *Order WA Vietnam*")
                bot.edit_message_text(text, chat_id, message_id, parse_mode="Markdown")
            except:
                pass
            break

        # Cek SMS untuk setiap order yang masih waiting
        changed = False
        for o in orders:
            if o['status'] != 'waiting':
                continue
            try:
                res = req_api(api_key, 'getStatus', id=o['id'])
                if res.startswith('STATUS_OK'):
                    code = res.split(':')[1] if ':' in res else '???'
                    o['status'] = 'got_otp'
                    o['code'] = code
                    changed = True
                    # Set status 6 (selesai) di API
                    req_api(api_key, 'setStatus', status='6', id=o['id'])
                elif res == 'STATUS_CANCEL':
                    o['status'] = 'cancelled'
                    changed = True
                # STATUS_WAIT_CODE = masih menunggu, lanjut
            except:
                pass

        # Update pesan jika ada perubahan
        if changed:
            try:
                text = format_order_message(orders, "🛒 *Order WA Vietnam*")
                # Tambah tombol cancel jika masih ada yang waiting
                remaining = [o for o in orders if o['status'] == 'waiting']
                if remaining:
                    markup = InlineKeyboardMarkup()
                    ids_str = ",".join([o['id'] for o in remaining])
                    markup.row(InlineKeyboardButton(f"🚫 Batalkan Sisa ({len(remaining)})", callback_data=f"cancelall_{ids_str}"))
                    bot.edit_message_text(text, chat_id, message_id, parse_mode="Markdown", reply_markup=markup)
                else:
                    bot.edit_message_text(text, chat_id, message_id, parse_mode="Markdown")
            except:
                pass

        time.sleep(CHECK_INTERVAL)

# =============================================
# COMMAND HANDLERS
# =============================================
@bot.message_handler(commands=['start'])
def start_cmd(message):
    user_id = message.from_user.id
    api_key = get_user_api(user_id)

    text = (
        "🤖 *Bot OTP WhatsApp Vietnam* 🇻🇳\n\n"
        "Bot ini khusus untuk order nomor WhatsApp Vietnam.\n"
        "OTP akan otomatis muncul di bawah nomor masing-masing.\n\n"
        "📋 *Perintah:*\n"
        "`/setapi API_KEY` — Daftarkan API Key SMSBower\n"
        "`/order N` — Order N nomor sekaligus (maks 20)\n"
        "`/balance` — Cek saldo\n"
        "`/help` — Bantuan\n\n"
    )

    if api_key:
        bal_res = req_api(api_key, 'getBalance')
        if 'ACCESS_BALANCE' in bal_res:
            bal = bal_res.split(':')[1]
            text += f"✅ API Key: Terdaftar\n💰 Saldo: *{bal} RUB*"
        else:
            text += "⚠️ API Key terdaftar tapi tidak valid.\nGunakan `/setapi API_KEY` untuk mengganti."
    else:
        text += "❌ Belum ada API Key.\nGunakan `/setapi API_KEY` untuk mendaftar."

    markup = InlineKeyboardMarkup()
    if api_key:
        markup.row(InlineKeyboardButton("🛒 Order 1 Nomor", callback_data="quick_1"))
        markup.row(
            InlineKeyboardButton("🛒 Order 5", callback_data="quick_5"),
            InlineKeyboardButton("🛒 Order 10", callback_data="quick_10")
        )
    bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=markup)

@bot.message_handler(commands=['help'])
def help_cmd(message):
    text = (
        "📖 *Panduan Penggunaan*\n\n"
        "1️⃣ Daftarkan API Key dari akun SMSBower Anda:\n"
        "   `/setapi API_KEY_ANDA`\n\n"
        "2️⃣ Order nomor WA Vietnam (contoh 5 nomor):\n"
        "   `/order 5`\n\n"
        "3️⃣ Bot akan otomatis cek OTP setiap 5 detik.\n"
        "   Ketika OTP masuk, akan langsung muncul di bawah nomor.\n\n"
        "4️⃣ Salin nomor (tanpa +84) langsung dari chat.\n\n"
        "⏱ Timeout: 5 menit per order\n"
        "📱 Maks order: 20 nomor sekaligus\n\n"
        "💰 Cek saldo: `/balance`"
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(commands=['setapi'])
def setapi_cmd(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "❌ Format: `/setapi API_KEY_KAMU`\n\nDapatkan API Key di web SMSBower.", parse_mode="Markdown")
        return

    api_key = parts[1].strip()
    bot.reply_to(message, "⏳ Mengecek API Key...")

    bal_res = req_api(api_key, 'getBalance')
    if 'ACCESS_BALANCE' in bal_res:
        bal = bal_res.split(':')[1]
        set_user_api(message.from_user.id, api_key)
        bot.send_message(message.chat.id, f"✅ API Key valid & tersimpan!\n💰 Saldo: *{bal} RUB*\n\nKetik `/order 5` untuk mulai order.", parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, "❌ API Key tidak valid atau server gangguan.")

@bot.message_handler(commands=['balance'])
def balance_cmd(message):
    api_key = get_user_api(message.from_user.id)
    if not api_key:
        bot.reply_to(message, "❌ Belum ada API Key. Gunakan `/setapi API_KEY`", parse_mode="Markdown")
        return

    bal_res = req_api(api_key, 'getBalance')
    if 'ACCESS_BALANCE' in bal_res:
        bal = bal_res.split(':')[1]
        bot.reply_to(message, f"💰 Saldo Anda: *{bal} RUB*", parse_mode="Markdown")
    else:
        bot.reply_to(message, f"❌ Gagal cek saldo: {bal_res}")

@bot.message_handler(commands=['order'])
def order_cmd(message):
    api_key = get_user_api(message.from_user.id)
    if not api_key:
        bot.reply_to(message, "❌ Belum ada API Key. Gunakan `/setapi API_KEY`", parse_mode="Markdown")
        return

    # Parse jumlah
    parts = message.text.split()
    count = 1
    if len(parts) >= 2:
        try:
            count = int(parts[1])
        except ValueError:
            bot.reply_to(message, "❌ Format: `/order 5` (angka 1-20)", parse_mode="Markdown")
            return

    if count < 1 or count > MAX_ORDER:
        bot.reply_to(message, f"❌ Jumlah harus antara 1 dan {MAX_ORDER}.", parse_mode="Markdown")
        return

    process_bulk_order(message.chat.id, api_key, count)

def process_bulk_order(chat_id, api_key, count):
    """Proses order banyak nomor sekaligus"""
    # Kirim pesan awal
    msg = bot.send_message(chat_id, f"⏳ Sedang memesan {count} nomor WA Vietnam...", parse_mode="Markdown")

    orders = []
    failed = 0

    for i in range(count):
        res = req_api(api_key, 'getNumber', service=SERVICE, country=COUNTRY_ID)

        if 'ACCESS_NUMBER' in res:
            parts = res.split(':')
            if len(parts) >= 3:
                t_id = parts[1]
                number = parts[2]
                orders.append({
                    'id': t_id,
                    'number': number,
                    'status': 'waiting',
                    'code': None
                })
        elif res == 'NO_BALANCE':
            bot.edit_message_text(
                f"❌ *Saldo tidak cukup!*\n\nBerhasil order {len(orders)} dari {count} nomor.",
                chat_id, msg.message_id, parse_mode="Markdown"
            )
            if not orders:
                return
            break
        elif res == 'NO_NUMBERS':
            failed += 1
            if failed >= 3 and not orders:
                bot.edit_message_text("❌ Nomor WA Vietnam sedang tidak tersedia.", chat_id, msg.message_id, parse_mode="Markdown")
                return
        else:
            failed += 1

        # Jeda kecil antar order agar tidak terlalu cepat
        if i < count - 1:
            time.sleep(0.3)

    if not orders:
        bot.edit_message_text("❌ Gagal memesan nomor. Coba lagi nanti.", chat_id, msg.message_id, parse_mode="Markdown")
        return

    # Tampilkan semua nomor
    text = format_order_message(orders, "🛒 *Order WA Vietnam*")

    markup = InlineKeyboardMarkup()
    ids_str = ",".join([o['id'] for o in orders])
    markup.row(InlineKeyboardButton(f"🚫 Batalkan Semua ({len(orders)})", callback_data=f"cancelall_{ids_str}"))

    bot.edit_message_text(text, chat_id, msg.message_id, parse_mode="Markdown", reply_markup=markup)

    # Mulai auto-check OTP di background thread
    thread = threading.Thread(
        target=auto_check_otp,
        args=(chat_id, msg.message_id, orders, api_key),
        daemon=True
    )
    thread.start()

# =============================================
# CALLBACK HANDLERS
# =============================================
@bot.callback_query_handler(func=lambda call: True)
def callback_q(call):
    user_id = call.from_user.id
    api_key = get_user_api(user_id)
    data = call.data

    if not api_key:
        bot.answer_callback_query(call.id, "❌ Belum ada API Key. Gunakan /setapi", show_alert=True)
        return

    # Quick order buttons
    if data.startswith("quick_"):
        count = int(data.split("_")[1])
        bot.answer_callback_query(call.id, f"Memesan {count} nomor...")
        process_bulk_order(call.message.chat.id, api_key, count)

    # Cancel all remaining orders
    elif data.startswith("cancelall_"):
        ids_str = data.split("_", 1)[1]
        ids_list = ids_str.split(",")
        cancelled = 0
        for t_id in ids_list:
            try:
                res = req_api(api_key, 'setStatus', status='8', id=t_id)
                if 'ACCESS_CANCEL' in res:
                    cancelled += 1
            except:
                pass
        bot.answer_callback_query(call.id, f"🚫 {cancelled} order dibatalkan & direfund.", show_alert=True)
        try:
            bot.edit_message_text(
                f"🚫 *{cancelled} order dibatalkan.*\nSaldo dikembalikan.",
                call.message.chat.id, call.message.message_id,
                parse_mode="Markdown"
            )
        except:
            pass

# =============================================
# MAIN
# =============================================
if __name__ == '__main__':
    init_db()
    print("Bot is running...")
    bot.infinity_polling()
