import subprocess
import sys

# প্রয়োজনীয় লাইব্রেরি ইনস্টল নিশ্চিতকরণ
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

import telebot
from telebot import types
from flask import Flask, jsonify, make_response, send_file
from flask_cors import CORS
import threading
import os
import time
import json
import urllib.parse
from datetime import datetime
from pymongo import MongoClient

BOT_TOKEN = "8712538290:AAHWVc4G7nQHzU5QpLiaaPWGrR8vpST_bBA"
ADMIN_ID = "7255626228"
BOT_USERNAME = "BongoBd_ot_Bot"
APP_URL = "https://bongo-bd-app-uixi.onrender.com/"
LOCAL_FILE = "database_backup.json"

bot = telebot.TeleBot(BOT_TOKEN, threaded=True)
app = Flask(__name__)
CORS(app)

MONGO_URI = "mongodb+srv://enamulhossen473_db_user:eN708090@cluster0.kq0upog.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

data_col = None
try:
    client = MongoClient(MONGO_URI, connect=True, serverSelectionTimeoutMS=4000)
    db = client["bongo_bd_db"]
    data_col = db["main_data"]
    client.server_info()
    print("MongoDB Connected Successfully!")
except Exception as e:
    print("MongoDB Connection Warning:", e)

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

def read_local():
    if os.path.exists(LOCAL_FILE):
        try:
            with open(LOCAL_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return get_default_data()

def write_local(data):
    try:
        clean = dict(data)
        if "_id" in clean:
            del clean["_id"]
        with open(LOCAL_FILE, 'w', encoding='utf-8') as f:
            json.dump(clean, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("Local write error:", e)

def load_data():
    global data_col
    if data_col is not None:
        try:
            rec = data_col.find_one({"_id": "app_config"})
            if rec:
                write_local(rec)
                return rec
            else:
                d = read_local()
                d["_id"] = "app_config"
                data_col.update_one({"_id": "app_config"}, {"$set": d}, upsert=True)
                return d
        except Exception as e:
            print("Mongo Read Failed, using local:", e)
    return read_local()

def save_data(data):
    global data_col
    write_local(data)
    if data_col is not None:
        try:
            data["_id"] = "app_config"
            data_col.replace_one({"_id": "app_config"}, data, upsert=True)
        except Exception as e:
            print("Mongo Save Failed:", e)

def upload_thumb_securely(photo_id):
    try:
        file_info = bot.get_file(photo_id)
        tg_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"
        encoded_url = urllib.parse.quote(tg_url, safe='')
        return f"https://images.weserv.nl/?url={encoded_url}&w=640&h=360&fit=cover&output=jpg&q=85"
    except Exception as e:
        print("Thumb Error:", e)
        return "https://placehold.co/640x360/1a1a1a/ffffff.png?text=Bongo+BD"

@app.route('/api/data', methods=['GET', 'OPTIONS'])
def get_app_data():
    data = load_data()
    if "_id" in data:
        del data["_id"]
    resp = make_response(jsonify(data))
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
    resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, Cache-Control'
    resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return resp

@app.route('/')
def home():
    if os.path.exists('index.html'):
        resp = make_response(send_file('index.html'))
        resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        return resp
    return "Bongo BD Server Live 24/7!"

def get_action_buttons():
    fresh_url = f"{APP_URL}?v={int(time.time())}"
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn_watch = types.InlineKeyboardButton("🎬 WATCH NOW", web_app=types.WebAppInfo(url=fresh_url))
    btn_update = types.InlineKeyboardButton("🔔 VIDEO UPDATE", callback_data="btn_update")
    btn_help = types.InlineKeyboardButton("💡 যেভাবে ভিডিও ডাউনলোড করবেন", callback_data="btn_help")
    markup.add(btn_watch, btn_update, btn_help)
    return markup

def get_admin_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    b1 = types.KeyboardButton("➕ Add Video")
    b2 = types.KeyboardButton("📢 Add Coming Soon")
    b3 = types.KeyboardButton("🔕 Delete Video")
    b4 = types.KeyboardButton("📊 Total Users")
    b5 = types.KeyboardButton("📁 Set Category")
    b6 = types.KeyboardButton("🎯 Set Ads Link")
    b7 = types.KeyboardButton("🎥 Set Welcome Video")
    b8 = types.KeyboardButton("🔔 Set Video Update")
    b9 = types.KeyboardButton("📢 BOT NOTICE")
    markup.add(b1, b2, b3, b4, b5, b6, b7, b8, b9)
    return markup

@bot.message_handler(commands=['admin'])
def open_admin_panel(message):
    if str(message.chat.id) != str(ADMIN_ID):
        bot.reply_to(message, "❌ আপনি অ্যাডমিন নন!")
        return
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
                bot.send_video(user_id, target_video['file_id'], caption=f"🎬 **{target_video['title']}**", protect_content=True, supports_streaming=True)
            except Exception:
                bot.send_document(user_id, target_video['file_id'], caption=f"🎬 **{target_video['title']}**")
            return
        else:
            bot.send_message(user_id, "⚠️️ দুঃখিত, এই ভিডিওটি পাওয়া যায়নি।")
            return

    markup = get_action_buttons()
    first_name = message.from_user.first_name or "বন্ধু"
    welcome_caption = f"**আসসালামুআলাইকুম {first_name} 🥰**\n\nআমাদের বট ২৪ ঘণ্টা সচল। নাটক দেখতে ও ডাউনলোড করতে নিচের **WATCH NOW** বাটনে ক্লিক করুন।"
    bot.send_message(message.chat.id, welcome_caption, reply_markup=markup, parse_mode="Markdown")

    if str(user_id) == str(ADMIN_ID):
        bot.send_message(message.chat.id, "🛠 **এডমিন প্যানেল সচল করা হয়েছে:**", reply_markup=get_admin_keyboard(), parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    chat_id = call.message.chat.id
    if call.data == "btn_update":
        bot.answer_callback_query(call.id)
        data = load_data()
        bot.send_message(chat_id, f"📢 **ভিডিও আপডেট:**\n\n{data.get('update_notice', 'বর্তমানে কোনো নতুন আপডেট নেই।')}")
    elif call.data == "btn_help":
        bot.answer_callback_query(call.id)
        bot.send_message(chat_id, "💡 WATCH NOW বাটনে চাপ দিয়ে ভিডিও ডাউনলোড করতে পারবেন।")

@bot.message_handler(content_types=['text', 'photo', 'video', 'document'])
def handle_admin_inputs(message):
    chat_id = message.chat.id
    if str(chat_id) != str(ADMIN_ID):
        return

    msg_txt = (message.text or "").strip()

    if "Add Video" in msg_txt:
        admin_state[chat_id] = {'step': 'category'}
        data = load_data()
        cats = data.get("categories", ["Top", "BPS5", "MOVIES", "DRAMA", "SERIES"])
        markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        for i in range(0, len(cats), 2):
            markup.row(*[types.KeyboardButton(c) for c in cats[i:i+2]])
        bot.send_message(chat_id, "📁 **ভিডিওর ক্যাটাগরি বেছে নিন:**", reply_markup=markup)
        return

    if chat_id not in admin_state:
        return
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
            "date": datetime.now().strftime("%d %B %Y"),
            "time": datetime.now().strftime("%I:%M %p")
        }
        data.setdefault("videos", []).insert(0, new_video)
        save_data(data)
        admin_state.pop(chat_id, None)
        bot.send_message(chat_id, "🎉 **ভিডিও সফলভাবে ক্লাউড ডাটাবেজে যুক্ত হয়েছে!**", reply_markup=get_admin_keyboard())

def run_bot():
    while True:
        try:
            bot.polling(none_stop=True, interval=0, timeout=20)
        except Exception as e:
            time.sleep(3)

if __name__ == "__main__":
    t = threading.Thread(target=run_bot)
    t.daemon = True
    t.start()
    
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
