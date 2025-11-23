# profile_handler.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.database import db
from bot.utils import get_user_session, format_currency
from datetime import datetime
from html import escape


async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user profile"""
    query = update.callback_query if update.callback_query else None
    user = update.effective_user

    session = get_user_session(user.id)
    if not session:
        text = "❌ Sesi berakhir. Silakan /login kembali."
        if query:
            await query.edit_message_text(text)
        else:
            await update.message.reply_text(text)
        return

    # Show loading
    from bot.loading import show_loading
    
    if query:
        loading_msg = await query.edit_message_text("⏳ Memuat profil...")
    else:
        loading_msg = await update.message.reply_text("⏳ Memuat profil...")

    try:
        from app.client.engsel import get_balance, get_tiering_info

        # ==============================
        # Data dasar dari session
        # ==============================
        phone = escape(str(session.get("phone_number", "-")))
        sub_type = escape(str(session.get("subscription_type", "-")))
        subscriber_id = escape(str(session.get("subscriber_id", "-")))

        # ==============================
        # Get balance
        # ==============================
        balance_text = ""
        try:
            balance = get_balance(session["api_key"], session["tokens"]["id_token"])
        except Exception:
            balance = None

        if balance:
            remaining = balance.get("remaining", 0)
            expired_at = balance.get("expired_at", 0)

            balance_text += f"💰 <b>Saldo Pulsa:</b> {format_currency(remaining)}\n"
            if expired_at:
                exp_date = datetime.fromtimestamp(expired_at).strftime("%d %b %Y")
                balance_text += f"📅 <b>Aktif Sampai:</b> {escape(exp_date)}\n"
        else:
            balance_text += "💰 <b>Saldo Pulsa:</b> -\n"

        # ==============================
        # Tiering info (PREPAID)
        # ==============================
        tier_text = ""
        if session.get("subscription_type") == "PREPAID":
            try:
                tiering = get_tiering_info(session["api_key"], session["tokens"])
                if tiering:
                    tier = tiering.get("tier", 0)
                    current_point = tiering.get("current_point", 0)
                    target = tiering.get("next_target_point") or 10000

                    if target and target > 0:
                        percent = int(current_point / target * 100)
                        percent = max(0, min(percent, 100))
                        bar_len = 10
                        filled = int(percent / (100 / bar_len))
                        bar = "█" * filled + "░" * (bar_len - filled)
                        bar_line = f"{bar} {percent}%"
                    else:
                        bar_line = "────────── N/A"

                    tier_text += "⭐ <b>XL Priority</b>\n"
                    tier_text += f"• Tier   : <b>{tier}</b>\n"
                    tier_text += f"• Points : <b>{current_point:,}</b>\n"
                    tier_text += f"• Progress: {bar_line}\n"
            except Exception:
                # Kalau gagal ambil tiering, profil tetap jalan
                pass

        # ==============================
        # Build text final (tanpa quote/box)
        # ==============================
        text = "👤 <b>Profil Saya</b>\n"
        text += "────────────────────\n\n"
        text += f"📱 <b>Nomor:</b> {phone}\n"
        text += f"📊 <b>Tipe:</b> {sub_type}\n"
        text += f"🆔 <b>Subscriber ID:</b> {subscriber_id}\n\n"

        text += balance_text + "\n"

        if tier_text:
            text += tier_text + "\n"

        text += "────────────────────"

        keyboard = [
            [InlineKeyboardButton("🔄 Refresh", callback_data="menu_profile")],
            [InlineKeyboardButton("🔙 Kembali", callback_data="menu_back")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await loading_msg.edit_text(
            text,
            reply_markup=reply_markup,
            parse_mode="HTML",
        )

    except Exception as e:
        err = escape(str(e))
        text = f"❌ Gagal memuat profil:\n{err}"
        keyboard = [[InlineKeyboardButton("🔙 Kembali", callback_data="menu_back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await loading_msg.edit_text(text, reply_markup=reply_markup, parse_mode="HTML")