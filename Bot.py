import datetime
import os
import re
import threading
from zoneinfo import ZoneInfo
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8125086974:AAE3VCoDJkeyZghr4xChed5EX2JKeex17n1M")

MAX_CHANNELS_PER_FOLDER = 100
CHANNELS_PER_PAGE = 10
IST = ZoneInfo("Asia/Kolkata")

# Nee main & backup channels (alane unchamu)
CHANNELS = [
    (-1003941578746, "https://t.me/+Sg-HX3SVwnQyZjFl", "📢 MAIN CHANNEL 💸💸"),
    (-1002735833404, "https://t.me/+xbkyXV8t-0llN2E9", "📢 BACK-UP CHANNEL 💸💸"),
]

# Daily 3 times (IST): 10:00 AM, 05:35 PM, 09:00 PM
AUTO_POST_TIMES = [
    datetime.time(hour=10, minute=0, tzinfo=IST),
    datetime.time(hour=17, minute=5, tzinfo=IST),
    datetime.time(hour=21, minute=0, tzinfo=IST),
]

PROMO_POSTS = [
    (
        "🔥 *REDEEM CODES & TELEGRAM PREMIUM HUB* 🔥\n"
        "⌛️ *LIMITED TIME ACCESS!*\n\n"
        "*What You'll Get:*\n"
        "▪️ Play Store Redeem Code Drops & Rewards\n"
        "▪️ Telegram Premium Offers, Drops & Alerts\n"
        "▪️ Instant Access & Daily Fresh Updates\n\n"
        "🚀 *Start Bot Now 👇*\n\n"
        "@GROWTHDESK4BOT\n"
        "@GROWTHDESK4BOT\n\n"
        "📈 Add Your Channel In Our Bot\n"
        "📩 *DM TO ADD : @ChiranjeeviTrader4*"
    ),
]

# 10 Folders (Prathi folder lo up to 100 channels pettukovachu)
FOLDERS = {
    f"folder_{i}": {
        "title": f"📁 Folder {i}",
        "channels": [],
    }
    for i in range(1, 11)
}

# Example: Folder 1 lo kotha channel add cheyalante ila add cheyachu:
FOLDERS["folder_1"]["channels"].extend([
    ("📢 New Channel 1", "https://t.me/+26Fs7pXdGPoxZmI1"),
])


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


def get_folder_channels(folder_key: str) -> list:
    folder_data = FOLDERS.get(folder_key, {})
    channels = folder_data.get("channels", [])
    return channels[:MAX_CHANNELS_PER_FOLDER]


def extract_postable_target(value):
    if isinstance(value, int):
        return value
    s = str(value).strip()
    if re.fullmatch(r"-?\d+", s):
        return int(s)
    if s.startswith("@"):
        return s
    match = re.match(r"^https?://t\.me/([A-Za-z0-9_]+)/?$", s)
    if match and not match.group(1).startswith("+"):
        return f"@{match.group(1)}"
    return None


def get_all_target_chats() -> list:
    targets = []
    seen = set()

    for ch_id, ch_url, _ in CHANNELS:
        t = extract_postable_target(ch_id) or extract_postable_target(ch_url)
        if t is not None and t not in seen:
            seen.add(t)
            targets.append(t)

    for folder_key in FOLDERS:
        for _, ch_url in get_folder_channels(folder_key):
            t = extract_postable_target(ch_url)
            if t is not None and t not in seen:
                seen.add(t)
                targets.append(t)

    return targets


async def get_missing_channels(context: ContextTypes.DEFAULT_TYPE, user_id: int):
    missing = []
    for ch_id, ch_url, label in CHANNELS:
        try:
            member = await context.bot.get_chat_member(chat_id=ch_id, user_id=user_id)
            print(f"Channel {ch_id} status for {user_id}: {member.status}", flush=True)
            if member.status not in ("member", "administrator", "creator"):
                missing.append((ch_url, label))
        except Exception as e:
            print(f"Error checking channel {ch_id}: {e}", flush=True)
            missing.append((ch_url, label))
    return missing


def build_main_keyboard(missing: list):
    keyboard = []

    for url, label in missing:
        keyboard.append([InlineKeyboardButton(label, url=url)])

    # 10 Folder buttons arranged 2 per row (5 rows)
    folder_keys = list(FOLDERS.keys())
    for idx in range(0, len(folder_keys), 2):
        row = []
        for key in folder_keys[idx : idx + 2]:
            title = FOLDERS[key]["title"]
            row.append(InlineKeyboardButton(title, callback_data=f"folder:{key}:0"))
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton("✅ Check Joined", callback_data="verify_join")])
    return InlineKeyboardMarkup(keyboard)


def build_folder_keyboard(folder_key: str, page: int = 0):
    channels = get_folder_channels(folder_key)
    total_channels = len(channels)
    total_pages = max(1, (total_channels + CHANNELS_PER_PAGE - 1) // CHANNELS_PER_PAGE)
    page = max(0, min(page, total_pages - 1))

    start_idx = page * CHANNELS_PER_PAGE
    end_idx = start_idx + CHANNELS_PER_PAGE
    page_channels = channels[start_idx:end_idx]

    keyboard = []
    for ch_label, ch_url in page_channels:
        keyboard.append([InlineKeyboardButton(ch_label, url=ch_url)])

    # Pagination controls when there are multiple pages
    if total_pages > 1:
        nav_row = []
        if page > 0:
            nav_row.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"folder:{folder_key}:{page - 1}"))
        nav_row.append(InlineKeyboardButton(f"{page + 1}/{total_pages}", callback_data="noop"))
        if page < total_pages - 1:
            nav_row.append(InlineKeyboardButton("Next ➡️", callback_data=f"folder:{folder_key}:{page + 1}"))
        keyboard.append(nav_row)

    keyboard.append([InlineKeyboardButton("⬅️ Back to Main", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)


async def send_scheduled_promo(context: ContextTypes.DEFAULT_TYPE):
    if not PROMO_POSTS:
        return

    slot_index = context.job.data if (context.job and isinstance(context.job.data, int)) else 0
    post_text = PROMO_POSTS[slot_index % len(PROMO_POSTS)]
    targets = get_all_target_chats()

    for chat_target in targets:
        try:
            await context.bot.send_message(
                chat_id=chat_target,
                text=post_text,
                parse_mode="Markdown",
            )
            print(f"Auto-posted promo slot {slot_index} to {chat_target}", flush=True)
        except Exception as e:
            print(f"Failed auto-post to {chat_target}: {e}", flush=True)


async def show_gate(update: Update, context: ContextTypes.DEFAULT_TYPE, missing: list, edit: bool = False):
    text = (
        "⚠️ *ACTION REQUIRED*\n\n"
        "Please join the required channels to use this bot.\n"
        "Once joined, click *'Check Joined'* below."
    )
    reply_markup = build_main_keyboard(missing)

    if edit and update.callback_query:
        await update.callback_query.edit_message_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode="Markdown",
        )
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=text,
            reply_markup=reply_markup,
            parse_mode="Markdown",
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
            parse_mode="Markdown",
        )
    else:
        await show_gate(update, context, missing, edit=False)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await check_and_unlock(update, context)


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data or ""

    if data == "noop":
        return

    if data == "verify_join":
        await check_and_unlock(update, context)

    elif data.startswith("folder:"):
        parts = data.split(":")
        folder_key = parts[1]
        page = int(parts[2]) if len(parts) > 2 else 0
        folder_data = FOLDERS.get(folder_key)
        if folder_data:
            channels = get_folder_channels(folder_key)
            await query.edit_message_text(
                text=f"*{folder_data['title']}* ({len(channels)}/{MAX_CHANNELS_PER_FOLDER} channels)\n\nChannels select cheyyi:",
                reply_markup=build_folder_keyboard(folder_key, page=page),
                parse_mode="Markdown",
            )

    elif data == "back_main":
        missing = await get_missing_channels(context, update.effective_user.id)
        await show_gate(update, context, missing, edit=True)


def schedule_promo_jobs(app):
    if app.job_queue is None:
        print("Warning: job_queue is None. Install python-telegram-bot[job-queue] for auto-posts.", flush=True)
        return

    for idx, post_time in enumerate(AUTO_POST_TIMES):
        app.job_queue.run_daily(
            send_scheduled_promo,
            time=post_time,
            data=idx,
            name=f"promo_job_{idx}",
        )
        print(f"Scheduled promo job #{idx + 1} at {post_time}", flush=True)


if __name__ == "__main__":
    start_health_server()
    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .connect_timeout(30.0)
        .read_timeout(30.0)
        .build()
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    schedule_promo_jobs(app)
    print("Bot polling started...", flush=True)
    app.run_polling(drop_pending_updates=True)
    
