import sqlite3
import json
from datetime import datetime
from typing import Optional, Dict, List
import threading

class Database:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.db_path = "telegram_bot.db"
            self.initialized = True
    
    def get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_db(self):
        """Initialize database tables"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # XL Accounts table (multiple accounts per user)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS xl_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                phone_number TEXT NOT NULL,
                subscriber_id TEXT,
                subscription_type TEXT,
                refresh_token TEXT NOT NULL,
                access_token TEXT,
                id_token TEXT,
                token_expires_at TIMESTAMP,
                is_active BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (telegram_id) REFERENCES users(telegram_id),
                UNIQUE(telegram_id, phone_number)
            )
        """)
        
        # Bookmarks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bookmarks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                family_code TEXT NOT NULL,
                family_name TEXT,
                is_enterprise BOOLEAN,
                variant_name TEXT,
                option_name TEXT,
                order_num INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (telegram_id) REFERENCES users(telegram_id)
            )
        """)
        
        # User preferences table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_preferences (
                telegram_id INTEGER PRIMARY KEY,
                language TEXT DEFAULT 'en',
                notifications_enabled BOOLEAN DEFAULT 1,
                FOREIGN KEY (telegram_id) REFERENCES users(telegram_id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    # User operations
    def create_or_update_user(self, telegram_id: int, username: str = None, 
                             first_name: str = None, last_name: str = None):
        """Create or update user"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO users (telegram_id, username, first_name, last_name)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET
                username = excluded.username,
                first_name = excluded.first_name,
                last_name = excluded.last_name,
                updated_at = CURRENT_TIMESTAMP
        """, (telegram_id, username, first_name, last_name))
        
        conn.commit()
        conn.close()
    
    def get_user(self, telegram_id: int) -> Optional[Dict]:
        """Get user by telegram ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    # XL Account operations
    def add_xl_account(self, telegram_id: int, phone_number: str, 
                       refresh_token: str, subscriber_id: str = None,
                       subscription_type: str = None) -> bool:
        """Add XL account for user"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Set all other accounts as inactive
            cursor.execute("""
                UPDATE xl_accounts 
                SET is_active = 0 
                WHERE telegram_id = ?
            """, (telegram_id,))
            
            # Insert new account
            cursor.execute("""
                INSERT INTO xl_accounts 
                (telegram_id, phone_number, refresh_token, subscriber_id, 
                 subscription_type, is_active)
                VALUES (?, ?, ?, ?, ?, 1)
                ON CONFLICT(telegram_id, phone_number) DO UPDATE SET
                    refresh_token = excluded.refresh_token,
                    subscriber_id = excluded.subscriber_id,
                    subscription_type = excluded.subscription_type,
                    is_active = 1,
                    updated_at = CURRENT_TIMESTAMP
            """, (telegram_id, phone_number, refresh_token, subscriber_id, subscription_type))
            
            conn.commit()
            return True
        except Exception as e:
            print(f"Error adding XL account: {e}")
            return False
        finally:
            conn.close()
    
    def update_xl_tokens(self, telegram_id: int, phone_number: str,
                         access_token: str = None, id_token: str = None,
                         refresh_token: str = None):
        """Update XL account tokens"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        updates = []
        params = []
        
        if access_token:
            updates.append("access_token = ?")
            params.append(access_token)
        if id_token:
            updates.append("id_token = ?")
            params.append(id_token)
        if refresh_token:
            updates.append("refresh_token = ?")
            params.append(refresh_token)
        
        if updates:
            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.extend([telegram_id, phone_number])
            
            cursor.execute(f"""
                UPDATE xl_accounts 
                SET {', '.join(updates)}
                WHERE telegram_id = ? AND phone_number = ?
            """, params)
            
            conn.commit()
        conn.close()
    
    def get_active_xl_account(self, telegram_id: int) -> Optional[Dict]:
        """Get active XL account for user"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM xl_accounts 
            WHERE telegram_id = ? AND is_active = 1
        """, (telegram_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    def get_all_xl_accounts(self, telegram_id: int) -> List[Dict]:
        """Get all XL accounts for user"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM xl_accounts 
            WHERE telegram_id = ?
            ORDER BY is_active DESC, created_at DESC
        """, (telegram_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def set_active_xl_account(self, telegram_id: int, phone_number: str) -> bool:
        """Set active XL account"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Deactivate all accounts
            cursor.execute("""
                UPDATE xl_accounts 
                SET is_active = 0 
                WHERE telegram_id = ?
            """, (telegram_id,))
            
            # Activate selected account
            cursor.execute("""
                UPDATE xl_accounts 
                SET is_active = 1 
                WHERE telegram_id = ? AND phone_number = ?
            """, (telegram_id, phone_number))
            
            conn.commit()
            return True
        except Exception as e:
            print(f"Error setting active account: {e}")
            return False
        finally:
            conn.close()
    
    def delete_xl_account(self, telegram_id: int, phone_number: str) -> bool:
        """Delete XL account"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                DELETE FROM xl_accounts 
                WHERE telegram_id = ? AND phone_number = ?
            """, (telegram_id, phone_number))
            
            conn.commit()
            return True
        except Exception as e:
            print(f"Error deleting account: {e}")
            return False
        finally:
            conn.close()
    
    # Bookmark operations
    def add_bookmark(self, telegram_id: int, family_code: str, family_name: str,
                    is_enterprise: bool, variant_name: str, option_name: str,
                    order_num: int) -> bool:
        """Add bookmark"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO bookmarks 
                (telegram_id, family_code, family_name, is_enterprise, 
                 variant_name, option_name, order_num)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (telegram_id, family_code, family_name, is_enterprise,
                  variant_name, option_name, order_num))
            
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()
    
    def get_bookmarks(self, telegram_id: int) -> List[Dict]:
        """Get all bookmarks for user"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM bookmarks 
            WHERE telegram_id = ?
            ORDER BY created_at DESC
        """, (telegram_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def delete_bookmark(self, telegram_id: int, bookmark_id: int) -> bool:
        """Delete bookmark"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                DELETE FROM bookmarks 
                WHERE telegram_id = ? AND id = ?
            """, (telegram_id, bookmark_id))
            
            conn.commit()
            return True
        except Exception as e:
            print(f"Error deleting bookmark: {e}")
            return False
        finally:
            conn.close()
    
    # User preferences
    def get_preferences(self, telegram_id: int) -> Dict:
        """Get user preferences"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM user_preferences 
            WHERE telegram_id = ?
        """, (telegram_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return {
            'language': 'en',
            'notifications_enabled': True
        }
    
    def update_preferences(self, telegram_id: int, **kwargs):
        """Update user preferences"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO user_preferences (telegram_id, language, notifications_enabled)
            VALUES (?, ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET
                language = excluded.language,
                notifications_enabled = excluded.notifications_enabled
        """, (telegram_id, kwargs.get('language', 'en'), 
              kwargs.get('notifications_enabled', True)))
        
        conn.commit()
        conn.close()


# Initialize database instance
db = Database()

def init_db():
    """Initialize database"""
    db.init_db()