# help_handler.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show help message"""
    query = update.callback_query if update.callback_query else None
    
    text = """
❓ <b>Bantuan MyXL Bot</b>

<b>Perintah Tersedia:</b>
/start - Mulai bot dan tampilkan menu utama
/login - Login dengan nomor XL
/profile - Lihat profil akun
/help - Tampilkan bantuan
/cancel - Batalkan operasi saat ini

<b>Fitur Bot:</b>
🔥 <b>Paket Hot</b> - Lihat paket-paket pilihan terbaik
📦 <b>Paket Saya</b> - Cek paket aktif Anda
🛒 <b>Semua Paket</b> - Jelajahi semua paket available
⭐ <b>Bookmark</b> - Simpan paket favorit
📋 <b>Riwayat</b> - Lihat riwayat transaksi
👨‍👩‍👧 <b>Family Plan</b> - Kelola Family Plan Organizer
⭕ <b>Circle</b> - Info Circle Anda
⚙️ <b>Akun</b> - Kelola multiple akun XL

<b>Cara Penggunaan:</b>

1️⃣ <b>Login</b>
   • Gunakan /login atau tombol Login
   • Masukkan nomor XL (628xxxxxxxxxx)
   • Masukkan kode OTP yang dikirim

2️⃣ <b>Lihat Paket</b>
   • Pilih menu Paket Hot atau Semua Paket
   • Klik paket untuk lihat detail
   • Bookmark paket favorit

3️⃣ <b>Cek Profil & Pulsa</b>
   • Gunakan /profile atau menu Profil
   • Lihat saldo pulsa dan info akun

4️⃣ <b>Multi Akun</b>
   • Login dengan nomor berbeda
   • Switch akun di menu Akun
   • Data terpisah per akun

<b>Tips:</b>
💡 Bot ini aman - data disimpan lokal per user
💡 
💡 Gunakan Bookmark untuk akses cepat
💡 Cek riwayat untuk track pembelian

<b>Dukungan:</b>
Jika ada masalah, gunakan /start untuk restart bot.

━━━━━━━━━━━━━━━━━━━━
Bot by MyXL Axiata Community
"""
    
    keyboard = [[InlineKeyboardButton("🔙 Kembali", callback_data="menu_back")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if query:
        await query.edit_message_text(
            text,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
    else:
        await update.message.reply_text(
            text,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )