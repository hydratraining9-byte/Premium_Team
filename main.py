import os
import re
import logging
import psycopg2
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, 
    CallbackQueryHandler, ContextTypes, filters
)

# Logging စနစ်
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# ----------------------------------------------------
# ⚙️ ENVIRONMENT VARIABLES (Render မှ ဖတ်ယူခြင်း)
# ----------------------------------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
GROUP_ID = int(os.getenv("GROUP_ID", "0"))
DATABASE_URL = os.getenv("DATABASE_URL")

# ----------------------------------------------------
# 🐘 POSTGRESQL DATABASE SETUP
# ----------------------------------------------------
def init_db():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            username TEXT,
            codename TEXT,
            points INT DEFAULT 0
        );
    ''')
    conn.commit()
    cur.close()
    conn.close()

init_db()

def get_or_create_user(user_id: int, username: str):
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("SELECT codename, points FROM users WHERE user_id = %s;", (user_id,))
    row = cur.fetchone()
    if not row:
        codename = f"VIP-{user_id % 10000:04d}"
        cur.execute(
            "INSERT INTO users (user_id, username, codename, points) VALUES (%s, %s, %s, %s);",
            (user_id, username, codename, 0)
        )
        conn.commit()
        cur.close()
        conn.close()
        return codename, 0
    cur.close()
    conn.close()
    return row[0], row[1]

def add_points(user_id: int, points_to_add: int):
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("UPDATE users SET points = points + %s WHERE user_id = %s;", (points_to_add, user_id))
    conn.commit()
    cur.close()
    conn.close()

# ----------------------------------------------------
# 🤖 BOT COMMANDS & HANDLERS
# ----------------------------------------------------

# 1. /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    codename, points = get_or_create_user(user.id, user.username or user.first_name)
    
    msg = (
        f"🛡️ **Welcome to CyberShield VIP Bot**\n\n"
        f"👤 Your CodeName: `{codename}`\n"
        f"⭐ Your Points: `{points}`\n\n"
        f"လုံခြုံရေးနှင့် Community စောင့်ရှောက်ရေးအတွက် အသင့်ရှိပါသည်။"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

# 2. /info
async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    codename, points = get_or_create_user(user.id, user.username or user.first_name)
    
    info_text = (
        f"📊 **User Security Profile**\n"
        f"• Name: {user.full_name}\n"
        f"• User ID: `{user.id}`\n"
        f"• CodeName: `{codename}`\n"
        f"• Points: `{points}`"
    )
    await update.message.reply_text(info_text, parse_mode="Markdown")

# 3. /owner
async def owner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👑 **CyberShield Bot Owner:** Contact System Administrator directly.")
    if OWNER_ID:
        user = update.effective_user
        await context.bot.send_message(
            chat_id=OWNER_ID,
            text=f"⚠️ **Owner Alert:** User {user.full_name} (`{user.id}`) used /owner command."
        )

# 4. /mc (My Code / CodeName)
async def my_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    codename, _ = get_or_create_user(user.id, user.username or user.first_name)
    await update.message.reply_text(f"🔑 Your Security CodeName is: `{codename}`", parse_mode="Markdown")

# 5. /ca (Community Alert Form - Owner DM Only)
async def ca_form(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != OWNER_ID:
        return  # Owner မှလွဲ၍ ငြင်းပယ်သည်

    if update.effective_chat.type != "private":
        await update.message.reply_text("⚠️ ဒီ Command ကို Bot ရဲ့ DM (Private) ထဲတွင်သာ သုံးပါခင်ဗျာ။")
        return

    # Form Usage: /ca Username | ID | Violation | Link | Deception
    text = update.message.text.replace("/ca", "").strip()
    if not text or "|" not in text:
        await update.message.reply_text(
            "⚠️ **`/ca` Form ဖြည့်စွက်နည်း:**\n\n"
            "`/ca TargetUsername | TargetID | Violation | MessageLink | Deception`\n\n"
            "ဥပမာ -\n"
            "`/ca @spammer | 1234567 | Scammer | t.me/xxx/1 | Fake Investment`",
            parse_mode="Markdown"
        )
        return

    parts = [p.strip() for p in text.split("|")]
    if len(parts) < 5:
        await update.message.reply_text("⚠️ Form အချက်အလက် (၅) ချက်စလုံး ပြည့်စုံစွာ ဖြည့်ပေးပါ။")
        return

    target_user, target_id, violation, msg_link, deception = parts[0], parts[1], parts[2], parts[3], parts[4]

    alert_msg = (
        f"🚨 **COMMUNITY ALERT (CA) FORM** 🚨\n"
        f"------------------------------------\n"
        f"🎯 **Target User:** {target_user} (`{target_id}`)\n"
        f"⚠️ **Violation:** {violation}\n"
        f"🔗 **Message Link:** {msg_link}\n"
        f"🎭 **Deception:** {deception}\n"
        f"------------------------------------\n"
        f"⚡ *CyberShield VIP Admin Enforcement*"
    )

    keyboard = [[InlineKeyboardButton("🚨 Report Violation", callback_data=f"report_{target_id}_{target_user}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Group ထို့ အလိုအလျောက် ပို့ပေးခြင်း
    if GROUP_ID:
        await context.bot.send_message(chat_id=GROUP_ID, text=alert_msg, parse_mode="Markdown", reply_markup=reply_markup)
        await update.message.reply_text("✅ Community Alert Form ကို Group သို့ အောင်မြင်စွာ ပို့ပြီးပါပြီ။")

# 6. Inline Button Handler (Direct Report Clicked)
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data.startswith("report_"):
        parts = query.data.split("_")
        target_id, target_user = parts[1], parts[2]
        reporter = query.from_user

        # Reporter ကို Point ၅ မှတ် ပေးခြင်း
        add_points(reporter.id, 5)
        _, new_points = get_or_create_user(reporter.id, reporter.username or reporter.first_name)

        # Confirm & Notification စာတို
        notify_text = f"✅ {target_user} ထို user သည် တိုင်ကြား ဟု {reporter.full_name} မှ အစီရင်ခံလိုက်ပါသည်။ (Point +5 | Total: {new_points})"
        await query.message.reply_text(notify_text)

# 7. 18+ Content Auto-Delete
async def filter_nsfw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text.lower()
    nsfw_keywords = ["18+", "porn", "sex", "hentai", "အောစာ", "အောကား"]
    
    if any(keyword in text for keyword in nsfw_keywords):
        try:
            await update.message.delete()
            warning = await update.message.chat.send_message(
                f"⚠️ {update.effective_user.mention_html()}, 18+ မက်ဆေ့ဂျ်များကို စနစ်မှ အလိုအလျောက် ဖျက်ဆီးလိုက်ပါသည်။",
                parse_mode="HTML"
            )
        except Exception as e:
            logging.error(f"Error deleting NSFW message: {e}")

# 8. Welcome Message & Member Alert
async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        await update.message.reply_text(f"👋 မင်္ဂလာပါ {member.full_name}၊ CyberShield Security Group မှ ကြိုဆိုပါသည်!")
        
        # Owner DM အကြောင်းကြားခြင်း
        if OWNER_ID:
            await context.bot.send_message(
                chat_id=OWNER_ID,
                text=f"🔔 **Member Alert:** {member.full_name} (`{member.id}`) ဝင်ရောက်လာပါသည်။"
            )

# ----------------------------------------------------
# 🚀 MAIN APPLICATION
# ----------------------------------------------------
if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("info", info))
    app.add_handler(CommandHandler("owner", owner))
    app.add_handler(CommandHandler("mc", my_code))
    app.add_handler(CommandHandler("ca", ca_form))

    # Callbacks & Messages
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), filter_nsfw))

    app.run_polling()
