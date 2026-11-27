import datetime
import json
import os
import re
import threading
import time
import urllib.request
from zoneinfo import ZoneInfo
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import Conflict
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8125086974:AAE3VCoDJkeyZghr4xChed5EX2JKeex17n1M")
ADMIN_USERNAMES = {"chiranjeevitrader4", "chiranjeavitrader4", "chiranjeavittrader4"}
ADMIN_USER_IDS = {
    int(x.strip())
    for x in os.environ.get("        ", "").split(",")
    if x.strip().isdigit()
}

DISPLAY_USERS_LABEL = "10k"
MAX_CHANNELS_PER_FOLDER = 100
CHANNELS_PER_PAGE = 10
MAX_REDEEM_CAP = 25
PER_REFERRAL_AMOUNT = 0.30
BONUS_AMOUNT = 10.0
NEW_USER_BONUS_AMOUNT = 10.0
REDEEM_SLABS = [(10, 10), (15, 15), (25, 25)]
IST = ZoneInfo("Asia/Kolkata")
WALLET_STORE_FILE = os.environ.get("WALLET_STORE_FILE", "user_wallets.json")
REDEEM_PHOTO_URL = "https://raw.githubusercontent.com/chiranjeavi-tech/growthdesk-bot/main/1795660640966.png"

CHANNELS = [
    (-1003941578746, "https://t.me/+L_jUVKFNZp5mOGJl", "📢 MAIN CHANNEL 💸💸"),
    (-1002735833404, "https://t.me/+6g8Hcs_EYOhlODM1", "📢 BACK-UP CHANNEL 💸💸"),
]

FOLDER_3_LINK = "https://t.me/addlist/-Qq__yiQlZQzODZl"
FOLDER_4_LINK = "https://t.me/addlist/UNOERSRR-Zs0Njk1"

AUTO_POST_TIMES = [
    datetime.time(hour=10, minute=0, tzinfo=IST),
    datetime.time(hour=13, minute=0, tzinfo=IST),
    datetime.time(hour=17, minute=5, tzinfo=IST),
    datetime.time(hour=21, minute=0, tzinfo=IST),
]

PROMO_POSTS = [
    (
        "🔥 *REDEEM CODES & TELEGRAM PREMIUM HUB* 🔥\n"
        "⌛️ *LIMITED TIME ACCESS!*\n\n"
        "*What You'll Get:*\n"
        "▪️ Per Referral: 0.30 | Bonus & New User Bonus: 10.00\n"
        "▪️ Redeem Codes: 10 Refs = ₹10 | 15 Refs = ₹15 | 25 Refs = ₹25\n"
        "▪️ Instant Access & Daily Fresh Updates\n\n"
        "🚀 *Start Bot Now 👇*\n\n"
        "@GROWTHDESK4BOT\n"
        "@GROWTHDESK4BOT\n\n"
        "📈 Add Your Channel In Our Bot\n"
        "📩 *DM TO ADD : @ChiranjeeviTrader4*"
    ),
]

FOLDERS = {f"folder_{i}": {"title": f"📁 Folder {i}", "channels": []} for i in range(1, 11)}
FOLDERS["folder_1"]["channels"].extend([("📢 New Channel 1", "https://t.me/+26Fs7pXdGPoxZmI1")])


def is_admin_user(update: Update) -> bool:
    user = update.effective_user
    if not user:
        return False
    if user.id in ADMIN_USER_IDS:
        return True
    return bool(user.username and user.username.strip().lower() in ADMIN_USERNAMES)


def _load_wallets() -> dict:
    if not os.path.exists(WALLET_STORE_FILE):
        return {}
    try:
        with open(WALLET_STORE_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
        loaded = {}
        for uid_str, data in raw.items():
            if re.fullmatch(r"\d+", str(uid_str)):
                loaded[int(uid_str)] = {
                    "balance": float(data.get("balance", 0.0)),
                    "referrals": int(data.get("referrals", 0)),
                    "referred_by": data.get("referred_by"),
                    "claimed_newcomer": bool(data.get("claimed_newcomer", False)),
                    "claimed_bonus": bool(data.get("claimed_bonus", False)),
                    "username": data.get("username", ""),
                    "first_name": data.get("first_name", ""),
                    "last_seen": data.get("last_seen", ""),
                }
        return loaded
    except Exception as e:
        print(f"Error loading wallets file: {e}", flush=True)
        return {}


def _save_wallets():
    try:
        with open(WALLET_STORE_FILE, "w", encoding="utf-8") as f:
            json.dump({str(uid): data for uid, data in USER_WALLETS.items()}, f, indent=2)
    except Exception as e:
        print(f"Error saving wallets file: {e}", flush=True)


USER_WALLETS = _load_wallets()


def get_user_wallet(user_id: int) -> dict:
    if user_id not in USER_WALLETS:
        USER_WALLETS[user_id] = {
            "balance": 0.0,
            "referrals": 0,
            "referred_by": None,
            "claimed_newcomer": False,
            "claimed_bonus": False,
            "username": "",
            "first_name": "",
            "last_seen": "",
        }
        _save_wallets()
    return USER_WALLETS[user_id]


def _track_current_user(update: Update):
    user = update.effective_user
    if not user:
        return
    w = get_user_wallet(user.id)
    w["username"] = f"@{user.username}" if user.username else "NoUsername"
    w["first_name"] = user.first_name or "Unknown"
    w["last_seen"] = datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M")
    _save_wallets()


def format_amount(amount: float) -> str:
    return f"{amount:.2f}"


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, format, *args):
        return


def _keep_alive_loop():
    ping_url = os.environ.get("RENDER_EXTERNAL_URL", "https://growthdesk-bot.onrender.com")
    while True:
        time.sleep(300)
        try:
            with urllib.request.urlopen(ping_url, timeout=15):
                pass
        except Exception:
            pass


def start_health_server():
    port = int(os.environ.get("PORT", "10000"))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    threading.Thread(target=_keep_alive_loop, daemon=True).start()


def get_folder_channels(folder_key: str) -> list:
    return FOLDERS.get(folder_key, {}).get("channels", [])[:MAX_CHANNELS_PER_FOLDER]


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
    targets, seen = [], set()
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
            if member.status not in ("member", "administrator", "creator"):
                missing.append((ch_url, label))
        except Exception as e:
            print(f"Error checking channel {ch_id}: {e}", flush=True)
            missing.append((ch_url, label))
    return missing


def build_two_folders_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📁 Folder 1 (100)", url=FOLDER_3_LINK),
            InlineKeyboardButton("📁 Folder 2 (100)", url=FOLDER_4_LINK),
        ]
    ])


def build_main_keyboard(missing: list):
    keyboard = [[InlineKeyboardButton(label, url=url)] for url, label in missing]
    folder_row = []
    if FOLDER_3_LINK:
        folder_row.append(InlineKeyboardButton("➕ Join", url=FOLDER_3_LINK))
    if FOLDER_4_LINK:
        folder_row.append(InlineKeyboardButton("➕ Join", url=FOLDER_4_LINK))
    if folder_row:
        keyboard.append(folder_row)
    keyboard.append([InlineKeyboardButton("✅ Check Joined", callback_data="verify_join")])
    return InlineKeyboardMarkup(keyboard)


def build_folder_keyboard(folder_key: str, page: int = 0):
    channels = get_folder_channels(folder_key)
    total_pages = max(1, (len(channels) + CHANNELS_PER_PAGE - 1) // CHANNELS_PER_PAGE)
    page = max(0, min(page, total_pages - 1))
    page_channels = channels[page * CHANNELS_PER_PAGE : (page + 1) * CHANNELS_PER_PAGE]
    keyboard = [[InlineKeyboardButton(lbl, url=u)] for lbl, u in page_channels]
    if total_pages > 1:
        nav = []
        if page > 0:
            nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"folder:{folder_key}:{page - 1}"))
        nav.append(InlineKeyboardButton(f"{page + 1}/{total_pages}", callback_data="noop"))
        if page < total_pages - 1:
            nav.append(InlineKeyboardButton("Next ➡️", callback_data=f"folder:{folder_key}:{page + 1}"))
        keyboard.append(nav)
    keyboard.append([InlineKeyboardButton("⬅️ Back to Main", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)


def build_unlocked_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(f"🎟 Redeem (Max ₹{MAX_REDEEM_CAP})", callback_data="sec_redeem"),
            InlineKeyboardButton(f"🔗 Referral ({format_amount(PER_REFERRAL_AMOUNT)})", callback_data="sec_referral"),
        ],
        [
            InlineKeyboardButton(f"🎁 Bonus ({format_amount(BONUS_AMOUNT)})", callback_data="sec_bonus"),
            InlineKeyboardButton(f"🆕 New User Bonus ({format_amount(NEW_USER_BONUS_AMOUNT)})", callback_data="sec_newcomer"),
        ],
    ])


def format_redeem_slabs() -> str:
    return " | ".join(f"{refs} Refs = ₹{code_rs}" for refs, code_rs in REDEEM_SLABS)


def apply_referral_if_valid(user_id: int, args: list):
    if not args:
        return
    raw_ref = args[0].strip()
    if not re.fullmatch(r"\d+", raw_ref):
        return
    referrer_id = int(raw_ref)
    if referrer_id == user_id:
        return
    wallet = get_user_wallet(user_id)
    if wallet["referred_by"] is None:
        wallet["referred_by"] = referrer_id
        ref_wallet = get_user_wallet(referrer_id)
        ref_wallet["referrals"] += 1
        ref_wallet["balance"] = round(ref_wallet["balance"] + PER_REFERRAL_AMOUNT, 2)
        _save_wallets()


async def send_redeem_with_photo(chat_id: int, user_id: int, context: ContextTypes.DEFAULT_TYPE, edit_query=None):
    wallet = get_user_wallet(user_id)
    caption_text = (
        f"💰 *Wallet Balance:* {format_amount(wallet['balance'])}\n"
        f"👥 *Referrals:* {wallet['referrals']}\n"
        f"🎟 *Redeem Codes:* {format_redeem_slabs()}"
    )
    try:
        await context.bot.send_photo(
            chat_id=chat_id,
            photo=REDEEM_PHOTO_URL,
            caption=caption_text,
            reply_markup=build_unlocked_keyboard(),
            parse_mode="Markdown",
        )
    except Exception as e:
        print(f"Photo send failed: {e}", flush=True)
        if edit_query is not None:
            await edit_query.edit_message_text(
                text=caption_text,
                reply_markup=build_unlocked_keyboard(),
                parse_mode="Markdown",
            )
        else:
            await context.bot.send_message(
                chat_id=chat_id,
                text=caption_text,
                reply_markup=build_unlocked_keyboard(),
                parse_mode="Markdown",
            )


async def send_unlocked_hub(chat_id: int, user_id: int, context: ContextTypes.DEFAULT_TYPE):
    wallet = get_user_wallet(user_id)
    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            "🎉 *Verified! Growth Desk access unlocked.*\n\n"
            f"💰 *Wallet Balance:* {format_amount(wallet['balance'])}\n\n"
            "Tap a button below to view details 👇"
        ),
        reply_markup=build_unlocked_keyboard(),
        parse_mode="Markdown",
    )


async def send_scheduled_promo(context: ContextTypes.DEFAULT_TYPE):
    if not PROMO_POSTS:
        return
    slot_index = context.job.data if (context.job and isinstance(context.job.data, int)) else 0
    post_text = PROMO_POSTS[slot_index % len(PROMO_POSTS)]
    for chat_target in get_all_target_chats():
        try:
            await context.bot.send_photo(
                chat_id=chat_target,
                photo=REDEEM_PHOTO_URL,
                caption=post_text,
                parse_mode="Markdown",
            )
        except Exception:
            try:
                await context.bot.send_message(chat_id=chat_target, text=post_text, parse_mode="Markdown")
            except Exception as inner_e:
                print(f"Failed auto-post to {chat_target}: {inner_e}", flush=True)


async def show_gate(update: Update, context: ContextTypes.DEFAULT_TYPE, missing: list, edit: bool = False):
    text = (
        "⚠️ *ACTION REQUIRED*\n\n"
        "Please join the required channels and folders to use this bot.\n"
        "Once joined, click *'Check Joined'* below."
    )
    reply_markup = build_main_keyboard(missing)
    if edit and update.callback_query:
        await update.callback_query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=text,
            reply_markup=reply_markup,
            parse_mode="Markdown",
        )


async def check_and_unlock(update: Update, context: ContextTypes.DEFAULT_TYPE, from_verify_button: bool = False):
    _track_current_user(update)
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    missing = await get_missing_channels(context, user_id)
    if not missing:
        if from_verify_button and update.callback_query:
            await update.callback_query.answer(text="✅ Verified! Access unlocked.", show_alert=False)
        await send_unlocked_hub(chat_id=chat_id, user_id=user_id, context=context)
    else:
        if from_verify_button and update.callback_query:
            await update.callback_query.answer(
                text="❌ You have not joined the required channels/folders yet. Please join and try again.",
                show_alert=True,
            )
            return
        await show_gate(update, context, missing, edit=False)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _track_current_user(update)
    apply_referral_if_valid(update.effective_user.id, context.args or [])
    await check_and_unlock(update, context, from_verify_button=False)


async def go_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _track_current_user(update)
    user_id = update.effective_user.id
    missing = await get_missing_channels(context, user_id)
    if missing:
        await show_gate(update, context, missing, edit=False)
        return
    await send_redeem_with_photo(chat_id=update.effective_chat.id, user_id=user_id, context=context)


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _track_current_user(update)
    if not is_admin_user(update):
        return
    total_users = len(USER_WALLETS)
    total_refs = sum(w.get("referrals", 0) for w in USER_WALLETS.values())
    total_balance = sum(float(w.get("balance", 0.0)) for w in USER_WALLETS.values())
    recent_lines = [
        f"• `{uid}` | {w.get('username') or 'NoUsername'} ({w.get('first_name') or 'Unknown'}) — *{format_amount(float(w.get('balance', 0.0)))}* | {w.get('last_seen') or '-'}"
        for uid, w in list(USER_WALLETS.items())[-15:]
    ]
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=(
            "📊 *Admin Stats*\n\n"
            f"👥 *Display Users:* *{DISPLAY_USERS_LABEL}*\n"
            f"👤 *Real Users:* *{total_users}*\n"
            f"🔗 *Total Referrals:* *{total_refs}*\n"
            f"💰 *Total Wallet Balance:* *{format_amount(total_balance)}*\n\n"
            "🧾 *Recent Users:*\n" + ("\n".join(recent_lines) if recent_lines else "No users yet")
        ),
        parse_mode="Markdown",
    )
       async def reaction_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _track_current_user(update)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=(
            "🎭 Emoji Info & Reactions\n\n"
            "• Tap reactions on broadcast posts in channels.\n"
            "• Use /go to open your wallet, bonuses, and redeem slabs."
        ),
    )
    
async def use_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _track_current_user(update)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=(
            "📝 How to Use @GROWTHDESK4BOT\n\n"
            "1. Join required channels & folders, then tap Check Joined.\n"
            "2. Run /go to open your wallet and buttons.\n"
            f"3. Earn {format_amount(PER_REFERRAL_AMOUNT)} per referral; milestones: {format_redeem_slabs()}."
        ),

async def hub_command(update: Update, context: ContextTypes.DEFAULT_TYPE):  
    _track_current_user(update)
    user_id = update.effective_user.id
    missing = await get_missing_channels(context, user_id)
    if missing:
        await show_gate(update, context, missing, edit=False)
        return
    await send_unlocked_hub(chat_id=update.effective_chat.id, user_id=user_id, context=context)


async def newcomer_command(update: Update, context: ContextTypes.DEFAULT_TYPE):    
    _track_current_user(update)
    user_id = update.effective_user.id
    missing = await get_missing_channels(context, user_id)
    if missing:
        await show_gate(update, context, missing, edit=False)
        return
    wallet = get_user_wallet(user_id)
    if not wallet["claimed_newcomer"]:
        wallet["claimed_newcomer"] = True
        wallet["balance"] = round(wallet["balance"] + NEW_USER_BONUS_AMOUNT, 2)
        _save_wallets()
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=(
            "🆕 *New User Bonus*\n"
            f"Bonus Amount: *{format_amount(NEW_USER_BONUS_AMOUNT)}*\n"
            f"💰 *Wallet Balance:* *{format_amount(wallet['balance'])}*"
        ),
        reply_markup=build_unlocked_keyboard(),
        parse_mode="Markdown",
    )


async def redeem_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _track_current_user(update)
    user_id = update.effective_user.id
    missing = await get_missing_channels(context, user_id)
    if missing:
        await show_gate(update, context, missing, edit=False)
        return
    await send_redeem_with_photo(chat_id=update.effective_chat.id, user_id=user_id, context=context)


async def folders_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _track_current_user(update)
    user_id = update.effective_user.id
    missing = await get_missing_channels(context, user_id)
    if missing:
        await show_gate(update, context, missing, edit=False)
        return
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=(
            "📁 *Growth Desk Folders (2)*\n\n"
            "1️⃣ Folder 1 (Up to 100 channels)\n"
            "2️⃣ Folder 2 (Up to 100 channels)\n\n"
            "Tap a button below to join 👇"
        ),
        reply_markup=build_two_folders_keyboard(),
        parse_mode="Markdown",
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data or ""
    user_id = query.from_user.id
    wallet = get_user_wallet(user_id)
    wallet["username"] = f"@{query.from_user.username}" if query.from_user.username else "NoUsername"
    wallet["first_name"] = query.from_user.first_name or "Unknown"
    wallet["last_seen"] = datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M")
    _save_wallets()
    ref_link = f"https://t.me/GROWTHDESK4BOT?start={user_id}"

    if data == "noop":
        await query.answer()
        return
    if data == "verify_join":
        await check_and_unlock(update, context, from_verify_button=True)
        return

    await query.answer()

    if data == "sec_redeem":
        await send_redeem_with_photo(chat_id=query.message.chat_id, user_id=user_id, context=context, edit_query=query)
    elif data == "sec_referral":
        await query.edit_message_text(
            text=(
                "🔗 *Referral*\n"
                f"Per Referral: *{format_amount(PER_REFERRAL_AMOUNT)}*\n"
                f"Your Referrals: *{wallet['referrals']}*\n"
                f"Redeem Slabs: *{format_redeem_slabs()}*\n"
                f"Your Referral Link: `{ref_link}`"
            ),
            reply_markup=build_unlocked_keyboard(),
            parse_mode="Markdown",
        )
    elif data == "sec_bonus":
        if not wallet["claimed_bonus"]:
            wallet["claimed_bonus"] = True
            wallet["balance"] = round(wallet["balance"] + BONUS_AMOUNT, 2)
            _save_wallets()
        await query.edit_message_text(
            text=(
                "🎁 *Bonus*\n"
                f"Bonus Amount: *{format_amount(BONUS_AMOUNT)}*\n"
                f"💰 *Wallet Balance:* *{format_amount(wallet['balance'])}*"
            ),
            reply_markup=build_unlocked_keyboard(),
            parse_mode="Markdown",
        )
    elif data == "sec_newcomer":
        if not wallet["claimed_newcomer"]:
            wallet["claimed_newcomer"] = True
            wallet["balance"] = round(wallet["balance"] + NEW_USER_BONUS_AMOUNT, 2)
            _save_wallets()
        await query.edit_message_text(
            text=(
                "🆕 *New User Bonus*\n"
                f"Bonus Amount: *{format_amount(NEW_USER_BONUS_AMOUNT)}*\n"
                f"💰 *Wallet Balance:* *{format_amount(wallet['balance'])}*"
            ),
            reply_markup=build_unlocked_keyboard(),
            parse_mode="Markdown",
        )
    elif data == "back_main":
        missing = await get_missing_channels(context, user_id)
        await show_gate(update, context, missing, edit=True)


async def global_error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    if isinstance(context.error, Conflict):
        print("Polling conflict detected; another instance is active.", flush=True)
        return
    print(f"Unhandled bot error: {context.error}", flush=True)


def main():
    start_health_server()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("go", go_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("reaction", reaction_command))
    app.add_handler(CommandHandler("use", use_command))
    app.add_handler(CommandHandler("hub", hub_command))
    app.add_handler(CommandHandler("newcomer", newcomer_command))
    app.add_handler(CommandHandler("redeem", redeem_command))
    app.add_handler(CommandHandler("folders", folders_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_error_handler(global_error_handler)

    if app.job_queue:
        for idx, run_time in enumerate(AUTO_POST_TIMES):
            app.job_queue.run_daily(
                send_scheduled_promo,
                time=run_time,
                data=idx,
                name=f"auto_promo_{idx}",
            )

    print("Bot polling started...", flush=True)
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
