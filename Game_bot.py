import random
import asyncio
import sqlite3
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    BotCommand,
    BotCommandScopeAllGroupChats,
    BotCommandScopeDefault
)
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters
)

BOT_TOKEN = "8097165950:AAFx-DSlj8Utwve-R3-vXB-2g5igJkQBRk0"

# ================== EMOJI LIST ==================
EMOJIS = [
    "🔥","⚡","💥","👺","👻","😈","🤡","💀","☠️","👽","🤖","🎃",
    "🐍","🐉","🦁","🐯","🐸","🐵","🦊","🐺","🐼","🐨",
    "🍎","🍌","🍉","🍓","🍒","🍩","🍪","🍫","🍿",
    "⚽","🏀","🏏","🎯","🎮","🎲","🎰",
    "🚀","✈️","🚁","🚗","🏎️","🚓","🚑",
    "❤️","💙","💚","💛","🖤","💜","🤍",
    "🧩","🎭","🎹","🎵","🎶","🎤","🎧","🎷","🎺","🛹","🎯"
]

# ================== DATABASE ==================
conn = sqlite3.connect("reaction_bot.db", check_same_thread=False)
cursor = conn.cursor()
db_lock = asyncio.Lock()

cursor.execute("""
CREATE TABLE IF NOT EXISTS scores_total(
    chat_id INTEGER,
    user_id INTEGER,
    points INTEGER,
    PRIMARY KEY(chat_id, user_id)
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS scores_daily(
    chat_id INTEGER,
    user_id INTEGER,
    points INTEGER,
    PRIMARY KEY(chat_id, user_id)
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS scores_monthly(
    chat_id INTEGER,
    user_id INTEGER,
    points INTEGER,
    PRIMARY KEY(chat_id, user_id)
)
""")
conn.commit()

# ================== GAME STATE ==================
active_game = {}

# ================== SCORE UPDATE ==================
async def update_score(chat_id, user_id):
    async with db_lock:
        cursor.execute(
            "INSERT INTO scores_total VALUES(?,?,1) "
            "ON CONFLICT(chat_id,user_id) DO UPDATE SET points=points+1",
            (chat_id, user_id)
        )
        cursor.execute(
            "INSERT INTO scores_daily VALUES(?,?,1) "
            "ON CONFLICT(chat_id,user_id) DO UPDATE SET points=points+1",
            (chat_id, user_id)
        )
        cursor.execute(
            "INSERT INTO scores_monthly VALUES(?,?,1) "
            "ON CONFLICT(chat_id,user_id) DO UPDATE SET points=points+1",
            (chat_id, user_id)
        )
        conn.commit()

# ================== COMMANDS ==================
async def set_commands(app: Application):
    commands = [
        BotCommand("reaction", "⚡ Start fast reaction emoji game"),
        BotCommand("leaderboard", "🏆 Top 10 leaderboard"),
        BotCommand("daily", "📊 Daily top 3"),
        BotCommand("monthly", "📊 Monthly top 3"),
        BotCommand("score", "📊 Show group scores"),
        BotCommand("help", "ℹ️ How to play"),
        BotCommand("start", "➕ Add bot to group"),
    ]
    await app.bot.set_my_commands(commands, scope=BotCommandScopeDefault())
    await app.bot.set_my_commands(commands, scope=BotCommandScopeAllGroupChats())

# ================== ADMIN CHECK ==================
async def is_bot_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    member = await context.bot.get_chat_member(
        update.effective_chat.id,
        context.bot.id
    )
    return member.status in ("administrator", "creator")

# ================== START ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.type == "private":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "➕ Add Me To Your Group ➕",
                url=f"https://t.me/{context.bot.username}?startgroup=true"
            )]
        ])
        await update.message.reply_text(
            "👋 Hello!\n\n🎮 Fast Reaction Emoji Game Bot\n\n⚡ Add me to your group & make me ADMIN",
            reply_markup=keyboard
        )
        return

    await update.message.reply_text(
        "⚡ Fast Reaction Emoji Game is active!\nType /reaction to start 🔥"
    )

# ================== HELP ==================
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎮 Fast Reaction Emoji Game\n\n"
        "1️⃣ /reaction\n"
        "2️⃣ Emoji dekho\n"
        "3️⃣ Same emoji bhejo\n\n"
        "👮 Bot must be ADMIN"
    )

# ================== REACTION GAME ==================
async def reaction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.type == "private":
        return

    if not await is_bot_admin(update, context):
        await update.message.reply_text("❌ Bot ko ADMIN banao")
        return

    chat_id = chat.id
    await update.message.reply_text("⏳ Get Ready...")
    await asyncio.sleep(random.randint(1, 2))

    emoji = random.choice(EMOJIS)
    active_game[chat_id] = {"emoji": emoji, "winner": None}

    await update.message.reply_text(
        f"⚡ SEND THIS EMOJI FAST!\n\n{emoji}"
    )

# ================== MESSAGE HANDLER ==================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    chat_id = update.effective_chat.id
    user = update.effective_user
    text = update.message.text.strip()

    if chat_id not in active_game:
        return

    game = active_game[chat_id]

    if text == game["emoji"] and game["winner"] is None:
        game["winner"] = user.id
        active_game.pop(chat_id)
        await update_score(chat_id, user.id)
        await update.message.reply_text(
            f"🏆 WINNER!\n\n{user.first_name} ⚡"
        )

# ================== SCORES ==================
async def score(update, context):
    chat_id = update.effective_chat.id
    cursor.execute(
        "SELECT user_id, points FROM scores_total "
        "WHERE chat_id=? ORDER BY points DESC",
        (chat_id,)
    )
    data = cursor.fetchall()
    if not data:
        await update.message.reply_text("No scores yet.")
        return

    text = "📊 GROUP SCORES\n\n"
    for uid, pts in data:
        try:
            member = await context.bot.get_chat_member(chat_id, uid)
            user = member.user
            name = f"@{user.username}" if user.username else user.first_name
            text += f"• {name}: {pts} pts\n"
        except:
            continue

    await update.message.reply_text(text)

# ================== LEADERBOARD ==================
async def show_leaderboard(update, context, table, top, title):
    chat_id = update.effective_chat.id
    cursor.execute(
        f"SELECT user_id, points FROM {table} "
        "WHERE chat_id=? ORDER BY points DESC LIMIT ?",
        (chat_id, top)
    )
    data = cursor.fetchall()
    if not data:
        await update.message.reply_text("No scores yet.")
        return

    text = f"🏆 {title}\n\n"
    for i, (uid, pts) in enumerate(data, 1):
        try:
            member = await context.bot.get_chat_member(chat_id, uid)
            user = member.user
            name = f"@{user.username}" if user.username else user.first_name
            text += f"{i}. {name} — {pts} pts\n"
        except:
            continue

    await update.message.reply_text(text)

async def leaderboard(update, context):
    await show_leaderboard(update, context, "scores_total", 10, "Top 10")

async def daily(update, context):
    await show_leaderboard(update, context, "scores_daily", 3, "Daily Top 3")

async def monthly(update, context):
    await show_leaderboard(update, context, "scores_monthly", 3, "Monthly Top 3")

# ================== MAIN ==================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("reaction", reaction))
    app.add_handler(CommandHandler("leaderboard", leaderboard))
    app.add_handler(CommandHandler("daily", daily))
    app.add_handler(CommandHandler("monthly", monthly))
    app.add_handler(CommandHandler("score", score))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.post_init = lambda app: set_commands(app)

    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()