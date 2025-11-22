# circle_handler.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.utils import get_user_session, format_quota, format_currency
from datetime import datetime


async def handle_circle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle circle callbacks"""
    query = update.callback_query
    await query.answer()
    
    action = query.data.replace("circle_", "")
    
    if action == "info":
        await show_circle_info(update, context)
    elif action.startswith("member_"):
        # Future: Handle member details
        await query.answer("🚧 Fitur dalam pengembangan", show_alert=True)


async def show_circle_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show circle info"""
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
        from app.client.circle import get_group_data, get_group_members, spending_tracker
        from app.client.encrypt import decrypt_circle_msisdn
        
        # Get group data
        group_res = get_group_data(session['api_key'], session['tokens'])
        
        if group_res.get('status') != 'SUCCESS':
            text = "⭕ <b>Circle</b>\n\n"
            text += "Anda belum tergabung dalam Circle.\n\n"
            text += "Circle adalah fitur untuk berbagi paket dengan teman dan keluarga."
            keyboard = [[InlineKeyboardButton("🔙 Kembali", callback_data="menu_back")]]
        else:
            group_data = group_res.get('data', {})
            group_id = group_data.get('group_id', '')
            
            if not group_id:
                text = "⭕ <b>Circle</b>\n\n"
                text += "Anda belum tergabung dalam Circle."
                keyboard = [[InlineKeyboardButton("🔙 Kembali", callback_data="menu_back")]]
            else:
                group_status = group_data.get('group_status', 'N/A')
                group_name = group_data.get('group_name', 'N/A')
                owner_name = group_data.get('owner_name', 'N/A')
                
                # Get members
                members_res = get_group_members(session['api_key'], session['tokens'], group_id)
                
                if members_res.get('status') != 'SUCCESS':
                    text = "⭕ <b>Circle</b>\n\n"
                    text += "Gagal memuat data Circle."
                    keyboard = [[InlineKeyboardButton("🔙 Kembali", callback_data="menu_back")]]
                else:
                    members_data = members_res.get('data', {})
                    members = members_data.get('members', [])
                    package = members_data.get('package', {})
                    
                    # Find parent info
                    parent_subs_id = ""
                    for member in members:
                        if member.get('member_role') == 'PARENT':
                            parent_subs_id = member.get('subscriber_number', '')
                            break
                    
                    # Get spending tracker
                    spend = 0
                    target = 0
                    if parent_subs_id:
                        try:
                            spending_res = spending_tracker(
                                session['api_key'],
                                session['tokens'],
                                parent_subs_id,
                                group_id
                            )
                            if spending_res.get('status') == 'SUCCESS':
                                spending_data = spending_res.get('data', {})
                                spend = spending_data.get('spend', 0)
                                target = spending_data.get('target', 0)
                        except:
                            pass
                    
                    # Build message
                    text = f"⭕ <b>Circle: {group_name}</b>\n"
                    text += "━━━━━━━━━━━━━━━━━━━━\n\n"
                    text += f"👤 <b>Owner:</b> {owner_name}\n"
                    text += f"📊 <b>Status:</b> {group_status}\n"
                    text += f"👥 <b>Members:</b> {len(members)}\n\n"
                    
                    # Package info
                    if package:
                        package_name = package.get('name', 'N/A')
                        benefit = package.get('benefit', {})
                        remaining = benefit.get('remaining', 0)
                        allocation = benefit.get('allocation', 0)
                        
                        text += f"📦 <b>Paket:</b> {package_name}\n"
                        text += f"📊 <b>Kuota:</b> {format_quota(remaining)} / {format_quota(allocation)}\n\n"
                    
                    # Spending tracker
                    if target > 0:
                        text += f"💰 <b>Spending:</b> {format_currency(spend)} / {format_currency(target)}\n\n"
                    
                    # Members
                    text += "<b>Anggota:</b>\n"
                    for idx, member in enumerate(members[:5], 1):
                        encrypted_msisdn = member.get('msisdn', '')
                        try:
                            msisdn = decrypt_circle_msisdn(session['api_key'], encrypted_msisdn)
                        except:
                            msisdn = "Hidden"
                        
                        member_name = member.get('member_name', 'N/A')
                        member_role = member.get('member_role', 'N/A')
                        member_status = member.get('status', 'N/A')
                        
                        role_emoji = "👑" if member_role == "PARENT" else "👤"
                        
                        # Check if this is the current user
                        if msisdn == session['phone_number']:
                            text += f"{idx}. {role_emoji} {member_name} (You)\n"
                        else:
                            text += f"{idx}. {role_emoji} {member_name}\n"
                        
                        text += f"   • Status: {member_status}\n"
                    
                    if len(members) > 5:
                        text += f"\n... dan {len(members) - 5} anggota lainnya"
                    
                    keyboard = [
                        [InlineKeyboardButton("🔄 Refresh", callback_data="circle_info")],
                        [InlineKeyboardButton("🔙 Kembali", callback_data="menu_back")]
                    ]
        
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
        text = f"❌ Gagal memuat Circle: {str(e)}"
        keyboard = [[InlineKeyboardButton("🔙 Kembali", callback_data="menu_back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if query:
            await query.edit_message_text(text, reply_markup=reply_markup)
        else:
            await update.message.reply_text(text, reply_markup=reply_markup)