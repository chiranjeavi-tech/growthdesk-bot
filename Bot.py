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
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8125086974:AAE3VCoDJkeyZghr4xChed5EX2JKeex17n1M")

ADMIN_USERNAMES = {"chiranjeevitraders4", "chiranjeavitraders4"}
MAX_CHANNELS_PER_FOLDER = 100
CHANNELS_PER_PAGE = 10
MAX_REDEEM_CAP = 25
PER_REFERRAL_AMOUNT = 0.30
BONUS_AMOUNT = 0.10
NEW_USER_BONUS_AMOUNT = 0.10
REDEEM_SLABS = [
    (10, 10),
    (15, 15),
    (25, 25),
]
IST = ZoneInfo("Asia/Kolkata")
WALLET_STORE_FILE = os.environ.get("WALLET_STORE_FILE", "user_wallets.json")

# Small Redeem Code photo URL (GitHub raw link or direct image URL)
REDEEM_PHOTO_URL = "https://raw.githubusercontent.com/chiranjeavi-tech/growthdesk-bot/main/1795660640966.png"

# Main & backup channels (kept as configured)
CHANNELS = [
    (-1003941578746, "https://t.me/+L_jUVKFNZp5mOGJl", "📢 MAIN CHANNEL 💸💸"),
    (-1002735833404, "https://t.me/+6g8Hcs_EYOhlODM1", "📢 BACK-UP CHANNEL 💸💸"),
]

# 3rd & 4th single-click Telegram folder links (up to 100 channels each)
FOLDER_3_LINK = "https://t.me/addlist/-Qq__yiQlZQzODZl"
FOLDER_4_LINK = "https://t.me/addlist/UNOERSRR-Zs0Njk1"

# Daily 4 times (IST): 10:00 AM, 01:00 PM, 05:05 PM, 09:00 PM
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
        "▪️ Per Referral: 0.30 | Bonus & New User Bonus: 0.10\n"
        "▪️ Redeem Codes: 10 Refs = ₹10 | 15 Refs = ₹15 | 25 Refs = ₹25\n"
        "▪️ Instant Access & Daily Fresh Updates\n\n"
        "🚀 *Start Bot Now 👇*\n\n"
        "@GROWTHDESK4BOT\n"
        "@GROWTHDESK4BOT\n\n"
        "📈 Add Your Channel In Our Bot\n"
        "📩 *DM TO ADD : @ChiranjeeviTrader4*"
    ),
]

# 10 Folders (Up to 100 channels per folder)
FOLDERS = {
    f"folder_{i}": {
        "title": f"📁 Folder {i}",
        "channels": [],
    }
    for i in range(1, 11)
}

FOLDERS["folder_1"]["channels"].extend([
    ("📢 New Channel 1", "https://t.me/+26Fs7pXdGPoxZmI1"),
])


def is_admin_user(update: Update) -> bool:
    user = update.effective_user
    if not user or not user.username:
        return False
    return user.username.strip().lower() in ADMIN_USERNAMES


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
                }
        return loaded
    except Exception as e:
        print(f"Error loading wallets file: {e}", flush=True)
        return {}


def _save_wallets():
    try:
        serialized = {str(uid): data for uid, data in USER_WALLETS.items()}
        with open(WALLET_STORE_FILE, "w", encoding="utf-8") as f:
            json.dump(serialized, f, indent=2)
    except Exception as e:
        print(f"Error saving wallets file: {e}", flush=True)


# Persistent user wallet & referral store
USER_WALLETS = _load_wallets()


def get_user_wallet(user_id: int) -> dict:
    if user_id not in USER_WALLETS:
        USER_WALLETS[user_id] = {
            "balance": 0.0,
            "referrals": 0,
            "referred_by": None,
            "claimed_newcomer": False,
            "claimed_bonus": False,
        }
        _save_wallets()
    return USER_WALLETS[user_id]


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


def build_two_folders_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📁 Folder 1 (100)", url=FOLDER_3_LINK),
            InlineKeyboardButton("📁 Folder 2 (100)", url=FOLDER_4_LINK),
        ]
    ])


def build_main_keyboard(missing: list):
    keyboard = []

    # 1st & 2nd: Main & Back-up channels
    for url, label in missing:
        keyboard.append([InlineKeyboardButton(label, url=url)])

    # 3rd & 4th: Direct single-click folder links (up to 100 channels each)
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
    total_channels = len(channels)
    total_pages = max(1, (total_channels + CHANNELS_PER_PAGE - 1) // CHANNELS_PER_PAGE)
    page = max(0, min(page, total_pages - 1))

    start_idx = page * CHANNELS_PER_PAGE
    end_idx = start_idx + CHANNELS_PER_PAGE
    page_channels = channels[start_idx:end_idx]

    keyboard = []
    for ch_label, ch_url in page_channels:
        keyboard.append([InlineKeyboardButton(ch_label, url=ch_url)])

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
    slabs_text = format_redeem_slabs()
    caption_text = (
        f"💰 *Wallet Balance:* {format_amount(wallet['balance'])}\n"
        f"👥 *Referrals:* {wallet['referrals']}\n"
        f"🎟 *Redeem Codes:* {slabs_text}"
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
    text = (
        "🎉 *Verified! Growth Desk access unlocked.*\n\n"
        f"💰 *Wallet Balance:* {format_amount(wallet['balance'])}\n\n"
        "Tap a button below to view details 👇"
    )
    await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=build_unlocked_keyboard(),
        parse_mode="Markdown",
    )


async def send_scheduled_promo(context: ContextTypes.DEFAULT_TYPE):
    if not PROMO_POSTS:
        return

    slot_index = context.job.data if (context.job and isinstance(context.job.data, int)) else 0
    post_text = PROMO_POSTS[slot_index % len(PROMO_POSTS)]
    targets = get_all_target_chats()

    for chat_target in targets:
        try:
            await context.bot.send_photo(
                chat_id=chat_target,
                photo=REDEEM_PHOTO_URL,
                caption=post_text,
                parse_mode="Markdown",
            )
            print(f"Auto-posted promo photo slot {slot_index} to {chat_target}", flush=True)
        except Exception as e:
            print(f"Promo photo failed for {chat_target}, sending text fallback: {e}", flush=True)
            try:
                await context.bot.send_message(
                    chat_id=chat_target,
                    text=post_text,
                    parse_mode="Markdown",
                )
                print(f"Auto-posted promo text slot {slot_index} to {chat_target}", flush=True)
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


async def check_and_unlock(update: Update, context: ContextTypes.DEFAULT_TYPE, from_verify_button: bool = False):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    get_user_wallet(user_id)
    print(f"Received /start or verify from user={user_id}, chat={chat_id}", flush=True)
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
    user_id = update.effective_user.id
    apply_referral_if_valid(user_id, context.args or [])
    await check_and_unlock(update, context, from_verify_button=False)


async def go_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    missing = await get_missing_channels(context, user_id)
    if missing:
        await show_gate(update, context, missing, edit=False)
        return

    await send_redeem_with_photo(chat_id=chat_id, user_id=user_id, context=context)


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not is_admin_user(update):
        await context.bot.send_message(
            chat_id=chat_id,
            text="⛔ Admin & Owner only command.",
        )
        return

    total_users = len(USER_WALLETS)
    total_refs = sum(w.get("referrals", 0) for w in USER_WALLETS.values())
    total_balance = sum(float(w.get("balance", 0.0)) for w in USER_WALLETS.values())

    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            "📊 Bot Statistics\n\n"
            f"👤 Total Users: {total_users}\n"
            f"🔗 Total Referrals: {total_refs}\n"
            f"💰 Total Wallet Balance: {format_amount(total_balance)}"
        ),
    )


async def reaction_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=(
            "🎭 Emoji Info & Reactions\n\n"
            "• Tap reactions on broadcast posts in channels.\n"
            "• Use /go to open your wallet, bonuses, and redeem slabs."
        ),
    )


async def use_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=(
            "📝 How to Use @GROWTHDESK4BOT\n\n"
            "1. Join required channels & folders, then tap Check Joined.\n"
            "2. Run /go to open your wallet and buttons.\n"
            f"3. Earn {format_amount(PER_REFERRAL_AMOUNT)} per referral; milestones: {format_redeem_slabs()}."
        ),
    )


async def hub_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    missing = await get_missing_channels(context, user_id)
    if missing:
        await show_gate(update, context, missing, edit=False)
        return
    await send_unlocked_hub(chat_id=chat_id, user_id=user_id, context=context)


async def newcomer_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
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
        chat_id=chat_id,
        text=(
            "🆕 *New User Bonus*\n"
            f"Bonus Amount: *{format_amount(NEW_USER_BONUS_AMOUNT)}*\n"
            f"💰 *Wallet Balance:* *{format_amount(wallet['balance'])}*"
        ),
        reply_markup=build_unlocked_keyboard(),
        parse_mode="Markdown",
    )


async def redeem_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    missing = await get_missing_channels(context, user_id)
    if missing:
        await show_gate(update, context, missing, edit=False)
        return

    await send_redeem_with_photo(chat_id=chat_id, user_id=user_id, context=context)


async def folders_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    missing = await get_missing_channels(context, user_id)
    if missing:
        await show_gate(update, context, missing, edit=False)
        return

    await context.bot.send_message(
        chat_id=chat_id,
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
    ref_link = f"https://t.me/GROWTHDESK4BOT?start={user_id}"

    if data == "noop":
        await query.answer()
        return

    if data == "verify_join":
        await check_and_unlock(update, context, from_verify_button=True)
        return

    await query.answer()

    if data == "sec_redeem":
        await send_redeem_with_photo(
           
