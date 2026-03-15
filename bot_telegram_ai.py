"""
Bot Telegram Auto Balas — Kata Kunci + Groq AI (GRATIS)
========================================================
Cara pakai:
1. py -m pip install python-telegram-bot requests
2. Isi TOKEN dan GROQ_API_KEY di bawah
3. Matikan Privacy Mode bot via @BotFather (/setprivacy → Disable)
4. Tambahkan bot ke grup & jadikan Admin
5. Jalankan: py bot_telegram_ai.py

Alur:
  Pesan masuk → Cek kata kunci → (cocok) langsung balas
                               → (tidak cocok) tanya ke Groq AI → balas
"""

import logging
import os
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

TOKEN           = os.environ.get("TOKEN", "ISI_TOKEN_BOT_TELEGRAM_KAMU")
GROQ_API_KEY    = os.environ.get("GROQ_API_KEY", "ISI_GROQ_API_KEY_KAMU")

# Kepribadian bot AI — khusus grup lowongan kerja
SYSTEM_PROMPT = """Kamu adalah asisten grup Telegram khusus lowongan kerja yang ramah, profesional, dan helpful.
Tugasmu membantu anggota grup dalam hal:
- Mencari informasi seputar lowongan kerja
- Tips melamar kerja, membuat CV, dan persiapan interview
- Penjelasan istilah-istilah dunia kerja (HRD, fresh graduate, kontrak, PKWT, dll)
- Saran karier dan pengembangan diri

Jawab dalam Bahasa Indonesia yang santai tapi tetap profesional.
Berikan jawaban yang singkat, jelas, dan padat (maks 4-5 kalimat).
Jika ditanya lowongan spesifik yang kamu tidak tahu, sarankan untuk cek di Jobstreet, LinkedIn, Glints, atau Kalibrr.
Jangan pernah menjanjikan pekerjaan atau memberikan informasi palsu."""

# Kata kunci (diproses duluan sebelum ke AI)
# Format: "kata_kunci": "balasan"
KATA_KUNCI = {
    # Sapaan
    "halo"          : "Halo! 👋 Selamat datang di grup lowongan kerja. Ada yang bisa dibantu?",
    "hai"           : "Hai! 😊 Mau cari lowongan atau butuh tips karier? Tanya aja!",
    "selamat pagi"  : "Selamat pagi! ☀️ Semangat berburu kerja hari ini! 💼",
    "selamat siang" : "Selamat siang! 🌤️ Ada info lowongan atau pertanyaan seputar karier?",
    "selamat malam" : "Selamat malam! 🌙 Masih semangat cari kerja? Tanya aja ke saya!",

    # Lowongan & melamar
    "cara melamar"  : "Cara melamar kerja:\n1️⃣ Siapkan CV & surat lamaran\n2️⃣ Cek kualifikasi lowongan\n3️⃣ Kirim via email / portal resmi\n4️⃣ Follow up 3-5 hari setelah melamar\n\n💡 Pastikan CV kamu ATS-friendly ya!",
    "lowongan"      : "Info lowongan terbaru ada di pinned message grup ini! 📌\nBisa juga cek di:\n🔹 Jobstreet\n🔹 LinkedIn\n🔹 Glints\n🔹 Kalibrr\n🔹 Indeed",
    "loker"         : "Cek lowongan terbaru di pinned message grup ini ya! 📌\nJangan lupa aktifkan notifikasi grup supaya tidak ketinggalan info loker!",
    "fresh graduate": "Untuk fresh graduate, platform yang cocok:\n🎓 Glints (banyak entry level)\n🎓 Kalibrr\n🎓 LinkedIn (aktifkan #OpenToWork)\n🎓 Jobstreet\n\nTips: tonjolkan pengalaman magang, organisasi, dan proyek kuliah di CV!",

    # CV & dokumen
    "cv"            : "Tips CV yang baik:\n✅ Maksimal 1-2 halaman\n✅ Format ATS-friendly (hindari tabel/foto berlebihan)\n✅ Tulis pencapaian, bukan sekadar tugas\n✅ Sesuaikan dengan job desc\n\nMau tips CV lebih detail? Tanya aja! 📄",
    "surat lamaran" : "Tips surat lamaran:\n✅ Singkat dan to the point (maks 1 halaman)\n✅ Sebutkan posisi yang dilamar\n✅ Jelaskan kenapa kamu cocok\n✅ Tunjukkan antusiasmemu\n\nJangan copy-paste template generik ya! 📝",
    "portofolio"    : "Portofolio penting terutama untuk bidang kreatif, tech, dan desain.\nBuat di: Behance, GitHub, Notion, atau Google Drive.\nPastikan mudah diakses dan rapi! 🗂️",

    # Interview
    "interview"     : "Tips sukses interview:\n💬 Pelajari profil perusahaan\n💬 Siapkan jawaban STAR (Situation, Task, Action, Result)\n💬 Latihan jawab pertanyaan umum\n💬 Datang/join tepat waktu\n💬 Siapkan pertanyaan untuk interviewer\n\nSemangat! 💪",
    "gaji"          : "Tips negosiasi gaji:\n💰 Riset gaji pasaran posisi tersebut\n💰 Sebutkan range, bukan angka pasti\n💰 Percaya diri dan dukung dengan pengalaman\n\nCek benchmark gaji di: Jobstreet Salary Report atau LinkedIn Salary Insights 📊",
    "psikotes"      : "Tips psikotes:\n🧠 Istirahat cukup sebelum tes\n🧠 Latihan soal TPA, numerik, verbal\n🧠 Jawab jujur untuk tes kepribadian\n🧠 Kelola waktu dengan baik\n\nLatihan di: TryOut.id atau aplikasi psikotes online 📱",

    # Istilah kerja
    "pkwt"          : "PKWT = Perjanjian Kerja Waktu Tertentu (kontrak).\nArtinya karyawan bekerja dalam jangka waktu tertentu sesuai kontrak.\nBerbeda dengan PKWTT (karyawan tetap). Pastikan baca kontrak dengan teliti ya! 📋",
    "magang"        : "Info magang:\n🎓 Cek Magang Merdeka (kampusmerdeka.kemdikbud.go.id)\n🎓 Glints & Kalibrr juga banyak lowongan magang\n🎓 LinkedIn — filter 'Internship'\n\nManfaatkan magang untuk bangun networking dan pengalaman! 💼",
    "resign"        : "Tips resign yang profesional:\n📝 Ajukan surat resign minimal 1 bulan sebelumnya\n📝 Selesaikan semua tanggung jawab\n📝 Jaga hubungan baik dengan rekan & atasan\n📝 Minta surat referensi jika perlu\n\nJangan lupa: dunia kerja itu sempit! 🤝",
    "linkedin"      : "Tips optimalkan LinkedIn:\n✅ Foto profesional\n✅ Headline yang menarik\n✅ Summary yang menggambarkan dirimu\n✅ Aktif posting & engage konten\n✅ Minta rekomendasi dari rekan/atasan\n✅ Aktifkan #OpenToWork 🔓",

    # Umum
    "terima kasih"  : "Sama-sama! 😊 Semoga segera dapat kerja yang sesuai ya! 🍀",
    "makasih"       : "Sama-sama! 🙏 Good luck job hunting-nya!",
    "thanks"        : "You're welcome! Good luck! 💪",
    "semangat"      : "Semangat terus! 💪 Rejeki tidak akan ke mana, yang penting terus usaha dan jangan mudah menyerah! 🌟",
}

# ─────────────────────────────────────────
#  PENGATURAN TAMBAHAN
# ─────────────────────────────────────────

# Bot hanya aktif di grup? (True = grup saja, False = grup + private)
HANYA_DI_GRUP = True

# Bot AI hanya balas kalau di-mention (@username_bot)?
# True = harus di-mention dulu | False = balas semua pesan (kalau tidak ada kata kunci)
AI_HANYA_JIKA_MENTION = True

AKTIFKAN_LOG = True

# ─────────────────────────────────────────
#  KODE BOT — tidak perlu diedit
# ─────────────────────────────────────────

if AKTIFKAN_LOG:
    logging.basicConfig(
        format="%(asctime)s | %(levelname)s | %(message)s",
        level=logging.INFO
    )

logger = logging.getLogger(__name__)


def tanya_groq(pesan: str) -> str:
    """Kirim pesan ke Groq AI dan kembalikan balasannya."""
    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "llama-3.3-70b-versatile",  # Model gratis terbaik di Groq
                "max_tokens": 500,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": pesan},
                ],
            },
            timeout=15,
        )
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"Error Groq API: {e}")
        return "Maaf, saya sedang tidak bisa memproses pertanyaanmu. Silakan hubungi admin ya! 🙏"


async def auto_balas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler utama: cek kata kunci → kalau tidak ada, tanya ke Groq AI."""
    pesan = update.message.text
    if not pesan:
        return

    pesan_lower  = pesan.lower()
    pengirim     = update.message.from_user.username or update.message.from_user.first_name
    bot_username = f"@{context.bot.username}".lower()
    di_mention   = bot_username in pesan_lower

    logger.info(f"[{update.message.chat.type}] @{pengirim}: {pesan[:80]}")

    # ── 1. Cek kata kunci dulu ──
    for kata, balasan in KATA_KUNCI.items():
        if kata in pesan_lower:
            logger.info(f"  → Kata kunci cocok: '{kata}'")
            await update.message.reply_text(balasan)
            return

    # ── 2. Kalau tidak ada kata kunci → tanya Groq AI ──
    if AI_HANYA_JIKA_MENTION and not di_mention:
        return

    logger.info("  → Tidak ada kata kunci, tanya ke Groq AI...")

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing"
    )

    balasan_ai = tanya_groq(pesan)
    await update.message.reply_text(balasan_ai)


async def welcome_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sambut member baru."""
    for member in update.message.new_chat_members:
        await update.message.reply_text(
            f"Selamat datang, {member.full_name}! 🎉\n\n"
            "Grup ini khusus info lowongan kerja & tips karier. "
            "Tanya apa saja ke bot kami, siap membantu! 🤖💼"
        )


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Bot aktif! ✅\n"
        "Saya siap menjawab pertanyaan seputar lowongan kerja & karier. "
        "Gunakan kata kunci atau tanya bebas — saya akan bantu dengan AI! 🤖"
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    daftar = "\n".join([f"• {k}" for k in KATA_KUNCI.keys()])
    await update.message.reply_text(
        f"📋 Kata kunci yang langsung saya kenali:\n\n{daftar}\n\n"
        "💡 Pertanyaan lain di luar daftar ini akan dijawab oleh AI secara otomatis!"
    )


def main():
    app = ApplicationBuilder().token(TOKEN).build()

    if HANYA_DI_GRUP:
        chat_filter = filters.TEXT & filters.ChatType.GROUPS
    else:
        chat_filter = filters.TEXT

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_member))
    app.add_handler(MessageHandler(chat_filter & ~filters.COMMAND, auto_balas))

    print("=" * 45)
    print("  Bot Telegram + Groq AI berjalan 🤖✨")
    print("  Tekan Ctrl+C untuk berhenti")
    print("=" * 45)

    app.run_polling()


if __name__ == "__main__":
    main()
