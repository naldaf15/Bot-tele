import logging
import os
import json
import requests
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CommandHandler,
    filters,
    ContextTypes,
)

# ─────────────────────────────────────────
#  KONFIGURASI
# ─────────────────────────────────────────

TOKEN        = os.environ.get("TOKEN", "ISI_TOKEN_BOT_TELEGRAM_KAMU")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "ISI_GROQ_API_KEY_KAMU")
SHEET_ID     = os.environ.get("SHEET_ID", "ISI_SHEET_ID_KAMU")
GOOGLE_CREDS = os.environ.get("GOOGLE_CREDENTIALS", "")

ADMIN_USERNAMES = ["Random_Email"]
HANYA_DI_GRUP   = True

SYSTEM_PROMPT = """Kamu adalah asisten grup Telegram khusus lowongan kerja yang ramah dan profesional.
Tugasmu membantu member mencari info loker, tips CV, dan interview.
Jawab singkat & padat (maks 5 kalimat). Prioritaskan referensi loker yang diberikan.
PENTING: Jika data referensi berisi informasi cara melamar, email, link, atau kontak, 
WAJIB sertakan di jawaban secara lengkap tanpa dipotong."""

# Kata kunci tetap (LENGKAP)
KATA_KUNCI = {
    "halo": "Halo! 👋 Selamat datang di grup lowongan kerja. Ada yang bisa dibantu?",
    "loker": "Cek info terbaru di pinned message atau ketik /daftar untuk melihat list!",
    "cv": "Pastikan CV kamu ATS-friendly. Ketik /bikin_CV untuk info pembuatan!",
    "alamat": "Alamat kantor pusat kami ada di Jakarta Timur. Untuk detail hubungi admin.",
    "cara melamar": "Siapkan CV ATS-friendly, cek kualifikasi, dan kirim via email resmi perusahaan.",
    "terima kasih": "Sama-sama! 😊 Semoga segera dapat pekerjaan yang diimpikan ya!",
    "kisi kisi": "📝 Kisi-kisi soal bisa cek di sini:\nhttps://t.me/c/1211036502/1/2974586",
    "cara kirim email": "📧 Panduan lengkap cara kirim email lamaran bisa cek di sini:\nhttps://t.me/c/1211036502/2920839",
    "kirim email": "📧 Panduan lengkap cara kirim email lamaran bisa cek di sini:\nhttps://t.me/c/1211036502/2920839",
    "real atau hoax": "🔍 Tergantung dari sumber lowongannya.\n✅ Jika sumbernya resmi/terpercaya → kemungkinan besar REAL\n❓ Kalau masih ragu → tag admin saja ya!",
    "hoax": "⚠️ Jika terindikasi hoax, jangan didatangi ya!\nTetap hati-hati demi keamanan 🙏",
    "real": "🚀 Kalau sudah dipastikan real, langsung gas lamar!",
    "info loker terbaru": "📢 Lowongan kerja update setiap hari di grup.\nLangsung cek & lamar ya, tidak perlu tanya lagi 👍\nKetik /daftar untuk lihat list terbaru!",
    "update loker": "📢 Lowongan kerja update setiap hari di grup.\nLangsung cek & lamar ya, tidak perlu tanya lagi 👍\nKetik /daftar untuk lihat list terbaru!",
    "update cv": "📄 Panduan update CV bisa cek di sini:\nhttps://t.me/c/1211036502/2919519",
    "info kopdar": "📍 Buat yang mau ikut kopdar:\nPantau grup setiap Jumat & Sabtu\nNanti lokasi akan diumumkan di grup ya!",
    "kopdar": "📍 Buat yang mau ikut kopdar:\nPantau grup setiap Jumat & Sabtu\nNanti lokasi akan diumumkan di grup ya!",
}

# ─────────────────────────────────────────
#  FUNGSI GOOGLE SHEETS
# ─────────────────────────────────────────

def get_sheet():
    try:
        creds_dict = json.loads(GOOGLE_CREDS)
        scopes     = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds      = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client     = gspread.authorize(creds)
        return client.open_by_key(SHEET_ID).sheet1
    except Exception:
        return None

def load_info() -> dict:
    sheet = get_sheet()
    if not sheet: return {}
    try:
        rows = sheet.get_all_records()
        return {row["nama"]: row["info"] for row in rows if row.get("nama")}
    except:
        return {}

def simpan_info(nama, info) -> bool:
    sheet = get_sheet()
    if not sheet: return False
    try:
        sheet.append_row([nama, info, datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
        return True
    except:
        return False

def hapus_info(nama_loker) -> bool:
    sheet = get_sheet()
    if not sheet: return False
    try:
        cell = sheet.find(nama_loker)
        sheet.delete_rows(cell.row)
        return True
    except:
        return False

# ─────────────────────────────────────────
#  LOGIKA AI & SMART SEARCH
# ─────────────────────────────────────────

def format_info_untuk_ai(pertanyaan_user: str) -> str:
    """Mencari data yang relevan agar tidak melebihi limit 6000 token Groq."""
    data = load_info()
    if not data: return ""

    pertanyaan_lower = pertanyaan_user.lower()
    # Kata-kata pendek yang tidak informatif (stop words)
    stop_words = {"pt", "di", "dan", "yang", "ada", "info", "tentang", "loker",
                  "untuk", "ke", "ini", "itu", "ya", "dong", "apa", "ada", "mau",
                  "cari", "saya", "aku", "bisa", "kasih", "tahu", "tolong"}
    
    # Ambil kata kunci bermakna dari pertanyaan user (min 3 karakter, bukan stop word)
    kata_pertanyaan = [
        k for k in pertanyaan_lower.split()
        if len(k) >= 3 and k not in stop_words
    ]

    hasil_relevan = []
    skor = {}

    for nama, info in data.items():
        nama_lower = nama.lower()
        gabungan = (nama_lower + " " + info.lower())
        nilai = 0

        # Skor: setiap kata dari pertanyaan yang ditemukan di nama/info loker
        for kata in kata_pertanyaan:
            if kata in nama_lower:
                nilai += 3   # bobot lebih tinggi jika match di nama
            elif kata in gabungan:
                nilai += 1

        if nilai > 0:
            skor[nama] = nilai

    # Urutkan berdasarkan skor tertinggi
    nama_terurut = sorted(skor, key=lambda x: skor[x], reverse=True)
    for nama in nama_terurut[:5]:
        hasil_relevan.append(f"• {nama}: {data[nama][:800]}")

    # Jika tidak ada yang cocok sama sekali, kirim 5 data terbaru sebagai konteks umum
    if not hasil_relevan:
        items = list(data.items())[-5:]
        for nama, info in items:
            hasil_relevan.append(f"• {nama}: {info[:500]}")

    return "REFERENSI DATA LOKER:\n" + "\n".join(hasil_relevan)

def tanya_groq(pesan: str) -> str:
    info_admin = format_info_untuk_ai(pesan)
    pesan_konteks = f"{info_admin}\n\nPertanyaan: {pesan}" if info_admin else pesan
    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": "llama-3.1-8b-instant",
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": pesan_konteks},
                ],
                "max_tokens": 700
            },
            timeout=15
        )
        return response.json()["choices"][0]["message"]["content"]
    except:
        return "Maaf, AI sedang sibuk. Coba lagi sebentar ya! 🙏"

# ─────────────────────────────────────────
#  COMMAND HANDLERS
# ─────────────────────────────────────────

async def cmd_tambah(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.username not in ADMIN_USERNAMES: return
    text = " ".join(context.args)
    if "|" not in text:
        await update.message.reply_text("Format: /tambah Nama Loker | Info Lengkap")
        return
    nama, info = text.split("|", 1)
    if simpan_info(nama.strip(), info.strip()):
        await update.message.reply_text(f"✅ Berhasil menyimpan: {nama.strip()}")
    else:
        await update.message.reply_text("❌ Gagal menyimpan ke Google Sheets.")

async def cmd_hapus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.username not in ADMIN_USERNAMES: return
    nama = " ".join(context.args)
    if hapus_info(nama):
        await update.message.reply_text(f"🗑️ Loker '{nama}' berhasil dihapus.")
    else:
        await update.message.reply_text("❌ Data tidak ditemukan.")

async def cmd_cari(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyword = " ".join(context.args).lower()
    if not keyword:
        await update.message.reply_text("Format: /cari [posisi]")
        return
    data = load_info()
    hasil = [f"📌 *{n}*\n{i[:150]}..." for n, i in data.items() if keyword in n.lower()]
    if hasil:
        await update.message.reply_text("🔍 *Hasil Pencarian:*\n\n" + "\n\n".join(hasil[:10]), parse_mode="Markdown")
    else:
        await update.message.reply_text(f"❌ Tidak ditemukan loker untuk '{keyword}'.")

async def cmd_daftar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_info()
    if not data:
        await update.message.reply_text("📭 Database loker masih kosong.")
        return
    baris = [f"{i}. *{n}*" for i, n in enumerate(list(data.keys())[-15:], 1)]
    await update.message.reply_text("📋 *15 Loker Terbaru:*\n\n" + "\n".join(baris), parse_mode="Markdown")

async def auto_balas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pesan = update.message.text
    if not pesan: return

    username = update.effective_user.username
    pesan_lower = pesan.lower()

    # 1. AUTO-SIMPAN LOKER dari Admin (format: Nama Loker | Info Lengkap)
    #    Admin cukup posting langsung tanpa /tambah
    if username in ADMIN_USERNAMES and "|" in pesan and len(pesan) > 30:
        nama, info = pesan.split("|", 1)
        nama = nama.strip()
        info = info.strip()
        if nama and info:
            if simpan_info(nama, info):
                await update.message.reply_text(f"✅ Loker *{nama}* berhasil disimpan ke database!", parse_mode="Markdown")
            else:
                await update.message.reply_text("⚠️ Gagal menyimpan ke Google Sheets.")
            return

    # 2. Cek Kata Kunci Tetap — hanya untuk pesan PENDEK (bukan postingan loker)
    if len(pesan) < 80:
        for k, v in KATA_KUNCI.items():
            if k in pesan_lower:
                await update.message.reply_text(v)
                return

    # 3. Respon AI (Mention/Reply)
    bot_username = f"@{context.bot.username}".lower()
    is_replied = update.message.reply_to_message and update.message.reply_to_message.from_user.id == context.bot.id
    if bot_username in pesan_lower or is_replied:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        await update.message.reply_text(tanya_groq(pesan))

# ─────────────────────────────────────────
#  MAIN RUNNER
# ─────────────────────────────────────────

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("tambah",    cmd_tambah))
    app.add_handler(CommandHandler("hapus",     cmd_hapus))
    app.add_handler(CommandHandler("cari",      cmd_cari))
    app.add_handler(CommandHandler("daftar",    cmd_daftar))
    app.add_handler(CommandHandler("bikin_CV",  lambda u, c: u.message.reply_text("📄 Klik di sini: https://t.me/c/1211036502/2919533")))
    app.add_handler(CommandHandler("start",     lambda u, c: u.message.reply_text("Bot Aktif! ✅")))
    
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, auto_balas))
    
    print("Bot sedang berjalan...")
    app.run_polling()

if __name__ == "__main__":
    main()