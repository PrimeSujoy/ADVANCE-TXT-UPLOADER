# Don't Remove Credit Tg - @Tushar0125
# Ask Doubt on telegram @Tushar0125
# Topic Support + Persistent SUDO_TARGETS Added by OpenAI Assistant (Udit request)

import os
import re
import sys
import json
import time
import m3u8
import aiohttp
import asyncio
import requests
import subprocess
import urllib.parse
import cloudscraper
import datetime
import random
import ffmpeg
import logging 
import yt_dlp
from subprocess import getstatusoutput
from aiohttp import web
from core import *  # expects: download(), download_video(), etc.
from urllib.parse import urlparse, parse_qs
from bs4 import BeautifulSoup
from yt_dlp import YoutubeDL
import yt_dlp as youtube_dl
import core as helper
from utils import progress_bar
from vars import API_ID, API_HASH, BOT_TOKEN
from aiohttp import ClientSession
from pyromod import listen
from pytube import YouTube

from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait
from pyrogram.errors.exceptions.bad_request_400 import StickerEmojiInvalid
from pyrogram.types.messages_and_media import message
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# ------------------------------------------------------------------
# GLOBAL / CONFIG
# ------------------------------------------------------------------
cookies_file_path = os.getenv("COOKIES_FILE_PATH", "youtube_cookies.txt")

OWNER_ID = 1368753935  # change if needed
SUDO_USERS = [7062964338, 6305120550]  # human sudo IDs (users)
AUTH_CHANNEL = -1002752608747          # allowed channel

# ---- NEW: Persistent chat->topic map ----
# Maps *chat_id string* -> topic_id int or None
SUDO_FILE = "sudo.json"
if os.path.exists(SUDO_FILE):
    try:
        with open(SUDO_FILE, "r") as _f:
            SUDO_TARGETS = json.load(_f)
    except Exception:
        SUDO_TARGETS = {}
else:
    SUDO_TARGETS = {}

def save_sudo():
    try:
        with open(SUDO_FILE, "w") as _f:
            json.dump(SUDO_TARGETS, _f)
    except Exception as e:
        print(f"Failed to save sudo.json: {e}")

def get_topic_for_chat(chat_id: int) -> int | None:
    """Return topic_id (int) or None for given chat."""
    return SUDO_TARGETS.get(str(chat_id))

def is_authorized(user_or_chat_id: int) -> bool:
    # Authorize if:
    # - Owner
    # - In SUDO_USERS list (human)
    # - Auth channel
    # - Chat is in SUDO_TARGETS (group/channel added)
    return (
        user_or_chat_id == OWNER_ID
        or user_or_chat_id in SUDO_USERS
        or user_or_chat_id == AUTH_CHANNEL
        or str(user_or_chat_id) in SUDO_TARGETS
    )

# ------------------------------------------------------------------
# BOT INIT
# ------------------------------------------------------------------
bot = Client(
    "bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# ------------------------------------------------------------------
# UTIL: random emoji feedback
# ------------------------------------------------------------------
async def show_random_emojis(message: Message):
    emojis = ['🎊', '🔮', '😎', '⚡️', '🚀', '✨', '💥', '🎉', '🥂', '🍾', '🦠', '🤖', '❤️‍🔥', '🕊️', '💃', '🥳','🐅','🦁']
    emoji_message = await message.reply_text(' '.join(random.choices(emojis, k=1)))
    return emoji_message

# ------------------------------------------------------------------
# TOPIC-AWARE SEND WRAPPERS
# ------------------------------------------------------------------
async def send_doc_topic(chat_id: int, document: str, caption: str = None, thumb: str = None):
    topic_id = get_topic_for_chat(chat_id)
    kwargs = {}
    if topic_id:
        kwargs["message_thread_id"] = topic_id
    await bot.send_document(chat_id=chat_id, document=document, caption=caption, **kwargs)

async def send_photo_topic(chat_id: int, photo: str, caption: str = None):
    topic_id = get_topic_for_chat(chat_id)
    kwargs = {}
    if topic_id:
        kwargs["message_thread_id"] = topic_id
    await bot.send_photo(chat_id=chat_id, photo=photo, caption=caption, **kwargs)

async def send_video_topic(chat_id: int, video: str, caption: str = None, thumb: str = None):
    topic_id = get_topic_for_chat(chat_id)
    kwargs = {}
    if topic_id:
        kwargs["message_thread_id"] = topic_id
    if thumb:
        kwargs["thumb"] = thumb
    await bot.send_video(chat_id=chat_id, video=video, caption=caption, **kwargs)

async def send_text_topic(chat_id: int, text: str, **addl):
    topic_id = get_topic_for_chat(chat_id)
    kwargs = addl.copy()
    if topic_id:
        kwargs["message_thread_id"] = topic_id
    await bot.send_message(chat_id, text, **kwargs)

# ------------------------------------------------------------------
# SUDO COMMAND (extended)
# ------------------------------------------------------------------
@bot.on_message(filters.command("sudo"))
async def sudo_command(bot: Client, message: Message):
    # Only OWNER can manage SUDO_TARGETS & SUDO_USERS
    if message.from_user and message.from_user.id != OWNER_ID:
        await message.reply_text("**🚫 You are not authorized to use this command.**")
        return

    try:
        args = message.text.strip().split()
        if len(args) < 2:
            await message.reply_text(
                "**Usage:**\n"
                "`/sudo add <chat_id> <topic_id or 0>`\n"
                "`/sudo remove <chat_id>`\n"
                "`/sudo useradd <user_id>`\n"
                "`/sudo userremove <user_id>`\n"
                "`/sudo list`"
            )
            return

        action = args[1].lower()

        # list
        if action == "list":
            text = "**SUDO TARGETS (chat -> topic)**\n"
            if not SUDO_TARGETS:
                text += "_none_\n"
            else:
                for k, v in SUDO_TARGETS.items():
                    text += f"- `{k}` → `{v if v else 'General'}`\n"
            text += "\n**SUDO USERS**\n"
            for u in SUDO_USERS:
                text += f"- `{u}`\n"
            await message.reply_text(text)
            return

        # add/remove chats
        if action in ("add", "remove"):
            if len(args) < 3:
                await message.reply_text("Usage: `/sudo add <chat_id> <topic_id or 0>` or `/sudo remove <chat_id>`")
                return
            chat_id = str(int(args[2]))  # normalize
            if action == "add":
                topic_id = int(args[3]) if len(args) > 3 else 0
                SUDO_TARGETS[chat_id] = topic_id if topic_id != 0 else None
                save_sudo()
                await message.reply_text(f"**✅ Chat {chat_id} added with topic `{topic_id if topic_id else 'General'}`.**")
            else:
                if chat_id in SUDO_TARGETS:
                    del SUDO_TARGETS[chat_id]
                    save_sudo()
                    await message.reply_text(f"**✅ Chat {chat_id} removed.**")
                else:
                    await message.reply_text(f"**⚠️ Chat {chat_id} not found.**")
            return

        # useradd / userremove (manage SUDO_USERS humans)
        if action in ("useradd", "userremove"):
            if len(args) < 3:
                await message.reply_text("Usage: `/sudo useradd <user_id>` or `/sudo userremove <user_id>`")
                return
            target_user_id = int(args[2])
            if action == "useradd":
                if target_user_id not in SUDO_USERS:
                    SUDO_USERS.append(target_user_id)
                    await message.reply_text(f"**✅ User {target_user_id} added to sudo list.**")
                else:
                    await message.reply_text(f"**⚠️ User {target_user_id} already in sudo list.**")
            else:
                if target_user_id == OWNER_ID:
                    await message.reply_text("**🚫 Owner cannot be removed.**")
                elif target_user_id in SUDO_USERS:
                    SUDO_USERS.remove(target_user_id)
                    await message.reply_text(f"**✅ User {target_user_id} removed.**")
                else:
                    await message.reply_text(f"**⚠️ User {target_user_id} not found.**")
            return

        await message.reply_text("**Invalid action. Use `/sudo list` for help.**")

    except Exception as e:
        await message.reply_text(f"**Error:** `{e}`")

# ------------------------------------------------------------------
# START / RESTART / STOP
# ------------------------------------------------------------------
keyboard = InlineKeyboardMarkup(
    [
        [InlineKeyboardButton("🇮🇳ʙᴏᴛ ᴍᴀᴅᴇ ʙʏ🇮🇳", url="https://t.me/Maisamyahu")],
        [InlineKeyboardButton("🔔ᴜᴘᴅᴀᴛᴇ ᴄʜᴀɴɴᴇʟ🔔", url="https://t.me/Medicoarmy")],
        [InlineKeyboardButton("🦋ғᴏʟʟᴏᴡ ᴜs🦋", url="https://t.me/Medicoarmy")],
    ]
)

image_urls = [
    "https://graph.org/file/996d4fc24564509244988-a7d93d020c96973ba8.jpg",
    "https://graph.org/file/96d25730136a3ea7e48de-b0a87a529feb485c8f.jpg",
    "https://graph.org/file/6593f76ddd8c735ae3ce2-ede9fa2df40079b8a0.jpg",
]
random_image_url = random.choice(image_urls) 
caption = (
    "**ʜᴇʟʟᴏ👋**\n\n"
    "➠ **ɪ ᴀᴍ ᴛxᴛ ᴛᴏ ᴠɪᴅᴇᴏ ᴜᴘʟᴏᴀᴅᴇʀ ʙᴏᴛ.**\n"
    "➠ **ғᴏʀ ᴜsᴇ ᴍᴇ sᴇɴᴅ /txt.\n"
    "➠ **ғᴏʀ ɢᴜɪᴅᴇ sᴇɴᴅ /help."
)

@bot.on_message(filters.command(["start"]))
async def start_command(bot: Client, message: Message):
    await bot.send_photo(chat_id=message.chat.id, photo=random_image_url, caption=caption, reply_markup=keyboard)

@bot.on_message(filters.command("stop"))
async def stop_handler(_, m: Message):
    await m.reply_text("**𝗦𝘁𝗼𝗽𝗽𝗲𝗱**🚦", True)
    os.execl(sys.executable, sys.executable, *sys.argv)

@bot.on_message(filters.command("restart"))
async def restart_handler(_, m: Message):
    if not is_authorized(m.from_user.id if m.from_user else 0):
        await m.reply_text("**🚫 You are not authorized to use this command.**")
        return
    await m.reply_text("🔮Restarted🔮", True)
    os.execl(sys.executable, sys.executable, *sys.argv)

# ------------------------------------------------------------------
# COOKIES UPLOAD
# ------------------------------------------------------------------
COOKIES_FILE_PATH = "youtube_cookies.txt"

@bot.on_message(filters.command("cookies") & filters.private)
async def cookies_handler(client: Client, m: Message):
    if not is_authorized(m.from_user.id):
        await m.reply_text("🚫 You are not authorized to use this command.")
        return

    await m.reply_text("𝗣𝗹𝗲𝗮𝘀𝗲 𝗨𝗽𝗹𝗼𝗮𝗱 𝗧𝗵𝗲 𝗖𝗼𝗼𝗸𝗶𝗲𝘀 𝗙𝗶𝗹𝗲 (.𝘁𝘅𝘁 𝗳𝗼𝗿𝗺𝗮𝘁).", quote=True)
    try:
        input_message: Message = await client.listen(m.chat.id)
        if not input_message.document or not input_message.document.file_name.endswith(".txt"):
            await m.reply_text("Invalid file type. Please upload a .txt file.")
            return
        downloaded_path = await input_message.download()
        with open(downloaded_path, "r") as uploaded_file:
            cookies_content = uploaded_file.read()
        with open(COOKIES_FILE_PATH, "w") as target_file:
            target_file.write(cookies_content)
        await input_message.reply_text(
            "✅ 𝗖𝗼𝗼𝗸𝗶𝗲𝘀 𝗨𝗽𝗱𝗮𝘁𝗲𝗱 𝗦𝘂𝗰𝗰𝗲𝘀𝘀𝗳𝘂𝗹𝗹𝘆.\n\n📂 𝗦𝗮𝘃𝗲𝗱 𝗜𝗻 youtube_cookies.txt."
        )
    except Exception as e:
        await m.reply_text(f"⚠️ An error occurred: {str(e)}")

# ------------------------------------------------------------------
# e2t COMMAND (unchanged functional)
# ------------------------------------------------------------------
UPLOAD_FOLDER = '/path/to/upload/folder'
EDITED_FILE_PATH = '/path/to/save/edited_output.txt'

@bot.on_message(filters.command('e2t'))
async def edit_txt(client, message: Message):
    await message.reply_text(
        "🎉 **Welcome to the .txt File Editor!**\n\n"
        "Please send your `.txt` file containing subjects, links, and topics."
    )
    input_message: Message = await bot.listen(message.chat.id)
    if not input_message.document:
        await message.reply_text("🚨 **Error**: Please upload a valid `.txt` file.")
        return

    file_name = input_message.document.file_name.lower()
    uploaded_file_path = os.path.join(UPLOAD_FOLDER, file_name)
    uploaded_file = await input_message.download(uploaded_file_path)

    await message.reply_text("🔄 **Send your .txt file name, or type 'd' for the default file name.**")
    user_response: Message = await bot.listen(message.chat.id)
    if user_response.text:
        user_response_text = user_response.text.strip().lower()
        if user_response_text == 'd':
            final_file_name = file_name
        else:
            final_file_name = user_response_text + '.txt'
    else:
        final_file_name = file_name

    try:
        with open(uploaded_file, 'r', encoding='utf-8') as f:
            content = f.readlines()
    except Exception as e:
        await message.reply_text(f"🚨 **Error**: Unable to read the file.\n\nDetails: {e}")
        return

    subjects = {}
    current_subject = None
    for line in content:
        line = line.strip()
        if line and ":" in line:
            title, url = line.split(":", 1)
            title, url = title.strip(), url.strip()
            if title in subjects:
                subjects[title]["links"].append(url)
            else:
                subjects[title] = {"links": [url], "topics": []}
            current_subject = title
        elif line.startswith("-") and current_subject:
            subjects[current_subject]["topics"].append(line.strip("- ").strip())

    sorted_subjects = sorted(subjects.items())
    for _, data in sorted_subjects:
        data["topics"].sort()

    try:
        final_file_path = os.path.join(UPLOAD_FOLDER, final_file_name)
        with open(final_file_path, 'w', encoding='utf-8') as f:
            for title, data in sorted_subjects:
                for link in data["links"]:
                    f.write(f"{title}:{link}\n")
                for topic in data["topics"]:
                    f.write(f"- {topic}\n")
    except Exception as e:
        await message.reply_text(f"🚨 **Error**: Unable to write the edited file.\n\nDetails: {e}")
        return

    try:
        await message.reply_document(
            document=final_file_path,
            caption="📥**𝗘𝗱𝗶𝘁𝗲𝗱 𝗕𝘆 ➤ 𝗔𝗗𝗜𝗧𝗬𝗔⚡️**"
        )
    except Exception as e:
        await message.reply_text(f"🚨 **Error**: Unable to send the file.\n\nDetails: {e}")
    finally:
        if os.path.exists(uploaded_file_path):
            os.remove(uploaded_file_path)

# ------------------------------------------------------------------
# yt2txt (owner only) - unchanged core
# ------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def sanitize_filename(name):
    return re.sub(r'[^\w\s-]', '', name).strip().replace(' ', '_')

def get_videos_with_ytdlp(url):
    ydl_opts = {'quiet': True, 'extract_flat': True, 'skip_download': True}
    try:
        with YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(url, download=False)
            if 'entries' in result:
                title = result.get('title', 'Unknown Title')
                videos = {}
                for entry in result['entries']:
                    video_url = entry.get('url', None)
                    video_title = entry.get('title', None)
                    if video_url:
                        videos[video_title if video_title else "Unknown Title"] = video_url
                return title, videos
            return None, None
    except Exception as e:
        logging.error(f"Error retrieving videos: {e}")
        return None, None

def save_to_file(videos, name):
    filename = f"{sanitize_filename(name)}.txt"
    with open(filename, 'w', encoding='utf-8') as file:
        for title, url in videos.items():
            if title == "Unknown Title":
                file.write(f"{url}\n")
            else:
                file.write(f"{title}: {url}\n")
    return filename

@bot.on_message(filters.command('yt2txt'))
async def ytplaylist_to_txt(client: Client, message: Message):
    user_id = message.chat.id
    if user_id != OWNER_ID:
        await message.reply_text("**🚫 You are not authorized to use this command.\n\n🫠 This Command is only for owner.**")
        return

    await message.delete()
    editable = await message.reply_text("📥 **Please enter the YouTube Playlist Url :**")
    input_msg = await client.listen(editable.chat.id)
    youtube_url = input_msg.text
    await input_msg.delete()
    await editable.delete()

    title, videos = get_videos_with_ytdlp(youtube_url)
    if videos:
        file_name = save_to_file(videos, title)
        await message.reply_document(
            document=file_name, 
            caption=f"`{title}`\n\n📥 𝗘𝘅𝘁𝗿𝗮𝗰𝘁𝗲𝗱 𝗕𝘆 ➤ 𝗔𝗗𝗜𝗧𝗬𝗔⚡️"
        )
        os.remove(file_name)
    else:
        await message.reply_text("⚠️ **Unable to retrieve videos. Please check the URL.**")

# ------------------------------------------------------------------
# userlist
# ------------------------------------------------------------------
@bot.on_message(filters.command("userlist") & filters.user(SUDO_USERS))
async def list_users(client: Client, msg: Message):
    if SUDO_USERS:
        users_list = "\n".join([f"User ID : `{user_id}`" for user_id in SUDO_USERS])
        await msg.reply_text(f"SUDO_USERS :\n{users_list}")
    else:
        await msg.reply_text("No sudo users.")

# ------------------------------------------------------------------
# help
# ------------------------------------------------------------------
@bot.on_message(filters.command("help"))
async def help_command(client: Client, msg: Message):
    help_text = (
        "`/start` - Start the bot⚡\n\n"
        "`/txt` - Download and upload files (sudo)🎬\n\n"
        "`/restart` - Restart the bot🔮\n\n" 
        "`/stop` - Stop ongoing process🛑\n\n"
        "`/cookies` - Upload cookies file🍪\n\n"
        "`/e2t` - Edit txt file📝\n\n"
        "`/yt2txt` - Create txt of yt playlist (owner)🗃️\n\n"
        "`/sudo ...` - Manage sudo users/groups/topics (owner)🎊\n\n"
        "`/userlist` - List of sudo user or group or channel📜\n\n"
    )
    await msg.reply_text(help_text)

# ------------------------------------------------------------------
# MAIN TXT UPLOAD / PROCESS (Topic-enabled)
# ------------------------------------------------------------------
@bot.on_message(filters.command(["txt"]))
async def upload(bot: Client, m: Message):
    # Authorization: allow if chat OR sender is allowed
    if not (is_authorized(m.chat.id) or (m.from_user and is_authorized(m.from_user.id))):
        await m.reply_text("**🚫You are not authorized to use this bot.**")
        return

    editable = await m.reply_text("⚡𝗦𝗘𝗡𝗗 𝗧𝗫𝗧 𝗙𝗜𝗟𝗘⚡")
    input: Message = await bot.listen(editable.chat.id)
    x = await input.download()
    await input.delete(True)
    file_name_raw = os.path.splitext(os.path.basename(x))[0]

    pdf_count = img_count = zip_count = video_count = 0

    try:    
        with open(x, "r") as f:
            content = f.read()
        content = content.split("\n")
        links = []
        for i in content:
            if "://" in i:
                url = i.split("://", 1)[1]
                links.append(i.split("://", 1))
                if ".pdf" in url:
                    pdf_count += 1
                elif url.endswith((".png", ".jpeg", ".jpg")):
                    img_count += 1
                elif ".zip" in url:
                    zip_count += 1
                else:
                    video_count += 1
        os.remove(x)
    except Exception:
        await m.reply_text("😶𝗜𝗻𝘃𝗮𝗹𝗶𝗱 𝗙𝗶𝗹𝗲 𝗜𝗻𝗽𝘂𝘁😶")
        os.remove(x)
        return

    await editable.edit(
        f"`𝗧𝗼𝘁𝗮𝗹 🔗 𝗟𝗶𝗻𝗸𝘀 𝗙𝗼𝘂𝗻𝗱 𝗔𝗿𝗲 {len(links)}\n\n"
        f"🔹Img : {img_count}  🔹Pdf : {pdf_count}\n"
        f"🔹Zip : {zip_count}  🔹Video : {video_count}\n\n"
        f"𝗦𝗲𝗻𝗱 𝗙𝗿𝗼𝗺 𝗪𝗵𝗲𝗿𝗲 𝗬𝗼𝘂 𝗪𝗮𝗻𝘁 𝗧𝗼 𝗗𝗼𝘄𝗻𝗹𝗼𝗮𝗱.`"
    )
    input0: Message = await bot.listen(editable.chat.id)
    raw_text = input0.text
    await input0.delete(True)
    try:
        arg = int(raw_text)
    except Exception:
        arg = 1

    await editable.edit("📚 𝗘𝗻𝘁𝗲𝗿 𝗬𝗼𝘂𝗿 𝗕𝗮𝘁𝗰𝗵 𝗡𝗮𝗺𝗲 📚\n\n🦠 𝗦𝗲𝗻𝗱 `1` 𝗙𝗼𝗿 𝗨𝘀𝗲 𝗗𝗲𝗳𝗮𝘂𝗹𝘁 🦠")
    input1: Message = await bot.listen(editable.chat.id)
    raw_text0 = input1.text
    await input1.delete(True)
    b_name = file_name_raw if raw_text0 == '1' else raw_text0

    await editable.edit("**📸 𝗘𝗻𝘁𝗲𝗿 𝗥𝗲𝘀𝗼𝗹𝘂𝘁𝗶𝗼𝗻 📸**\n➤ `144`\n➤ `240`\n➤ `360`\n➤ `480`\n➤ `720`\n➤ `1080`")
    input2: Message = await bot.listen(editable.chat.id)
    raw_text2 = input2.text
    await input2.delete(True)
    if raw_text2 == "144":
        res = "256x144"
    elif raw_text2 == "240":
        res = "426x240"
    elif raw_text2 == "360":
        res = "640x360"
    elif raw_text2 == "480":
        res = "854x480"
    elif raw_text2 == "720":
        res = "1280x720"
    elif raw_text2 == "1080":
        res = "1920x1080" 
    else: 
        res = "UN"

    await editable.edit("📛 𝗘𝗻𝘁𝗲𝗿 𝗬𝗼𝘂𝗿 𝗡𝗮𝗺𝗲 📛\n\n🐥 𝗦𝗲𝗻𝗱 `1` 𝗙𝗼𝗿 𝗨𝘀𝗲 𝗗𝗲𝗳𝗮𝘂𝗹𝘁 🐥")
    input3: Message = await bot.listen(editable.chat.id)
    raw_text3 = input3.text
    await input3.delete(True)
    credit = "️[Aditya⚡️️](https://t.me/Maisamyahu)"
    if raw_text3 == '1':
        CR = credit
    else:
        # allow "Text,https://link"
        try:
            text, link = raw_text3.split(',', 1)
            CR = f'[{text.strip()}]({link.strip()})'
        except ValueError:
            CR = raw_text3

    await editable.edit("**𝗘𝗻𝘁𝗲𝗿 𝗣𝘄 𝗧𝗼𝗸𝗲𝗻 𝗙𝗼𝗿 𝗣𝘄 𝗨𝗽𝗹𝗼𝗮𝗱𝗶𝗻𝗴 𝗼𝗿 𝗦𝗲𝗻𝗱 `3` 𝗙𝗼𝗿 𝗢𝘁𝗵𝗲𝗿𝘀**")
    input4: Message = await bot.listen(editable.chat.id)
    raw_text4 = input4.text
    await input4.delete(True)
    MR = raw_text4  # keep for later use

    await editable.edit("𝗡𝗼𝘄 𝗦𝗲𝗻𝗱 𝗧𝗵𝗲 𝗧𝗵𝘂𝗺𝗯 𝗨𝗿𝗹 𝗘𝗴 » https://graph.org/file/13a89d77002442255efad-989ac290c1b3f13b44.jpg\n\n𝗢𝗿 𝗜𝗳 𝗗𝗼𝗻'𝘁 𝗪𝗮𝗻𝘁 𝗧𝗵𝘂𝗺𝗯𝗻𝗮𝗶𝗹 𝗦𝗲𝗻𝗱 = 𝗻𝗼")
    input6 = await bot.listen(editable.chat.id)
    raw_text6 = input6.text
    await input6.delete(True)
    await editable.delete()

    thumb = raw_text6
    if thumb and (thumb.startswith("http://") or thumb.startswith("https://")):
        getstatusoutput(f"wget '{thumb}' -O 'thumb.jpg'")
        thumb = "thumb.jpg"
    elif thumb.lower() == "no":
        thumb = None

    failed_count = 0
    if len(links) == 1:
        count = 1
    else:
        count = int(raw_text) if raw_text.isdigit() else 1 

    cpimg = "https://graph.org/file/5ed50675df0faf833efef-e102210eb72c1d5a17.jpg"  

    for i in range(count - 1, len(links)):
        V = links[i][1].replace("file/d/","uc?export=download&id=").replace("www.youtube-nocookie.com/embed", "youtu.be").replace("?modestbranding=1", "").replace("/view?usp=sharing","") # .replace("mpd","m3u8")
        url = "https://" + V

        # -------------------- URL transforms (unchanged) --------------------
        if "visionias" in url:
            async with ClientSession() as session:
                async with session.get(url, headers={'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9', 'Accept-Language': 'en-US,en;q=0.9', 'Cache-Control': 'no-cache', 'Connection': 'keep-alive', 'Pragma': 'no-cache', 'Referer': 'http://www.visionias.in/', 'Sec-Fetch-Dest': 'iframe', 'Sec-Fetch-Mode': 'navigate', 'Sec-Fetch-Site': 'cross-site', 'Upgrade-Insecure-Requests': '1', 'User-Agent': 'Mozilla/5.0 (Linux; Android 12; RMX2121) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Mobile Safari/537.36', 'sec-ch-ua': '"Chromium";v="107", "Not=A?Brand";v="24"', 'sec-ch-ua-mobile': '?1', 'sec-ch-ua-platform': '"Android"',}) as resp:
                    text = await resp.text()
                    url = re.search(r"(https://.*?playlist.m3u8.*?)\"", text).group(1)
                        
        elif 'media-cdn.classplusapp.com/drm/' in url:
            url = f"https://dragoapi.vercel.app/video/{url}"

        elif 'videos.classplusapp' in url:                                                                                                                                                                                                                                                                                                                                                  
            url = requests.get(
                'https://api.classplusapp.com/cams/uploader/video/jw-signed-url',
                headers={'x-access-token': 'eyJjb3Vyc2VJZCI6IjQ1NjY4NyIsInR1dG9ySWQiOm51bGwsIm9yZ0lkIjo0ODA2MTksImNhdGVnb3J5SWQiOm51bGx9'},
                params={'url': f'{url}'}
            ).json()['url']
                                                                                                                                                                                                                                                                                                                                                  
        elif "tencdn.classplusapp" in url or "media-cdn-alisg.classplusapp.com" in url or "videos.classplusapp" in url or "media-cdn.classplusapp" in url:
            headers = {'Host': 'api.classplusapp.com', 'x-access-token': 'eyJjb3Vyc2VJZCI6IjQ1NjY4NyIsInR1dG9ySWQiOm51bGwsIm9yZ0lkIjo0ODA2MTksImNhdGVnb3J5SWQiOm51bGx9', 'user-agent': 'Mobile-Android', 'app-version': '1.4.37.1', 'api-version': '18', 'device-id': '5d0d17ac8b3c9f51', 'device-details': '2848b866799971ca_2848b8667a33216c_SDK-30', 'accept-encoding': 'gzip'}
            params = (('url', f'{url}'),)
            response = requests.get('https://api.classplusapp.com/cams/uploader/video/jw-signed-url', headers=headers, params=params)
            url = response.json()['url']

        elif "https://appx-transcoded-videos.livelearn.in/videos/rozgar-data/" in url:
            url = url.replace("https://appx-transcoded-videos.livelearn.in/videos/rozgar-data/", "")
            name1 = links[i][0].replace("\t", "").replace(":", "").replace("/", "").replace("+", "").replace("#", "").replace("|", "").replace("@", "@").replace("*", "").replace(".", "").replace("https", "").replace("http", "").strip()
            name = f'{str(count).zfill(3)}) {name1[:60]}'
            cmd = f'yt-dlp -o "{name}.mp4" "{url}"'
                
        elif "https://appx-transcoded-videos-mcdn.akamai.net.in/videos/bhainskipathshala-data/" in url:
            url = url.replace("https://appx-transcoded-videos-mcdn.akamai.net.in/videos/bhainskipathshala-data/", "")
            name1 = links[i][0].replace("\t", "").replace(":", "").replace("/", "").replace("+", "").replace("#", "").replace("|", "").replace("@", "@").replace("*", "").replace(".", "").replace("https", "").replace("http", "").strip()
            name = f'{str(count).zfill(3)}) {name1[:60]}'
            cmd = f'yt-dlp -o "{name}.mp4" "{url}"'

        elif "apps-s3-jw-prod.utkarshapp.com" in url:
            if 'enc_plain_mp4' in url:
                url = url.replace(url.split("/")[-1], res+'.mp4')
            elif 'Key-Pair-Id' in url:
                url = None
            elif '.m3u8' in url:
                q = ((m3u8.loads(requests.get(url).text)).data['playlists'][1]['uri']).split("/")[0]
                x = url.split("/")[5]
                x = url.replace(x, "")
                url = ((m3u8.loads(requests.get(url).text)).data['playlists'][1]['uri']).replace(q+"/", x)

        elif "/master.mpd" in url or "d1d34p8vz63oiq" in url or "sec1.pw.live" in url:
            # pw token usage
            url = f"https://anonymouspwplayer-b99f57957198.herokuapp.com/pw?url={url}?token={MR}"

        if 'khansirvod4.pc.cdn.bitgravity.com' in url:               
            parts = url.split('/')               
            part3 = parts[3] 
            part4 = parts[4]
            part5 = parts[5]
            url = f"https://kgs-v4.akamaized.net/kgs-cv/{part3}/{part4}/{part5}"

        # -------------------- quality format selection --------------------
        if "youtu" in url:
            ytf = f"b[height<={raw_text2}][ext=mp4]/bv[height<={raw_text2}][ext=mp4]+ba[ext=m4a]/b[ext=mp4]"
        else:
            ytf = f"b[height<={raw_text2}]/bv[height<={raw_text2}]+ba/b/bv+ba"

        if "edge.api.brightcove.com" in url:
            bcov = 'bcov_auth=...'  # truncated for brevity: keep your original big token
            url = url.split("bcov_auth")[0]+bcov
            
        # prepare yt-dlp commands for some source types
        if "jw-prod" in url:
            cmd = f'yt-dlp -o "{name}.mp4" "{url}"'
        elif "webvideos.classplusapp." in url:
            cmd = f'yt-dlp --add-header "referer:https://web.classplusapp.com/" --add-header "x-cdn-tag:empty" -f "{ytf}" "{url}" -o "{name}.mp4"'
        elif "youtube.com" in url or "youtu.be" in url:
            cmd = f'yt-dlp --cookies youtube_cookies.txt -f "{ytf}" "{url}" -o "{name}.mp4"'
        else:
            cmd = f'yt-dlp -f "{ytf}" "{url}" -o "{name}.mp4"'

        # -------------------- names & captions --------------------
        name1 = links[i][0].replace("\t", "").replace(":", "").replace("/", "").replace("+", "").replace("#", "").replace("|", "").replace("@", "").replace("*", "").replace(".", "").replace("https", "").replace("http", "").strip()
        name = f'{str(count).zfill(3)}) {name1[:60]}'

        cc  = f'**🎬 Vɪᴅ Iᴅ : {str(count).zfill(3)}.\n\nTitle : {name1}.({res}).mkv\n\n📚 Bᴀᴛᴄʜ Nᴀᴍᴇ : {b_name}\n\n📇 Exᴛʀᴀᴄᴛᴇᴅ Bʏ : {CR}**'
        cyt = f'**🎬 Vɪᴅ Iᴅ : {str(count).zfill(3)}.\n\nTitle : {name1}.({res}).mp4\n\n\n🔗𝗩𝗶𝗱𝗲𝗼 𝗨𝗿𝗹 ➤ <a href="{url}">__Click Here to Watch Video__</a>\n\n📚 Bᴀᴛᴄʜ Nᴀᴍᴇ : {b_name}\n\n📇 Exᴛʀᴀ𝗰𝘁𝗲𝗱 Bʏ : {CR}**'
        cpvod = f'**🎬 Vɪᴅ Iᴅ : {str(count).zfill(3)}.\n\n\nTitle : {name1}.({res}).mkv\n\n\n🔗𝗩𝗶𝗱𝗲𝗼 𝗨𝗿𝗹 ➤ <a href="{url}">__Click Here to Watch Video__</a>\n\n📚 Bᴀᴛᴄʜ Nᴀᴍᴇ : {b_name}\n\n📇 Exᴛʀᴀ𝗰𝘁𝗲𝗱 Bʏ : {CR}**'
        cimg = f'**📕 Pᴅꜰ Iᴅ : {str(count).zfill(3)}.\n\nTitle : {name1}.jpg\n\n📚 Bᴀᴛᴄʜ Nᴀᴍᴇ : {b_name}\n\n📇 Exᴛʀᴀ𝗰𝘁𝗲𝗱 Bʏ : {CR}**'
        cczip = f'**📕 Pᴅꜰ Iᴅ : {str(count).zfill(3)}.\n\nTitle : {name1}.zip\n\n📚 Bᴀᴛᴄʜ Nᴀᴍᴇ : {b_name}\n\n📇 Exᴛʀᴀ𝗰𝘁𝗲𝗱 Bʏ : {CR}**'
        cc1 = f'**📕 Pᴅꜰ Iᴅ : {str(count).zfill(3)}.\n\nTitle : {name1}.pdf\n\n📚 Bᴀᴛᴄʜ Nᴀᴍᴇ : {b_name}\n\n📇 Exᴛʀᴀ𝗰𝘁𝗲𝗱 Bʏ : {CR}**'

        chat_id = m.chat.id  # current chat (group/channel/private)

        try:
            if "drive" in url:
                try:
                    ka = await helper.download(url, name)
                    await send_doc_topic(chat_id, ka, cc1)
                    count+=1
                    os.remove(ka)
                    await asyncio.sleep(1)
                except FloodWait as e:
                    await m.reply_text(str(e))
                    await asyncio.sleep(e.x)
                    continue

            elif ".pdf" in url:
                try:
                    await asyncio.sleep(4)
                    url_pdf = url.replace(" ", "%20")
                    scraper = cloudscraper.create_scraper()
                    response = scraper.get(url_pdf)
                    if response.status_code == 200:
                        pdf_path = f'{name}.pdf'
                        with open(pdf_path, 'wb') as file:
                            file.write(response.content)
                        await asyncio.sleep(1)
                        await send_doc_topic(chat_id, pdf_path, cc1)
                        count += 1
                        os.remove(pdf_path)
                    else:
                        await send_text_topic(chat_id, f"Failed to download PDF: {response.status_code} {response.reason}")
                except FloodWait as e:
                    await m.reply_text(str(e))
                    await asyncio.sleep(e.x)
                    continue

            elif "media-cdn.classplusapp.com/drm/" in url:
                try:
                    await send_photo_topic(chat_id, cpimg, cpvod)
                    count +=1
                except Exception as e:
                    await m.reply_text(str(e))    
                    await asyncio.sleep(1)    
                    continue          

            elif any(ext in url.lower() for ext in [".jpg", ".jpeg", ".png"]):
                try:
                    await asyncio.sleep(4)
                    url_img = url.replace(" ", "%20")
                    scraper = cloudscraper.create_scraper()
                    response = scraper.get(url_img)
                    if response.status_code == 200:
                        img_path = f'{name}.jpg'
                        with open(img_path, 'wb') as file:
                            file.write(response.content)
                        await asyncio.sleep(1)
                        await send_photo_topic(chat_id, img_path, cimg)
                        count += 1
                        os.remove(img_path)
                    else:
                        await send_text_topic(chat_id, f"Failed to download Image: {response.status_code} {response.reason}")
                except FloodWait as e:
                    await m.reply_text(str(e))
                    await asyncio.sleep(e.x)
                    return  
                except Exception as e:
                    await m.reply_text(f"An error occurred: {str(e)}")
                    await asyncio.sleep(4)  
                        
            elif ".zip" in url:
                try:
                    download_cmd = f'{cmd} -R 25 --fragment-retries 25'
                    os.system(download_cmd)
                    zip_path = f'{name}.zip'
                    if os.path.exists(zip_path):
                        await send_doc_topic(chat_id, zip_path, cczip)
                        count += 1
                        os.remove(zip_path)
                    else:
                        await send_text_topic(chat_id, f"Zip failed: {url}")
                except FloodWait as e:
                    await m.reply_text(str(e))
                    await asyncio.sleep(e.x)
                    count += 1
                    continue
                        
            else:
                # treat as video
                emoji_message = await show_random_emojis(m)
                remaining_links = len(links) - count
                Show = (
                    f"**🍁 𝗗𝗢𝗪𝗡𝗟𝗢𝗔𝗗𝗜𝗡𝗚 🍁**\n\n"
                    f"**📝ɴᴀᴍᴇ » ** `{name}`\n\n"
                    f"🔗ᴛᴏᴛᴀʟ ᴜʀʟ » {len(links)}\n\n"
                    f"🗂️ɪɴᴅᴇx » {str(count)}/{len(links)}\n\n"
                    f"🌐ʀᴇᴍᴀɪɴɪɴɢ ᴜʀʟ » {remaining_links}\n\n"
                    f"❄ǫᴜᴀʟɪᴛʏ » {res}`\n\n"
                    f"**🔗ᴜʀʟ » ** `{url}`\n\n"
                    f"𝗕𝗢𝗧 𝗠𝗔𝗗𝗘 𝗕𝗬 ➤ 𝗔𝗗𝗜𝗧𝗬𝗔⚡️\n\n"
                )
                prog = await m.reply_text(Show)
                res_file = await helper.download_video(url, cmd, name)
                filename = res_file
                await prog.delete(True)
                await emoji_message.delete()

                # Instead of helper.send_vid (no topic param), do our own:
                if filename and os.path.exists(filename):
                    await send_video_topic(chat_id, filename, cc, thumb=thumb)
                    try:
                        os.remove(filename)
                    except Exception:
                        pass
                else:
                    await send_text_topic(chat_id, f"Download failed: {url}")

                count += 1
                await asyncio.sleep(1)

        except Exception as e:
            await send_text_topic(
                chat_id,
                f'‼️𝗗𝗼𝘄𝗻𝗹𝗼𝗮𝗱𝗶𝗻𝗴 𝗙𝗮𝗶𝗹𝗲𝗱‼️\n\n📝𝗡𝗮𝗺𝗲 » `{name}`\n\n🔗𝗨𝗿𝗹 » {url}'
            )
            count += 1
            failed_count += 1
            continue   

    # ------------------------------------------------------------------
    # SUMMARY
    # ------------------------------------------------------------------
    await send_text_topic(
        m.chat.id,
        f"`✨𝗕𝗔𝗧𝗖𝗛 𝗦𝗨𝗠𝗠𝗔𝗥𝗬✨\n\n"
        f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
        f"📛𝗜𝗻𝗱𝗲𝘅 𝗥𝗮𝗻𝗴𝗲 » ({raw_text} to {len(links)})\n"
        f"📚𝗕𝗮𝘁𝗰𝗵 𝗡𝗮𝗺𝗲 » {b_name}\n\n"
        f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
        f"✨𝗧𝗫𝗧 𝗦𝗨𝗠𝗠𝗔𝗥𝗬✨ : {len(links)}\n"
        f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
        f"🔹𝗩𝗶𝗱𝗲𝗼 » {video_count}\n🔹𝗣𝗱𝗳 » {pdf_count}\n🔹𝗜𝗺𝗴 » {img_count}\n🔹𝗭𝗶𝗽 » {zip_count}\n🔹𝗙𝗮𝗶𝗹𝗲𝗱 𝗨𝗿𝗹 » {failed_count}\n\n"
        f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
        f"✅𝗦𝗧𝗔𝗧𝗨𝗦 » 𝗖𝗢𝗠𝗣𝗟𝗘𝗧𝗘𝗗`"
    )
    await send_text_topic(m.chat.id, f"<pre><code>📥𝗘𝘅𝘁𝗿𝗮𝗰𝘁𝗲𝗱 𝗕𝘆 ➤『{CR}』</code></pre>")
    await send_text_topic(m.chat.id, f"<pre><code>『😏𝗥𝗲𝗮𝗰𝘁𝗶𝗼𝗻 𝗞𝗼𝗻 𝗗𝗲𝗴𝗮😏』</code></pre>")                 

# ------------------------------------------------------------------
# RUN
# ------------------------------------------------------------------
bot.run()

# This block (asyncio.run(main())) was unreachable & erroneous in original; removed.
# If you have external web app / webhook main(), handle separately.
