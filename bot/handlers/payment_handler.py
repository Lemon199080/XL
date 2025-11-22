from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from bot.utils import get_user_session, format_currency
from app.type_dict import PaymentItem
import json

# Conversation states
EWALLET_PHONE = 1


async def handle_payment_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle payment confirmation"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    session = get_user_session(user.id)
    
    if not session:
        await query.edit_message_text("❌ Sesi berakhir. Silakan /login kembali.")
        return
    
    action = query.data.replace("confirm_", "").replace("ewallet_", "")
    package_info = context.user_data.get('current_package')
    
    if not package_info:
        await query.edit_message_text("❌ Data paket tidak ditemukan")
        return
    
    if action == "balance":
        await execute_balance_purchase(update, context, session, package_info)
    elif action == "qris":
        await execute_qris_purchase(update, context, session, package_info)
    elif action in ["dana", "ovo", "shopeepay", "gopay"]:
        wallet = action.upper()
        context.user_data['payment_method'] = wallet
        
        # Ask for phone number for DANA and OVO
        if wallet in ['DANA', 'OVO']:
            text = f"💳 <b>{wallet}</b>\n\n"
            text += f"Masukkan nomor {wallet} Anda:\n"
            text += f"Format: 08xxxxxxxxxx\n\n"
            text += f"Atau /cancel untuk membatalkan"
            
            keyboard = [[InlineKeyboardButton("❌ Batal", callback_data="pkg_hot")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
            
            # Set waiting state
            context.user_data['waiting_ewallet_phone'] = True
        else:
            await execute_ewallet_purchase(update, context, session, package_info, wallet)


async def receive_ewallet_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive e-wallet phone number"""
    # Check if we're waiting for phone
    if not context.user_data.get('waiting_ewallet_phone'):
        return
    
    user = update.effective_user
    phone = update.message.text.strip()
    
    # Validate phone
    if not phone.startswith("08") or len(phone) < 10 or len(phone) > 13 or not phone.isdigit():
        await update.message.reply_text(
            "❌ Format nomor salah!\n\n"
            "Gunakan format: 08xxxxxxxxxx\n"
            "Silakan coba lagi atau /cancel"
        )
        return
    
    # Clear waiting state
    context.user_data['waiting_ewallet_phone'] = False
    
    session = get_user_session(user.id)
    package_info = context.user_data.get('current_package')
    payment_method = context.user_data.get('payment_method', 'DANA')
    
    context.user_data['ewallet_phone'] = phone
    
    await update.message.reply_text("⏳ Memproses...")
    await execute_ewallet_purchase(update, context, session, package_info, payment_method, phone)


async def execute_balance_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE,
                                   session: dict, package_info: dict):
    """Execute balance purchase"""
    query = update.callback_query if update.callback_query else None
    
    try:
        from app.client.engsel import get_package
        from app.client.purchase.balance import settlement_balance
        
        option_code = package_info['option_code']
        
        # Get package details
        package = get_package(
            session['api_key'],
            session['tokens'],
            option_code
        )
        
        if not package:
            text = "❌ Gagal memuat detail paket"
            if query:
                await query.edit_message_text(text)
            else:
                await update.message.reply_text(text)
            return
        
        # Prepare payment items
        payment_items = [
            PaymentItem(
                item_code=option_code,
                product_type="",
                item_price=package['package_option']['price'],
                item_name=package['package_option']['name'],
                tax=0,
                token_confirmation=package['token_confirmation']
            )
        ]
        
        payment_for = package['package_family'].get('payment_for', 'BUY_PACKAGE')
        
        text = "⏳ Memproses pembelian...\n\nMohon tunggu..."
        if query:
            await query.edit_message_text(text)
        else:
            msg = await update.message.reply_text(text)
        
        # Execute purchase
        result = settlement_balance(
            api_key=session['api_key'],
            tokens=session['tokens'],
            items=payment_items,
            payment_for=payment_for,
            ask_overwrite=False,
            overwrite_amount=package['package_option']['price']
        )
        
        if result and result.get('status') == 'SUCCESS':
            text = "✅ <b>Pembelian Berhasil!</b>\n\n"
            text += f"📦 {package_info['family_name']}\n"
            text += f"💰 {format_currency(package_info['price'])}\n\n"
            text += "Paket telah aktif di nomor Anda.\n"
            text += "Cek di menu Paket Saya untuk detail."
        else:
            error_msg = result.get('message', 'Unknown error') if result else 'No response'
            text = f"❌ <b>Pembelian Gagal</b>\n\n"
            text += f"Error: {error_msg}\n\n"
            text += "Silakan coba lagi atau hubungi customer service."
        
        keyboard = [[InlineKeyboardButton("🏠 Menu Utama", callback_data="menu_back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if query:
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
        else:
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
            
    except Exception as e:
        text = f"❌ Error: {str(e)}"
        if query:
            await query.edit_message_text(text)
        else:
            await update.message.reply_text(text)


async def execute_ewallet_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE,
                                   session: dict, package_info: dict, 
                                   payment_method: str, wallet_number: str = ""):
    """Execute e-wallet purchase"""
    query = update.callback_query if update.callback_query else None
    
    try:
        from app.client.engsel import get_package
        from app.client.purchase.ewallet import settlement_multipayment
        
        option_code = package_info['option_code']
        
        # Get package details
        package = get_package(
            session['api_key'],
            session['tokens'],
            option_code
        )
        
        if not package:
            text = "❌ Gagal memuat detail paket"
            if query:
                await query.edit_message_text(text)
            else:
                await update.message.reply_text(text)
            return
        
        # Prepare payment items
        payment_items = [
            PaymentItem(
                item_code=option_code,
                product_type="",
                item_price=package['package_option']['price'],
                item_name=package['package_option']['name'],
                tax=0,
                token_confirmation=package['token_confirmation']
            )
        ]
        
        payment_for = package['package_family'].get('payment_for', 'BUY_PACKAGE')
        
        text = "⏳ Membuat link pembayaran...\n\nMohon tunggu..."
        if query:
            await query.edit_message_text(text)
        else:
            msg = await update.message.reply_text(text)
        
        # Execute purchase
        result = settlement_multipayment(
            api_key=session['api_key'],
            tokens=session['tokens'],
            items=payment_items,
            wallet_number=wallet_number,
            payment_method=payment_method,
            payment_for=payment_for,
            ask_overwrite=False,
            overwrite_amount=package['package_option']['price']
        )
        
        if result and result.get('status') == 'SUCCESS':
            deeplink = result.get('data', {}).get('deeplink', '')
            
            text = "✅ <b>Link Pembayaran Berhasil Dibuat!</b>\n\n"
            text += f"📦 {package_info['family_name']}\n"
            text += f"💰 {format_currency(package_info['price'])}\n"
            text += f"💳 {payment_method}\n\n"
            
            if deeplink and payment_method != 'OVO':
                text += f"🔗 <b>Link Pembayaran:</b>\n{deeplink}\n\n"
                text += "Klik link di atas untuk melanjutkan pembayaran."
            else:
                text += "Silakan buka aplikasi OVO Anda untuk menyelesaikan pembayaran."
        else:
            error_msg = result.get('message', 'Unknown error') if result else 'No response'
            text = f"❌ <b>Gagal Membuat Link</b>\n\n"
            text += f"Error: {error_msg}"
        
        keyboard = [[InlineKeyboardButton("🏠 Menu Utama", callback_data="menu_back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if query:
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
        else:
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
            
    except Exception as e:
        text = f"❌ Error: {str(e)}"
        if query:
            await query.edit_message_text(text)
        else:
            await update.message.reply_text(text)


async def execute_qris_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE,
                                session: dict, package_info: dict):
    """Execute QRIS purchase"""
    query = update.callback_query if update.callback_query else None
    
    try:
        from app.client.engsel import get_package
        from app.client.purchase.qris import settlement_qris, get_qris_code
        
        option_code = package_info['option_code']
        
        # Get package details
        package = get_package(
            session['api_key'],
            session['tokens'],
            option_code
        )
        
        if not package:
            text = "❌ Gagal memuat detail paket"
            if query:
                await query.edit_message_text(text)
            else:
                await update.message.reply_text(text)
            return
        
        # Prepare payment items
        payment_items = [
            PaymentItem(
                item_code=option_code,
                product_type="",
                item_price=package['package_option']['price'],
                item_name=package['package_option']['name'],
                tax=0,
                token_confirmation=package['token_confirmation']
            )
        ]
        
        payment_for = package['package_family'].get('payment_for', 'BUY_PACKAGE')
        
        text = "⏳ Membuat QR Code...\n\nMohon tunggu..."
        if query:
            await query.edit_message_text(text)
        else:
            msg = await update.message.reply_text(text)
        
        # Execute purchase
        transaction_id = settlement_qris(
            api_key=session['api_key'],
            tokens=session['tokens'],
            items=payment_items,
            payment_for=payment_for,
            ask_overwrite=False,
            overwrite_amount=package['package_option']['price']
        )
        
        if transaction_id:
            # Get QR code
            qris_code = get_qris_code(
                session['api_key'],
                session['tokens'],
                transaction_id
            )
            
            if qris_code:
                import base64
                import qrcode
                from io import BytesIO
                
                # Generate QR code image
                qr = qrcode.QRCode(version=1, box_size=10, border=5)
                qr.add_data(qris_code)
                qr.make(fit=True)
                img = qr.make_image(fill_color="black", back_color="white")
                
                # Save to bytes
                buf = BytesIO()
                img.save(buf, format='PNG')
                buf.seek(0)
                
                text = "✅ <b>QR Code Berhasil Dibuat!</b>\n\n"
                text += f"📦 {package_info['family_name']}\n"
                text += f"💰 {format_currency(package_info['price'])}\n\n"
                text += "Scan QR Code di bawah ini dengan aplikasi pembayaran Anda.\n\n"
                text += f"Transaction ID: <code>{transaction_id}</code>"
                
                # Send QR code as photo
                await update.effective_message.reply_photo(
                    photo=buf,
                    caption=text,
                    parse_mode='HTML'
                )
                
                keyboard = [[InlineKeyboardButton("🏠 Menu Utama", callback_data="menu_back")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                if query:
                    await query.delete_message()
                
                return
        
        text = "❌ Gagal membuat QR Code"
        keyboard = [[InlineKeyboardButton("🏠 Menu Utama", callback_data="menu_back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if query:
            await query.edit_message_text(text, reply_markup=reply_markup)
        else:
            await update.message.reply_text(text, reply_markup=reply_markup)
            
    except Exception as e:
        text = f"❌ Error: {str(e)}"
        if query:
            await query.edit_message_text(text)
        else:
            await update.message.reply_text(text)


async def cancel_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel payment"""
    context.user_data.clear()
    await update.message.reply_text(
        "❌ Pembayaran dibatalkan.\n\n"
        "Gunakan /start untuk kembali ke menu utama."
    )
    return ConversationHandler.END