import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import requests
import sqlite3
import os

# Ambil Token dari Environment Variable, atau replace dengan token default
TOKEN = os.environ.get("BOT_TOKEN", "8647699255:AAG1ZO_AIjAZvSCYeoeqE0s3VxUo21hCgd0")
bot = telebot.TeleBot(TOKEN)

API_BASE = "https://smsbower.page/stubs/handler_api.php"
# Jika menggunakan Railway volume, mount volume ke /data dan set DB_PATH /data/database.db
DB_PATH = os.environ.get("DB_PATH", "database.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, api_key TEXT)''')
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

def req_api(api_key, action, **kwargs):
    params = {'api_key': api_key, 'action': action}
    params.update(kwargs)
    try:
        r = requests.get(API_BASE, params=params, timeout=10)
        return r.text
    except Exception as e:
        return f"ERROR: {str(e)}"

@bot.message_handler(commands=['start'])
def start_cmd(message):
    user_id = message.from_user.id
    api_key = get_user_api(user_id)
    
    text = (
        "🤖 *Bot OTP WhatsApp Vietnam (SMSBower)* 🇻🇳\n\n"
        "Selamat datang! Bot ini khusus untuk order nomor WhatsApp dari negara Vietnam.\n\n"
        "🛠 *Cara Menggunakan:*\n"
        "1. Daftarkan API Key akun SMSBower Anda dengan perintah:\n"
        "`/setapi API_KEY_ANDA`\n"
        "2. Tekan tombol *Order WA Vietnam* di bawah untuk membeli nomor.\n\n"
        "🛡 *Status Anda:*\n"
    )
    
    markup = InlineKeyboardMarkup()
    
    if api_key:
        bal_res = req_api(api_key, 'getBalance')
        if 'ACCESS_BALANCE' in bal_res:
            bal = bal_res.split(':')[1]
            text += f"✅ API Key Terdaftar\n💰 Saldo: {bal} RUB"
            markup.row(InlineKeyboardButton("🛒 Order WA Vietnam", callback_data="order_wa"))
            markup.row(InlineKeyboardButton("⚙️ Profil / Cek Saldo", callback_data="profile"))
        else:
            text += f"❌ API Key Terdaftar, tapi invalid/salah.\nKirim ulang `/setapi API_KEY` untuk mengganti."
    else:
        text += "❌ Belum ada API Key. Silakan gunakan `/setapi API_KEY`"
    
    bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=markup)

@bot.message_handler(commands=['setapi'])
def setapi_cmd(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "❌ Format salah.\nGunakan: `/setapi API_KEY_KAMU`\n\nAPI Key bisa didapat di web SMSBower.", parse_mode="Markdown")
        return
    
    api_key = parts[1].strip()
    # Test API Key first
    bot.reply_to(message, "⏳ Sedang mengecek API Key Anda...")
    bal_res = req_api(api_key, 'getBalance')
    if 'ACCESS_BALANCE' in bal_res:
        set_user_api(message.from_user.id, api_key)
        bot.send_message(message.chat.id, "✅ API Key berhasil disimpan dan valid! Ketik /start untuk memunculkan menu.")
    else:
        bot.send_message(message.chat.id, "❌ API Key yang Anda masukkan salah atau web sedang gangguan. Gagal menyimpan.")

@bot.callback_query_handler(func=lambda call: True)
def callback_q(call):
    user_id = call.from_user.id
    api_key = get_user_api(user_id)
    
    if not api_key:
        bot.answer_callback_query(call.id, "❌ Anda belum mengatur API Key. Gunakan /setapi API_KEY", show_alert=True)
        return

    data = call.data

    if data == "profile":
        bal_res = req_api(api_key, 'getBalance')
        if 'ACCESS_BALANCE' in bal_res:
            bal = bal_res.split(':')[1]
            text = f"👤 *Profil Anda*\n\n💰 Saldo: {bal} RUB\n🔑 API Key: `Terpasang`"
            markup = InlineKeyboardMarkup()
            markup.row(InlineKeyboardButton("🔙 Kembali", callback_data="back_start"))
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=markup)
        else:
            bot.answer_callback_query(call.id, "❌ Gagal cek saldo. Pastikan API Key benar.", show_alert=True)

    elif data == "back_start":
        bot.delete_message(call.message.chat.id, call.message.message_id)
        start_cmd(call.message)

    elif data == "order_wa":
        bot.answer_callback_query(call.id, "Mencari nomor... Mohon tunggu.")
        # service=wa, country=10 (Vietnam)
        res = req_api(api_key, 'getNumber', service='wa', country='10')
        
        if 'ACCESS_NUMBER' in res:
            parts = res.split(':')
            if len(parts) >= 3:
                t_id = parts[1]
                number = parts[2]
                text = (
                    f"✅ *Nomor Berhasil Didapat!*\n\n"
                    f"📱 *Nomor:* `{number}`\n"
                    f"🌐 *Negara:* Vietnam\n"
                    f"💬 *Layanan:* WhatsApp\n"
                    f"🆔 *ID Order:* `{t_id}`\n\n"
                    f"Silakan masukkan nomor ini di WhatsApp, lalu tekan tombol *Cek SMS* setelah OTP dikirim."
                )
                markup = InlineKeyboardMarkup()
                # Cek sms button and Cancel button
                markup.row(InlineKeyboardButton("✉️ Cek SMS", callback_data=f"check_{t_id}"))
                markup.row(InlineKeyboardButton("❌ Batal / Refund", callback_data=f"cancel_{t_id}"))
                
                bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=markup)
            else:
                bot.answer_callback_query(call.id, "❌ Format response API tidak sesuai.", show_alert=True)
                
        elif res == "NO_NUMBERS":
            bot.answer_callback_query(call.id, "❌ Nomor WA Vietnam sedang kosong saat ini.", show_alert=True)
        elif res == "NO_BALANCE":
            bot.answer_callback_query(call.id, "❌ Saldo Anda tidak cukup.", show_alert=True)
        else:
            bot.answer_callback_query(call.id, f"❌ Error: {res}", show_alert=True)

    elif data.startswith("check_"):
        t_id = data.split("_")[1]
        res = req_api(api_key, 'getStatus', id=t_id)
        
        if res == 'STATUS_WAIT_CODE':
            bot.answer_callback_query(call.id, "⏳ Belum ada SMS masuk... Tunggu beberapa detik.", show_alert=True)
        elif res.startswith('STATUS_OK'):
            code = res.split(':')[1]
            text = (
                f"🎉 *SMS / OTP Berhasil Diterima!*\n\n"
                f"✉️ *Kode OTP:* `{code}`\n\n"
                f"Selesai! Anda siap menggunakan WhatsApp."
            )
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode="Markdown")
            # Update status to complete (6)
            req_api(api_key, 'setStatus', status='6', id=t_id)
        else:
            bot.answer_callback_query(call.id, f"ℹ️ Status: {res}", show_alert=True)

    elif data.startswith("cancel_"):
        t_id = data.split("_")[1]
        res = req_api(api_key, 'setStatus', status='8', id=t_id)
        
        if 'ACCESS_CANCEL' in res:
            bot.edit_message_text("🚫 *Order Dibatalkan.*\n\nSaldo Anda tidak jadi terpotong.", call.message.chat.id, call.message.message_id, parse_mode="Markdown")
        else:
            # Bisa jadi status error
            bot.answer_callback_query(call.id, f"❌ Gagal membatalkan. Status: {res}", show_alert=True)

if __name__ == '__main__':
    init_db()
    print("Bot is running...")
    bot.infinity_polling()
