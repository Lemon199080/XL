# bot/handlers/package_handler.py

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.database import db
from bot.utils import get_user_session, format_currency, format_quota
import json


async def handle_package_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle package menu callbacks"""
    query = update.callback_query
    await query.answer()
    
    action = query.data.replace("pkg_", "")
    
    if action == "hot":
        await show_hot_packages(update, context)
    elif action == "hot2":
        await show_hot2_packages(update, context)
    elif action == "store":
        await show_store_menu(update, context)
    elif action == "segments":
        await show_store_segments(update, context)
    elif action == "family_search":
        await show_family_search(update, context)
    elif action == "bookmark":
        await show_bookmarks(update, context)
    elif action == "my_packages":
        await show_my_packages(update, context)
    elif action.startswith("detail_"):
        option_code = action.replace("detail_", "")
        await show_package_detail(update, context, option_code)
    elif action == "addbm":
        await add_current_bookmark(update, context)


async def handle_family_pagination(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle family packages pagination"""
    query = update.callback_query
    await query.answer()
    
    page = int(query.data.replace("fampg_", ""))
    family_code = context.user_data.get('current_family_code')
    
    if not family_code:
        await query.answer("❌ Data tidak ditemukan", show_alert=True)
        return
    
    await show_family_packages(update, context, family_code, page)


async def show_hot_packages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show hot packages"""
    query = update.callback_query
    user = update.effective_user
    
    session = get_user_session(user.id)
    if not session:
        await query.edit_message_text(
            "❌ Sesi berakhir. Silakan /login kembali."
        )
        return
    
    loading_msg = await query.edit_message_text("⏳ Memuat paket...")
    
    try:
        with open("hot_data/hot.json", "r", encoding="utf-8") as f:
            hot_packages = json.load(f)
        
        text = "🔥 <b>Paket Hot</b>\n\n"
        text += "Paket-paket pilihan terbaik:\n\n"
        
        keyboard = []
        for idx, pkg in enumerate(hot_packages[:10]):
            family_name = pkg.get('family_name', 'N/A')
            variant_name = pkg.get('variant_name', 'N/A')
            option_name = pkg.get('option_name', 'N/A')
            
            text += f"{idx+1}. {family_name} - {option_name}\n"
            
            keyboard.append([InlineKeyboardButton(
                f"{idx+1}. {option_name[:30]}",
                callback_data=f"hot_select_{idx}"
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 Kembali", callback_data="menu_back")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await loading_msg.edit_text(
            text,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        
    except Exception as e:
        await loading_msg.edit_text(
            f"❌ Gagal memuat paket: {str(e)}\n\n"
            "Gunakan /start untuk kembali."
        )


async def show_hot2_packages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show hot2 packages (bundle packages)"""
    query = update.callback_query
    user = update.effective_user
    
    session = get_user_session(user.id)
    if not session:
        await query.edit_message_text(
            "❌ Sesi berakhir. Silakan /login kembali."
        )
        return
    
    loading_msg = await query.edit_message_text("⏳ Memuat paket...")
    
    try:
        with open("hot_data/hot2.json", "r", encoding="utf-8") as f:
            hot2_packages = json.load(f)
        
        text = "🔥🔥 <b>Paket Hot2 (Bundle)</b>\n\n"
        text += "Paket bundle dengan harga spesial:\n\n"
        
        keyboard = []
        for idx, pkg in enumerate(hot2_packages[:10]):
            name = pkg.get('name', 'N/A')
            price = pkg.get('price', 'N/A')
            detail = pkg.get('detail', '')
            
            text += f"{idx+1}. <b>{name}</b>\n"
            text += f"   💰 {price}\n"
            if detail:
                # Show first line of detail only
                first_line = detail.split('\n')[0]
                text += f"   📝 {first_line[:40]}...\n"
            text += "\n"
            
            keyboard.append([InlineKeyboardButton(
                f"{idx+1}. {name[:30]}",
                callback_data=f"hot2_select_{idx}"
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 Kembali", callback_data="pkg_store")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await loading_msg.edit_text(
            text,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        
    except Exception as e:
        await loading_msg.edit_text(
            f"❌ Gagal memuat paket: {str(e)}\n\n"
            "Gunakan /start untuk kembali."
        )


async def handle_hot_packages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle hot package selection"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    session = get_user_session(user.id)
    
    if not session:
        await query.edit_message_text(
            "❌ Sesi berakhir. Silakan /login kembali."
        )
        return
    
    action = query.data.replace("hot_", "")
    
    if action.startswith("select_"):
        try:
            idx = int(action.replace("select_", ""))
            
            with open("hot_data/hot.json", "r", encoding="utf-8") as f:
                hot_packages = json.load(f)
            
            if idx >= len(hot_packages):
                await query.edit_message_text("❌ Paket tidak ditemukan.")
                return
            
            selected = hot_packages[idx]
            
            from app.client.engsel import get_family
            
            loading_msg = await query.edit_message_text("⏳ Memuat detail paket...")
            
            family_data = get_family(
                session['api_key'],
                session['tokens'],
                selected['family_code'],
                selected.get('is_enterprise', False)
            )
            
            if not family_data:
                await loading_msg.edit_text("❌ Gagal memuat detail paket.")
                return
            
            option_code = None
            for variant in family_data['package_variants']:
                if variant['name'] == selected['variant_name']:
                    for option in variant['package_options']:
                        if option['order'] == selected['order']:
                            option_code = option['package_option_code']
                            break
            
            if option_code:
                await show_package_detail(update, context, option_code)
            else:
                await loading_msg.edit_text("❌ Paket tidak ditemukan.")
                
        except Exception as e:
            await query.edit_message_text(f"❌ Error: {str(e)}")


async def handle_hot2_packages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle hot2 package selection"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    session = get_user_session(user.id)
    
    if not session:
        await query.edit_message_text(
            "❌ Sesi berakhir. Silakan /login kembali."
        )
        return
    
    action = query.data.replace("hot2_", "")
    
    if action.startswith("select_"):
        try:
            idx = int(action.replace("select_", ""))
            
            with open("hot_data/hot2.json", "r", encoding="utf-8") as f:
                hot2_packages = json.load(f)
            
            if idx >= len(hot2_packages):
                await query.edit_message_text("❌ Paket tidak ditemukan.")
                return
            
            selected = hot2_packages[idx]
            
            # Show hot2 package detail
            await show_hot2_detail(update, context, selected, idx)
                
        except Exception as e:
            await query.edit_message_text(f"❌ Error: {str(e)}")


async def show_hot2_detail(update: Update, context: ContextTypes.DEFAULT_TYPE, package_data: dict, idx: int):
    """Show hot2 package detail"""
    query = update.callback_query
    user = update.effective_user
    
    session = get_user_session(user.id)
    if not session:
        await query.edit_message_text("❌ Sesi berakhir. Silakan /login kembali.")
        return
    
    loading_msg = await query.edit_message_text("⏳ Memuat detail paket...")
    
    try:
        from app.client.engsel import get_package_details
        
        name = package_data.get('name', 'N/A')
        price = package_data.get('price', 'N/A')
        detail = package_data.get('detail', '')
        packages = package_data.get('packages', [])
        payment_for = package_data.get('payment_for', 'BUY_PACKAGE')
        
        # Get first package details for display
        main_package_detail = None
        if packages:
            first_pkg = packages[0]
            main_package_detail = get_package_details(
                session['api_key'],
                session['tokens'],
                first_pkg['family_code'],
                first_pkg['variant_code'],
                first_pkg['order'],
                first_pkg.get('is_enterprise'),
                first_pkg.get('migration_type')
            )
        
        text = f"🔥🔥 <b>{name}</b>\n"
        text += "━━━━━━━━━━━━━━━━━━━━\n\n"
        text += f"<b>Harga:</b> {price}\n\n"
        
        if detail:
            text += f"<b>Detail:</b>\n{detail}\n\n"
        
        text += f"<b>Bundle berisi {len(packages)} paket:</b>\n"
        for i, pkg in enumerate(packages, 1):
            option_name = pkg.get('option_name', 'N/A')
            if option_name:
                text += f"{i}. {option_name}\n"
        
        text += "\n━━━━━━━━━━━━━━━━━━━━"
        
        # Store package data for purchase
        context.user_data['current_hot2_package'] = {
            'data': package_data,
            'idx': idx
        }
        
        keyboard = [
            [
                InlineKeyboardButton("💰 Pulsa", callback_data=f"buy_hot2_balance"),
                InlineKeyboardButton("💳 E-Wallet", callback_data=f"buy_hot2_ewallet")
            ],
            [
                InlineKeyboardButton("📱 QRIS", callback_data=f"buy_hot2_qris")
            ],
            [InlineKeyboardButton("🔙 Kembali", callback_data="pkg_hot2")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await loading_msg.edit_text(
            text,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        
    except Exception as e:
        await loading_msg.edit_text(f"❌ Error: {str(e)}")


async def show_package_detail(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                              option_code: str):
    """Show package detail"""
    query = update.callback_query
    user = update.effective_user
    
    session = get_user_session(user.id)
    if not session:
        await query.edit_message_text(
            "❌ Sesi berakhir. Silakan /login kembali."
        )
        return
    
    loading_msg = await query.edit_message_text("⏳ Memuat detail paket...")
    
    try:
        from app.client.engsel import get_package
        
        package = get_package(
            session['api_key'],
            session['tokens'],
            option_code
        )
        
        if not package:
            await loading_msg.edit_text("❌ Gagal memuat detail paket.")
            return
        
        family_name = package.get('package_family', {}).get('name', 'N/A')
        variant_name = package.get('package_detail_variant', {}).get('name', 'N/A')
        option_name = package.get('package_option', {}).get('name', 'N/A')
        price = package.get('package_option', {}).get('price', 0)
        validity = package.get('package_option', {}).get('validity', 'N/A')
        
        text = f"📦 <b>{family_name}</b>\n"
        text += f"━━━━━━━━━━━━━━━━━━━━\n\n"
        text += f"<b>Paket:</b> {option_name}\n"
        text += f"<b>Varian:</b> {variant_name}\n"
        text += f"<b>Harga:</b> {format_currency(price)}\n"
        text += f"<b>Masa Aktif:</b> {validity}\n\n"
        
        benefits = package.get('package_option', {}).get('benefits', [])
        if benefits:
            text += "<b>Benefit:</b>\n"
            for benefit in benefits[:5]:
                name = benefit.get('name', 'N/A')
                data_type = benefit.get('data_type', '')
                total = benefit.get('total', 0)
                
                if data_type == 'DATA' and total > 0:
                    quota = format_quota(total)
                    text += f"• {name}: {quota}\n"
                elif data_type == 'VOICE' and total > 0:
                    text += f"• {name}: {total/60:.0f} menit\n"
                elif data_type == 'TEXT' and total > 0:
                    text += f"• {name}: {total} SMS\n"
                elif benefit.get('is_unlimited'):
                    text += f"• {name}: Unlimited\n"
        
        text += "\n━━━━━━━━━━━━━━━━━━━━\n"
        text += f"<b>Kode:</b> <code>{option_code}</code>"
        
        context.user_data['current_package'] = {
            'option_code': option_code,
            'family_name': family_name,
            'option_name': option_name,
            'price': price
        }
        
        keyboard = [
            [
                InlineKeyboardButton("💰 Pulsa", callback_data=f"buy_balance"),
                InlineKeyboardButton("💳 E-Wallet", callback_data=f"buy_ewallet")
            ],
            [
                InlineKeyboardButton("📱 QRIS", callback_data=f"buy_qris")
            ],
            [
                InlineKeyboardButton("⭐ Bookmark", callback_data=f"pkg_addbm"),
                InlineKeyboardButton("🔙 Kembali", callback_data="pkg_hot")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await loading_msg.edit_text(
            text,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        
    except Exception as e:
        await loading_msg.edit_text(f"❌ Error: {str(e)}")


async def show_my_packages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's active packages"""
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
    
    if query:
        loading_msg = await query.edit_message_text("⏳ Memuat paket...")
    else:
        loading_msg = await update.message.reply_text("⏳ Memuat paket...")
    
    try:
        from app.client.engsel import send_api_request
        
        path = "api/v8/packages/quota-details"
        payload = {
            "is_enterprise": False,
            "lang": "en",
            "family_member_id": ""
        }
        
        res = send_api_request(
            session['api_key'],
            path,
            payload,
            session['tokens']['id_token'],
            "POST"
        )
        
        if res.get('status') != 'SUCCESS':
            text = "❌ Gagal memuat paket."
        else:
            quotas = res['data']['quotas']
            
            text = "📦 <b>Paket Aktif Saya</b>\n\n"
            
            if not quotas:
                text += "Tidak ada paket aktif."
            else:
                for idx, quota in enumerate(quotas[:10], 1):
                    quota_name = quota.get('name', 'N/A')
                    text += f"{idx}. {quota_name}\n"
                    
                    benefits = quota.get('benefits', [])
                    if benefits:
                        for benefit in benefits[:2]:
                            name = benefit.get('name', '')
                            remaining = benefit.get('remaining', 0)
                            total = benefit.get('total', 0)
                            data_type = benefit.get('data_type', '')
                            
                            if data_type == 'DATA':
                                text += f"   • {format_quota(remaining)}/{format_quota(total)}\n"
                    
                    text += "\n"
        
        keyboard = [[InlineKeyboardButton("🔙 Kembali", callback_data="menu_back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await loading_msg.edit_text(text, reply_markup=reply_markup, parse_mode='HTML')
            
    except Exception as e:
        text = f"❌ Error: {str(e)}"
        await loading_msg.edit_text(text)


async def show_bookmarks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user bookmarks"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    bookmarks = db.get_bookmarks(user.id)
    
    if not bookmarks:
        text = "⭐ <b>Bookmark</b>\n\nAnda belum memiliki bookmark."
        keyboard = [[InlineKeyboardButton("🔙 Kembali", callback_data="menu_back")]]
    else:
        text = "⭐ <b>Bookmark</b>\n\n"
        keyboard = []
        
        for idx, bm in enumerate(bookmarks[:10], 1):
            family_name = bm['family_name']
            option_name = bm['option_name']
            text += f"{idx}. {family_name} - {option_name}\n"
            
            keyboard.append([InlineKeyboardButton(
                f"{idx}. {option_name[:30]}",
                callback_data=f"pkg_bm_select_{bm['id']}"
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 Kembali", callback_data="menu_back")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')


async def show_store_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show store menu"""
    query = update.callback_query
    await query.answer()
    
    text = "🛒 <b>Semua Paket</b>\n\nPilih kategori:"
    
    keyboard = [
        [
            InlineKeyboardButton("🔥 Hot", callback_data="pkg_hot"),
            InlineKeyboardButton("🔥🔥 Hot2", callback_data="pkg_hot2")
        ],
        [InlineKeyboardButton("📊 Store Segments", callback_data="pkg_segments")],
        [InlineKeyboardButton("🔍 Family Code", callback_data="pkg_family_search")],
        [InlineKeyboardButton("🔙 Kembali", callback_data="menu_back")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')


async def show_store_segments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show store segments"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    session = get_user_session(user.id)
    
    if not session:
        await query.edit_message_text("❌ Sesi berakhir. Silakan /login kembali.")
        return
    
    loading_msg = await query.edit_message_text("⏳ Memuat segments...")
    
    try:
        from app.client.store.segments import get_segments
        
        segments_res = get_segments(session['api_key'], session['tokens'], False)
        
        if not segments_res or segments_res.get('status') != 'SUCCESS':
            await loading_msg.edit_text("❌ Gagal memuat segments")
            return
        
        segments = segments_res.get('data', {}).get('store_segments', [])
        
        if not segments:
            text = "📊 <b>Store Segments</b>\n\nTidak ada promo saat ini."
            keyboard = [[InlineKeyboardButton("🔙 Kembali", callback_data="pkg_store")]]
        else:
            text = "📊 <b>Store Segments</b>\n\n"
            text += "Banner & Paket Promo:\n\n"
            
            keyboard = []
            package_count = 0
            
            for seg_idx, segment in enumerate(segments[:3]):
                title = segment.get('title', 'N/A')
                banners = segment.get('banners', [])
                
                text += f"<b>{title}</b>\n"
                
                for banner_idx, banner in enumerate(banners[:3]):
                    banner_title = banner.get('title', 'N/A')
                    price = banner.get('discounted_price', 0)
                    action_type = banner.get('action_type', '')
                    action_param = banner.get('action_param', '')
                    
                    package_count += 1
                    text += f"{package_count}. {banner_title} - Rp{price:,}\n"
                    
                    context_key = f"seg_{package_count}"
                    context.user_data[context_key] = {
                        'action_type': action_type,
                        'action_param': action_param,
                        'title': banner_title
                    }
                    
                    keyboard.append([InlineKeyboardButton(
                        f"{package_count}. {banner_title[:30]}",
                        callback_data=f"seg_{package_count}"
                    )])
                
                text += "\n"
            
            keyboard.append([InlineKeyboardButton("🔙 Kembali", callback_data="pkg_store")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await loading_msg.edit_text(text, reply_markup=reply_markup, parse_mode='HTML')
        
    except Exception as e:
        await loading_msg.edit_text(f"❌ Error: {str(e)}")


async def show_family_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show family code search"""
    query = update.callback_query
    await query.answer()
    
    text = "🔍 <b>Cari Paket dengan Family Code</b>\n\n"
    text += "Kirim family code paket yang ingin dicari.\n\n"
    text += "Contoh:\n"
    text += "<code>08a3b1e6-8e78-4e45-a540-b40f06871cfe</code>\n\n"
    text += "Atau ketik /cancel untuk membatalkan."
    
    keyboard = [[InlineKeyboardButton("🔙 Kembali", callback_data="pkg_store")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
    
    context.user_data['waiting_family_code'] = True


async def handle_family_code_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle family code input"""
    if not context.user_data.get('waiting_family_code'):
        return
    
    family_code = update.message.text.strip()
    context.user_data['waiting_family_code'] = False
    
    if len(family_code) != 36 or family_code.count('-') != 4:
        await update.message.reply_text(
            "❌ Format family code salah!\n\n"
            "Format yang benar:\n"
            "<code>08a3b1e6-8e78-4e45-a540-b40f06871cfe</code>\n\n"
            "Coba lagi dengan /start",
            parse_mode='HTML'
        )
        return
    
    await update.message.reply_text("🔍 Mencari paket...")
    await show_family_packages(update, context, family_code)


async def show_family_packages(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                               family_code: str, page: int = 1):
    """Show family packages with pagination"""
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
        from app.client.engsel import get_family
        
        family_data = get_family(
            session['api_key'],
            session['tokens'],
            family_code,
            None,
            None
        )
        
        if not family_data:
            text = "❌ Gagal memuat paket family"
            if query:
                await query.edit_message_text(text)
            else:
                await update.message.reply_text(text)
            return
        
        family_name = family_data['package_family']['name']
        variants = family_data['package_variants']
        
        # Store family code for pagination
        context.user_data['current_family_code'] = family_code
        
        # Collect all packages
        all_packages = []
        for variant in variants:
            variant_name = variant['name']
            variant_code = variant['package_variant_code']
            for option in variant['package_options']:
                all_packages.append({
                    'variant_name': variant_name,
                    'variant_code': variant_code,
                    'option_name': option['name'],
                    'price': option['price'],
                    'option_code': option['package_option_code'],
                    'order': option['order']
                })
        
        # Pagination
        per_page = 8
        total_pages = (len(all_packages) + per_page - 1) // per_page
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        page_packages = all_packages[start_idx:end_idx]
        
        text = f"📦 <b>{family_name}</b>\n"
        text += f"Total: {len(all_packages)} paket | Halaman {page}/{total_pages}\n\n"
        
        keyboard = []
        
        # Group by variant for display
        current_variant = None
        pkg_num = start_idx + 1
        
        for pkg in page_packages:
            if current_variant != pkg['variant_name']:
                current_variant = pkg['variant_name']
                text += f"\n<b>{current_variant}</b>\n"
            
            text += f"{pkg_num}. {pkg['option_name']} - {format_currency(pkg['price'])}\n"
            
            # Store in context
            context.user_data[f"fam_{pkg_num}"] = {
                'option_code': pkg['option_code'],
                'name': pkg['option_name'],
                'price': pkg['price']
            }
            
            keyboard.append([InlineKeyboardButton(
                f"{pkg_num}. {pkg['option_name'][:35]}",
                callback_data=f"fam_{pkg_num}"
            )])
            
            pkg_num += 1
        
        # Pagination buttons
        nav_buttons = []
        if page > 1:
            nav_buttons.append(InlineKeyboardButton(
                "⬅️ Prev",
                callback_data=f"fampg_{page-1}"
            ))
        
        nav_buttons.append(InlineKeyboardButton(
            f"📄 {page}/{total_pages}",
            callback_data="ignore"
        ))
        
        if page < total_pages:
            nav_buttons.append(InlineKeyboardButton(
                "Next ➡️",
                callback_data=f"fampg_{page+1}"
            ))
        
        if nav_buttons:
            keyboard.append(nav_buttons)
        
        keyboard.append([InlineKeyboardButton("🔙 Kembali", callback_data="pkg_store")])
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


async def handle_segment_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle segment selection"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    session = get_user_session(user.id)
    
    if not session:
        await query.edit_message_text("❌ Sesi berakhir. Silakan /login kembali.")
        return
    
    seg_id = query.data
    package_data = context.user_data.get(seg_id)
    
    if not package_data:
        await query.answer("❌ Data tidak ditemukan", show_alert=True)
        return
    
    action_type = package_data['action_type']
    action_param = package_data['action_param']
    
    if action_type == 'PDP':
        await show_package_detail(update, context, action_param)
    elif action_type == 'PLP':
        await show_family_packages(update, context, action_param)
    else:
        await query.answer("⚠️ Tipe aksi tidak didukung", show_alert=True)


async def handle_family_package_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle family package selection"""
    query = update.callback_query
    await query.answer()
    
    pkg_id = query.data
    package_data = context.user_data.get(pkg_id)
    
    if not package_data:
        await query.answer("❌ Data tidak ditemukan", show_alert=True)
        return
    
    option_code = package_data['option_code']
    await show_package_detail(update, context, option_code)


async def add_current_bookmark(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add current package to bookmarks"""
    query = update.callback_query
    user = update.effective_user
    
    package_info = context.user_data.get('current_package')
    
    if not package_info:
        await query.answer("❌ Data paket tidak ditemukan", show_alert=True)
        return
    
    session = get_user_session(user.id)
    if not session:
        await query.answer("❌ Sesi berakhir", show_alert=True)
        return
    
    try:
        from app.client.engsel import get_package
        
        package = get_package(
            session['api_key'],
            session['tokens'],
            package_info['option_code']
        )
        
        if not package:
            await query.answer("❌ Gagal memuat detail paket", show_alert=True)
            return
        
        family_code = package['package_family']['package_family_code']
        family_name = package['package_family']['name']
        variant_name = package.get('package_detail_variant', {}).get('name', 'N/A')
        option_name = package['package_option']['name']
        order = package['package_option']['order']
        is_enterprise = False
        
        success = db.add_bookmark(
            telegram_id=user.id,
            family_code=family_code,
            family_name=family_name,
            is_enterprise=is_enterprise,
            variant_name=variant_name,
            option_name=option_name,
            order_num=order
        )
        
        if success:
            await query.answer("✅ Ditambahkan ke bookmark!", show_alert=True)
        else:
            await query.answer("⚠️ Paket sudah ada di bookmark", show_alert=True)
            
    except Exception as e:
        await query.answer(f"❌ Error: {str(e)}", show_alert=True)


async def handle_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle package purchase"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    session = get_user_session(user.id)
    
    if not session:
        await query.edit_message_text("❌ Sesi berakhir. Silakan /login kembali.")
        return
    
    action = query.data.replace("buy_", "")
    
    # Check if it's hot2 package
    if action.startswith("hot2_"):
        hot2_data = context.user_data.get('current_hot2_package')
        if not hot2_data:
            await query.answer("❌ Data paket tidak ditemukan", show_alert=True)
            return
        
        package_data = hot2_data['data']
        
        # For hot2, we'll implement purchase later
        # For now, just show info
        await query.answer(
            "🚧 Fitur pembelian Hot2 dalam pengembangan.\n"
            "Silakan gunakan CLI untuk saat ini.",
            show_alert=True
        )
        return
    
    # Regular package purchase
    package_info = context.user_data.get('current_package')
    if not package_info:
        await query.answer("❌ Data paket tidak ditemukan", show_alert=True)
        return
    
    option_code = package_info['option_code']
    price = package_info['price']
    item_name = f"{package_info['family_name']} - {package_info['option_name']}"
    
    try:
        if action == "balance":
            from bot.handlers.payment_handler import purchase_with_balance
            await purchase_with_balance(update, context, session, option_code, price, item_name)
        elif action == "ewallet":
            from bot.handlers.payment_handler import purchase_with_ewallet
            await purchase_with_ewallet(update, context, session, option_code, price, item_name)
        elif action == "qris":
            from bot.handlers.payment_handler import purchase_with_qris
            await purchase_with_qris(update, context, session, option_code, price, item_name)
    except Exception as e:
        await query.edit_message_text(
            f"❌ Terjadi kesalahan: {str(e)}\n\n"
            "Gunakan /start untuk kembali."
        )