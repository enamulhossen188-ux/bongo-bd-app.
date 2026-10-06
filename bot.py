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

# ২য় বটের নিজস্ব টোকেন ও কনফিগারেশন
BOT_TOKEN = "8712538290:AAHskUrqeMrwwAYtGR7PDamWRt9EMEOwopA"
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
    try:
        r = requests.get(f"{BIN_URL}/latest", headers=HEADERS, timeout=12)
        if r.status_code == 200:
            res = r.json().get("record", {})
            if isinstance(res, dict) and "videos" in res:
                return res
    except Exception as e:
        print("JSONBin Read Error:", e)

    return {
        "users": [],
        "categories": ["Top", "BPS5", "MOVIES", "DRAMA", "SERIES", "COMING SOON"],
        "ads": {"ad1": "https://google.com", "ad2": "https://google.com"},
        "welcome_video": "",
        "update_notice": "বর্তমানে কোনো নতুন আপডেট নেই। আমাদের সাথেই থাকুন!",
        "videos": []
    }

def save_data(data):
    try:
        requests.put(BIN_URL, headers=HEADERS, json=data, timeout=12)
    except Exception as e:
        print("JSONBin Save Error:", e)

# ছবি থেকে স্থায়ী ক্লাউড লিংক তৈরি (যা কখনো কালো বা নষ্ট হবে না)
def upload_thumb_securely(photo_id):
    try:
        file_info = bot.get_file(photo_id)
        downloaded = bot.download_file(file_info.file_path)
        
        # Freeimage ক্লাউড এপিআই দিয়ে পার্মানেন্ট ডিরেক্ট লিংক তৈরি
        res = requests.post(
            "https://freeimage.host/api/1/upload",
            data={
                "key": "6d207e02198a847aa98d0a2a901485a5",
                "action": "upload",
                "format": "json"
            },
            files={"source": ("thumb.jpg", downloaded, "image/jpeg")},
            timeout=20
        )
        if res.status_code == 200:
            img_data = res.json()
            if "image" in img_data and "url" in img_data["image"]:
                return img_data["image"]["url"]
    except Exception as e:
        print("Freeimage Error:", e)

    # ব্যাকআপ হিসেবে Catbox ক্লাউড
    try:
        res2 = requests.post(
            "https://catbox.moe/user/api.php",
            data={"reqtype": "fileupload"},
            files={"fileToUpload": ("thumb.jpg", downloaded, "image/jpeg")},
            timeout=15
        )
        if res2.status_code == 200 and res2.text.strip().startswith("http"):
            return res2.text.strip()
    except Exception as e:
        print("Catbox Error:", e)

    return "https://placehold.co/640x360/111827/ffffff.png?text=Bongo+BD"

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

def format_button_label(video):
    title = video.get('title', 'Video').strip()
    if len(title) > 30:
        return f"🗑 {title[:28]}.."
    return f"🗑️ {title}"

def get_delete_view_data(page=0):
    data = load_data(force_refresh=True)
    videos = data.get("videos", [])
    if not videos:
        return None, None

    per_page = 8
    start_idx = page * per_page
    end_idx = start_idx + per_page
    current_videos = videos[start_idx:end_idx]

    text_msg = f"🗑️ **ডিলিট মেনু (পেজ: {page+1}/{(len(videos)+per_page-1)//per_page}):**\n\n"
    markup = types.InlineKeyboardMarkup()

    for idx, v in enumerate(current_videos, start=start_idx + 1):
        text_msg += f"**{idx}.** {v.get('title')} ({v.get('category')})\n"
        btn_label = f"{idx}. {format_button_label(v)}"
        markup.add(types.InlineKeyboardButton(btn_label, callback_data=f"delvid_{v.get('id')}_{page}"))

    nav_buttons = []
    if page > 0:
        nav_buttons.append(types.InlineKeyboardButton("⬅️ Previous", callback_data=f"delpage_{page-1}"))
    if end_idx < len(videos):
        nav_buttons.append(types.InlineKeyboardButton("Next ➡️", callback_data=f"delpage_{page+1}"))
    
    if nav_buttons:
        markup.row(*nav_buttons)

    markup.add(types.InlineKeyboardButton("❌ বন্ধ করুন (Close)", callback_data="close_admin_menu"))
    return text_msg, markup

def get_category_keyboard():
    data = load_data(force_refresh=True)
    cats = data.get("categories", ["Top", "BPS5", "MOVIES", "DRAMA", "SERIES", "COMING SOON"])
    markup = types.InlineKeyboardMarkup()

    for c in cats:
        markup.add(types.InlineKeyboardButton(f"🗑 Delete: {c}", callback_data=f"delcat_{c}"))

    markup.add(types.InlineKeyboardButton("➕ Add New Category", callback_data="add_new_category"))
    markup.add(types.InlineKeyboardButton("❌ বন্ধ করুন (Close)", callback_data="close_admin_menu"))
    return markup

@bot.message_handler(commands=['admin'])
def open_admin_panel(message):
    if str(message.chat.id) != str(ADMIN_ID):
        bot.reply_to(message, "❌ আপনি অ্যাডমিন নন!")
        return
    bot.send_message(
        message.chat.id, 
        "🛠 **এডমিন প্যানেল সচল করা হয়েছে:**", 
        reply_markup=get_admin_keyboard(),
        parse_mode="Markdown"
    )

@bot.message_handler(commands=['cancel'])
def cancel_process(message):
    chat_id = message.chat.id
    if chat_id in admin_state:
        del admin_state[chat_id]
        bot.send_message(chat_id, "🔄 কাজ বাতিল করা হয়েছে।", reply_markup=get_admin_keyboard() if str(chat_id) == str(ADMIN_ID) else types.ReplyKeyboardRemove())
    else:
        bot.send_message(chat_id, "বর্তমানে কোনো কাজ চালু নেই।", reply_markup=get_admin_keyboard() if str(chat_id) == str(ADMIN_ID) else types.ReplyKeyboardRemove())

@bot.message_handler(commands=['start'])
def send_welcome(message):
    data = load_data(force_refresh=True)
    user_id = message.chat.id
    if "users" not in data: data["users"] = []
    if user_id not in data["users"]:
        data["users"].append(user_id)
        save_data(data)

    text_parts = message.text.split()
    if len(text_parts) > 1 and text_parts[1].startswith("vid_"):
        video_id = text_parts[1].replace("vid_", "")
        target_video = next((v for v in data.get("videos", []) if str(v.get("id")) == str(video_id)), None)

        if target_video and target_video.get("file_id"):
            bot.send_message(message.chat.id, f"🎬 **{target_video['title']}**\n⏳ আপনার ভিডিওটি ইনবক্সে পাঠানো হচ্ছে...")
            try:
                bot.send_video(message.chat.id, target_video['file_id'], caption=f"🎬 **{target_video['title']}**\n\nউপভোগ করুন!", protect_content=True, supports_streaming=True)
            except Exception:
                bot.send_document(message.chat.id, target_video['file_id'], caption=f"🎬 **{target_video['title']}**")
            return

    markup = get_action_buttons()
    first_name = message.from_user.first_name or "বন্ধু"
    welcome_caption = f"**আসসালামুআলাইকুম {first_name} 🥰**\n\nআমাদের বট ২৪ ঘণ্টা সচল। নাটক দেখতে ও ডাউনলোড করতে নিচের **WATCH NOW** বাটনে ক্লিক করুন।"

    welcome_vid = data.get("welcome_video")
    if welcome_vid:
        try:
            bot.send_video(message.chat.id, welcome_vid, caption=welcome_caption, reply_markup=markup, parse_mode="Markdown")
        except Exception:
            bot.send_message(message.chat.id, welcome_caption, reply_markup=markup, parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, welcome_caption, reply_markup=markup, parse_mode="Markdown")

    if str(user_id) == str(ADMIN_ID):
        bot.send_message(message.chat.id, "🛠️ **এডমিন প্যানেল সচল করা হয়েছে:**", reply_markup=get_admin_keyboard(), parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    chat_id = call.message.chat.id
    
    if call.data == "btn_update":
        bot.answer_callback_query(call.id)
        data = load_data(force_refresh=True)
        notice_text = data.get("update_notice", "বর্তমানে কোনো নতুন আপডেট নেই। আমাদের সাথেই থাকুন!")
        bot.send_message(chat_id, f"📢 **ভিডিও আপডেট:**\n\n{notice_text}")
        return
        
    elif call.data == "btn_help":
        bot.answer_callback_query(call.id)
        bot.send_message(chat_id, "💡 **যেভাবে ভিডিও ডাউনলোড করবেন:**\n১. WATCH NOW বাটনে ক্লিক করে অ্যাপে ঢুকুন।\n২. পছন্দের ভিডিও সিলেক্ট করুন।\n৩. দুটি বিজ্ঞাপন ১০ সেকেন্ড করে ভিজিট করুন।\n৪. ডাউনলোড বাটনে চাপ দিলে ভিডিও ইনবক্সে চলে আসবে!")
        return

    if str(chat_id) != str(ADMIN_ID):
        bot.answer_callback_query(call.id, "❌ আপনি অ্যাডমিন নন!")
        return

    if call.data == "close_admin_menu":
        bot.delete_message(chat_id, call.message.message_id)
        bot.answer_callback_query(call.id, "বন্ধ করা হয়েছে!")
        return

    if call.data.startswith("delvid_"):
        parts = call.data.split("_")
        del_id = parts[1]
        page = int(parts[2]) if len(parts) > 2 else 0

        data = load_data(force_refresh=True)
        videos = data.get("videos", [])
        data["videos"] = [v for v in videos if str(v.get('id')) != str(del_id)]
        save_data(data)

        bot.answer_callback_query(call.id, "✅ সফলভাবে ডিলিট করা হয়েছে!", show_alert=True)
        txt, kb = get_delete_view_data(page)
        if kb:
            bot.edit_message_text(txt, chat_id, call.message.message_id, reply_markup=kb, parse_mode="Markdown")
        else:
            bot.edit_message_text("❌ আর কোনো ভিডিও নেই!", chat_id, call.message.message_id)
        return

    if call.data.startswith("delcat_"):
        cat_to_del = call.data.replace("delcat_", "").strip()
        data = load_data(force_refresh=True)
        cats = data.get("categories", [])
        if cat_to_del in cats:
            cats.remove(cat_to_del)
            data["categories"] = cats
            save_data(data)
            bot.answer_callback_query(call.id, f"✅ '{cat_to_del}' মুছে ফেলা হয়েছে!", show_alert=True)
            bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=get_category_keyboard())
        return

    if call.data == "add_new_category":
        admin_state[chat_id] = {'step': 'add_single_category'}
        bot.answer_callback_query(call.id)
        bot.send_message(chat_id, "📁 **যে নতুন ক্যাটাগরি যুক্ত করতে চান তার নাম লিখে পাঠান:**\n(বাতিল করতে /cancel লিখুন)")
        return

@bot.message_handler(content_types=['text', 'photo', 'video', 'document'])
def handle_admin_inputs(message):
    chat_id = message.chat.id 
    if str(chat_id) != str(ADMIN_ID): return

    if message.text == "➕ Add Video":
        admin_state[chat_id] = {'step': 'category'}
        data = load_data(force_refresh=True)
        cats = data.get("categories", ["Top", "BPS5", "MOVIES", "DRAMA", "SERIES"])
        markup = types.
