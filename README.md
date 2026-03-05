# 🤖 Bot Telegram OTP WhatsApp Vietnam (SMSBower)

Bot Telegram untuk order nomor WhatsApp Vietnam via API SMSBower.
Setiap pengguna bisa mendaftarkan API Key mereka sendiri.

## 📁 Struktur File

```
sms_bot/
├── bot.py            # Kode utama bot
├── requirements.txt  # Library Python
├── Procfile          # Konfigurasi Railway
├── runtime.txt       # Versi Python
└── .gitignore
```

## 🚀 Deploy ke Railway

### Langkah 1: Siapkan GitHub Repository
1. Buat repository baru di GitHub (kosong, tanpa README)
2. Upload semua file dari folder `sms_bot` ini ke repository tersebut

Atau via terminal:
```bash
cd sms_bot
git init
git add .
git commit -m "first commit"
git remote add origin https://github.com/USERNAME/NAMA_REPO.git
git push -u origin main
```

### Langkah 2: Buat Project di Railway
1. Buka [railway.app](https://railway.app) dan login
2. Klik **"New Project"**
3. Pilih **"Deploy from GitHub Repo"**
4. Pilih repository yang baru dibuat

### Langkah 3: Tambahkan Environment Variable
Di dashboard Railway project Anda:
1. Klik service yang baru dibuat
2. Buka tab **"Variables"**
3. Tambahkan variable berikut:

| Variable   | Value                                                  |
|------------|--------------------------------------------------------|
| `BOT_TOKEN`| `8647699255:AAG1ZO_AIjAZvSCYeoeqE0s3VxUo21hCgd0`     |

### Langkah 4: Tambahkan Volume (Penting!)
Agar database API Key pengguna tidak hilang saat redeploy:
1. Di dashboard, klik service → **Settings**
2. Scroll ke **"Volumes"** → klik **"Add Volume"**
3. Set **Mount Path** = `/data`
4. Tambahkan variable baru:

| Variable  | Value              |
|-----------|--------------------|
| `DB_PATH` | `/data/database.db` |

### Langkah 5: Deploy!
Railway akan otomatis deploy. Cek tab **"Deployments"** untuk melihat status.

---

## 🎮 Cara Pengguna Memakai Bot

1. Buka bot di Telegram, ketik `/start`
2. Daftarkan API Key SMSBower: `/setapi API_KEY_KAMU`
3. Tekan tombol **"🛒 Order WA Vietnam"**
4. Masukkan nomor yang didapat ke WhatsApp
5. Tekan **"✉️ Cek SMS"** untuk melihat kode OTP
6. Selesai!

## ⚠️ Catatan
- Bot ini HANYA untuk layanan WhatsApp dari negara Vietnam
- Setiap user harus punya akun & API Key sendiri di [smsbower.page](https://smsbower.page)
- API Key disimpan per user Telegram, aman dan terpisah
