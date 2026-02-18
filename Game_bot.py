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

BOT_TOKEN = "8592264429:AAFATqJbdxTzQoPJKkMCkA0iDQqA4sEx5hs"

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

# Total scores
cursor.execute("""
CREATE TABLE IF NOT EXISTS scores_total(
    chat_id INTEGER,
    user_id INTEGER,
    points INTEGER,
    PRIMARY KEY(chat_id, user_id)
)
""")

# Daily scores
cursor.execute("""
CREATE TABLE IF NOT EXISTS scores_daily(
    chat_id INTEGER,
    user_id INTEGER,
    points INTEGER,
    PRIMARY KEY(chat_id, user_id)
)
""")

# Monthly scores
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
active_game = {}  # chat_id : {"emoji":..., "winner":None}

# ================== HELPER FUNCTIONS ==================
def update_score(chat_id, user_id):
    # Total
    cursor.execute("INSERT INTO scores_total(chat_id,user_id,points) VALUES(?,?,1) "
                   "ON CONFLICT(chat_id,user_id) DO UPDATE SET points=points+1",
                   (chat_id,user_id))
    # Daily
    cursor.execute("INSERT INTO scores_daily(chat_id,user_id,points) VALUES(?,?,1) "
                   "ON CONFLICT(chat_id,user_id) DO UPDATE SET points=points+1",
                   (chat_id,user_id))
    # Monthly
    cursor.execute("INSERT INTO scores_monthly(chat_id,user_id,points) VALUES(?,?,1) "
                   "ON CONFLICT(chat_id,user_id) DO UPDATE SET points=points+1",
                   (chat_id,user_id))
    conn.commit()

# ================== COMMAND POPUP ==================
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
    chat = update.effective_chat
    bot_id = context.bot.id
    member = await context.bot.get_chat_member(chat.id, bot_id)
    return member.status in ["administrator", "creator"]

# ================== /START ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.type == "private":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Add Me To Your Group ➕",
                url=f"https://t.me/{context.bot.username}?startgroup=true")]
        ])
        await update.message.reply_text(
            "👋 **Hello!**\n\n"
            "🎮 **Fast Reaction Emoji Game Bot**\n\n"
            "⚡ Bring speed & fun games to your group!\n\n"
            "✅ **Important:** Make this bot **ADMIN** in the group to work properly.\n\n"
            "👇 Add me to your group to start playing",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        return
    # GROUP CHAT
    await update.message.reply_text(
        "⚡ Fast Reaction Emoji Game is active!\n"
        "Make sure I am **ADMIN** to work properly.\n"
        "Type /reaction to start 🔥",
        parse_mode="Markdown"
    )

# ================== HELP ==================
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎮 *Fast Reaction Emoji Game*\n\n"
        "1️⃣ Type /reaction\n"
        "2️⃣ Wait for emoji\n"
        "3️⃣ First user to send SAME emoji wins 🏆\n\n"
        "👮 Bot must be **ADMIN** in group\n"
        "⌨️ Type / to see all commands",
        parse_mode="Markdown"
    )

# ================== GAME ==================
async def reaction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.type == "private":
        await update.message.reply_text("❌ This game works only in groups.")
        return
    if not await is_bot_admin(update, context):
        await update.message.reply_text("❌ I need to be **ADMIN** to start the game.\nPlease promote me first.")
        return

    chat_id = chat.id
    await update.message.reply_text("⏳ Get Ready...")
    await asyncio.sleep(random.randint(2,5))
    emoji = random.choice(EMOJIS)
    active_game[chat_id] = {"emoji": emoji, "winner": None}
    await update.message.reply_text(f"⚡ *SEND THIS EMOJI FAST!*\n\n{emoji}", parse_mode="Markdown")

# ================== HANDLE MESSAGES ==================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    text = update.message.text

    if chat_id not in active_game:
        return

    game = active_game[chat_id]

    # First correct emoji wins
    if text == game["emoji"]:
        if game["winner"] is None:
            game["winner"] = user.id
            active_game.pop(chat_id)
            update_score(chat_id, user.id)
            await update.message.reply_text(
                f"🏆 **WINNER!**\n\n{user.mention_html()} was the fastest ⚡",
                parse_mode="HTML"
            )
        return

    # Wrong emoji
    await update.message.reply_text("❌ Wrong emoji!")

# ================== LEADERBOARD FUNCTIONS ==================
async def show_leaderboard(update, context, table, top=10, title="Leaderboard"):
    chat_id = update.effective_chat.id
    cursor.execute(f"SELECT user_id, points FROM {table} WHERE chat_id=? ORDER BY points DESC LIMIT ?", (chat_id, top))
    data = cursor.fetchall()
    if not data:
        await update.message.reply_text("No scores yet.")
        return

    text = f"🏆 **{title}** 🏆\n\n"
    rank = 1
    for uid, pts in data:
        member = await context.bot.get_chat_member(chat_id, uid)
        name = member.user.first_name
        # Clickable username with ID
        mention = f"[{name}](tg://user?id={uid})"
        text += f"{rank}. {mention} — {pts} pts\n"
        rank += 1
    await update.message.reply_text(text, parse_mode="Markdown")

async def leaderboard(update, context):
    await show_leaderboard(update, context, "scores_total", top=10, title="Top 10 Leaderboard")

async def daily(update, context):
    await show_leaderboard(update, context, "scores_daily", top=3, title="Daily Top 3")

async def monthly(update, context):
    await show_leaderboard(update, context, "scores_monthly", top=3, title="Monthly Top 3")

# ================== SCORE ==================
async def score(update, context):
    chat_id = update.effective_chat.id
    cursor.execute("SELECT user_id, points FROM scores_total WHERE chat_id=? ORDER BY points DESC", (chat_id,))
    data = cursor.fetchall()
    if not data:
        await update.message.reply_text("No scores yet.")
        return
    text = "📊 *GROUP SCORES*\n\n"
    for uid, pts in data:
        member = await context.bot.get_chat_member(chat_id, uid)
        text += f"• {member.user.first_name}: {pts} pts\n"
    await update.message.reply_text(text, parse_mode="Markdown")

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
    app.post_init = set_commands
    app.run_polling()

if __name__ == "__main__":
    main()