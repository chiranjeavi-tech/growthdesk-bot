import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler

BOT_TOKEN = os.environ.get("BOT_TOKEN", "9120888974:AAE3VCcdJXeyZghrxC9ed5EX2JKeew17m3M")

CHANNELS = [
   (-1003941578746, "https://t.me/+Sg-HX3SVwnQyZjFl", "📢 Join Channel 1"),
  (-1002735833404, "https://t.me/+xbkyXV8t-0llN2E9", "📢 Join Channel 2"),
]

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, format, *args):
        return

def start_health_server():
    port = int(os.environ.get("PORT", "10000"))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()

async def get_missing_channels(context: ContextTypes.DEFAULT_TYPE, user_id: int):
    missing = []
    for ch_id, ch_url, label in CHANNELS:
        try:
            member = await context.bot.get_chat_member(chat_id=ch_id, user_id=user_id)
            print(f"Channel {ch_id} status for {user_id}: {member.status}", flush=True)
            if member.status not in ["member", "administrator", "creator"]:
                missing.append((ch_url, label))
        except Exception as e:
            print(f"Error checking channel {ch_id}: {e}", flush=True)
            missing.append((ch_url, label))
    return missing

async def show_gate(context: ContextTypes.DEFAULT_TYPE, chat_id: int, missing: list):
    keyboard = [[InlineKeyboardButton(label, url=url)] for url, label in missing]
    keyboard.append([InlineKeyboardButton("✅ Joined, Verify", callback_data="verify_join")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(
        chat_id=chat_id,
        text="🔒 *Access Locked!*\n\nGrowth Desk access kosam kindha unna channels lo join ayyi *Joined, Verify* nokku.",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def check_and_unlock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    print(f"Received /start or verify from user={user_id}, chat={chat_id}", flush=True)
    missing = await get_missing_channels(context, user_id)

    if not missing:
        await context.bot.send_message(
            chat_id=chat_id,
            text="🎉 *Verified!* Growth Desk access unlock ayyindi.",
            parse_mode="Markdown"
        )
    else:
        await show_gate(context, chat_id, missing)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await check_and_unlock(update, context)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "verify_join":
        await check_and_unlock(update, context)

if __name__ == "__main__":
    start_health_server()
    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .connect_timeout(30.0)
        .read_timeout(30.0)
        .get_updates_connect_timeout(30.0)
        .get_updates_read_timeout(30.0)
        .build()
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    print("Growth Desk Bot is running...", flush=True)
    app.run_polling(drop_pending_updates=False)
  
