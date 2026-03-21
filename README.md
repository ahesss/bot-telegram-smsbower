# 🤖 Bot Telegram OTP WhatsApp (SMSBower)

Bot Telegram untuk order nomor WhatsApp dari berbagai negara (Vietnam, Colombia, Philipina, Mexico, USA, Germany) via API SMSBower.
Setiap pengguna bisa mendaftarkan API Key mereka sendiri.

## 📁 Struktur File

```
sms_bot/
├── bot.py            # Kode utama bot (Multi-country & Autobuy Brutal)
├── requirements.txt  # Library Python
├── Procfile          # Konfigurasi Railway
├── runtime.txt       # Versi Python
└── .gitignore
```

## 🚀 Deploy ke Railway

### Langkah 1: Siapkan GitHub Repository
1. Buat repository baru di GitHub (kosong, tanpa README)
2. Upload semua file dari folder ini ke repository tersebut

### Langkah 2: Buat Project di Railway
1. Buka [railway.app](https://railway.app) dan login
2. Pilih **"Deploy from GitHub Repo"**
3. Pilih repository yang baru dibuat

### Langkah 3: Tambahkan Environment Variable
Tambahkan variable berikut di Railway:

| Variable   | Value                                                  |
|------------|--------------------------------------------------------|
| `BOT_TOKEN`| `API_TOKEN_BOT_TELEGRAM_ANDA`                          |

### Langkah 4: Tambahkan Volume (Penting!)
Agar database API Key pengguna tidak hilang saat redeploy:
1. Klik service → **Settings**
2. **"Volumes"** → **"Add Volume"**
3. Set **Mount Path** = `/data`
4. Tambahkan variable: `DB_PATH = /data/database.db`

---

## 🎮 Cara Pengguna Memakai Bot

1. Buka bot di Telegram, ketik `/start`
2. Daftarkan API Key SMSBower: `/setapi API_KEY_KAMU`
3. Pilih negara: 🇻🇳 VN, 🇨🇴 CO, 🇵🇭 PH, 🇲🇽 MX, 🇺🇸 US, atau 🇩🇪 DE
4. Pilih jumlah nomor atau gunakan fitur **🔥 Autobuy Brutal**
5. Selesai!

## ⚠️ Fitur Baru: Sniper Mode
- **🇺🇸 USA Sniper**: ID 187, Price $0.779 - $0.883
- **🇩🇪 Germany Sniper**: ID 43, Price $0.962 - $1.089
- **Autobuy**: Mendukung mode Brutal Sniper untuk semua negara.
- **Multi-country**: Mendukung VN, CO, PH, MX, US, DE.
