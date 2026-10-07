import asyncio
import logging
import sqlite3
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# 🔑 HARDCODED CONFIGURATIONS
BOT_TOKEN = "8906991132:AAHOomBtHEe55ePedEoEFPoIFBN7Chi6Nks"
OWNER_ID = 7677244398
PREMIUM_GROUP_ID = -1003725494113

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            code_name TEXT,
            points INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

def get_or_create_codename(user_id: int, username: str) -> str:
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT code_name FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    
    if row:
        code_name = row[0]
    else:
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0] + 1
        code_name = f"{count:02d}"
        cursor.execute("INSERT INTO users (user_id, username, code_name, points) VALUES (?, ?, ?, 0)",
                       (user_id, username, code_name))
        conn.commit()
    conn.close()
    return code_name

def add_point(user_id: int):
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET points = points + 10 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

init_db()

# --- FSM STATES FOR /CA FORM ---
class CAForm(StatesGroup):
    target_username = State()
    target_id = State()
    violation = State()
    msg_link = State()
    deception = State()
    photo = State()

# --- 1. 18+ CONTENT FILTER ---
NSFW_KEYWORDS = ["18+", "porn", "sex", "hentai", "xxx", "nudity", "အပြာစာပေ", "အပြာကား"]

@dp.message(F.chat.id == PREMIUM_GROUP_ID)
async def nsfw_filter(message: Message):
    text = message.text or message.caption or ""
    if any(keyword in text.lower() for keyword in NSFW_KEYWORDS):
        await message.delete()
        user_mention = f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name
        await message.answer(f"⚠️ {user_mention} သင်သည် Telegram စည်းကမ်းကို ဒီဂရုထဲတွင် ချိုးဖောက်လို့မရပါ!")
        return

# --- 2. COMMANDS (/start, /info, /owner, /mc) ---
@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.reply("🛡️ **CyberShield VIP Bot Activated.**\nPremium Enforcement System Online.")

@dp.message(Command("info"), F.chat.id == PREMIUM_GROUP_ID)
async def cmd_info(message: Message):
    user = message.from_user
    info_text = (
        "👤 **USER INFORMATION**\n"
        "➖➖➖➖➖➖➖➖➖➖\n"
        f"🏷️ **First Name:** {user.first_name}\n"
        f"🏷️ **Last Name:** {user.last_name or 'N/A'}\n"
        f"🔗 **Username:** @{user.username or 'No Username'}\n"
        "🔒 *User ID Hidden for Security Policy*"
    )
    await message.reply(info_text, parse_mode="Markdown")

@dp.message(Command("owner"), F.chat.id == PREMIUM_GROUP_ID)
async def cmd_owner(message: Message):
    user = message.from_user
    username_str = f"@{user.username}" if user.username else user.first_name
    alert_text = f"🚨 **ATTENTION OWNER:**\n\n{username_str} ထို user သည် သင့်ကို Group ထဲတွင်ခေါ်ဆောင်နေပါသည်!"
    await bot.send_message(chat_id=OWNER_ID, text=alert_text)
    await message.reply("📩 Owner ထံ အကြောင်းကြားစာ အောင်မြင်စွာ ပို့ပြီးပါပြီ။")

@dp.message(Command("mc"), F.chat.id == PREMIUM_GROUP_ID)
async def cmd_mc(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    code_name = get_or_create_codename(user_id, username)
    await message.reply(f"🏷️ **Your Code Name:** `{code_name}`", parse_mode="Markdown")

# --- 3. OWNER ONLY /CA FORM FLOW ---
@dp.message(Command("CA"), F.from_user.id == OWNER_ID)
async def start_ca_form(message: Message, state: FSMContext):
    await message.reply("📝 **Target Username** ကို ရိုက်ထည့်ပါ (ဥပမာ- @scammer_name):")
    await state.set_state(CAForm.target_username)

@dp.message(CAForm.target_username)
async def process_target_username(message: Message, state: FSMContext):
    await state.update_data(target_username=message.text)
    await message.reply("🆔 **Target ID** ကို ရိုက်ထည့်ပါ:")
    await state.set_state(CAForm.target_id)

@dp.message(CAForm.target_id)
async def process_target_id(message: Message, state: FSMContext):
    await state.update_data(target_id=message.text)
    await message.reply("⚠️ **Violation (ကျူးလွန်မှု အကြောင်းအရင်း)** ကို ရိုက်ထည့်ပါ:")
    await state.set_state(CAForm.violation)

@dp.message(CAForm.violation)
async def process_violation(message: Message, state: FSMContext):
    await state.update_data(violation=message.text)
    await message.reply("🔗 **Message Link** ကို ရိုက်ထည့်ပါ:")
    await state.set_state(CAForm.msg_link)

@dp.message(CAForm.msg_link)
async def process_msg_link(message: Message, state: FSMContext):
    await state.update_data(msg_link=message.text)
    await message.reply("📝 **Deception (လိမ်လည်မှု အသေးစိတ်)** ကို ရိုက်ထည့်ပါ:")
    await state.set_state(CAForm.deception)

@dp.message(CAForm.deception)
async def process_deception(message: Message, state: FSMContext):
    await state.update_data(deception=message.text)
    await message.reply("📸 **Proof Screenshot (ဓာတ်ပုံ)** ပို့ပေးပါ:")
    await state.set_state(CAForm.photo)

@dp.message(CAForm.photo, F.photo)
async def process_photo_and_review(message: Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    await state.update_data(photo=photo_id)
    data = await state.get_data()

    review_text = (
        "📋 **COMMUNITY ALERT REVIEW (Owner Only)**\n"
        "➖➖➖➖➖➖➖➖➖➖\n"
        f"🎯 **Target Username:** {data['target_username']}\n"
        f"🆔 **Target ID:** `{data['target_id']}`\n"
        f"⚠️ **Violation:** {data['violation']}\n"
        f"🔗 **Message Link:** {data['msg_link']}\n"
        f"📝 **Deception:** {data['deception']}\n"
        "➖➖➖➖➖➖➖➖➖➖\n"
        "📌 အထက်ပါ ဖောင်ကို Premium Group သို့ ပို့ရန် Approve နှိပ်ပါ။"
    )

    approve_kbd = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="✅ Approve & Broadcast", callback_data="owner_approve_ca")]]
    )

    await message.answer_photo(photo=photo_id, caption=review_text, parse_mode="Markdown", reply_markup=approve_kbd)

@dp.callback_query(F.data == "owner_approve_ca", F.from_user.id == OWNER_ID)
async def broadcast_ca_to_group(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    clean_username = data['target_username'].replace("@", "")

    group_card_text = (
        "🚨 **COMMUNITY ALERT (PREMIUM TEAM)**\n"
        "➖➖➖➖➖➖➖➖➖➖\n"
        f"👤 **Target Username:** @{clean_username}\n"
        f"🆔 **Target ID:** `{data['target_id']}`\n"
        f"⚠️ **Violation:** {data['violation']}\n"
        f"🔗 **Message Link:** {data['msg_link']}\n"
        f"📝 **Deception:** {data['deception']}\n"
        "➖➖➖➖➖➖➖➖➖➖\n"
        "📌 **Action Required:** Report တိုင်ကြားရန် အောက်ပါ ခလုတ်ကို နှိပ်ပါ။"
    )

    action_kbd = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚨 Report Scammer", url=f"https://t.me/{clean_username}")],
            [InlineKeyboardButton(text="✅ Confirm Report Done", callback_data=f"confirm_rep_{clean_username}")]
        ]
    )

    await bot.send_photo(
        chat_id=PREMIUM_GROUP_ID,
        photo=data['photo'],
        caption=group_card_text,
        parse_mode="Markdown",
        reply_markup=action_kbd
    )

    await callback.message.edit_caption(caption="✅ **Community Alert ကို Premium Group သို့ အောင်မြင်စွာ ပို့ပြီးပါပြီ။**")
    await state.clear()

# --- 4. MEMBER REPORT CONFIRMATION ---
@dp.callback_query(F.data.startswith("confirm_rep_"))
async def member_confirm_report(callback: CallbackQuery):
    user = callback.from_user
    username_str = f"@{user.username}" if user.username else user.first_name

    add_point(user.id)

    success_msg = f"✅ Premium user - {username_str} ထို user သည် တိုင်ကြားစာကို အောင်မြင်စွာ တင်ပြီးပါပြီ။"
    await bot.send_message(chat_id=PREMIUM_GROUP_ID, text=success_msg)
    await callback.answer("🎉 တိုင်ကြားစာ အတည်ပြုချက် ရရှိပါပြီ (+10 Points)", show_alert=True)

# --- 5. WELCOME & OWNER ALERT ---
@dp.message(F.new_chat_members, F.chat.id == PREMIUM_GROUP_ID)
async def welcome_new_member(message: Message):
    for member in message.new_chat_members:
        welcome_text = f"👋 **Welcome {member.first_name} to Premium Team!**"
        await message.reply(welcome_text)

        owner_alert = (
            "🔔 **NEW MEMBER JOINED GROUP**\n"
            f"👤 Name: {member.first_name}\n"
            f"🔗 Username: @{member.username or 'None'}\n"
            f"🆔 User ID: `{member.id}`"
        )
        await bot.send_message(chat_id=OWNER_ID, text=owner_alert, parse_mode="Markdown")

# --- WEB SERVER FOR RENDER FREE TIER ---
async def handle(request):
    return web.Response(text="CyberShield VIP Bot is Live 24/7!")

async def main():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 10000)
    await site.start()
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
                      
