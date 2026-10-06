import subprocess
import sys

# সার্ভারে লাইব্রেরি নিশ্চিত করার অটো-হ্যান্ডলার
REQUIRED_PACKAGES = [
    "pyTelegramBotAPI",
    "Flask",
    "Flask-CORS",
    "requests",
    "pymongo",
    "dnspython"
]

for pkg in REQUIRED_PACKAGES:
    try:
        __import__(pkg.replace("-", "_").split("[")[0])
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])

import os
import time
import json
import urllib.parse
from datetime import datetime
import threading
import telebot
from telebot import types
from flask import Flask, jsonify, make_response, send_file
from flask_cors import CORS
from pymongo import MongoClient

# কনফিগারেশন
BOT_TOKEN = "8712538290:AAHWVc4G7nQHzU5QpLiaaPWGrR8vpST_bBA"
ADMIN_ID = "7255626228"
BOT_USERNAME = "BongoBd_ot_Bot"
APP_URL = "https://bongo-bd-app-uixi.onrender.com/"

bot = telebot.TeleBot(BOT_TOKEN, threaded=True)
app = Flask(__name__)
CORS(app)

MONGO_URI = "mongodb+srv://enamulhossen473_db_user:eN708090@cluster0.kq0upog.mongodb.net/bongo_bd_db?retryWrites=true&w=majority"
client = MongoClient(MONGO_URI, connect=False)
db = client["bongo_bd_db"]
data_col = db["main_data"]

admin_state = {}

def get_default_data():
    return {
        "_id": "app_config",
        "users": [],
        "categories": ["Top", "BPS5", "MOVIES", "DRAMA", "SERIES", "COMING SOON"],
        "ads": {"ad1": "https://google.com", "ad2": "https://google.com"},
        "welcome_video": "",
        "update_notice": "বর্তমানে কোনো নতুন আপডেট নেই। আমাদের সাথেই থাকুন!",
        "videos": []
    }

def load_data():
    try:
        rec = data_col.find_one({"_id": "app_config"})
        if rec:
            return rec
        default_data = get_default_data()
        data_col.update_one({"_id": "app_config"}, {"$set": default_data}, upsert=True)
        return default_data
    except Exception as e:
        print("Read Error:", e)
        return get_default_data()

def save_data(data):
    try:
        data["_id"] = "app_config"
        data_col.update_one({"_id": "app_config"}, {"$set": data}, upsert=True)
        print("MongoDB Save Successful!")
    except Exception as e:
        print("Save Error:", e)

def upload_thumb_securely(photo_id):
    try:
        file_info = bot.get_file(photo_id)
        tg_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"
        encoded_url = urllib.parse.quote(tg_url, safe='')
        return f"https://images.weserv.nl/?url={encoded_url}&w=640&h=360&fit=cover&output=jpg&q=85"
    except Exception as e:
        return "https://placehold.co/640x360/1a1a1a/ffffff.png?text=Bongo+BD"

@app.route('/api/data', methods=['GET'])
def get_app_data():
    data = load_data()
    if "_id" in data:
        del data["_id"]
    resp = make_response(jsonify(data))
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return resp

@app.route('/')
def home():
    if os.path.exists('index.html'):
        return send_file('index.html')
    return "Bongo BD Server Live 24/7!"

def get_action_buttons():
    fresh_url = f"{APP_URL}?v={int(time.time())}"
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn_watch = types.InlineKeyboardButton("🎬 WATCH NOW", web_app=types.WebAppInfo(url=fresh_url))
    markup.add(btn_watch)
    return markup

def get_admin_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    b1 = types.KeyboardButton("➕ Add Video")
    b2 = types.KeyboardButton("🔕 Delete Video")
    b3 = types.KeyboardButton("📊 Total Users")
    markup.add(b1, b2, b3)
    return markup

@bot.message_handler(commands=['admin'])
def open_admin_panel(message):
    if str(message.chat.id) != str(ADMIN_ID): return
    admin_state.pop(message.chat.id, None)
    bot.send_message(message.chat.id, "🛠 **এডমিন প্যানেল সচল করা হয়েছে:**", reply_markup=get_admin_keyboard(), parse_mode="Markdown")

@bot.message_handler(commands=['cancel'])
def cancel_process(message):
    admin_state.pop(message.chat.id, None)
    bot.send_message(message.chat.id, "🔄 বাতিল করা হয়েছে।", reply_markup=get_admin_keyboard() if str(message.chat.id) == str(ADMIN_ID) else types.ReplyKeyboardRemove())

@bot.message_handler(commands=['start'])
def send_welcome(message):
    data = load_data()
    user_id = message.chat.id
    if user_id not in data.get("users", []):
        data.setdefault("users", []).append(user_id)
        save_data(data)

    text_parts = message.text.split()
    if len(text_parts) > 1 and text_parts[1].startswith("vid_"):
        video_id = text_parts[1].replace("vid_", "").strip()
        target_video = next((v for v in data.get("videos", []) if str(v.get("id")).strip() == video_id), None)
        if target_video and target_video.get("file_id"):
            bot.send_message(user_id, f"🎬 **{target_video['title']}**\n⏳ পাঠানো হচ্ছে...")
            try:
                bot.send_video(user_id, target_video['file_id'], caption=f"🎬 **{target_video['title']}**")
            except Exception:
                bot.send_document(user_id, target_video['file_id'], caption=f"🎬 **{target_video['title']}**")
            return

    first_name = message.from_user.first_name or "বন্ধু"
    welcome_caption = f"**আসসালামুআলাইকুম {first_name} 🥰**\n\nআমাদের বট ২৪ ঘণ্টা সচল। নাটক দেখতে নিচে ক্লিক করুন।"
    bot.send_message(message.chat.id, welcome_caption, reply_markup=get_action_buttons(), parse_mode="Markdown")

    if str(user_id) == str(ADMIN_ID):
        bot.send_message(message.chat.id, "🛠 **এডমিন প্যানেল:**", reply_markup=get_admin_keyboard(), parse_mode="Markdown")

@bot.message_handler(content_types=['text', 'photo', 'video', 'document'])
def handle_admin_inputs(message):
    chat_id = message.chat.id
    if str(chat_id) != str(ADMIN_ID): return

    msg_txt = (message.text or "").strip()

    if "Add Video" in msg_txt:
        admin_state[chat_id] = {'step': 'category'}
        data = load_data()
        cats = data.get("categories", ["Top", "BPS5", "MOVIES", "DRAMA"])
        markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        for i in range(0, len(cats), 2):
            markup.row(*[types.KeyboardButton(c) for c in cats[i:i+2]])
        bot.send_message(chat_id, "📁 **ভিডিওর ক্যাটাগরি বেছে নিন:**", reply_markup=markup)
        return

    if chat_id not in admin_state: return
    step = admin_state[chat_id].get('step')

    if step == 'category' and message.text:
        admin_state[chat_id]['category'] = message.text.strip()
        admin_state[chat_id]['step'] = 'title'
        bot.send_message(chat_id, "🎬 **ভিডিওর নাম (Title) লিখুন:**", reply_markup=types.ReplyKeyboardRemove())

    elif step == 'title' and message.text:
        admin_state[chat_id]['title'] = message.text.strip()
        admin_state[chat_id]['step'] = 'thumb'
        bot.send_message(chat_id, "🖼 **থাম্বনেইল ছবি পাঠান:**")

    elif step == 'thumb' and (message.photo or message.text):
        thumb_url = upload_thumb_securely(message.photo[-1].file_id) if message.photo else message.text.strip()
        admin_state[chat_id]['thumb'] = thumb_url
        admin_state[chat_id]['step'] = 'video'
        bot.send_message(chat_id, "📥 **ভিডিও ফাইলটি পাঠান:**")

    elif step == 'video' and (message.video or message.document):
        file_id = message.video.file_id if message.video else message.document.file_id
        data = load_data()
        
        new_video = {
            "id": int(time.time()),
            "category": admin_state[chat_id].get('category', 'Top'),
            "title": admin_state[chat_id].get('title', 'Video'),
            "thumb": admin_state[chat_id].get('thumb', ''),
            "file_id": file_id,
            "date": datetime.now().strftime("%d %B %Y")
        }
        
        data.setdefault("videos", []).insert(0, new_video)
        save_data(data)
        
        admin_state.pop(chat_id, None)
        bot.send_message(chat_id, "🎉 **ভিডিও সফলভাবে ক্লাউড ডাটাবেজে যুক্ত হয়েছে!**", reply_markup=get_admin_keyboard())

def run_bot():
    while True:
        try:
            bot.polling(none_stop=True, interval=0, timeout=20)
        except Exception:
            time.sleep(3)

if __name__ == "__main__":
    t = threading.Thread(target=run_bot)
    t.daemon = True
    t.start()
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
