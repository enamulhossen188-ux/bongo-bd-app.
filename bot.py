import subprocess
import sys

for pkg in ["pyTelegramBotAPI", "Flask", "Flask-CORS", "requests"]:
    try:
        __import__(pkg.replace("-", "_"))
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])

import telebot
from telebot import types
from flask import Flask, jsonify, make_response, send_file
from flask_cors import CORS
import threading
import json
import os
import time
import requests
import base64
from datetime import datetime

# ==================== কনফিগারেশন ====================
BOT_TOKEN = "8712538290:AAEtdSplx6_AvSeTtPYO9hl5ysqgbgYQQ88"
ADMIN_ID = "7255626228"
APP_URL = "https://bongo-bd-app-uixi.onrender.com"
DB_CHANNEL_ID = -1003902807907  # আপনার প্রাইভেট স্টোরেজ চ্যানেল
# ====================================================

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
app = Flask(__name__)
CORS(app)

cached_data = None
last_cache_time = 0
CACHE_DURATION = 300  # ৫ মিনিট পর পর চ্যানেল থেকে সিঙ্ক

admin_state = {}

def get_default_data():
    return {
        "users": [],
        "categories": ["BPS5", "MOVIES", "DRAMA", "SERIES", "COMING SOON"],
        "sub_categories": {
            "MOVIES": ["MOVIES", "HINDI"],
            "DRAMA": ["DRAMA", "FUNNY", "ROMANCE"],
            "SERIES": ["SULTAN SALAHUDDIN", "USER NOT FOUND", "REAL TIME LOVE"]
        },
        "ads": {"ad1": "https://google.com", "ad2": "https://google.com"},
        "welcome_video": "",
        "update_notice": "বর্তমানে কোনো নতুন আপডেট নেই। আমাদের সাথেই থাকুন!",
        "videos": []
    }

def get_db_file_content():
    try:
        chat = bot.get_chat(DB_CHANNEL_ID)
        pinned = chat.pinned_message
        if pinned and pinned.document:
            file_info = bot.get_file(pinned.document.file_id)
            content = bot.download_file(file_info.file_path)
            return json.loads(content.decode('utf-8'))
    except Exception as e:
        print("Telegram Pinned DB Read Error:", e)
    return None

def load_data(force_refresh=False):
    global cached_data, last_cache_time
    current_time = time.time()

    if not force_refresh and cached_data and (current_time - last_cache_time < CACHE_DURATION):
        return cached_data

    data = get_db_file_content()
    if data and "videos" in data:
        if "sub_categories" not in data:
            data["sub_categories"] = {}
        cached_data = data
        last_cache_time = current_time
        return cached_data

    if cached_data:
        return cached_data

    cached_data = get_default_data()
    return cached_data

def save_data(data):
    global cached_data, last_cache_time
    cached_data = data
    last_cache_time = time.time()
    try:
        json_bytes = json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8')
        sent_doc = bot.send_document(
            DB_CHANNEL_ID,
            ("db_backup_bot1.json", json_bytes),
            caption=f"📦 Database Update: {datetime.now().strftime('%d %b %Y, %I:%M:%S %p')}"
        )
        try:
            bot.pin_chat_message(DB_CHANNEL_ID, sent_doc.message_id, disable_notification=True)
        except Exception:
            pass
    except Exception as e:
        print("Telegram DB Save Error:", e)

def upload_thumb_securely(photo_id):
    try:
        file_info = bot.get_file(photo_id)
        downloaded = bot.download_file(file_info.file_path)

        try:
            b64_img = base64.b64encode(downloaded).decode('utf-8')
            res_imgbb = requests.post(
                "https://api.imgbb.com/1/upload",
                data={"key": "6d207e02198a847aa5a0a0333f00e615", "image": b64_img},
                timeout=15
            )
            if res_imgbb.status_code == 200:
                img_url = res_imgbb.json().get("data", {}).get("url")
                if img_url:
                    return img_url
        except Exception as e:
            print("ImgBB Upload Error:", e)

        try:
            res_catbox = requests.post(
                "https://catbox.moe/user/api.php",
                data={"reqtype": "fileupload"},
                files={"fileToUpload": ("thumb.jpg", downloaded, "image/jpeg")},
                timeout=20
            )
            if res_catbox.status_code == 200 and res_catbox.text.strip().startswith("http"):
                return res_catbox.text.strip()
        except Exception as e:
            print("Catbox Upload Error:", e)

    except Exception as e:
        print("Thumbnail Processing Error:", e)

    try:
        file_info = bot.get_file(photo_id)
        tg_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"
        return f"https://images.weserv.nl/?url={tg_url}&w=800&fit=cover&output=jpg&q=90"
    except Exception:
        return ""

@app.route('/api/data', methods=['GET'])
def get_app_data():
    data = load_data()
    resp = make_response(jsonify(data))
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
    resp.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return resp

@app.route('/')
def home():
    if os.path.exists('index.html'):
        return send_file('index.html')
    return "Bongo BD Server Live 24/7!"

def get_action_buttons():
    fresh_url = f"{APP_URL}?ts={int(datetime.now().timestamp())}"
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
    is_cs = video.get("is_coming_soon") or video.get("category") == "COMING SOON"
    if is_cs:
        return f"🗑 [📢 CS] {title[:25]}"
    if len(title) > 30:
        return f"🗑️ {title[:28]}.."
    return f"🗑️ {title}"

def get_delete_view_data(page=0):
    data = load_data()
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
        is_cs = v.get("is_coming_soon") or v.get("category") == "COMING SOON"
        tag = " [📢 COMING SOON]" if is_cs else ""
        text_msg += f"**{idx}.** {v.get('title')}{tag}\n"
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

# ==================== বাটন দিয়ে সম্পূর্ণ ক্যাটাগরি ম্যানেজমেন্ট ====================
def get_main_category_keyboard():
    data = load_data()
    cats = data.get("categories", ["BPS5", "MOVIES", "DRAMA", "SERIES", "COMING SOON"])
    markup = types.InlineKeyboardMarkup()

    for c in cats:
        markup.row(
            types.InlineKeyboardButton(f"📁 {c} (সাব-ক্যাটাগরি)", callback_data=f"managecat_{c}"),
            types.InlineKeyboardButton("🗑️ মুছুন", callback_data=f"delcat_{c}")
        )

    markup.add(types.InlineKeyboardButton("➕ নতুন মূল ক্যাটাগরি যোগ করুন", callback_data="add_new_category"))
    markup.add(types.InlineKeyboardButton("❌ বন্ধ করুন (Close)", callback_data="close_admin_menu"))
    return markup

def get_sub_category_keyboard(main_cat):
    data = load_data()
    sub_map = data.get("sub_categories", {})
    sub_list = sub_map.get(main_cat, [])

    markup = types.InlineKeyboardMarkup()
    for sc in sub_list:
        markup.add(types.InlineKeyboardButton(f"🗑️ Delete Sub: {sc}", callback_data=f"delsub_{main_cat}_{sc}"))

    markup.add(types.InlineKeyboardButton(f"➕ Add Sub-Category under {main_cat}", callback_data=f"addsub_{main_cat}"))
    markup.add(types.InlineKeyboardButton("⬅️ মূল ক্যাটাগরি লিস্টে ফিরুন", callback_data="back_to_main_cat"))
    return markup

@bot.my_chat_member_handler()
def handle_bot_blocked_or_unblocked(update: types.ChatMemberUpdated):
    user_id = update.chat.id
    new_status = update.new_chat_member.status
    data = load_data()
    users = data.get("users", [])

    if new_status in ["kicked", "left"]:
        if user_id in users:
            users.remove(user_id)
            data["users"] = users
            save_data(data)
    elif new_status == "member":
        if user_id not in users:
            users.append(user_id)
            data["users"] = users
            save_data(data)

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
        bot.send_message(chat_id, "🔄 আগের অসমাপ্ত কাজ বাতিল করা হয়েছে।", reply_markup=get_admin_keyboard())
    else:
        bot.send_message(chat_id, "বর্তমানে কোনো কাজ চালু নেই।", reply_markup=get_admin_keyboard())

@bot.message_handler(commands=['users', 'stats'])
def show_total_users(message):
    if str(message.chat.id) != str(ADMIN_ID): return
    data = load_data()
    user_list = data.get("users", [])
    active_users = []
    removed_any = False

    for uid in user_list:
        try:
            bot.send_chat_action(uid, 'typing')
            active_users.append(uid)
            time.sleep(0.02)
        except Exception:
            removed_any = True

    if removed_any:
        data["users"] = active_users
        save_data(data)

    msg_text = (
        "📊 **বটের ইউজার পরিসংখ্যান**\n\n"
        f"👥 মোট সক্রিয় ইউজার: **{len(active_users)}** জন\n"
        f"🎬 মোট ভিডিও: **{len(data.get('videos', []))}** টি\n"
        f"📁 মোট ক্যাটাগরি: **{len(data.get('categories', []))}** টি"
    )
    bot.send_message(message.chat.id, msg_text, parse_mode="Markdown")

@bot.message_handler(commands=['start'])
def send_welcome(message):
    data = load_data()
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
    else:
        bot.send_message(message.chat.id, "নাটক দেখতে উপরের 🎬 WATCH NOW বাটনে ক্লিক করুন।", reply_markup=types.ReplyKeyboardRemove())

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    chat_id = call.message.chat.id
    
    if call.data == "btn_update":
        bot.answer_callback_query(call.id)
        data = load_data()
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

    # ক্যাটাগরি মেনু নেভিগেশন
    if call.data == "back_to_main_cat":
        bot.edit_message_text(
            "📁 **ক্যাটাগরি ম্যানেজমেন্ট:**\nযেকোনো ক্যাটাগরির ভেতরে সাব-ক্যাটাগরি যোগ করতে বা মুছতে সিলেক্ট করুন:",
            chat_id, call.message.message_id, reply_markup=get_main_category_keyboard()
        )
        bot.answer_callback_query(call.id)
        return

    if call.data.startswith("managecat_"):
        main_c = call.data.replace("managecat_", "")
        bot.edit_message_text(
            f"📁 **'{main_c}' এর সাব-ক্যাটাগরি ম্যানেজমেন্ট:**\nনিচে থেকে সাব-ক্যাটাগরি মুছুন বা নতুন যোগ করুন:",
            chat_id, call.message.message_id, reply_markup=get_sub_category_keyboard(main_c)
        )
        bot.answer_callback_query(call.id)
        return

    if call.data == "add_new_category":
        admin_state[chat_id] = {'step': 'add_single_category'}
        bot.answer_callback_query(call.id)
        bot.send_message(chat_id, "📁 **যে নতুন মূল ক্যাটাগরি যুক্ত করতে চান তার নাম লিখে পাঠান:**\n(বাতিল করতে /cancel লিখুন)")
        return

    if call.data.startswith("addsub_"):
        main_c = call.data.replace("addsub_", "")
        admin_state[chat_id] = {'step': 'add_single_sub_category', 'main_cat': main_c}
        bot.answer_callback_query(call.id)
        bot.send_message(chat_id, f"📁 **'{main_c}' এর নিচে যে সাব-ক্যাটাগরি যুক্ত করতে চান তার নাম লিখে দিন:**\n(বাতিল করতে /cancel লিখুন)")
        return

    if call.data.startswith("delcat_"):
        cat_to_del = call.data.replace("delcat_", "")
        data = load_data(force_refresh=True)
        if cat_to_del in data.get("categories", []):
            data["categories"].remove(cat_to_del)
            data.get("sub_categories", {}).pop(cat_to_del, None)
            save_data(data)
            bot.answer_callback_query(call.id, f"✅ '{cat_to_del}' ক্যাটাগরি মুছে ফেলা হয়েছে!", show_alert=True)
            bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=get_main_category_keyboard())
        return

    if call.data.startswith("delsub_"):
        _, main_c, sub_c = call.data.split("_", 2)
        data = load_data(force_refresh=True)
        if main_c in data.get("sub_categories", {}) and sub_c in data["sub_categories"][main_c]:
            data["sub_categories"][main_c].remove(sub_c)
            save_data(data)
            bot.answer_callback_query(call.id, f"✅ '{sub_c}' মুছে ফেলা হয়েছে!", show_alert=True)
            bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=get_sub_category_keyboard(main_c))
        return

    if call.data.startswith("delpage_"):
        page = int(call.data.split("_")[1])
        txt, kb = get_delete_view_data(page)
        if kb:
            bot.edit_message_text(txt, chat_id, call.message.message_id, reply_markup=kb, parse_mode="Markdown")
        bot.answer_callback_query(call.id)
        return

    if call.data.startswith("delvid_"):
        parts = call.data.split("_")
        del_id = parts[1]
        page = int(parts[2]) if len(parts) > 2 else 0

        data = load_data(force_refresh=True)
        videos = data.get("videos", [])
        new_videos = [v for v in videos if str(v.get('id')) != str(del_id)]
        data["videos"] = new_videos
        save_data(data)

        bot.answer_callback_query(call.id, "✅ সফলভাবে ডিলিট করা হয়েছে!", show_alert=True)
        txt, kb = get_delete_view_data(page)
        if kb:
            bot.edit_message_text(txt, chat_id, call.message.message_id, reply_markup=kb, parse_mode="Markdown")
        else:
            bot.edit_message_text("❌ আর কোনো ভিডিও বা পোস্ট নেই!", chat_id, call.message.message_id)
        return

@bot.message_handler(content_types=['text', 'photo', 'video', 'document'])
def handle_admin_inputs(message):
    chat_id = message.chat.id 
    if str(chat_id) != str(ADMIN_ID): return

    if message.text == "➕ Add Video":
        admin_state[chat_id] = {'step': 'category'}
        data = load_data()
        cats = data.get("categories", ["BPS5", "MOVIES", "DRAMA", "SERIES"])
        markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        for i in range(0, len(cats), 2):
            markup.row(*[types.KeyboardButton(c) for c in cats[i:i+2]])
        bot.send_message(chat_id, "📁 **ভিডিওর মূল ক্যাটাগরি বেছে নিন:**", reply_markup=markup)
        return

    elif message.text == "📢 Add Coming Soon":
        admin_state[chat_id] = {'step': 'cs_title', 'category': 'COMING SOON', 'is_coming_soon': True}
        bot.send_message(chat_id, "🎬 **কামিং সুন ভিডিওর টাইটেল লিখুন:**", reply_markup=types.ReplyKeyboardRemove())
        return

    elif message.text == "🔕 Delete Video":
        txt, kb = get_delete_view_data(0)
        if not kb:
            bot.send_message(chat_id, "❌ কোনো ভিডিও বা কামিং সুন পোস্ট পাওয়া যায়নি!", reply_markup=get_admin_keyboard())
            return
        bot.send_message(chat_id, txt, reply_markup=kb, parse_mode="Markdown")
        return

    elif message.text == "📊 Total Users":
        show_total_users(message)
        return

    elif message.text == "📁 Set Category":
        bot.send_message(
            chat_id,
            "📁 **ক্যাটাগরি ও সাব-ক্যাটাগরি ম্যানেজমেন্ট:**\nএখানে সরাসরি বাটন থেকে উপরে ও নিচের সব ক্যাটাগরি ম্যানেজ করুন:",
            reply_markup=get_main_category_keyboard()
        )
        return

    elif message.text == "🎯 Set Ads Link":
        admin_state[chat_id] = {'step': 'ad_1'}
        bot.send_message(chat_id, "🎯 **Task 1 এর এড লিংক (URL) পাঠান:**\n(বাতিল করতে /cancel লিখুন)", reply_markup=types.ReplyKeyboardRemove())
        return

    elif message.text == "🎥 Set Welcome Video":
        admin_state[chat_id] = {'step': 'welcome_video'}
        bot.send_message(chat_id, "🎥 **স্টার্টের সময় যে ভিডিওটি শো করবে সেটি পাঠান:**")
        return

    elif message.text == "🔔 Set Video Update":
        admin_state[chat_id] = {'step': 'set_video_update'}
        data = load_data()
        current_up = data.get("update_notice", "বর্তমানে কোনো নতুন আপডেট নেই। আমাদের সাথেই থাকুন!")
        bot.send_message(
            chat_id, 
            f"🔔 **বর্তমানে সেভ করা ভিডিও আপডেট:**\n`{current_up}`\n\nইউজাররা যখন 'VIDEO UPDATE' বাটনে চাপ দিবে তখন কী মেসেজ দেখাবে তা লিখে পাঠান:\n(বাতিল করতে /cancel লিখুন)",
            parse_mode="Markdown",
            reply_markup=types.ReplyKeyboardRemove()
        )
        return

    elif message.text == "📢 BOT NOTICE":
        admin_state[chat_id] = {'step': 'notice_input'}
        bot.send_message(
            chat_id, 
            "🖼 **নোটিশের ছবি (Photo) পাঠান (ছবির সাথে ক্যাপশনে লেখা দিতে পারেন) অথবা শুধু মেসেজ লিখুন:**\n(বাতিল করতে /cancel লিখুন)", 
            reply_markup=types.ReplyKeyboardRemove()
        )
        return

    if chat_id not in admin_state: return
    step = admin_state[chat_id].get('step')

    # মূল ক্যাটাগরি তৈরি
    if step == 'add_single_category' and message.text:
        new_c = message.text.strip().upper()
        data = load_data(force_refresh=True)
        cats = data.get("categories", [])
        if new_c and new_c not in cats:
            cats.append(new_c)
            data["categories"] = cats
            save_data(data)
            del admin_state[chat_id]
            bot.send_message(chat_id, f"✅ **'{new_c}' মূল ক্যাটাগরি সফলভাবে যুক্ত হয়েছে!**", reply_markup=get_admin_keyboard())
        else:
            bot.send_message(chat_id, "⚠️ এই ক্যাটাগরি ইতিমধ্যে রয়েছে অথবা ভুল নাম দিয়েছেন।")

    # সাব-ক্যাটাগরি তৈরি
    elif step == 'add_single_sub_category' and message.text:
        sub_c = message.text.strip().upper()
        main_c = admin_state[chat_id]['main_cat']
        data = load_data(force_refresh=True)
        sub_map = data.setdefault("sub_categories", {})
        sub_list = sub_map.setdefault(main_c, [])
        if sub_c not in sub_list:
            sub_list.append(sub_c)
            save_data(data)
            del admin_state[chat_id]
            bot.send_message(chat_id, f"✅ **'{main_c}' এর নিচে '{sub_c}' সাব-ক্যাটাগরি যুক্ত হয়েছে!**", reply_markup=get_admin_keyboard())
        else:
            bot.send_message(chat_id, "⚠️ এই সাব-ক্যাটাগরি আগে থেকেই রয়েছে।")

    # ভিডিও আপলোডে ক্যাটাগরি নির্বাচন
    elif step == 'category' and message.text:
        chosen_cat = message.text.strip().upper()
        admin_state[chat_id]['category'] = chosen_cat
        data = load_data()
        sub_list = data.get("sub_categories", {}).get(chosen_cat, [])

        if sub_list:
            admin_state[chat_id]['step'] = 'sub_category'
            markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
            for sc in sub_list:
                markup.add(types.KeyboardButton(sc))
            bot.send_message(chat_id, f"📁 **{chosen_cat} এর সাব-ক্যাটাগরি বেছে নিন:**", reply_markup=markup)
        else:
            admin_state[chat_id]['sub_category'] = ''
            admin_state[chat_id]['step'] = 'title'
            bot.send_message(chat_id, "🎬 **ভিডিওর নাম (Title) লিখুন:**", reply_markup=types.ReplyKeyboardRemove())

    # ভিডিও আপলোডে সাব-ক্যাটাগরি নির্বাচন
    elif step == 'sub_category' and message.text:
        admin_state[chat_id]['sub_category'] = message.text.strip().upper()
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
        file_id = message.video.file_id if message.video else message.document.file_id
        data = load_data(force_refresh=True)
        new_video = {
            "id": int(time.time()),
            "category": admin_state[chat_id]['category'],
            "sub_category": admin_state[chat_id].get('sub_category', ''),
            "title": admin_state[chat_id]['title'],
            "thumb": admin_state[chat_id]['thumb'],
            "file_id": file_id,
            "date": datetime.now().strftime("%d %B %Y"),
            "time": datetime.now().strftime("%I:%M %p")
        }
        data.setdefault("videos", []).insert(0, new_video)
        save_data(data)
        del admin_state[chat_id]
        bot.reply_to(message, "🎉 **ভিডিও সফলভাবে আপলোড হয়েছে!**", reply_markup=get_admin_keyboard())

    elif step == 'set_video_update' and message.text:
        new_notice = message.text.strip()
        data = load_data(force_refresh=True)
        data["update_notice"] = new_notice
        save_data(data)
        del admin_state[chat_id]
        bot.send_message(chat_id, f"✅ **ভিডিও আপডেট সফলভাবে সেট করা হয়েছে!**\n\n\"{new_notice}\"", reply_markup=get_admin_keyboard())
        return

    elif step == 'ad_1' and message.text:
        admin_state[chat_id]['ad1'] = message.text.strip()
        admin_state[chat_id]['step'] = 'ad_2'
        bot.send_message(chat_id, "🎯 **এবার Task 2 এর এড লিংক (URL) পাঠান:**")

    elif step == 'ad_2' and message.text:
        data = load_data(force_refresh=True)
        data["ads"] = {
            "ad1": admin_state[chat_id]['ad1'],
            "ad2": message.text.strip()
        }
        save_data(data)
        del admin_state[chat_id]
        bot.send_message(chat_id, "✅ **বিজ্ঞাপনের লিংক দুটি আপডেট হয়েছে!**", reply_markup=get_admin_keyboard())

    elif step == 'notice_input' and (message.photo or message.text):
        data = load_data()
        user_list = data.get("users", [])
        bot.send_message(chat_id, f"⏳ **{len(user_list)} জন ইউজারের কাছে নোটিশ পাঠানো শুরু হয়েছে...**", reply_markup=get_admin_keyboard())
        del admin_state[chat_id]

        fresh_url = f"{APP_URL}?ts={int(datetime.now().timestamp())}"
        notice_markup = types.InlineKeyboardMarkup()
        btn_watch = types.InlineKeyboardButton("🎬 WATCH NOW", web_app=types.WebAppInfo(url=fresh_url))
        notice_markup.add(btn_watch)

        is_photo = bool(message.photo)
        photo_id = message.photo[-1].file_id if is_photo else None
        caption_text = message.caption or (message.text if not is_photo else "")

        sent = 0
        for uid in user_list:
            try:
                if is_photo:
                    if caption_text:
                        bot.send_photo(uid, photo_id, caption=caption_text, reply_markup=notice_markup)
                    else:
                        bot.send_photo(uid, photo_id, reply_markup=notice_markup)
                else:
                    bot.send_message(uid, f"📢 **নোটিশ:**\n\n{caption_text}", reply_markup=notice_markup, parse_mode="Markdown")
                sent += 1
                time.sleep(0.04)
            except Exception:
                pass
        bot.send_message(chat_id, f"✅ মোট **{sent}** জন ইউজারের কাছে নোটিশ পাঠানো সম্পন্ন!")

    elif step == 'cs_title' and message.text:
        admin_state[chat_id]['title'] = message.text.strip()
        admin_state[chat_id]['step'] = 'cs_notice'
        bot.send_message(chat_id, "📝 **পপ-আপে কী নোটিশ শো করবে তা লিখে দিন:**")

    elif step == 'cs_notice' and message.text:
        admin_state[chat_id]['notice'] = message.text.strip()
        admin_state[chat_id]['step'] = 'cs_thumb'
        bot.send_message(chat_id, "🖼 **কামিং সুন পোস্টের থাম্বনেইল ছবি পাঠান:**")

    elif step == 'cs_thumb' and (message.photo or message.text):
        if message.photo:
            bot.send_chat_action(chat_id, 'upload_photo')
            thumb_url = upload_thumb_securely(message.photo[-1].file_id)
        else:
            thumb_url = message.text.strip()

        data = load_data(force_refresh=True)
        new_item = {
            "id": int(time.time()),
            "category": "COMING SOON",
            "sub_category": "",
            "is_coming_soon": True,
            "title": admin_state[chat_id]['title'],
            "notice": admin_state[chat_id]['notice'],
            "thumb": thumb_url,
            "date": datetime.now().strftime("%d %B %Y"),
            "time": datetime.now().strftime("%I:%M %p")
        }
        data.setdefault("videos", []).insert(0, new_item)
        save_data(data)
        del admin_state[chat_id]
        bot.send_message(chat_id, "✅ **কামিং সুন পোস্ট সফলভাবে যুক্ত হয়েছে!**", reply_markup=get_admin_keyboard())

    elif step == 'welcome_video' and message.video:
        data = load_data(force_refresh=True)
        data['welcome_video'] = message.video.file_id
        save_data(data)
        del admin_state[chat_id]
        bot.send_message(chat_id, "✅ **ওয়েলকাম ভিডিও সেট হয়েছে!**", reply_markup=get_admin_keyboard())

def run_bot():
    while True:
        try:
            bot.polling(none_stop=True, interval=0, timeout=20)
        except Exception as e:
            print("Bot polling reconnecting...", e)
            time.sleep(3)

if __name__ == "__main__":
    t = threading.Thread(target=run_bot)
    t.daemon = True
    t.start()
    
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
