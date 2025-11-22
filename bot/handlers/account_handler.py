# account_handler.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.database import db
from bot.utils import refresh_user_session


async def show_accounts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all user accounts"""
    query = update.callback_query if update.callback_query else None
    user = update.effective_user
    
    accounts = db.get_all_xl_accounts(user.id)
    
    if not accounts:
        text = "⚙️ <b>Kelola Akun</b>\n\n"
        text += "Anda belum memiliki akun XL yang terdaftar.\n\n"
        text += "Gunakan /login untuk menambah akun."
        
        keyboard = [[InlineKeyboardButton("🔙 Kembali", callback_data="menu_back")]]
    else:
        text = "⚙️ <b>Kelola Akun</b>\n\n"
        text += f"Total akun: {len(accounts)}\n\n"
        
        keyboard = []
        
        for idx, account in enumerate(accounts, 1):
            phone = account['phone_number']
            sub_type = account.get('subscription_type', 'N/A')
            is_active = account['is_active']
            
            status = "✅ Active" if is_active else "⚪"
            
            text += f"{idx}. {phone}\n"
            text += f"   • {sub_type} {status}\n\n"
            
            # Button for each account
            if is_active:
                keyboard.append([InlineKeyboardButton(
                    f"✅ {phone} (Active)",
                    callback_data=f"acc_noop_{idx}"
                )])
            else:
                keyboard.append([InlineKeyboardButton(
                    f"🔄 Switch to {phone}",
                    callback_data=f"acc_switch_{phone}"
                )])
        
        keyboard.append([
            InlineKeyboardButton("➕ Tambah Akun", callback_data="menu_login"),
            InlineKeyboardButton("🔙 Kembali", callback_data="menu_back")
        ])
    
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


async def handle_account_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle account management actions"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    action = query.data.replace("acc_", "")
    
    if action.startswith("switch_"):
        phone_number = action.replace("switch_", "")
        
        # Switch active account
        success = db.set_active_xl_account(user.id, phone_number)
        
        if success:
            # Refresh session
            refresh_user_session(user.id)
            
            await query.answer("✅ Akun berhasil diganti!", show_alert=True)
            
            # Show main menu with new account
            from bot.handlers.start_handler import show_main_menu
            await show_main_menu(update, context)
        else:
            await query.answer("❌ Gagal mengganti akun", show_alert=True)
    
    elif action.startswith("delete_"):
        phone_number = action.replace("delete_", "")
        
        # Delete account
        success = db.delete_xl_account(user.id, phone_number)
        
        if success:
            await query.answer("✅ Akun berhasil dihapus!", show_alert=True)
            await show_accounts(update, context)
        else:
            await query.answer("❌ Gagal menghapus akun", show_alert=True)
    
    elif action.startswith("noop_"):
        await query.answer("Akun ini sedang aktif", show_alert=False)