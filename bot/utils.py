import time
from typing import Optional, Dict
from telegram import InlineKeyboardButton
from bot.database import db
from app.client.ciam import get_new_token
from app.client.engsel import get_profile
from app.util import ensure_api_key


class SessionManager:
    """Manage user sessions with token refresh"""
    
    def __init__(self):
        self.sessions = {}  # telegram_id -> session data
        self.api_key = ensure_api_key()
    
    def get_session(self, telegram_id: int) -> Optional[Dict]:
        """Get or create session for user"""
        
        # Check if session exists and is valid
        if telegram_id in self.sessions:
            session = self.sessions[telegram_id]
            # Check if tokens need refresh (older than 5 minutes)
            if time.time() - session.get('last_refresh', 0) < 300:
                return session
        
        # Get active XL account
        xl_account = db.get_active_xl_account(telegram_id)
        if not xl_account:
            return None
        
        # Refresh tokens
        try:
            tokens = get_new_token(
                self.api_key,
                xl_account['refresh_token'],
                xl_account['subscriber_id']
            )
            
            if not tokens:
                return None
            
            # Update database
            db.update_xl_tokens(
                telegram_id=telegram_id,
                phone_number=xl_account['phone_number'],
                access_token=tokens['access_token'],
                id_token=tokens['id_token'],
                refresh_token=tokens.get('refresh_token', xl_account['refresh_token'])
            )
            
            # Create session
            session = {
                'api_key': self.api_key,
                'tokens': tokens,
                'phone_number': xl_account['phone_number'],
                'subscriber_id': xl_account['subscriber_id'],
                'subscription_type': xl_account['subscription_type'],
                'last_refresh': time.time()
            }
            
            self.sessions[telegram_id] = session
            return session
            
        except Exception as e:
            print(f"Error refreshing session for {telegram_id}: {e}")
            return None
    
    def clear_session(self, telegram_id: int):
        """Clear session for user"""
        if telegram_id in self.sessions:
            del self.sessions[telegram_id]
    
    def refresh_session(self, telegram_id: int) -> bool:
        """Force refresh session"""
        self.clear_session(telegram_id)
        session = self.get_session(telegram_id)
        return session is not None


# Global session manager instance
session_manager = SessionManager()


def get_user_session(telegram_id: int) -> Optional[Dict]:
    """Get user session"""
    return session_manager.get_session(telegram_id)


def refresh_user_session(telegram_id: int) -> bool:
    """Refresh user session"""
    return session_manager.refresh_session(telegram_id)


def clear_user_session(telegram_id: int):
    """Clear user session"""
    session_manager.clear_session(telegram_id)


def format_currency(amount: int) -> str:
    """Format currency"""
    return f"Rp {amount:,}".replace(',', '.')


def format_quota(bytes_amount: int) -> str:
    """Format data quota"""
    GB = 1024 ** 3
    MB = 1024 ** 2
    KB = 1024
    
    if bytes_amount >= GB:
        return f"{bytes_amount / GB:.2f} GB"
    elif bytes_amount >= MB:
        return f"{bytes_amount / MB:.2f} MB"
    elif bytes_amount >= KB:
        return f"{bytes_amount / KB:.2f} KB"
    else:
        return f"{bytes_amount} B"


def truncate_text(text: str, max_length: int = 50) -> str:
    """Truncate text to max length"""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."


def escape_markdown(text: str) -> str:
    """Escape markdown special characters"""
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text


def split_message(text: str, max_length: int = 4096) -> list:
    """Split long message into multiple messages"""
    if len(text) <= max_length:
        return [text]
    
    messages = []
    current = ""
    
    for line in text.split('\n'):
        if len(current) + len(line) + 1 <= max_length:
            current += line + '\n'
        else:
            if current:
                messages.append(current)
            current = line + '\n'
    
    if current:
        messages.append(current)
    
    return messages


def parse_callback_data(callback_data: str) -> Dict[str, str]:
    """Parse callback data into dictionary"""
    parts = callback_data.split('_')
    if len(parts) < 2:
        return {'action': callback_data}
    
    result = {'prefix': parts[0], 'action': parts[1]}
    
    if len(parts) > 2:
        result['data'] = '_'.join(parts[2:])
    
    return result


def build_callback_data(prefix: str, action: str, data: str = None) -> str:
    """Build callback data string"""
    callback = f"{prefix}_{action}"
    if data:
        callback += f"_{data}"
    return callback[:64]  # Telegram limit


def get_error_message(error: Exception) -> str:
    """Get user-friendly error message"""
    error_str = str(error).lower()
    
    if 'timeout' in error_str:
        return "⏱️ Koneksi timeout. Silakan coba lagi."
    elif 'connection' in error_str:
        return "🔌 Gagal terhubung ke server. Periksa koneksi internet Anda."
    elif 'invalid' in error_str:
        return "❌ Data tidak valid. Silakan coba lagi."
    elif 'token' in error_str:
        return "🔐 Sesi berakhir. Silakan login kembali dengan /login"
    else:
        return f"❌ Terjadi kesalahan: {str(error)}"


def validate_phone_number(phone: str) -> tuple[bool, str]:
    """Validate phone number format"""
    phone = phone.strip()
    
    if not phone.startswith('628'):
        return False, "Nomor harus diawali dengan 628"
    
    if not phone.isdigit():
        return False, "Nomor hanya boleh berisi angka"
    
    if len(phone) < 11 or len(phone) > 14:
        return False, "Panjang nomor harus 11-14 digit"
    
    return True, "Valid"


def format_date(timestamp: int) -> str:
    """Format timestamp to readable date"""
    from datetime import datetime
    dt = datetime.fromtimestamp(timestamp)
    return dt.strftime("%d %b %Y, %H:%M WIB")


def get_pagination_keyboard(current_page: int, total_pages: int, 
                           prefix: str, action: str) -> list:
    """Generate pagination keyboard"""
    keyboard = []
    buttons = []
    
    # Previous button
    if current_page > 1:
        buttons.append(InlineKeyboardButton(
            "⬅️ Prev",
            callback_data=f"{prefix}_{action}_{current_page-1}"
        ))
    
    # Page indicator
    buttons.append(InlineKeyboardButton(
        f"📄 {current_page}/{total_pages}",
        callback_data="ignore"
    ))
    
    # Next button
    if current_page < total_pages:
        buttons.append(InlineKeyboardButton(
            "Next ➡️",
            callback_data=f"{prefix}_{action}_{current_page+1}"
        ))
    
    if buttons:
        keyboard.append(buttons)
    
    return keyboard