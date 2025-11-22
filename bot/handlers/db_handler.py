from telegram import Update
from telegram.ext import ContextTypes
from bot.database import db


MAX_TELEGRAM_TEXT = 4000  # aman < 4096


async def send_long_text(message, text: str, parse_mode: str | None = None):
    """
    Kirim teks panjang, auto-split kalau lebih dari limit Telegram.
    Kalau terlalu panjang, parse_mode HTML bakal di-drop biar aman.
    """
    if len(text) <= MAX_TELEGRAM_TEXT:
        return await message.reply_text(text, parse_mode=parse_mode)

    # Kalau terlalu panjang, kita pecah per baris biar nggak motong di tengah kata
    lines = text.splitlines()
    chunk = []
    current_len = 0

    # Untuk chunking, kita pakai plain text saja (tanpa HTML) biar nggak error
    for line in lines:
        # +1 buat newline
        if current_len + len(line) + 1 > MAX_TELEGRAM_TEXT:
            await message.reply_text("\n".join(chunk))
            chunk = []
            current_len = 0
        chunk.append(line)
        current_len += len(line) + 1

    if chunk:
        await message.reply_text("\n".join(chunk))


async def db_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Perintah /db untuk melihat isi database"""
    msg = update.effective_message
    args = context.args

    if not args:
        text = (
            "📊 <b>Database Viewer</b>\n\n"
            "Gunakan perintah:\n"
            "• <code>/db users</code>\n"
            "• <code>/db accounts</code>\n"
            "• <code>/db bookmarks</code>\n"
            "• <code>/db prefs</code>\n"
            "• <code>/db user &lt;telegram_id&gt;</code>\n"
            "• <code>/db phone &lt;nomor&gt;</code>\n"
        )
        return await msg.reply_text(text, parse_mode="HTML")

    cmd = args[0].lower()

    # ========================
    # /db users
    # ========================
    if cmd == "users":
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users ORDER BY created_at DESC")
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()

        if not rows:
            return await msg.reply_text("❌ Tidak ada user.")

        lines = ["👥 USERS:\n"]
        for u in rows:
            lines.append(
                f"- {u['telegram_id']} | @{u.get('username') or '-'} | {u.get('first_name') or ''} {u.get('last_name') or ''}".strip()
            )

        text = "\n".join(lines)
        return await send_long_text(msg, text)

    # ========================
    # /db accounts
    # ========================
    if cmd == "accounts":
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM xl_accounts ORDER BY updated_at DESC")
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()

        if not rows:
            return await msg.reply_text("❌ Tidak ada akun XL.")

        lines = ["📱 XL ACCOUNTS:\n"]
        for a in rows:
            status = "🟢 Active" if a.get("is_active") else "⚪ Inactive"
            lines.append(
                f"- {a['phone_number']} | user: {a['telegram_id']} | "
                f"type: {a.get('subscription_type') or '-'} | {status}"
            )

        text = "\n".join(lines)
        return await send_long_text(msg, text)

    # ========================
    # /db bookmarks
    # ========================
    if cmd == "bookmarks":
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM bookmarks ORDER BY created_at DESC"
        )
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()

        if not rows:
            return await msg.reply_text("❌ Tidak ada bookmark.")

        lines = ["⭐ BOOKMARKS:\n"]
        for b in rows:
            lines.append(
                f"- {b['id']} | user: {b['telegram_id']} | "
                f"{b.get('family_name') or ''} | {b.get('variant_name') or ''} | "
                f"code: {b['family_code']}"
            )

        text = "\n".join(lines)
        return await send_long_text(msg, text)

    # ========================
    # /db prefs
    # ========================
    if cmd == "prefs":
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM user_preferences")
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()

        if not rows:
            return await msg.reply_text("❌ Tidak ada preferences.")

        lines = ["⚙️ USER PREFERENCES:\n"]
        for p in rows:
            lines.append(
                f"- user {p['telegram_id']} | lang={p.get('language')} | notif={p.get('notifications_enabled')}"
            )

        text = "\n".join(lines)
        return await send_long_text(msg, text)

    # ========================
    # /db user <id>
    # ========================
    if cmd == "user" and len(args) > 1:
        try:
            tid = int(args[1])
        except ValueError:
            return await msg.reply_text("❌ telegram_id harus angka.")

        row = db.get_user(tid)
        if not row:
            return await msg.reply_text("❌ User tidak ditemukan.")

        lines = ["👤 USER DETAIL:\n"]
        for k, v in row.items():
            lines.append(f"{k}: {v}")

        text = "\n".join(lines)
        return await send_long_text(msg, text)

    # ========================
    # /db phone <628xxxx>
    # ========================
    if cmd == "phone" and len(args) > 1:
        phone = args[1]
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM xl_accounts WHERE phone_number = ?",
            (phone,),
        )
        r = cur.fetchone()
        conn.close()

        if not r:
            return await msg.reply_text("❌ Nomor tidak ditemukan.")

        data = dict(r)
        lines = ["📱 PHONE DETAIL:\n"]
        for k, v in data.items():
            lines.append(f"{k}: {v}")

        text = "\n".join(lines)
        return await send_long_text(msg, text)

    # ========================
    # Command tidak dikenali
    # ========================
    return await msg.reply_text("❌ Perintah tidak dikenali. Ketik /db untuk bantuan.")
