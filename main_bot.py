import logging
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
from dotenv import load_dotenv

load_dotenv()

from bot.handlers import (
    start_handler,
    login_handler,
    package_handler,
    profile_handler,
    transaction_handler,
    family_handler,
    circle_handler,
    account_handler,
    help_handler,
    payment_handler,
)
from bot.database import init_db

# Import state dari login_handler biar konsisten
from bot.handlers.login_handler import LOGIN_PHONE, LOGIN_OTP
from bot.handlers.db_handler import db_command

# State khusus untuk e-wallet (ConversationHandler)
EWALLET_PHONE = 0

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle text input umum:
    - Nomor e-wallet (kalau waiting_ewallet_phone == True)
    - Kode family (kalau waiting_family_code == True)
    """
    if context.user_data.get("waiting_ewallet_phone"):
        await payment_handler.receive_ewallet_phone(update, context)
    elif context.user_data.get("waiting_family_code"):
        await package_handler.handle_family_code_input(update, context)
    else:
        # Kalau mau, bisa tambahkan default response di sini
        await update.message.reply_text("❓ Input tidak dikenal. Gunakan /help untuk bantuan.")


def main() -> None:
    """Start the bot."""
    # Initialize database
    init_db()

    # Get bot token from environment
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        raise ValueError("TELEGRAM_BOT_TOKEN not found in environment variables")

    # Create the Application
    application = Application.builder().token(bot_token).build()

    # =====================================================================
    # Command handlers
    # =====================================================================
    application.add_handler(CommandHandler("start", start_handler.start))
    application.add_handler(CommandHandler("help", help_handler.help_command))
    application.add_handler(CommandHandler("profile", profile_handler.show_profile))
    application.add_handler(CommandHandler("cancel", start_handler.cancel))
    application.add_handler(CommandHandler("db", db_command))

    # =====================================================================
    # Login ConversationHandler
    #  - /login
    #  - tombol 🔐 Login (callback_data="menu_login")
    # =====================================================================
    login_conv_handler = ConversationHandler(
        entry_points=[
            # /login via command
            CommandHandler("login", login_handler.login_start),
            # tombol login via inline button
            CallbackQueryHandler(login_handler.login_start, pattern="^menu_login$"),
        ],
        states={
            LOGIN_PHONE: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    login_handler.receive_phone,
                )
            ],
            LOGIN_OTP: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    login_handler.receive_otp,
                )
            ],
        },
        fallbacks=[
            CommandHandler("cancel", login_handler.cancel_login),
        ],
    )
    application.add_handler(login_conv_handler)

    # =====================================================================
    # E-wallet payment ConversationHandler
    #  - Entry dari callback_data yang diawali "confirm_ewallet_"
    # =====================================================================
    ewallet_conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(
                payment_handler.handle_payment_confirm,
                pattern="^confirm_ewallet_",
            )
        ],
        states={
            EWALLET_PHONE: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    payment_handler.receive_ewallet_phone,
                )
            ],
        },
        fallbacks=[CommandHandler("cancel", payment_handler.cancel_payment)],
    )
    application.add_handler(ewallet_conv_handler)

    # =====================================================================
    # Callback query handlers (non-conversation)
    # =====================================================================

    # Paket
    application.add_handler(
        CallbackQueryHandler(
            package_handler.handle_package_menu,
            pattern="^pkg_",
        )
    )
    application.add_handler(
        CallbackQueryHandler(
            package_handler.handle_hot_packages,
            pattern="^hot_",
        )
    )
    application.add_handler(
        CallbackQueryHandler(
            package_handler.handle_purchase,
            pattern="^buy_",
        )
    )
    application.add_handler(
        CallbackQueryHandler(
            package_handler.handle_segment_selection,
            pattern="^seg_",
        )
    )
    # Pilih paket family (misal fam_1, fam_2, dst)
    application.add_handler(
        CallbackQueryHandler(
            package_handler.handle_family_package_selection,
            pattern="^fam_\\d+$",
        )
    )
    # Pagination paket family (misal fampg_next, fampg_prev)
    application.add_handler(
        CallbackQueryHandler(
            package_handler.handle_family_pagination,
            pattern="^fampg_",
        )
    )

    # Payment (non-conversation)
    application.add_handler(
        CallbackQueryHandler(
            payment_handler.handle_payment_confirm,
            pattern="^confirm_",
        )
    )
    application.add_handler(
        CallbackQueryHandler(
            payment_handler.handle_payment_confirm,
            pattern="^ewallet_",
        )
    )

    # Transaksi
    application.add_handler(
        CallbackQueryHandler(
            transaction_handler.handle_transaction,
            pattern="^trx_",
        )
    )

    # Family main menu (misal menu lain di family_handler dengan pattern fam_xxx)
    application.add_handler(
        CallbackQueryHandler(
            family_handler.handle_family,
            pattern="^fam_",
        )
    )

    # Circle
    application.add_handler(
        CallbackQueryHandler(
            circle_handler.handle_circle,
            pattern="^circle_",
        )
    )

    # Account
    application.add_handler(
        CallbackQueryHandler(
            account_handler.handle_account_action,
            pattern="^acc_",
        )
    )

    # ⚠️ Handler ini untuk semua menu_ KECUALI menu_login (karena sudah ditangani di login_conv_handler)
    application.add_handler(
        CallbackQueryHandler(
            start_handler.handle_main_menu,
            pattern="^menu_",
        )
    )

    # =====================================================================
    # Message handlers for text input (fallback umum)
    # =====================================================================
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_text_input,
        )
    )

    logger.info("Bot started successfully!")
    print("✅ Bot is running... Press Ctrl+C to stop.")

    # Run the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
