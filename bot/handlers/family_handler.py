# family_handler.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.utils import get_user_session, format_quota
from datetime import datetime


async def handle_family(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle family plan callbacks"""
    query = update.callback_query
    await query.answer()
    
    action = query.data.replace("fam_", "")
    
    if action == "info":
        await show_family_info(update, context)
    elif action.startswith("member_"):
        # Future: Handle member details
        await query.answer("🚧 Fitur dalam pengembangan", show_alert=True)


async def show_family_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show family plan info"""
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
        from app.client.famplan import get_family_data
        
        res = get_family_data(session['api_key'], session['tokens'])
        
        if not res.get('data'):
            text = "👨‍👩‍👧 <b>Family Plan</b>\n\n"
            text += "Anda belum terdaftar sebagai organizer Family Plan."
            keyboard = [[InlineKeyboardButton("🔙 Kembali", callback_data="menu_back")]]
        else:
            family_detail = res['data']
            member_info = family_detail['member_info']
            
            plan_type = member_info.get('plan_type', 'N/A')
            
            if not plan_type or plan_type == "":
                text = "👨‍👩‍👧 <b>Family Plan</b>\n\n"
                text += "Anda belum terdaftar sebagai organizer Family Plan."
                keyboard = [[InlineKeyboardButton("🔙 Kembali", callback_data="menu_back")]]
            else:
                parent_msisdn = member_info.get('parent_msisdn', 'N/A')
                members = member_info.get('members', [])
                total_quota = member_info.get('total_quota', 0)
                remaining_quota = member_info.get('remaining_quota', 0)
                end_date = member_info.get('end_date', 0)
                
                # Count empty slots
                empty_slots = len([m for m in members if m.get('msisdn') == ''])
                filled_slots = len(members) - empty_slots
                
                text = "👨‍👩‍👧 <b>Family Plan</b>\n"
                text += "━━━━━━━━━━━━━━━━━━━━\n\n"
                text += f"📱 <b>Parent:</b> {parent_msisdn}\n"
                text += f"📊 <b>Plan:</b> {plan_type}\n"
                text += f"👥 <b>Members:</b> {filled_slots}/{len(members)}\n"
                text += f"📦 <b>Shared Quota:</b> {format_quota(remaining_quota)} / {format_quota(total_quota)}\n"
                
                if end_date:
                    exp_date = datetime.fromtimestamp(end_date).strftime("%d %b %Y")
                    text += f"📅 <b>Berlaku Sampai:</b> {exp_date}\n"
                
                text += "\n<b>Anggota:</b>\n"
                
                for idx, member in enumerate(members[:5], 1):  # Limit to 5
                    msisdn = member.get('msisdn', '')
                    alias = member.get('alias', 'N/A')
                    member_type = member.get('member_type', 'N/A')
                    
                    if msisdn == '':
                        text += f"{idx}. <i>Slot kosong</i>\n"
                    else:
                        quota_allocated = member.get('usage', {}).get('quota_allocated', 0)
                        quota_used = member.get('usage', {}).get('quota_used', 0)
                        
                        text += f"{idx}. {msisdn} ({alias})\n"
                        text += f"   • {member_type}\n"
                        text += f"   • {format_quota(quota_used)} / {format_quota(quota_allocated)}\n"
                
                if len(members) > 5:
                    text += f"\n... dan {len(members) - 5} anggota lainnya"
                
                keyboard = [
                    [InlineKeyboardButton("🔄 Refresh", callback_data="fam_info")],
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
        text = f"❌ Gagal memuat Family Plan: {str(e)}"
        keyboard = [[InlineKeyboardButton("🔙 Kembali", callback_data="menu_back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if query:
            await query.edit_message_text(text, reply_markup=reply_markup)
        else:
            await update.message.reply_text(text, reply_markup=reply_markup)