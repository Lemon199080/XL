# login_handler.py
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from bot.database import db
from app.client.ciam import get_otp, submit_otp
from app.client.engsel import get_profile
from app.util import ensure_api_key

# Conversation states
LOGIN_PHONE, LOGIN_OTP = range(2)


async def login_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start login process"""
    user = update.effective_user
    
    text = (
        "🔐 <b>Login ke MyXL</b>\n\n"
        "Masukkan nomor XL Anda (format: 628xxxxxxxxxx)\n\n"
        "Contoh: 6281234567890\n\n"
        "Gunakan /cancel untuk membatalkan."
    )
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode='HTML')
    else:
        await update.message.reply_text(text, parse_mode='HTML')
    
    return LOGIN_PHONE


async def receive_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive phone number and request OTP"""
    phone_number = update.message.text.strip()
    
    # Validate phone number
    if not phone_number.startswith("628") or len(phone_number) < 11 or len(phone_number) > 14:
        await update.message.reply_text(
            "❌ Nomor tidak valid.\n\n"
            "Pastikan nomor diawali dengan '628' dan memiliki panjang 11-14 digit.\n\n"
            "Silakan coba lagi:"
        )
        return LOGIN_PHONE
    
    # Request OTP
    await update.message.reply_text("⏳ Meminta OTP...")
    
    try:
        subscriber_id = get_otp(phone_number)
        
        if not subscriber_id:
            await update.message.reply_text(
                "❌ Gagal mengirim OTP. Silakan coba lagi.\n\n"
                "Gunakan /cancel untuk membatalkan atau kirim nomor lagi."
            )
            return LOGIN_PHONE
        
        # Store data in context
        context.user_data['phone_number'] = phone_number
        context.user_data['subscriber_id'] = subscriber_id
        context.user_data['otp_attempts'] = 0
        
        await update.message.reply_text(
            "✅ OTP berhasil dikirim!\n\n"
            "Masukkan 6 digit kode OTP yang dikirim ke nomor Anda:\n\n"
            "Gunakan /cancel untuk membatalkan."
        )
        
        return LOGIN_OTP
        
    except Exception as e:
        await update.message.reply_text(
            f"❌ Terjadi kesalahan: {str(e)}\n\n"
            "Gunakan /cancel untuk membatalkan atau kirim nomor lagi."
        )
        return LOGIN_PHONE


async def receive_otp(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive OTP and complete login"""
    otp_code = update.message.text.strip()
    
    # Validate OTP format
    if not otp_code.isdigit() or len(otp_code) != 6:
        await update.message.reply_text(
            "❌ Kode OTP tidak valid.\n\n"
            "Pastikan kode OTP terdiri dari 6 digit angka.\n\n"
            "Silakan coba lagi:"
        )
        return LOGIN_OTP
    
    # Get stored data
    phone_number = context.user_data.get('phone_number')
    subscriber_id = context.user_data.get('subscriber_id')
    attempts = context.user_data.get('otp_attempts', 0)
    
    if attempts >= 5:
        await update.message.reply_text(
            "❌ Terlalu banyak percobaan gagal.\n\n"
            "Gunakan /login untuk memulai lagi."
        )
        return ConversationHandler.END
    
    await update.message.reply_text("⏳ Memverifikasi OTP...")
    
    try:
        # Get API key
        api_key = ensure_api_key()
        
        # Submit OTP
        tokens = submit_otp(api_key, "SMS", phone_number, otp_code)
        
        if not tokens:
            context.user_data['otp_attempts'] = attempts + 1
            remaining = 5 - (attempts + 1)
            
            await update.message.reply_text(
                f"❌ Kode OTP salah.\n\n"
                f"Sisa percobaan: {remaining}\n\n"
                "Silakan coba lagi:"
            )
            return LOGIN_OTP
        
        # Get profile info
        profile_data = get_profile(api_key, tokens['access_token'], tokens['id_token'])
        subscription_type = profile_data['profile']['subscription_type']
        
        # Save to database
        user = update.effective_user
        success = db.add_xl_account(
            telegram_id=user.id,
            phone_number=phone_number,
            refresh_token=tokens['refresh_token'],
            subscriber_id=subscriber_id,
            subscription_type=subscription_type
        )
        
        # Update tokens
        db.update_xl_tokens(
            telegram_id=user.id,
            phone_number=phone_number,
            access_token=tokens['access_token'],
            id_token=tokens['id_token']
        )
        
        if success:
            await update.message.reply_text(
                "✅ <b>Login berhasil!</b>\n\n"
                f"Nomor: {phone_number}\n"
                f"Tipe: {subscription_type}\n\n"
                "Mengalihkan ke menu utama...",
                parse_mode='HTML'
            )
            
            # Clear context data
            context.user_data.clear()
            
            # Show main menu
            from bot.handlers.start_handler import show_main_menu
            await show_main_menu(update, context)
            
            return ConversationHandler.END
        else:
            await update.message.reply_text(
                "❌ Gagal menyimpan akun. Silakan coba lagi.\n\n"
                "Gunakan /login untuk memulai lagi."
            )
            return ConversationHandler.END
            
    except Exception as e:
        await update.message.reply_text(
            f"❌ Terjadi kesalahan: {str(e)}\n\n"
            "Gunakan /login untuk memulai lagi."
        )
        return ConversationHandler.END


async def cancel_login(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel login process"""
    context.user_data.clear()
    
    await update.message.reply_text(
        "❌ Proses login dibatalkan.\n\n"
        "Gunakan /start untuk kembali ke menu utama."
    )
    
    return ConversationHandler.END