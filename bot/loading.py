# bot/loading.py

import asyncio
from telegram import Update
from telegram.ext import ContextTypes


class LoadingAnimation:
    """Loading animation helper"""
    
    ANIMATIONS = {
        'dots': ['⚪', '⚫'],
        'clock': ['🕐', '🕑', '🕒', '🕓', '🕔', '🕕'],
        'spinner': ['◐', '◓', '◑', '◒'],
        'arrows': ['⬆️', '↗️', '➡️', '↘️', '⬇️', '↙️', '⬅️', '↖️'],
        'loading': ['▱▱▱▱▱', '▰▱▱▱▱', '▰▰▱▱▱', '▰▰▰▱▱', '▰▰▰▰▱', '▰▰▰▰▰'],
    }
    
    def __init__(self, message, text: str = "Loading", animation: str = 'dots'):
        self.message = message
        self.base_text = text
        self.frames = self.ANIMATIONS.get(animation, self.ANIMATIONS['dots'])
        self.current_frame = 0
        self.is_running = False
        self.task = None
    
    async def start(self):
        """Start animation"""
        self.is_running = True
        self.task = asyncio.create_task(self._animate())
    
    async def stop(self, final_text: str = None):
        """Stop animation"""
        self.is_running = False
        if self.task:
            await self.task
        
        if final_text:
            try:
                await self.message.edit_text(final_text, parse_mode='HTML')
            except:
                pass
    
    async def _animate(self):
        """Animation loop"""
        while self.is_running:
            try:
                frame = self.frames[self.current_frame]
                text = f"{frame} {self.base_text}..."
                await self.message.edit_text(text)
                
                self.current_frame = (self.current_frame + 1) % len(self.frames)
                await asyncio.sleep(0.5)
            except Exception as e:
                # Message might be deleted or expired
                break


async def show_loading(query_or_message, text: str = "Memuat", animation: str = 'dots'):
    """
    Show loading animation
    
    Usage:
        loading, msg = await show_loading(query, "Memuat data")
        # Do something...
        await loading.stop("✅ Selesai!")
    """
    if hasattr(query_or_message, 'edit_message_text'):
        # It's a CallbackQuery
        msg = await query_or_message.edit_message_text(f"⚪ {text}...")
    else:
        # It's a Message
        msg = await query_or_message.reply_text(f"⚪ {text}...")
    
    loading = LoadingAnimation(msg, text, animation)
    await loading.start()
    
    return loading, msg


async def quick_loading(query_or_message, text: str, duration: float = 1.0):
    """
    Show quick loading animation for short operations
    
    Usage:
        await quick_loading(query, "Menyimpan")
        # Operation completes automatically after duration
    """
    if hasattr(query_or_message, 'edit_message_text'):
        msg = await query_or_message.edit_message_text(f"⚪ {text}...")
    else:
        msg = await query_or_message.reply_text(f"⚪ {text}...")
    
    await asyncio.sleep(duration)
    return msg