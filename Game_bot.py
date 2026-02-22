import random
import asyncio
import sqlite3
import time
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
    "🧩","🎭","🎹","🎵","🎶","🎤","🎧","🎷","🎺","🛹"
]

# ================== DATABASE ==================
conn = sqlite3.connect("reaction_bot.db", check_same_thread=False)
cursor = conn.cursor()

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
# chat_id : {"emoji": str, "winner": None/int, "end_time": float}

# ================== SCORE UPDATE ==================
def update_score(chat_id, user_id):
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

# ================== COMMAND SET ==================
async def set_commands(app: Application):
    commands = [
        BotCommand("reaction", "⚡ Start reaction game"),
        BotCommand("leaderboard", "🏆 Top 10 leaderboard"),
        BotCommand("daily", "📊 Daily top 3"),
        BotCommand("monthly", "📊 Monthly top 3"),
        BotCommand("score", "📊 Group scores"),
        BotCommand("help", "ℹ️ How to play"),
        BotCommand("start", "➕ Add bot"),
    ]
    await app.bot.set_my_commands(commands, scope=BotCommandScopeDefault())
    await app.bot.set_my_commands(commands, scope=BotCommandScopeAllGroupChats())

# ================== ADMIN CHECK ==================
async def is_bot_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
                "➕ Add Me To Group",
                url=f"https://t.me/{context.bot.username}?startgroup=true"
            )]
        ])
        await update.message.reply_text(
            "🎮 *Fast Reaction Emoji Game*\n\n"
            "➕ Add me to your group\n"
            "👮 Make me ADMIN",
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        return

    await update.message.reply_text(
        "⚡ Reaction Game Active!\nType /reaction to play",
        parse_mode="Markdown"
    )

# ================== HELP ==================
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎮 *Fast Reaction Game*\n\n"
        "1️⃣ /reaction\n"
        "2️⃣ Emoji dekho\n"
        "3️⃣ Same emoji bhejo\n\n"
        "⏱️ Time limit: 20 sec\n"
        "👮 Bot must be ADMIN",
        parse_mode="Markdown"
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
    await asyncio.sleep(random.randint(2, 5))

    emoji = random.choice(EMOJIS)
    end_time = time.time() + 20

    active_game[chat_id] = {
        "emoji": emoji,
        "winner": None,
        "end_time": end_time
    }

    await update.message.reply_text(
        f"⚡ *SEND THIS EMOJI FAST!*\n\n{emoji}\n\n⏱️ Time limit: *20 seconds*",
        parse_mode="Markdown"
    )

    await asyncio.sleep(20)
    if chat_id in active_game and active_game[chat_id]["winner"] is None:
        active_game.pop(chat_id)
        await context.bot.send_message(chat_id, "⌛ Time over! No one reacted.")

# ================== MESSAGE HANDLER ==================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in active_game:
        return

    game = active_game[chat_id]

    if time.time() > game["end_time"]:
        active_game.pop(chat_id, None)
        return

    if update.message.text == game["emoji"]:
        if game["winner"] is None:
            game["winner"] = update.effective_user.id
            active_game.pop(chat_id)
            update_score(chat_id, update.effective_user.id)
            await update.message.reply_text(
                f"🏆 **WINNER!**\n\n{update.effective_user.mention_html()} ⚡",
                parse_mode="HTML"
            )

# ================== STYLED LEADERBOARD (USERNAME) ==================
async def show_leaderboard(update, context, table, top, title):
    chat_id = update.effective_chat.id
    cursor.execute(
        f"SELECT user_id, points FROM {table} "
        "WHERE chat_id=? ORDER BY points DESC LIMIT ?",
        (chat_id, top)
    )
    rows = cursor.fetchall()

    if not rows:
        await update.message.reply_text("😶 No scores yet.")
        return

    header = (
        "╔════════════════╗\n"
        f"   🏆 *{title.upper()}* 🏆\n"
        "╚════════════════╝\n\n"
    )

    medals = ["👑", "🥈", "🥉"]
    body = ""

    for i, (uid, pts) in enumerate(rows):
        try:
            member = await context.bot.get_chat_member(chat_id, uid)
            user = member.user

            display = f"@{user.username}" if user.username else user.first_name
            icon = medals[i] if i < 3 else f"{i+1}️⃣"

            body += (
                f"{icon} *{display}*\n"
                f"   └─ ⭐ Points: `{pts}`\n\n"
            )
        except:
            continue

    footer = "⚡ _Type /reaction to play & climb ranks!_"

    await update.message.reply_text(
        header + body + footer,
        parse_mode="Markdown"
    )

async def leaderboard(update, context):
    await show_leaderboard(update, context, "scores_total", 10, "Top 10")

async def daily(update, context):
    await show_leaderboard(update, context, "scores_daily", 3, "Daily Top 3")

async def monthly(update, context):
    await show_leaderboard(update, context, "scores_monthly", 3, "Monthly Top 3")

# ================== SCORE ==================
async def score(update, context):
    chat_id = update.effective_chat.id
    cursor.execute(
        "SELECT user_id, points FROM scores_total "
        "WHERE chat_id=? ORDER BY points DESC",
        (chat_id,)
    )
    rows = cursor.fetchall()
    if not rows:
        await update.message.reply_text("No scores yet.")
        return

    text = "📊 *GROUP SCORES*\n\n"
    for uid, pts in rows:
        try:
            member = await context.bot.get_chat_member(chat_id, uid)
            user = member.user
            name = f"@{user.username}" if user.username else user.first_name
            text += f"• {name}: {pts} pts\n"
        except:
            pass

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