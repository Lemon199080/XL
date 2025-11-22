# transaction_handler.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.utils import get_user_session, format_currency, format_date


async def handle_transaction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle transaction callbacks"""
    query = update.callback_query
    await query.answer()
    
    action = query.data.replace("trx_", "")
    
    if action == "history":
        await show_transaction_history(update, context)
    elif action.startswith("page_"):
        page = int(action.replace("page_", ""))
        await show_transaction_history(update, context, page)


async def show_transaction_history(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                   page: int = 1):
    """Show transaction history"""
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
    
    try:
        from app.client.engsel import get_transaction_history
        
        data = get_transaction_history(session['api_key'], session['tokens'])
        
        if not data or 'list' not in data:
            text = "📋 <b>Riwayat Transaksi</b>\n\nTidak ada riwayat transaksi."
            keyboard = [[InlineKeyboardButton("🔙 Kembali", callback_data="menu_back")]]
        else:
            transactions = data['list']
            
            # Pagination
            per_page = 5
            total_pages = (len(transactions) + per_page - 1) // per_page
            start_idx = (page - 1) * per_page
            end_idx = start_idx + per_page
            
            text = f"📋 <b>Riwayat Transaksi</b>\n"
            text += f"Halaman {page}/{total_pages}\n"
            text += "━━━━━━━━━━━━━━━━━━━━\n\n"
            
            if not transactions:
                text += "Tidak ada transaksi."
            else:
                for idx, trx in enumerate(transactions[start_idx:end_idx], start=start_idx + 1):
                    title = trx.get('title', 'N/A')
                    price = trx.get('price', 'N/A')
                    status = trx.get('status', 'N/A')
                    payment_status = trx.get('payment_status', 'N/A')
                    timestamp = trx.get('timestamp', 0)
                    payment_method = trx.get('payment_method_label', 'N/A')
                    
                    # Status emoji
                    if status == 'SUCCESS' or payment_status == 'SUCCESS':
                        status_emoji = "✅"
                    elif status == 'FAILED' or payment_status == 'FAILED':
                        status_emoji = "❌"
                    elif status == 'PENDING':
                        status_emoji = "⏳"
                    else:
                        status_emoji = "❓"
                    
                    text += f"{status_emoji} <b>{title}</b>\n"
                    text += f"   💰 {price}\n"
                    text += f"   💳 {payment_method}\n"
                    text += f"   📅 {format_date(timestamp)}\n"
                    text += f"   📊 {status}\n\n"
            
            # Build keyboard with pagination
            keyboard = []
            
            # Pagination buttons
            nav_buttons = []
            if page > 1:
                nav_buttons.append(InlineKeyboardButton(
                    "⬅️ Prev",
                    callback_data=f"trx_page_{page-1}"
                ))
            if page < total_pages:
                nav_buttons.append(InlineKeyboardButton(
                    "Next ➡️",
                    callback_data=f"trx_page_{page+1}"
                ))
            
            if nav_buttons:
                keyboard.append(nav_buttons)
            
            keyboard.append([
                InlineKeyboardButton("🔄 Refresh", callback_data="trx_history"),
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
            
    except Exception as e:
        text = f"❌ Gagal memuat riwayat: {str(e)}"
        if query:
            await query.edit_message_text(text)
        else:
            await update.message.reply_text(text)