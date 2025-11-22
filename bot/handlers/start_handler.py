from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
)
from bot.database import db
from bot.utils import get_user_session


# =====================================================================
# Helper: Kartu profil keren (tanpa fetch API XL)
# =====================================================================
def build_profile_card(xl_account: dict, user) -> str:
    """
    Bangun kartu profil XL dalam bentuk teks monospaced (<pre>),
    biar kelihatan rapi di Telegram (parse_mode='HTML').
    """
    phone = xl_account.get("phone_number", "N/A")
    tipe = xl_account.get("subscription_type", "Unknown")
    tg_user = f"@{user.username}" if user.username else user.first_name

    lines = [
        "╔════════════════════════════╗",
        "       👤 PROFIL XL ANDA",
        "╚════════════════════════════╝",
        "",
        f"📱 Nomor   : {phone}",
        f"📊 Tipe    : {tipe}",
        f"💬 User: {tg_user}",
    ]

    # Gunakan <pre> supaya alignment tetap rapi
    return "<pre>" + "\n".join(lines) + "</pre>"


# =====================================================================
# /start handler
# =====================================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start command handler"""
    user = update.effective_user

    # Create or update user in database
    db.create_or_update_user(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
    )

    # Check if user has active XL account
    xl_account = db.get_active_xl_account(user.id)

    if xl_account:
        # Langsung lempar ke menu utama kalau sudah punya akun XL aktif
        await show_main_menu(update, context)
        return

    # User needs to login
    keyboard = [
        [InlineKeyboardButton("🔐 Login", callback_data="menu_login")],
        [InlineKeyboardButton("❓ Help", callback_data="menu_help")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    welcome_text = (
        f"👋 Selamat datang, {user.first_name}!\n\n"
        "Bot ini membantu Anda mengelola paket XL Axiata.\n\n"
        "Silakan login terlebih dahulu untuk menggunakan bot ini."
    )

    # /start biasanya dari message, tapi kita amankan juga kalau dipanggil dari callback
    if update.message:
        await update.message.reply_text(welcome_text, reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.edit_message_text(
            welcome_text, reply_markup=reply_markup
        )


# =====================================================================
# Menu utama
# =====================================================================
async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show main menu"""
    user = update.effective_user
    xl_account = db.get_active_xl_account(user.id)

    if not xl_account:
        # Kalau tiba-tiba akun sudah tidak ada / belum login, balikin ke start
        await start(update, context)
        return

    # Ambil session kalau nanti butuh, tapi TIDAK fetch apa-apa ke API XL
    session = get_user_session(user.id)
    # (session sengaja tidak dipakai sekarang, cuma disiapkan kalau nanti mau dipakai)

    # Build kartu profil fancy (tanpa fetch balance/tiering)
    profile_text = build_profile_card(xl_account, user)

    keyboard = [
        [
            InlineKeyboardButton("👤 Profil", callback_data="menu_profile"),
            InlineKeyboardButton("📦 Paket Saya", callback_data="menu_my_packages"),
        ],
        [
            InlineKeyboardButton("🔥 Paket Hot", callback_data="pkg_hot"),
            InlineKeyboardButton("🛒 Semua Paket", callback_data="pkg_store"),
        ],
        [
            InlineKeyboardButton("Riwayat", callback_data="trx_history"),
            InlineKeyboardButton("Bookmark", callback_data="pkg_bookmark"),
        ],
        [
            InlineKeyboardButton("Family Plan", callback_data="fam_info"),
            InlineKeyboardButton("Circle", callback_data="circle_info"),
        ],
        [
            InlineKeyboardButton("⚙️ Akun", callback_data="menu_accounts"),
            InlineKeyboardButton("❓ Help", callback_data="menu_help"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    menu_text = (
        f"{profile_text}\n\n"
        "Pilih menu di bawah ini:"
    )

    # Check if this is from callback query or message
    if update.callback_query:
        await update.callback_query.edit_message_text(
            menu_text,
            reply_markup=reply_markup,
            parse_mode="HTML",
        )
    else:
        await update.message.reply_text(
            menu_text,
            reply_markup=reply_markup,
            parse_mode="HTML",
        )


# =====================================================================
# Handler tombol menu utama
# =====================================================================
async def handle_main_menu(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle main menu callbacks"""
    query = update.callback_query
    await query.answer()

    data = query.data

    # Semua callback yang terkait main menu dimulai dengan "menu_"
    # Contoh: menu_profile, menu_login, menu_accounts, menu_help, menu_back
    if data.startswith("menu_"):
        action = data.replace("menu_", "")
    else:
        action = data  # untuk callback lain seperti pkg_hot, pkg_store, dll.

    if action == "back":
        await show_main_menu(update, context)

    elif action == "login":
        from bot.handlers.login_handler import login_start

        await login_start(update, context)

    elif action == "profile":
        from bot.handlers.profile_handler import show_profile

        await show_profile(update, context)

    elif action == "my_packages":
        from bot.handlers.package_handler import show_my_packages

        await show_my_packages(update, context)

    elif action == "accounts":
        from bot.handlers.account_handler import show_accounts

        await show_accounts(update, context)

    elif action == "help":
        from bot.handlers.help_handler import help_command

        await help_command(update, context)

    # Callback lain di luar "menu_*" bisa lu handle di handler terpisah:
    # - pkg_hot
    # - pkg_store
    # - trx_history
    # - pkg_bookmark
    # - fam_info
    # - circle_info
    # Dll.


# =====================================================================
# Cancel (untuk ConversationHandler)
# =====================================================================
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel current operation"""
    await update.message.reply_text(
        "❌ Operasi dibatalkan.\n\nGunakan /start untuk kembali ke menu utama."
    )
    return ConversationHandler.END
