import telebot
from telebot import types
from flask import Flask, jsonify, make_response, send_file
from flask_cors import CORS
import threading
import json
import os
import time
import requests
from datetime import datetime
import urllib.parse

# নতুন টোকেন ও কনফিগারেশন
BOT_TOKEN = "8712538290:AAHWVc4G7nQHzU5QpLiaaPWGrR8vpST_bBA"
ADMIN_ID = "7255626228"
APP_URL = "https://bongo-bd-app-uixi.onrender.com/"
STORAGE_CHANNEL_ID = -1003902807907

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
app = Flask(__name__)
CORS(app)

BIN_ID = "6ac43001ac6210605a17383a"
JSONBIN_API_KEY = "$2a$10$YXJkOPYEpFL1pS32JSWh7O5Zs7VMzulVbyfBwxBkvPOQ9EY1m0/ri"
BIN_URL = f"https://api.jsonbin.io/v3/b/{BIN_ID}"
HEADERS = {
    "X-Master-Key": JSONBIN_API_KEY,
    "Content-Type": "application/json"
}

cached_data = None
admin_state = {}

def load_data(force_refresh=True):
    global cached_data
    try:
        r = requests.get(f"{BIN_URL}/latest", headers=HEADERS, timeout=10)
        if r.status_code == 200:
            res = r.json().get("record", {})
            if isinstance(res, dict) and "videos" in res:
                cached_data = res
                return cached_data
    except Exception as e:
        print("JSONBin Load Error:", e)

    if cached_data:
        return cached_data

    return {
        "users": [],
        "categories": ["Top", "BPS5", "MOVIES", "DRAMA", "SERIES", "COMING SOON"],
        "ads": {"ad1": "https://google.com", "ad2": "https://google.com"},
        "welcome_video": "",
        "update_notice": "বর্তমানে কোনো নতুন আপডেট নেই। আমাদের সাথেই থাকুন!",
        "videos": []
    }

def save_data(data):
    global cached_data
    cached_data = data
    try:
        requests.put(BIN_URL, headers=HEADERS, json=data, timeout=10)
    except Exception as e:
        print("JSONBin Save Error:", e)

def upload_thumb_securely(photo_id):
    try:
        file_info = bot.get_file(photo_id)
        file_bytes = bot.download_file(file_info.file_path)
        res = requests.post(
            "https://freeimage.host/api/1/upload",
            data={"key": "6d207e02198a847aa98d0a2a901485a5", "action": "upload", "format": "json"},
            files={"source": ("thumb.jpg", file_bytes, "image/jpeg")},
            timeout=15
        )
        if res.status_code == 200:
            data = res.json()
            if "image" in data and "url" in data["image"]:
                return data["image"]["url"]
    except Exception as e:
        print("Cloud Upload Error:", e)

    try:
        file_info = bot.get_file(photo_id)
        tg_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"
        enc = urllib.parse.quote(tg_url, safe='')
        return f"https://images.weserv.nl/?url={enc}&w=640&h=360&fit=cover&output=jpg&q=85"
    except Exception as e:
        return "https://placehold.co/640x360/1a1a1a/ffffff.png?text=BongoBD"

@app.route('/api/data', methods=['GET', 'OPTIONS'])
def get_app_data():
    data = load_data(force_refresh=True)
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
    markup.add(
        types.InlineKeyboardButton("🎬 WATCH NOW", web_app=types.WebAppInfo(url=fresh_url)),
        types.InlineKeyboardButton("🔔 VIDEO UPDATE", callback_data="btn_update"),
        types.InlineKeyboardButton("💡 যেভাবে ভিডিও ডাউনলোড করবেন", callback_data="btn_help")
    )
    return markup

def get_admin_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("➕ Add Video"),
        types.KeyboardButton("📢 Add Coming Soon"),
        types.KeyboardButton("🔕 Delete Video"),
        types.KeyboardButton("📊 Total Users"),
        types.KeyboardButton("📁 Set Category"),
        types.KeyboardButton("🎯 Set Ads Link"),
        types.KeyboardButton("🎥 Set Welcome Video"),
        types.KeyboardButton("🔔 Set Video Update"),
        types.KeyboardButton("📢 BOT NOTICE")
    )
    return markup

def get_delete_view_data(page=0):
    data = load_data(force_refresh=True)
    videos = data.get("videos", [])
    if not videos: return None, None
    per_page = 8
    start_idx = page * per_page
    current_videos = videos[start_idx:start_idx + per_page]

    text_msg = f"🗑️ **ডিলিট মেনু (পেজ: {page+1}/{(len(videos)+per_page-1)//per_page}):**\n\n"
    markup = types.InlineKeyboardMarkup()
    for idx, v in enumerate(current_videos, start=start_idx + 1):
        text_msg += f"**{idx}.** {v.get('title')} ({v.get('category')})\n"
        markup.add(types.InlineKeyboardButton(f"🗑️ {idx}. {v.get('title')[:25]}", callback_data=f"delvid_{v.get('id')}_{page}"))

    navs = []
    if page > 0:
        navs.append(types.InlineKeyboardButton("⬅️ Prev", callback_data=f"delpage_{page-1}"))
    if start_idx + per_page < len(videos):
        navs.append(types.InlineKeyboardButton("Next ➡️️", callback_data=f"delpage_{page+1}"))
    if navs: markup.row(*navs)
    markup.add(types.InlineKeyboardButton("❌ বন্ধ করুন", callback_data="close_admin_menu"))
    return text_msg, markup

def get_category_keyboard():
    data = load_data(force_refresh=True)
    cats = data.get("categories", ["Top", "BPS5", "MOVIES", "DRAMA", "SERIES", "COMING SOON"])
    markup = types.InlineKeyboardMarkup()
    for c in cats:
        markup.add(types.InlineKeyboardButton(f"🗑 Delete: {c}", callback_data=f"delcat_{c}"))
    markup.add(types.InlineKeyboardButton("➕ Add New Category", callback_data="add_new_category"))
    markup.add(types.InlineKeyboardButton("❌ বন্ধ করুন", callback_data="close_admin_menu"))
    return markup

@bot.message_handler(commands=['admin'])
def open_admin_panel(message):
    if str(message.chat.id) != str(ADMIN_ID): return
    bot.send_message(message.chat.id, "🛠 **এডমিন প্যানেল:**", reply_markup=get_admin_keyboard(), parse_mode="Markdown")

@bot.message_handler(commands=['cancel'])
def cancel_process(message):
    chat_id = message.chat.id
    if chat_id in admin_state: del admin_state[chat_id]
    bot.send_message(chat_id, "🔄 কাজ বাতিল করা হয়েছে।", reply_markup=get_admin_keyboard() if str(chat_id) == str(ADMIN_ID) else types.ReplyKeyboardRemove())

@bot.message_handler(commands=['start'])
def send_welcome(message):
    data = load_data(force_refresh=True)
    user_id = message.chat.id
    if user_id not in data.get("users", []):
        data.setdefault("users", []).append(user_id)
        save_data(data)

    text_parts = message.text.split()
    if len(text_parts) > 1 and text_parts[1].startswith("vid_"):
        video_id = text_parts[1].replace("vid_", "")
        target = next((v for v in data.get("videos", []) if str(v.get("id")) == str(video_id)), None)
        if target and target.get("file_id"):
            bot.send_message(chat_id=user_id, text=f"🎬 **{target['title']}**\n⏳ ভিডিও পাঠানো হচ্ছে...")
            try:
                bot.send_video(user_id, target['file_id'], caption=f"🎬 **{target['title']}**", protect_content=True, supports_streaming=True)
            except Exception:
                bot.send_document(user_id, target['file_id'], caption=f"🎬 **{target['title']}**")
            return

    first_name = message.from_user.first_name or "বন্ধু"
    caption = f"**আসসালামুআলাইকুম {first_name} 🥰**\n\nনাটক দেখতে ও ডাউনলোড করতে নিচের **WATCH NOW** বাটনে ক্লিক করুন।"
    welcome_vid = data.get("welcome_video")
    if welcome_vid:
        try:
            bot.send_video(user_id, welcome_vid, caption=caption, reply_markup=get_action_buttons(), parse_mode="Markdown")
        except Exception:
            bot.send_message(user_id, caption, reply_markup=get_action_buttons(), parse_mode="Markdown")
    else:
        bot.send_message(user_id, caption, reply_markup=get_action_buttons(), parse_mode="Markdown")

    if str(user_id) == str(ADMIN_ID):
        bot.send_message(user_id, "🛠 **এডমিন প্যানেল সচল করা হয়েছে:**", reply_markup=get_admin_keyboard(), parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    chat_id = call.message.chat.id
    if call.data == "btn_update":
        bot.answer_callback_query(call.id)
        data = load_data(force_refresh=True)
        bot.send_message(chat_id, f"📢 **ভিডিও আপডেট:**\n\n{data.get('update_notice', 'কোনো নতুন আপডেট নেই।')}")
        return
    elif call.data == "btn_help":
        bot.answer_callback_query(call.id)
        bot.send_message(chat_id, "💡 **ভিডিও ডাউনলোড নিয়ম:**\n১. WATCH NOW বাটনে চাপুন।\n২. ভিডিও সিলেক্ট করে দুটি এড সম্পূর্ণ দেখুন।\n৩. ডাউনলোড বাটনে চাপুন।")
        return

    if str(chat_id) != str(ADMIN_ID): return

    if call.data == "close_admin_menu":
        bot.delete_message(chat_id, call.message.message_id)
        return
    elif call.data.startswith("delpage_"):
        page = int(call.data.split("_")[1])
        txt, kb = get_delete_view_data(page)
        if kb: bot.edit_message_text(txt, chat_id, call.message.message_id, reply_markup=kb, parse_mode="Markdown")
        bot.answer_callback_query(call.id)
    elif call.data.startswith("delvid_"):
        parts = call.data.split("_")
        del_id = parts[1]
        page = int(parts[2]) if len(parts) > 2 else 0
        data = load_data(force_refresh=True)
        data["videos"] = [v for v in data.get("videos", []) if str(v.get('id')) != str(del_id)]
        save_data(data)
        bot.answer_callback_query(call.id, "✅ ডিলিট সম্পন্ন!", show_alert=True)
        txt, kb = get_delete_view_data(page)
        if kb: bot.edit_message_text(txt, chat_id, call.message.message_id, reply_markup=kb, parse_mode="Markdown")
        else: bot.edit_message_text("❌ আর কোনো ভিডিও নেই!", chat_id, call.message.message_id)
    elif call.data.startswith("delcat_"):
        cat_to_del = call.data.replace("delcat_", "").strip()
        data = load_data(force_refresh=True)
        cats = data.get("categories", [])
        if cat_to_del in cats:
            cats.remove(cat_to_del)
            data["categories"] = cats
            save_data(data)
            bot.answer_callback_query(call.id, f"✅ '{cat_to_del}' মুছে ফেলা হয়েছে!")
            bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=get_category_keyboard())
    elif call.data == "add_new_category":
        admin_state[chat_id] = {'step': 'add_single_category'}
        bot.answer_callback_query(call.id)
        bot.send_message(chat_id, "📁 **নতুন ক্যাটাগরির নাম লিখে পাঠান:**")

@bot.message_handler(content_types=['text', 'photo', 'video', 'document'])
def handle_admin_inputs(message):
    chat_id = message.chat.id 
    if str(chat_id) != str(ADMIN_ID): return

    if message.text == "➕ Add Video":
        admin_state[chat_id] = {'step': 'category'}
        data = load_data(force_refresh=True)
        cats = data.get("categories", ["Top", "BPS5", "MOVIES", "DRAMA", "SERIES"])
        markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        for i in range(0, len(cats), 2):
            markup.row(*[types.KeyboardButton(c) for c in cats[i:i+2]])
        bot.send_message(chat_id, "📁 **ভিডিওর ক্যাটাগরি বেছে নিন:**", reply_markup=markup)
        return
    elif message.text == "🔕 Delete Video":
        txt, kb = get_delete_view_data(0)
        if not kb:
            bot.send_message(chat_id, "❌ কোনো ভিডিও পাওয়া যায়নি!", reply_markup=get_admin_keyboard())
            return
        bot.send_message(chat_id, txt, reply_markup=kb, parse_mode="Markdown")
        return
    elif message.text == "📁 Set Category":
        bot.send_message(chat_id, "📁 **ক্যাটাগরি ম্যানেজমেন্ট:**", reply_markup=get_category_keyboard())
        return

    if chat_id not in admin_state: return
    step = admin_state[chat_id].get('step')

    if step == 'add_single_category' and message.text:
        new_c = message.text.strip().upper()
        data = load_data(force_refresh=True)
        cats = data.get("categories", [])
        if new_c and new_c not in cats:
            cats.append(new_c)
            data["categories"] = cats
            save_data(data)
            del admin_state[chat_id]
            bot.send_message(chat_id, f"✅ **'{new_c}' ক্যাটাগরি যুক্ত হয়েছে!**", reply_markup=get_admin_keyboard())
    elif step == 'category' and message.text:
        admin_state[chat_id]['category'] = message.text.strip()
        admin_state[chat_id]['step'] = 'title'
        bot.send_message(chat_id, "🎬 **ভিডিওর নাম (Title) লিখুন:**", reply_markup=types.ReplyKeyboardRemove())
    elif step == 'title' and message.text:
        admin_state[chat_id]['title'] = message.text.strip()
        admin_state[chat_id]['step'] = 'thumb'
        bot.send_message(chat_id, "🖼 **থাম্বনেইল ছবি পাঠান:**")
    elif step == 'thumb' and (message.photo or message.text):
        if message.photo:
            bot.send_chat_action(chat_id, 'upload_photo')
            thumb_url = upload_thumb_securely(message.photo[-1].file_id)
        else:
            thumb_url = message.text.strip()
        admin_state[chat_id]['thumb'] = thumb_url
        admin_state[chat_id]['step'] = 'video'
        bot.send_message(chat_id, "📥 **ভিডিও ফাইলটি পাঠান:**")
    elif step == 'video' and (message.video or message.document):
        incoming_file_id = message.video.file_id if message.video else message.document.file_id
        try:
            bot.send_chat_action(chat_id, 'upload_video')
            if message.video:
                fwd = bot.send_video(STORAGE_CHANNEL_ID, incoming_file_id, caption=f"🎬 {admin_state[chat_id]['title']}")
                file_id = fwd.video.file_id
            else:
                fwd = bot.send_document(STORAGE_CHANNEL_ID, incoming_file_id, caption=f"🎬 {admin_state[chat_id]['title']}")
                file_id = fwd.document.file_id
        except Exception as err:
            print("Channel Backup Error:", err)
            file_id = incoming_file_id

        data = load_data(force_refresh=True)
        new_video = {
            "id": int(time.time()),
            "category": admin_state[chat_id]['category'],
            "title": admin_state[chat_id]['title'],
            "thumb": admin_state[chat_id]['thumb'],
            "file_id": file_id,
            "date": datetime.now().strftime("%d %B %Y"),
            "time": datetime.now().strftime("%I:%M %p")
        }
        data.setdefault("videos", []).insert(0, new_video)
        save_data(data)
        del admin_state[chat_id]
        bot.reply_to(message, "🎉 **ভিডিও সফলভাবে আপলোড ও ক্লাউডে ব্যাকআপ হয়েছে!**", reply_markup=get_admin_keyboard())

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
