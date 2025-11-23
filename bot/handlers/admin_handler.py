# bot/handlers/admin_handler.py

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from bot.database import db
from bot.utils import get_user_session, format_currency
import json
import os

# Admin user IDs (tambahkan Telegram ID admin di sini)
ADMIN_IDS = [1788035021]  # Ganti dengan Telegram ID admin yang sebenarnya

# Conversation states
ADMIN_ADD_FAMILY, ADMIN_ADD_VARIANT, ADMIN_ADD_ORDER = range(3)
ADMIN_ADD_HOT2_NAME, ADMIN_ADD_HOT2_PRICE, ADMIN_ADD_HOT2_DETAIL, ADMIN_ADD_HOT2_PAYMENT, ADMIN_ADD_HOT2_PACKAGES = range(5, 10)


def is_admin(user_id: int) -> bool:
    """Check if user is admin"""
    return user_id in ADMIN_IDS


async def admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show admin menu"""
    query = update.callback_query if update.callback_query else None
    user = update.effective_user
    
    if not is_admin(user.id):
        text = "❌ Anda tidak memiliki akses admin."
        if query:
            await query.answer(text, show_alert=True)
        else:
            await update.message.reply_text(text)
        return
    
    text = "👑 <b>Admin Panel</b>\n\n"
    text += "Kelola paket Hot:"
    
    keyboard = [
        [
            InlineKeyboardButton("🔥 Hot (Simple)", callback_data="admin_menu_hot"),
            InlineKeyboardButton("🔥🔥 Hot2 (Bundle)", callback_data="admin_menu_hot2")
        ],
        [InlineKeyboardButton("🔙 Kembali", callback_data="menu_back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if query:
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')


# ==================== HOT (hot.json) ====================

async def admin_hot_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show hot menu"""
    query = update.callback_query
    await query.answer()
    
    text = "🔥 <b>Kelola Hot Packages</b>\n\n"
    text += "Single package per entry"
    
    keyboard = [
        [InlineKeyboardButton("➕ Tambah", callback_data="admin_add_hot")],
        [InlineKeyboardButton("📋 Lihat", callback_data="admin_list_hot")],
        [InlineKeyboardButton("🗑️ Hapus", callback_data="admin_delete_hot")],
        [InlineKeyboardButton("🔙 Kembali", callback_data="admin_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')


async def list_hot_packages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all hot packages"""
    query = update.callback_query
    
    try:
        with open("hot_data/hot.json", "r", encoding="utf-8") as f:
            hot_packages = json.load(f)
        
        text = "📋 <b>Daftar Paket Hot</b>\n\n"
        
        if not hot_packages:
            text += "Belum ada paket hot."
        else:
            for idx, pkg in enumerate(hot_packages, 1):
                family_name = pkg.get('family_name', 'N/A')
                variant_name = pkg.get('variant_name', 'N/A')
                option_name = pkg.get('option_name', 'N/A')
                text += f"{idx}. {family_name}\n"
                text += f"   • {variant_name} - {option_name}\n\n"
        
        keyboard = [
            [InlineKeyboardButton("➕ Tambah", callback_data="admin_add_hot")],
            [InlineKeyboardButton("🗑️ Hapus", callback_data="admin_delete_hot")],
            [InlineKeyboardButton("🔙 Kembali", callback_data="admin_menu_hot")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
        
    except Exception as e:
        await query.edit_message_text(f"❌ Error: {str(e)}")


async def show_delete_hot_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show delete hot package menu"""
    query = update.callback_query
    
    try:
        with open("hot_data/hot.json", "r", encoding="utf-8") as f:
            hot_packages = json.load(f)
        
        if not hot_packages:
            await query.answer("❌ Tidak ada paket untuk dihapus", show_alert=True)
            await admin_hot_menu(update, context)
            return
        
        text = "🗑️ <b>Hapus Paket Hot</b>\n\n"
        text += "Pilih paket yang ingin dihapus:"
        
        keyboard = []
        
        for idx, pkg in enumerate(hot_packages):
            option_name = pkg.get('option_name', 'N/A')
            
            keyboard.append([InlineKeyboardButton(
                f"{idx+1}. {option_name[:35]}",
                callback_data=f"admin_delete_hot_confirm_{idx}"
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 Kembali", callback_data="admin_menu_hot")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
        
    except Exception as e:
        await query.edit_message_text(f"❌ Error: {str(e)}")


async def delete_hot_package(update: Update, context: ContextTypes.DEFAULT_TYPE, idx: int):
    """Delete hot package by index"""
    query = update.callback_query
    
    try:
        with open("hot_data/hot.json", "r", encoding="utf-8") as f:
            hot_packages = json.load(f)
        
        if idx >= len(hot_packages):
            await query.answer("❌ Paket tidak ditemukan", show_alert=True)
            return
        
        deleted = hot_packages.pop(idx)
        
        with open("hot_data/hot.json", "w", encoding="utf-8") as f:
            json.dump(hot_packages, f, indent=4, ensure_ascii=False)
        
        await query.answer("✅ Paket berhasil dihapus!", show_alert=True)
        await list_hot_packages(update, context)
        
    except Exception as e:
        await query.answer(f"❌ Error: {str(e)}", show_alert=True)


async def start_add_hot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start add hot package conversation"""
    query = update.callback_query
    user = update.effective_user
    
    if not is_admin(user.id):
        await query.answer("❌ Akses ditolak", show_alert=True)
        return ConversationHandler.END
    
    text = "➕ <b>Tambah Paket Hot</b>\n\n"
    text += "Masukkan <b>Family Code</b> paket:\n\n"
    text += "Contoh:\n"
    text += "<code>08a3b1e6-8e78-4e45-a540-b40f06871cfe</code>\n\n"
    text += "Atau /cancel untuk membatalkan."
    
    await query.edit_message_text(text, parse_mode='HTML')
    
    return ADMIN_ADD_FAMILY


async def receive_family_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive family code"""
    family_code = update.message.text.strip()
    
    if len(family_code) != 36 or family_code.count('-') != 4:
        await update.message.reply_text(
            "❌ Format family code salah!\n\n"
            "Silakan coba lagi atau /cancel"
        )
        return ADMIN_ADD_FAMILY
    
    context.user_data['admin_family_code'] = family_code
    
    user = update.effective_user
    session = get_user_session(user.id)
    
    if not session:
        await update.message.reply_text("❌ Sesi berakhir. Silakan /login")
        return ConversationHandler.END
    
    # Load family data
    loading_msg = await update.message.reply_text("🔍 Mencari paket...")
    
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
            await loading_msg.edit_text("❌ Family code tidak ditemukan")
            return ConversationHandler.END
        
        family_name = family_data['package_family']['name']
        context.user_data['admin_family_name'] = family_name
        context.user_data['admin_family_data'] = family_data
        
        # Show variants
        text = f"✅ Ditemukan: <b>{family_name}</b>\n\n"
        text += "Pilih Variant:\n\n"
        
        variants = family_data['package_variants']
        for idx, variant in enumerate(variants):
            text += f"{idx+1}. {variant['name']}\n"
        
        text += "\nKirim nomor variant:"
        
        await loading_msg.edit_text(text, parse_mode='HTML')
        
        return ADMIN_ADD_VARIANT
        
    except Exception as e:
        await loading_msg.edit_text(f"❌ Error: {str(e)}")
        return ConversationHandler.END


async def receive_variant_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive variant choice"""
    choice = update.message.text.strip()
    
    if not choice.isdigit():
        await update.message.reply_text("❌ Input harus nomor. Coba lagi:")
        return ADMIN_ADD_VARIANT
    
    family_data = context.user_data.get('admin_family_data')
    variants = family_data['package_variants']
    
    idx = int(choice) - 1
    
    if idx < 0 or idx >= len(variants):
        await update.message.reply_text("❌ Nomor tidak valid. Coba lagi:")
        return ADMIN_ADD_VARIANT
    
    selected_variant = variants[idx]
    context.user_data['admin_variant'] = selected_variant
    
    # Show options
    text = f"✅ Variant: <b>{selected_variant['name']}</b>\n\n"
    text += "Pilih Option:\n\n"
    
    options = selected_variant['package_options']
    for idx, option in enumerate(options):
        text += f"{idx+1}. {option['name']} - Rp{option['price']:,}\n"
    
    text += "\nKirim nomor option:"
    
    await update.message.reply_text(text, parse_mode='HTML')
    
    return ADMIN_ADD_ORDER


async def receive_option_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive option choice and save"""
    choice = update.message.text.strip()
    
    if not choice.isdigit():
        await update.message.reply_text("❌ Input harus nomor. Coba lagi:")
        return ADMIN_ADD_ORDER
    
    variant = context.user_data.get('admin_variant')
    options = variant['package_options']
    
    idx = int(choice) - 1
    
    if idx < 0 or idx >= len(options):
        await update.message.reply_text("❌ Nomor tidak valid. Coba lagi:")
        return ADMIN_ADD_ORDER
    
    selected_option = options[idx]
    
    # Save to hot.json
    try:
        with open("hot_data/hot.json", "r", encoding="utf-8") as f:
            hot_packages = json.load(f)
        
        family_data = context.user_data.get('admin_family_data')
        
        new_package = {
            "family_name": context.user_data['admin_family_name'],
            "family_code": context.user_data['admin_family_code'],
            "is_enterprise": family_data['package_family'].get('is_enterprise', False),
            "variant_name": variant['name'],
            "option_name": selected_option['name'],
            "order": selected_option['order']
        }
        
        hot_packages.append(new_package)
        
        with open("hot_data/hot.json", "w", encoding="utf-8") as f:
            json.dump(hot_packages, f, indent=4, ensure_ascii=False)
        
        await update.message.reply_text(
            f"✅ <b>Berhasil ditambahkan!</b>\n\n"
            f"📦 {new_package['family_name']}\n"
            f"• {new_package['variant_name']}\n"
            f"• {new_package['option_name']}\n\n"
            "Gunakan /admin untuk kembali ke admin panel.",
            parse_mode='HTML'
        )
        
        context.user_data.clear()
        return ConversationHandler.END
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")
        return ConversationHandler.END


# ==================== HOT2 (hot2.json) ====================

async def admin_hot2_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show hot2 menu"""
    query = update.callback_query
    await query.answer()
    
    text = "🔥🔥 <b>Kelola Hot2 Packages</b>\n\n"
    text += "Bundle packages (multiple packages in one)"
    
    keyboard = [
        [InlineKeyboardButton("📋 Lihat", callback_data="admin_list_hot2")],
        [InlineKeyboardButton("🗑️ Hapus", callback_data="admin_delete_hot2")],
        [InlineKeyboardButton("🔙 Kembali", callback_data="admin_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')


async def list_hot2_packages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all hot2 packages"""
    query = update.callback_query
    
    try:
        with open("hot_data/hot2.json", "r", encoding="utf-8") as f:
            hot2_packages = json.load(f)
        
        text = "📋 <b>Daftar Paket Hot2</b>\n\n"
        
        if not hot2_packages:
            text += "Belum ada paket hot2."
        else:
            for idx, pkg in enumerate(hot2_packages, 1):
                name = pkg.get('name', 'N/A')
                price = pkg.get('price', 'N/A')
                packages_count = len(pkg.get('packages', []))
                
                text += f"{idx}. <b>{name}</b>\n"
                text += f"   • Harga: {price}\n"
                text += f"   • Paket: {packages_count} item\n\n"
        
        keyboard = [
            [InlineKeyboardButton("🗑️ Hapus", callback_data="admin_delete_hot2")],
            [InlineKeyboardButton("🔙 Kembali", callback_data="admin_menu_hot2")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
        
    except Exception as e:
        await query.edit_message_text(f"❌ Error: {str(e)}")


async def show_delete_hot2_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show delete hot2 package menu"""
    query = update.callback_query
    
    try:
        with open("hot_data/hot2.json", "r", encoding="utf-8") as f:
            hot2_packages = json.load(f)
        
        if not hot2_packages:
            await query.answer("❌ Tidak ada paket untuk dihapus", show_alert=True)
            await admin_hot2_menu(update, context)
            return
        
        text = "🗑️ <b>Hapus Paket Hot2</b>\n\n"
        text += "Pilih paket yang ingin dihapus:"
        
        keyboard = []
        
        for idx, pkg in enumerate(hot2_packages):
            name = pkg.get('name', 'N/A')
            
            keyboard.append([InlineKeyboardButton(
                f"{idx+1}. {name[:35]}",
                callback_data=f"admin_delete_hot2_confirm_{idx}"
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 Kembali", callback_data="admin_menu_hot2")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
        
    except Exception as e:
        await query.edit_message_text(f"❌ Error: {str(e)}")


async def delete_hot2_package(update: Update, context: ContextTypes.DEFAULT_TYPE, idx: int):
    """Delete hot2 package by index"""
    query = update.callback_query
    
    try:
        with open("hot_data/hot2.json", "r", encoding="utf-8") as f:
            hot2_packages = json.load(f)
        
        if idx >= len(hot2_packages):
            await query.answer("❌ Paket tidak ditemukan", show_alert=True)
            return
        
        deleted = hot2_packages.pop(idx)
        
        with open("hot_data/hot2.json", "w", encoding="utf-8") as f:
            json.dump(hot2_packages, f, indent=4, ensure_ascii=False)
        
        await query.answer("✅ Paket berhasil dihapus!", show_alert=True)
        await list_hot2_packages(update, context)
        
    except Exception as e:
        await query.answer(f"❌ Error: {str(e)}", show_alert=True)


# ==================== CALLBACK HANDLERS ====================

async def handle_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin callbacks"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    if not is_admin(user.id):
        await query.answer("❌ Akses ditolak", show_alert=True)
        return
    
    action = query.data.replace("admin_", "")
    
    # Hot menu
    if action == "menu_hot":
        await admin_hot_menu(update, context)
    elif action == "list_hot":
        await list_hot_packages(update, context)
    elif action == "delete_hot":
        await show_delete_hot_menu(update, context)
    elif action.startswith("delete_hot_confirm_"):
        idx = int(action.replace("delete_hot_confirm_", ""))
        await delete_hot_package(update, context, idx)
    
    # Hot2 menu
    elif action == "menu_hot2":
        await admin_hot2_menu(update, context)
    elif action == "list_hot2":
        await list_hot2_packages(update, context)
    elif action == "delete_hot2":
        await show_delete_hot2_menu(update, context)
    elif action.startswith("delete_hot2_confirm_"):
        idx = int(action.replace("delete_hot2_confirm_", ""))
        await delete_hot2_package(update, context, idx)
    
    # Back to main admin menu
    elif action == "menu":
        await admin_menu(update, context)


async def cancel_add_hot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel add hot package"""
    context.user_data.clear()
    
    await update.message.reply_text(
        "❌ Dibatalkan.\n\n"
        "Gunakan /admin untuk kembali ke admin panel."
    )
    
    return ConversationHandler.END