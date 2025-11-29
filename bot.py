import json
import os
import re
from typing import Dict

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, constants
from telegram.ext import (
    Application, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters, Defaults
)

# ---------------- Config ----------------
TOKEN = os.getenv("BOT_TOKEN")           # مهم: توکن از محیط میاد
OWNER_ID = 1645273556                    # آیدی خودت
YOUTUBE_URL = "https://www.youtube.com/channel/UCfyIOJ9fAt7GtnetPRACCxA"
STATE_FILE = "state.json"
DELETE_ENGLISH = True

# کلمات ممنوعه
BLOCKED_WORDS = ["کسخل", "لاشی", "کس", "کص", "کیر"]


def _normalize_fa(text: str) -> str:
    if not text:
        return ""
    text = text.replace("ك", "ک").replace("ي", "ی").replace("ة", "ه").replace("ۀ", "ه")
    text = text.replace("أ", "ا").replace("إ", "ا").replace("ؤ", "و").replace("ئ", "ی")
    text = re.sub(r"[\u0640]", "", text)
    text = re.sub(r"[\u064B-\u065F\u0670\u06D6-\u06ED]", "", text)
    text = re.sub(r"[\u200b\u200c]", "", text)
    text = re.sub(r"[^0-9A-Za-z\u0600-\u06FF]", "", text)
    return text.lower()


def contains_blocked_word(message: str) -> bool:
    norm_msg = _normalize_fa(message)
    for w in BLOCKED_WORDS:
        if _normalize_fa(w) in norm_msg:
            return True
    return False


def contains_english(message: str) -> bool:
    return bool(re.search(r"[A-Za-z]", message or ""))


# ---------------- State File ----------------
def load_state() -> Dict[str, Dict[str, bool]]:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_state(state: Dict[str, Dict[str, bool]]):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


STATE = load_state()


def ensure_user(state: Dict[str, Dict[str, bool]], user_id: int):
    if str(user_id) not in state:
        state[str(user_id)] = {"allowed": False, "clicked_link": False}


# ---------------- Handlers ----------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    user = update.effective_user
    chat = update.effective_chat
    text = update.message.text or ""
    user_id = user.id

    # صاحب ربات فیلتر نمی‌شود
    if user_id == OWNER_ID:
        return

    ensure_user(STATE, user_id)
    st = STATE[str(user_id)]

    # اگر اجازه ندارد
    if not st["allowed"]:
        try:
            await update.message.delete()
        except:
            pass

        mention = user.mention_html() if user else "کاربر"

        keyboard = [
            [InlineKeyboardButton("📺 گرفتن لینک کانال یوتیوب", callback_data=f"get_link:{user_id}")],
            [InlineKeyboardButton("✅ سابسکرایب کردم", callback_data=f"subscribed:{user_id}")]
        ]

        await chat.send_message(
            text=f"👋 {mention}\n\nبرای ارسال پیام، اول «گرفتن لینک کانال یوتیوب» رو بزن و بعد «سابسکرایب کردم».",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    # فیلتر انگلیسی
    if DELETE_ENGLISH and contains_english(text):
        try:
            await update.message.delete()
        except:
            pass
        return

    # فیلتر کلمات ممنوعه
    if contains_blocked_word(text):
        try:
            await update.message.delete()
        except:
            pass
        return


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return

    user = query.from_user
    user_id = user.id
    data = query.data

    ensure_user(STATE, user_id)
    st = STATE[str(user_id)]

    if ":" in data:
        action, target_id = data.split(":")
        if int(target_id) != user_id:
            await query.answer("این دکمه برای تو نیست.", show_alert=True)
            return
    else:
        action = data

    if action == "get_link":
        st["clicked_link"] = True
        save_state(STATE)
        await query.answer("لینک برایت ارسال شد.")
        kb = [[InlineKeyboardButton("باز کردن کانال یوتیوب", url=YOUTUBE_URL)]]
        await query.message.reply_text("📺 اینم کانال:", reply_markup=InlineKeyboardMarkup(kb))

    elif action == "subscribed":
        if not st["clicked_link"]:
            await query.answer("اول لینک کانال رو بگیر.", show_alert=True)
            return
        st["allowed"] = True
        save_state(STATE)
        await query.answer("دسترسی فعال شد!")
        try:
            await query.edit_message_text("🎉 حالا می‌تونی پیام بدی.")
        except:
            pass


async def main():
    defaults = Defaults(parse_mode=constants.ParseMode.HTML)
    app = Application.builder().token(TOKEN).defaults(defaults).build()

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(handle_callback))

    print("Bot is running on Render...")
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    await app.updater.idle()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
