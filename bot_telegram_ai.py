"""
Bot Telegram Auto Balas — Kata Kunci + Info Admin + Groq AI (GRATIS)
=====================================================================
Cara pakai:
1. py -m pip install python-telegram-bot requests
2. Isi TOKEN, GROQ_API_KEY, dan ADMIN_IDS di bawah
3. Matikan Privacy Mode bot via @BotFather (/setprivacy → Disable)
4. Tambahkan bot ke grup & jadikan Admin
5. Jalankan: py bot_telegram_ai.py

Perintah admin:
  /tambah nama | deskripsi   → simpan info loker
  /hapus nama                → hapus info loker
  /daftar                    → lihat semua info tersimpan
  /broadcast pesan           → kirim pesan ke semua grup

Alur:
  Pesan masuk → Cek kata kunci → (cocok) langsung balas
                               → (tidak cocok) cek mention/reply
                               → gabungkan info admin + tanya Groq AI → balas
"""

import logging
import os
import json
import requests
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CommandHandler,
    filters,
    ContextTypes,
)

# ─────────────────────────────────────────
#  KONFIGURASI — edit bagian ini
# ─────────────────────────────────────────

TOKEN        = os.environ.get("TOKEN", "ISI_TOKEN_BOT_TELEGRAM_KAMU")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "ISI_GROQ_API_KEY_KAMU")

# Isi dengan username admin (tanpa @), bisa lebih dari satu
ADMIN_USERNAMES = ["Random_Email", "username_admin2"]

# File penyimpanan info dari admin
INFO_FILE = "info_loker.json"

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
AI_HANYA_JIKA_MENTION = True
AKTIFKAN_LOG          = True

# ─────────────────────────────────────────
#  KODE BOT — tidak perlu diedit
# ─────────────────────────────────────────

if AKTIFKAN_LOG:
    logging.basicConfig(
        format="%(asctime)s | %(levelname)s | %(message)s",
        level=logging.INFO
    )

logger = logging.getLogger(__name__)


# ── Manajemen info dari admin ──

def load_info() -> dict:
    """Load info loker dari file JSON."""
    if os.path.exists(INFO_FILE):
        with open(INFO_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_info(data: dict):
    """Simpan info loker ke file JSON."""
    with open(INFO_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def format_info_untuk_ai() -> str:
    """Format semua info admin untuk dikirim ke AI."""
    data = load_info()
    if not data:
        return ""
    baris = ["INFO TERBARU DARI ADMIN:"]
    for nama, isi in data.items():
        baris.append(f"• {nama}: {isi}")
    return "\n".join(baris)

def is_admin(username: str) -> bool:
    """Cek apakah user adalah admin."""
    return username and username.lower() in [a.lower() for a in ADMIN_USERNAMES]


# ── Groq AI ──

def tanya_groq(pesan: str) -> str:
    """Kirim pesan ke Groq AI dengan konteks info admin."""
    info_admin = format_info_untuk_ai()

    # Gabungkan info admin ke dalam pesan kalau ada
    pesan_dengan_konteks = pesan
    if info_admin:
        pesan_dengan_konteks = f"{info_admin}\n\nPertanyaan member: {pesan}"

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "llama-3.3-70b-versatile",
                "max_tokens": 500,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": pesan_dengan_konteks},
                ],
            },
            timeout=15,
        )
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"Error Groq API: {e}")
        return "Maaf, saya sedang tidak bisa memproses pertanyaanmu. Silakan hubungi admin ya! 🙏"


# ── Handler perintah admin ──

async def cmd_tambah(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin tambah info: /tambah nama | deskripsi"""
    username = update.message.from_user.username or ""
    if not is_admin(username):
        await update.message.reply_text("⛔ Perintah ini hanya untuk admin.")
        return

    teks = " ".join(context.args)
    if "|" not in teks:
        await update.message.reply_text(
            "Format salah. Gunakan:\n/tambah nama_loker | deskripsi lengkap\n\n"
            "Contoh:\n/tambah PT Maju Jaya | Lowongan Staff Admin, gaji 4-5jt, domisili Jakarta, kirim CV ke hrd@majujaya.com"
        )
        return

    nama, isi = teks.split("|", 1)
    nama = nama.strip()
    isi  = isi.strip()

    data = load_info()
    data[nama] = isi
    save_info(data)

    logger.info(f"Admin @{username} tambah info: {nama}")
    await update.message.reply_text(f"✅ Info berhasil disimpan!\n\n📌 *{nama}*\n{isi}", parse_mode="Markdown")


async def cmd_hapus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin hapus info: /hapus nama"""
    username = update.message.from_user.username or ""
    if not is_admin(username):
        await update.message.reply_text("⛔ Perintah ini hanya untuk admin.")
        return

    nama = " ".join(context.args).strip()
    if not nama:
        await update.message.reply_text("Format: /hapus nama_loker")
        return

    data = load_info()
    if nama in data:
        del data[nama]
        save_info(data)
        await update.message.reply_text(f"🗑️ Info *{nama}* berhasil dihapus.", parse_mode="Markdown")
    else:
        await update.message.reply_text(f"❌ Info *{nama}* tidak ditemukan.\n\nKetik /daftar untuk lihat semua info.", parse_mode="Markdown")


async def cmd_daftar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lihat semua info tersimpan: /daftar"""
    username = update.message.from_user.username or ""
    if not is_admin(username):
        await update.message.reply_text("⛔ Perintah ini hanya untuk admin.")
        return

    data = load_info()
    if not data:
        await update.message.reply_text("📭 Belum ada info yang tersimpan.\n\nTambahkan dengan:\n/tambah nama | deskripsi")
        return

    baris = ["📋 *Daftar Info Tersimpan:*\n"]
    for i, (nama, isi) in enumerate(data.items(), 1):
        baris.append(f"{i}. *{nama}*\n   {isi[:100]}{'...' if len(isi) > 100 else ''}")

    await update.message.reply_text("\n\n".join(baris), parse_mode="Markdown")


async def cmd_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin broadcast pesan: /broadcast pesan"""
    username = update.message.from_user.username or ""
    if not is_admin(username):
        await update.message.reply_text("⛔ Perintah ini hanya untuk admin.")
        return

    pesan = " ".join(context.args)
    if not pesan:
        await update.message.reply_text("Format: /broadcast isi pesanmu di sini")
        return

    await update.message.reply_text(f"📢 *INFO TERBARU*\n\n{pesan}", parse_mode="Markdown")


# ── Handler pesan biasa ──

async def auto_balas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler utama."""
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

    # ── 1. Cek kata kunci ──
    for kata, balasan in KATA_KUNCI.items():
        if kata in pesan_lower:
            logger.info(f"  → Kata kunci cocok: '{kata}'")
            await update.message.reply_text(balasan)
            return

    # ── 2. Balas AI kalau di-mention atau reply ke bot ──
    if not di_mention and not di_reply_ke_bot:
        return

    logger.info("  → Tanya ke Groq AI dengan konteks info admin...")
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    balasan_ai = tanya_groq(pesan)
    await update.message.reply_text(balasan_ai)


async def welcome_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        await update.message.reply_text(
            f"Selamat datang, {member.full_name}! 🎉\n\n"
            "Grup ini khusus info lowongan kerja & tips karier. "
            "Tanya apa saja ke bot kami, siap membantu! 🤖💼"
        )


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Bot aktif! ✅\n\n"
        "💡 Cara pakai:\n"
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

    # Perintah admin
    app.add_handler(CommandHandler("tambah",    cmd_tambah))
    app.add_handler(CommandHandler("hapus",     cmd_hapus))
    app.add_handler(CommandHandler("daftar",    cmd_daftar))
    app.add_handler(CommandHandler("broadcast", cmd_broadcast))

    # Perintah umum
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help",  cmd_help))

    # Pesan masuk
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_member))
    app.add_handler(MessageHandler(chat_filter & ~filters.COMMAND, auto_balas))

    print("=" * 45)
    print("  Bot Telegram + Groq AI berjalan 🤖✨")
    print("  Tekan Ctrl+C untuk berhenti")
    print("=" * 45)

    app.run_polling()


if __name__ == "__main__":
    main()
