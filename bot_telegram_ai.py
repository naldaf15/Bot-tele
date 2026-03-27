"""
Bot Telegram Auto Balas — Kata Kunci + Google Sheets + Groq AI (GRATIS)
=======================================================================
Cara pakai:
1. py -m pip install python-telegram-bot requests gspread google-auth
2. Set variabel di Railway: TOKEN, GROQ_API_KEY, SHEET_ID, GOOGLE_CREDENTIALS
3. Jalankan: py bot_telegram_ai.py
"""

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

# Isi dengan username admin (tanpa @)
ADMIN_USERNAMES = ["Random_Email"]

# Kepribadian bot AI
SYSTEM_PROMPT = """Kamu adalah asisten grup Telegram khusus lowongan kerja yang ramah, profesional, dan helpful.
Tugasmu membantu anggota grup dalam hal:
- Mencari informasi seputar lowongan kerja
- Tips melamar kerja, membuat CV, dan persiapan interview
- Penjelasan istilah-istilah dunia kerja (HRD, fresh graduate, kontrak, PKWT, dll)
- Saran karier dan pengembangan diri

Jawab dalam Bahasa Indonesia yang santai tapi tetap profesional.
Berikan jawaban yang singkat, jelas, dan padat (maks 4-5 kalimat).
Jika ada INFO TERBARU DARI ADMIN di bawah, prioritaskan info tersebut dalam jawabanmu.
Jangan pernah menjanjikan pekerjaan atau memberikan informasi palsu."""

# Kata kunci tetap
KATA_KUNCI = {
    "halo"          : "Halo! 👋 Selamat datang di grup lowongan kerja. Ada yang bisa dibantu?",
    "hai"           : "Hai! 😊 Mau cari lowongan atau butuh tips karier? Tanya aja!",
    "selamat pagi"  : "Selamat pagi! ☀️ Semangat berburu kerja hari ini! 💼",
    "selamat siang" : "Selamat siang! 🌤️ Ada info lowongan atau pertanyaan seputar karier?",
    "selamat malam" : "Selamat malam! 🌙 Masih semangat cari kerja? Tanya aja ke saya!",
    "cara melamar"  : "Cara melamar kerja:\n1️⃣ Siapkan CV & surat lamaran\n2️⃣ Cek kualifikasi lowongan\n3️⃣ Kirim via email / portal resmi\n4️⃣ Follow up 3-5 hari setelah melamar\n\n💡 Pastikan CV kamu ATS-friendly ya!",
    "lowongan"      : "Info lowongan terbaru ada di pinned message grup ini! 📌\nBisa juga cek di:\n🔹 Jobstreet\n🔹 LinkedIn\n🔹 Glints\n🔹 Kalibrr\n🔹 Indeed",
    "loker"         : "Cek lowongan terbaru di pinned message grup ini ya! 📌\nJangan lupa aktifkan notifikasi grup supaya tidak ketinggalan info loker!",
    "fresh graduate": "Untuk fresh graduate, platform yang cocok:\n🎓 Glints (banyak entry level)\n🎓 Kalibrr\n🎓 LinkedIn (aktifkan #OpenToWork)\n🎓 Jobstreet\n\nTips: tonjolkan pengalaman magang, organisasi, dan proyek kuliah di CV!",
    "cv"            : "Tips CV yang baik:\n✅ Maksimal 1-2 halaman\n✅ Format ATS-friendly (hindari tabel/foto berlebihan)\n✅ Tulis pencapaian, bukan sekadar tugas\n✅ Sesuaikan dengan job desc\n\nMau tips CV lebih detail? Tanya aja! 📄",
    "surat lamaran" : "Tips surat lamaran:\n✅ Singkat dan to the point (maks 1 halaman)\n✅ Sebutkan posisi yang dilamar\n✅ Jelaskan kenapa kamu cocok\n✅ Tunjukkan antusiasmemu\n\nJangan copy-paste template generik ya! 📝",
    "portofolio"    : "Portofolio penting terutama untuk bidang kreatif, tech, dan desain.\nBuat di: Behance, GitHub, Notion, atau Google Drive.\nPastikan mudah diakses dan rapi! 🗂️",
    "interview"     : "Tips sukses interview:\n💬 Pelajari profil perusahaan\n💬 Siapkan jawaban STAR (Situation, Task, Action, Result)\n💬 Latihan jawab pertanyaan umum\n💬 Datang/join tepat waktu\n💬 Siapkan pertanyaan untuk interviewer\n\nSemangat! 💪",
    "gaji"          : "Tips negosiasi gaji:\n💰 Riset gaji pasaran posisi tersebut\n💰 Sebutkan range, bukan angka pasti\n💰 Percaya diri dan dukung dengan pengalaman\n\nCek benchmark gaji di: Jobstreet Salary Report atau LinkedIn Salary Insights 📊",
    "psikotes"      : "Tips psikotes:\n🧠 Istirahat cukup sebelum tes\n🧠 Latihan soal TPA, numerik, verbal\n🧠 Jawab jujur untuk tes kepribadian\n🧠 Kelola waktu dengan baik\n\nLatihan di: TryOut.id atau aplikasi psikotes online 📱",
    "pkwt"          : "PKWT = Perjanjian Kerja Waktu Tertentu (kontrak).\nArtinya karyawan bekerja dalam jangka waktu tertentu sesuai kontrak.\nBerbeda dengan PKWTT (karyawan tetap). Pastikan baca kontrak dengan teliti ya! 📋",
    "magang"        : "Info magang:\n🎓 Cek Magang Merdeka (kampusmerdeka.kemdikbud.go.id)\n🎓 Glints & Kalibrr juga banyak lowongan magang\n🎓 LinkedIn — filter 'Internship'\n\nManfaatkan magang untuk bangun networking dan pengalaman! 💼",
    "resign"        : "Tips resign yang profesional:\n📝 Ajukan surat resign minimal 1 bulan sebelumnya\n📝 Selesaikan semua tanggung jawab\n📝 Jaga hubungan baik dengan rekan & atasan\n📝 Minta surat referensi jika perlu\n\nJangan lupa: dunia kerja itu sempit! 🤝",
    "linkedin"      : "Tips optimalkan LinkedIn:\n✅ Foto profesional\n✅ Headline yang menarik\n✅ Summary yang menggambarkan dirimu\n✅ Aktif posting & engage konten\n✅ Minta rekomendasi dari rekan/atasan\n✅ Aktifkan #OpenToWork 🔓",
    "terima kasih"  : "Sama-sama! 😊 Semoga segera dapat kerja yang sesuai ya! 🍀",
    "makasih"       : "Sama-sama! 🙏 Good luck job hunting-nya!",
    "thanks"        : "You're welcome! Good luck! 💪",
    "semangat"      : "Semangat terus! 💪 Rejeki tidak akan ke mana, yang penting terus usaha dan jangan mudah menyerah! 🌟",
}

# ─────────────────────────────────────────
#  PENGATURAN TAMBAHAN
# ─────────────────────────────────────────

HANYA_DI_GRUP         = True
AKTIFKAN_LOG          = True

# ─────────────────────────────────────────
#  KODE BOT
# ─────────────────────────────────────────

if AKTIFKAN_LOG:
    logging.basicConfig(
        format="%(asctime)s | %(levelname)s | %(message)s",
        level=logging.INFO
    )

logger = logging.getLogger(__name__)


# ── Google Sheets ──

def get_sheet():
    """Koneksi ke Google Sheets."""
    try:
        creds_dict = json.loads(GOOGLE_CREDS)
        scopes     = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds      = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client     = gspread.authorize(creds)
        sheet      = client.open_by_key(SHEET_ID).sheet1
        return sheet
    except Exception as e:
        logger.error(f"Error koneksi Google Sheets: {e}")
        return None

def load_info() -> dict:
    """Load semua info dari Google Sheets."""
    sheet = get_sheet()
    if not sheet:
        return {}
    try:
        rows = sheet.get_all_records()
        return {row["nama"]: row["info"] for row in rows if row.get("nama")}
    except Exception as e:
        logger.error(f"Error load info: {e}")
        return {}

def tambah_info(nama: str, info: str) -> bool:
    """Tambah info baru ke Google Sheets."""
    sheet = get_sheet()
    if not sheet:
        return False
    try:
        # Cek kalau nama sudah ada, update
        rows = sheet.get_all_records()
        for i, row in enumerate(rows, start=2):
            if row.get("nama", "").lower() == nama.lower():
                sheet.update(f"A{i}:C{i}", [[nama, info, datetime.now().strftime("%Y-%m-%d %H:%M")]])
                return True
        # Kalau belum ada, tambah baris baru
        sheet.append_row([nama, info, datetime.now().strftime("%Y-%m-%d %H:%M")])
        return True
    except Exception as e:
        logger.error(f"Error tambah info: {e}")
        return False

def hapus_info(nama: str) -> bool:
    """Hapus info dari Google Sheets."""
    sheet = get_sheet()
    if not sheet:
        return False
    try:
        rows = sheet.get_all_records()
        for i, row in enumerate(rows, start=2):
            if row.get("nama", "").lower() == nama.lower():
                sheet.delete_rows(i)
                return True
        return False
    except Exception as e:
        logger.error(f"Error hapus info: {e}")
        return False

def format_info_untuk_ai() -> str:
    """Format semua info untuk dikirim ke AI."""
    data = load_info()
    if not data:
        return ""
    baris = ["INFO TERBARU DARI ADMIN:"]
    for nama, info in data.items():
        baris.append(f"• {nama}: {info}")
    return "\n".join(baris)

def is_admin(username: str) -> bool:
    return username and username.lower() in [a.lower() for a in ADMIN_USERNAMES]


# ── Groq AI ──

def tanya_groq(pesan: str) -> str:
    info_admin = format_info_untuk_ai()
    pesan_konteks = f"{info_admin}\n\nPertanyaan member: {pesan}" if info_admin else pesan
    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "llama-3.1-8b-instant",
                "max_tokens": 500,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": pesan_konteks},
                ],
            },
            timeout=15,
        )
        data = response.json()
        logger.info(f"Groq response: {data}")
        if "choices" not in data:
            logger.error(f"Groq error response: {data}")
            return "Maaf, AI sedang sibuk. Coba lagi sebentar ya! 🙏"
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"Error Groq API: {e}")
        return "Maaf, saya sedang tidak bisa memproses pertanyaanmu. Silakan hubungi admin ya! 🙏"


# ── Perintah Admin ──

async def cmd_tambah(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/tambah nama | deskripsi"""
    username = update.message.from_user.username or ""
    if not is_admin(username):
        await update.message.reply_text("⛔ Perintah ini hanya untuk admin.")
        return

    teks = " ".join(context.args)
    if "|" not in teks:
        await update.message.reply_text(
            "Format:\n/tambah nama_loker | deskripsi lengkap\n\n"
            "Contoh:\n/tambah PT Yamaha | Staff Admin, gaji 4-6jt, email: hrd@yamaha.co.id, deadline 30 Maret"
        )
        return

    nama, info = teks.split("|", 1)
    nama = nama.strip()
    info = info.strip()

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    if tambah_info(nama, info):
        await update.message.reply_text(
            f"✅ Info berhasil disimpan ke Google Sheets!\n\n📌 *{nama}*\n{info}",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("❌ Gagal menyimpan. Coba lagi ya!")


async def cmd_hapus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/hapus nama"""
    username = update.message.from_user.username or ""
    if not is_admin(username):
        await update.message.reply_text("⛔ Perintah ini hanya untuk admin.")
        return

    nama = " ".join(context.args).strip()
    if not nama:
        await update.message.reply_text("Format: /hapus nama_loker")
        return

    if hapus_info(nama):
        await update.message.reply_text(f"🗑️ Info *{nama}* berhasil dihapus.", parse_mode="Markdown")
    else:
        await update.message.reply_text(f"❌ Info *{nama}* tidak ditemukan.\n\nKetik /daftar untuk lihat semua info.", parse_mode="Markdown")


async def cmd_daftar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/daftar"""
    username = update.message.from_user.username or ""
    if not is_admin(username):
        await update.message.reply_text("⛔ Perintah ini hanya untuk admin.")
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    data = load_info()

    if not data:
        await update.message.reply_text("📭 Belum ada info tersimpan.\n\nTambahkan dengan:\n/tambah nama | deskripsi")
        return

    baris = ["📋 *Daftar Info Tersimpan:*\n"]
    for i, (nama, info) in enumerate(data.items(), 1):
        baris.append(f"{i}. *{nama}*\n   {info[:120]}{'...' if len(info) > 120 else ''}")

    await update.message.reply_text("\n\n".join(baris), parse_mode="Markdown")


async def cmd_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/broadcast pesan"""
    username = update.message.from_user.username or ""
    if not is_admin(username):
        await update.message.reply_text("⛔ Perintah ini hanya untuk admin.")
        return

    pesan = " ".join(context.args)
    if not pesan:
        await update.message.reply_text("Format: /broadcast isi pesanmu")
        return

    await update.message.reply_text(f"📢 *INFO TERBARU*\n\n{pesan}", parse_mode="Markdown")


# ── Handler Pesan ──

def extract_linkedin_url(teks: str) -> str:
    """Cari link LinkedIn dalam teks (jobs, posts, atau URL apapun dari linkedin.com)."""
    import re
    pattern = r'https?://(?:www\.)?linkedin\.com/[^\s]+'
    match = re.search(pattern, teks)
    return match.group(0) if match else ""

async def auto_balas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pesan = update.message.text
    if not pesan:
        return

    pesan_lower  = pesan.lower()
    pengirim     = update.message.from_user.username or update.message.from_user.first_name
    bot_username = f"@{context.bot.username}".lower()
    di_mention   = bot_username in pesan_lower

    di_reply_ke_bot = (
        update.message.reply_to_message is not None and
        update.message.reply_to_message.from_user.id == context.bot.id
    )

    logger.info(f"[{update.message.chat.type}] @{pengirim}: {pesan[:80]}")

    # ── Deteksi link LinkedIn dari admin ──
    linkedin_url = extract_linkedin_url(pesan)
    if linkedin_url and is_admin(pengirim):
        from datetime import datetime

        # Pisahkan semua baris, buang yang kosong
        baris = [b.strip() for b in pesan.strip().splitlines() if b.strip()]

        # Pisahkan baris URL dan bukan URL
        baris_info = [b for b in baris if not b.startswith("http")]
        baris_url  = [b for b in baris if b.startswith("http")]

        if baris_info:
            nama_auto = baris_info[0]
            # Gabung semua info + URL jadi SATU baris dengan pemisah " | "
            detail    = baris_info[1:] + [f"Link: {u}" for u in baris_url]
            info_simpan = " | ".join(detail) if detail else f"Link: {linkedin_url}"
        else:
            nama_auto   = f"Loker LinkedIn {datetime.now().strftime('%d/%m %H:%M')}"
            info_simpan = f"Link: {linkedin_url}"

        if tambah_info(nama_auto, info_simpan):
            # Tampilkan preview rapi ke grup
            preview = info_simpan.replace(" | ", "\n")
            await update.message.reply_text(
                f"✅ Lowongan berhasil disimpan!\n\n"
                f"📌 *{nama_auto}*\n{preview}\n\n"
                f"💡 Member bisa tanya ke bot untuk info ini.",
                parse_mode="Markdown"
            )
        return

    # 1. Cek kata kunci
    for kata, balasan in KATA_KUNCI.items():
        if kata in pesan_lower:
            logger.info(f"  → Kata kunci: '{kata}'")
            await update.message.reply_text(balasan)
            return

    # 2. Balas AI kalau di-mention atau reply ke bot
    if not di_mention and not di_reply_ke_bot:
        return

    logger.info("  → Tanya Groq AI + info Google Sheets...")
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    await update.message.reply_text(tanya_groq(pesan))


async def welcome_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        await update.message.reply_text(
            f"Selamat datang, {member.full_name}! 🎉\n\n"
            "Grup ini khusus info lowongan kerja & tips karier. "
            "Tanya apa saja ke bot kami, siap membantu! 🤖💼"
        )



async def cmd_template(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """template command"""
    teks = (
        "*Template Share Lowongan*\n\n"
        "Copy teks berikut, isi datanya, lalu kirim ke grup:\n\n"
        "[Nama Perusahaan] - [Posisi] - [Kota]\n"
        "Posisi: \n"
        "Penempatan: \n"
        "Gaji: \n"
        "Kualifikasi: \n"
        "Email: \n"
        "WhatsApp: \n"
        "Deadline: \n"
        "[Link LinkedIn / URL Lowongan]\n\n"
        "*Contoh:*\n\n"
        "PT Yamaha Motor - Staff Admin - Cikarang\n"
        "Posisi: Staff Administration\n"
        "Penempatan: Cikarang, Jawa Barat\n"
        "Gaji: Rp 4.000.000 - 6.000.000\n"
        "Kualifikasi: Min D3, fresh graduate welcome\n"
        "Email: hrd@yamaha.co.id\n"
        "WhatsApp: 08123456789\n"
        "Deadline: 31 Maret 2026\n"
        "https://linkedin.com/posts/yamaha"
    )
    await update.message.reply_text(teks, parse_mode="Markdown")

async def cmd_bikin_cv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📄 *Pembuatan CV Baru*\n\nUntuk pembuatan CV baru silahkan klik link berikut:\n👉 https://t.me/c/1211036502/2919533",
        parse_mode="Markdown"
    )

async def cmd_update_cv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔄 *Update CV*\n\nUntuk update CV silahkan klik link berikut:\n👉 https://t.me/c/1211036502/2919519",
        parse_mode="Markdown"
    )

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Bot aktif! ✅\n\n"
        "💡 Cara pakai member:\n"
        "• Ketik kata kunci (halo, cv, loker, dll)\n"
        "• Mention: @namabot pertanyaanmu\n"
        "• Reply pesan bot untuk tanya lanjut\n\n"
        "👮 Perintah admin:\n"
        "/tambah nama | deskripsi\n"
        "/hapus nama\n"
        "/daftar\n"
        "/broadcast pesan"
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    daftar = "\n".join([f"• {k}" for k in KATA_KUNCI.keys()])
    await update.message.reply_text(
        f"📋 Kata kunci yang langsung saya kenali:\n\n{daftar}\n\n"
        "💡 Pertanyaan lain? Mention atau reply pesan saya!"
    )


def main():
    app = ApplicationBuilder().token(TOKEN).build()

    if HANYA_DI_GRUP:
        chat_filter = filters.TEXT & filters.ChatType.GROUPS
    else:
        chat_filter = filters.TEXT

    app.add_handler(CommandHandler("tambah",    cmd_tambah))
    app.add_handler(CommandHandler("hapus",     cmd_hapus))
    app.add_handler(CommandHandler("daftar",    cmd_daftar))
    app.add_handler(CommandHandler("broadcast", cmd_broadcast))
    app.add_handler(CommandHandler("start",     cmd_start))
    app.add_handler(CommandHandler("help",      cmd_help))
    app.add_handler(CommandHandler("template",  cmd_template))
    app.add_handler(CommandHandler("bikin_CV",  cmd_bikin_cv))
    app.add_handler(CommandHandler("update_CV", cmd_update_cv))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_member))
    app.add_handler(MessageHandler(chat_filter & ~filters.COMMAND, auto_balas))

    print("=" * 50)
    print("  Bot Telegram + Google Sheets + Groq AI 🤖✨")
    print("  Tekan Ctrl+C untuk berhenti")
    print("=" * 50)

    app.run_polling()


if __name__ == "__main__":
    main()
