import telebot
from telebot import types
from flask import Flask, jsonify, make_response
from flask_cors import CORS
import threading
import json
import os
import time
import requests
from datetime import datetime

# আপনার নতুন টোকেন ও আইডি
BOT_TOKEN = "8712538290:AAHskUrqeMrwwAYtGR7PDamWRt9EMEOwopA"
ADMIN_ID = "7255626228"

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)
CORS(app)

# JSONBin কনফিগারেশন
BIN_ID = "6abbadacac6210605a01bb77"
JSONBIN_API_KEY = "$2a$10$YXJkOPYEpFL1pS32JSWh7O5Zs7VMzulVbyfBwxBkvPOQ9EY1m0/ri"

BIN_URL = f"https://api.jsonbin.io/v3/b/{BIN_ID}"
HEADERS = {
    "X-Master-Key": JSONBIN_API_KEY,
    "Content-Type": "application/json"
}

# --- ইন-মেমোরি ক্যাশ (লাখ লাখ ইউজারেও ডাটাবেজ ফাস্ট রাখার জন্য) ---
cached_data = None
last_cache_time = 0
CACHE_DURATION = 600  # ১০ মিনিট (৬০০ সেকেন্ড) পর পর ডাটাবেজ আপডেট নেবে

broadcast_history = []
admin_state = {}

def load_data(force_refresh=False):
    global cached_data, last_cache_time
    current_time = time.time()

    # মেমোরিতে ডাটা থাকলে সেখান থেকেই ইনস্ট্যান্ট রিটার্ন করবে
    if not force_refresh and cached_data and (current_time - last_cache_time < CACHE_DURATION):
        return cached_data

    try:
        r = requests.get(f"{BIN_URL}/latest", headers=HEADERS, timeout=10)
        if r.status_code == 200:
            cached_data = r.json().get("record", {})
            last_cache_time = current_time
            return cached_data
    except Exception as e:
        print("JSONBin Read Error:", e)

    if cached_data:
        return cached_data

    return {
        "users": [],
        "categories": ["BPS5", "MOVIES", "DRAMA", "SERIES", "COMING SOON"],
        "ads": {"ad1": "https://google.com", "ad2": "https://google.com"},
        "welcome_video": "",
        "videos": []
    }

def save_data(data):
    global cached_data, last_cache_time
    cached_data = data
    last_cache_time = time.time()
    try:
        requests.put(BIN_URL, headers=HEADERS, json=data, timeout=10)
    except Exception as e:
        print("JSONBin Save Error:", e)

# সুপার ফাস্ট এপিআই (মেমোরি থেকে ডাটা পাঠায়)
@app.route('/api/data', methods=['GET'])
def get_app_data():
    data = load_data()
    resp = make_response(jsonify(data))
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
    resp.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return resp

@app.route('/')
def home():
    return "Bongo BD Bot Server Live 24/7!"

def get_action_buttons():
    # আপনার নতুন GitHub Pages এর ফ্রেশ লিঙ্ক যুক্ত করা হয়েছে
    fresh_url = f"https://enamulhossen188-ux.github.io/bongo-bd-app/index.html?ts={int(datetime.now().timestamp())}"
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
    b8 = types.KeyboardButton("📢 BOT NOTICE")
    markup.add(b1, b2, b3, b4, b5, b6, b7, b8)
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
        "🛠️ **Bongo BD এডমিন প্যানেল সচল করা হয়েছে:**", 
        reply_markup=get_admin_keyboard(),
        parse_mode="Markdown"
    )

@bot.message_handler(commands=['cancel'])
def cancel_process(message):
    chat_id = message.chat.id
    if chat_id in admin_state:
        del admin_state[chat_id]
        bot.send_message(chat_id, "🔄 আগের অসমাপ্ত কাজ বাতিল করা হয়েছে।", reply_markup=get_admin_keyboard() if str(chat_id) == str(ADMIN_ID) else types.ReplyKeyboardRemove())
    else:
        bot.send_message(chat_id, "বর্তমানে কোনো কাজ চালু নেই।", reply_markup=get_admin_keyboard() if str(chat_id) == str(ADMIN_ID) else None)

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

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    if call.data == "btn_update":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "🔔 **আপডেট নোটিফিকেশন:** নতুন সব নাটক বা পর্ব খুব দ্রুত মিনি অ্যাপে যুক্ত করা হচ্ছে। সাথে থাকুন!")
    elif call.data == "btn_help":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "💡 **যেভাবে ভিডিও ডাউনলোড করবেন:**\n১. WATCH NOW বাটনে ক্লিক করে অ্যাপে ঢুকুন।\n২. পছন্দের ভিডিও সিলেক্ট করুন।\n৩. দুটি বিজ্ঞাপন ১০ সেকেন্ড করে ভিজিট করুন।\n৪. ডাউনলোড বাটনে চাপ দিলে ভিডিও ইনবক্সে চলে আসবে!")

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
        bot.send_message(chat_id, "📁 **ভিডিওর ক্যাটাগরি বেছে নিন:**", reply_markup=markup)
        return

    # কামিং সুন পোস্ট অ্যাড করার অপশন
    elif message.text == "📢 Add Coming Soon":
        admin_state[chat_id] = {'step': 'cs_title', 'category': 'COMING SOON', 'is_coming_soon': True}
        bot.send_message(chat_id, "🎬 **কামিং সুন ভিডিওর টাইটেল লিখুন (যেমন: Bachelor Point Season 5 Ep 121-128):**", reply_markup=types.ReplyKeyboardRemove())
        return

    # ভিডিও ডিলিট করার বাটন হ্যান্ডলার
    elif message.text == "🔕 Delete Video":
        data = load_data()
        videos = data.get("videos", [])
        if not videos:
            bot.send_message(chat_id, "❌ কোনো ভিডিও পাওয়া যায়নি!", reply_markup=get_admin_keyboard())
            return
        admin_state[chat_id] = {'step': 'delete_video'}
        msg_txt = "🗑️ **যে ভিডিওটি ডিলিট করতে চান তার ID লিখে পাঠান:**\n\n"
        for v in videos[:15]:
            msg_txt += f"🆔 `{v['id']}` - {v['title']}\n"
        msg_txt += "\n(বাতিল করতে /cancel লিখুন)"
        bot.send_message(chat_id, msg_txt, parse_mode="Markdown", reply_markup=types.ReplyKeyboardRemove())
        return

    # ক্যাটাগরি সেট করার বাটন হ্যান্ডলার
    elif message.text == "📁 Set Category":
        admin_state[chat_id] = {'step': 'set_category'}
        data = load_data()
        cats = data.get("categories", ["BPS5", "MOVIES", "DRAMA", "SERIES", "COMING SOON"])
        bot.send_message(
            chat_id,
            f"📁 **বর্তমান ক্যাটাগরি তালিকা:**\n`{', '.join(cats)}`\n\nনতুন ক্যাটাগরি তালিকা কমা (`,`) দিয়ে লিখে পাঠান।\n(বাতিল করতে /cancel লিখুন)",
            parse_mode="Markdown",
            reply_markup=types.ReplyKeyboardRemove()
        )
        return

    # এড লিংক সেট করার বাটন হ্যান্ডলার
    elif message.text == "🎯 Set Ads Link":
        admin_state[chat_id] = {'step': 'ad_1'}
        bot.send_message(chat_id, "🎯 **Task 1 এর এড লিংক (URL) পাঠান:**\n(বাতিল করতে /cancel লিখুন)", reply_markup=types.ReplyKeyboardRemove())
        return

    # নোটিশ ব্রডকাস্ট বাটন হ্যান্ডলার
    elif message.text == "📢 BOT NOTICE":
        admin_state[chat_id] = {'step': 'notice_msg'}
        bot.send_message(chat_id, "📢 **সব ইউজারের কাছে পাঠানোর জন্য নোটিশ লিখুন:**\n(বাতিল করতে /cancel লিখুন)", reply_markup=types.ReplyKeyboardRemove())
        return

    elif message.text == "📊 Total Users":
        show_total_users(message)
        return

    elif message.text == "🎥 Set Welcome Video":
        admin_state[chat_id] = {'step': 'welcome_video'}
        bot.send_message(chat_id, "🎥 **স্টার্টের সময় যে ভিডিওটি শো করবে সেটি পাঠান:**")
        return

    if chat_id not in admin_state: return
    step = admin_state[chat_id].get('step')

    # Delete Video সম্পন্ন করা
    if step == 'delete_video' and message.text:
        del_id = message.text.strip()
        data = load_data()
        videos = data.get("videos", [])
        new_videos = [v for v in videos if str(v.get('id')) != str(del_id)]
        if len(new_videos) < len(videos):
            data["videos"] = new_videos
            save_data(data)
            del admin_state[chat_id]
            bot.send_message(chat_id, f"✅ ভিডিও ID `{del_id}` সফলভাবে মুছে ফেলা হয়েছে!", parse_mode="Markdown", reply_markup=get_admin_keyboard())
        else:
            bot.send_message(chat_id, "❌ এই ID-র ভিডিও খুঁজে পাওয়া যায়নি। সঠিক ID দিন বা /cancel লিখুন:")

    # Set Category সম্পন্ন করা
    elif step == 'set_category' and message.text:
        new_cats = [c.strip() for c in message.text.split(",") if c.strip()]
        if new_cats:
            data = load_data()
            data["categories"] = new_cats
            save_data(data)
            del admin_state[chat_id]
            bot.send_message(chat_id, f"✅ **ক্যাটাগরি আপডেট সম্পন্ন!**\nনতুন ক্যাটাগরি: `{', '.join(new_cats)}`", parse_mode="Markdown", reply_markup=get_admin_keyboard())
        else:
            bot.send_message(chat_id, "❌ সঠিক ফরম্যাটে ক্যাটাগরি নাম লিখুন।")

    # Set Ads Link সম্পন্ন করা
    elif step == 'ad_1' and message.text:
        admin_state[chat_id]['ad1'] = message.text.strip()
        admin_state[chat_id]['step'] = 'ad_2'
        bot.send_message(chat_id, "🎯 **এবার Task 2 এর এড লিংক (URL) পাঠান:**")

    elif step == 'ad_2' and message.text:
        data = load_data()
        data["ads"] = {
            "ad1": admin_state[chat_id]['ad1'],
            "ad2": message.text.strip()
        }
        save_data(data)
        del admin_state[chat_id]
        bot.send_message(chat_id, "✅ **বিজ্ঞাপনের লিংক দুটি আপডেট হয়েছে!**", reply_markup=get_admin_keyboard())

    # BOT NOTICE ব্রডকাস্ট সম্পন্ন করা
    elif step == 'notice_msg' and message.text:
        notice = message.text.strip()
        data = load_data()
        user_list = data.get("users", [])
        bot.send_message(chat_id, f"⏳ **{len(user_list)} জন ইউজারের কাছে নোটিশ পাঠানো হচ্ছে...**", reply_markup=get_admin_keyboard())
        del admin_state[chat_id]
        
        sent = 0
        for uid in user_list:
            try:
                bot.send_message(uid, f"📢 **নোটিশ:**\n\n{notice}")
                sent += 1
                time.sleep(0.04)
            except Exception:
                pass
        bot.send_message(chat_id, f"✅ মোট **{sent}** জন ইউজারের কাছে নোটিশ পাঠানো সম্পন্ন!")

    # কামিং সুন তথ্য প্রসেস করা
    elif step == 'cs_title' and message.text:
        admin_state[chat_id]['title'] = message.text.strip()
        admin_state[chat_id]['step'] = 'cs_notice'
        bot.send_message(chat_id, "📝 **পপ-আপে কী নোটিশ শো করবে তা লিখে দিন (যেমন: 'পর্ব ১২১ থেকে ১২৮ আসবে ২০ অক্টোবরের ভেতর...'):**")

    elif step == 'cs_notice' and message.text:
        admin_state[chat_id]['notice'] = message.text.strip()
        admin_state[chat_id]['step'] = 'cs_thumb'
        bot.send_message(chat_id, "🖼 **কামিং সুন পোস্টের থাম্বনেইল ছবি পাঠান:**")

    elif step == 'cs_thumb' and (message.photo or message.text):
        if message.photo:
            bot.send_chat_action(chat_id, 'upload_photo')
            file_info = bot.get_file(message.photo[-1].file_id)
            downloaded = bot.download_file(file_info.file_path)
            res = requests.post("https://catbox.moe/user/api.php", data={"reqtype": "fileupload"}, files={"fileToUpload": ("thumb.jpg", downloaded, "image/jpeg")})
            thumb_url = res.text.strip() if res.status_code == 200 else f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"
        else:
            thumb_url = message.text.strip()

        data = load_data()
        new_item = {
            "id": len(data.get('videos', [])) + 1,
            "category": "COMING SOON",
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
        bot.send_message(chat_id, "✅ **কামিং সুন পোস্ট সফলভাবে যুক্ত হয়েছে! ইউজাররা এতে ক্লিক করলে পপ-আপ দেখতে পাবে।**", reply_markup=get_admin_keyboard())

    # সাধারণ ভিডিও আপলোড লজিক
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
            file_info = bot.get_file(message.photo[-1].file_id)
            downloaded = bot.download_file(file_info.file_path)
            res = requests.post("https://catbox.moe/user/api.php", data={"reqtype": "fileupload"}, files={"fileToUpload": ("thumb.jpg", downloaded, "image/jpeg")})
            thumb_url = res.text.strip() if res.status_code == 200 else f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"
        else:
            thumb_url = message.text.strip()

        admin_state[chat_id]['thumb'] = thumb_url
        admin_state[chat_id]['step'] = 'video'
        bot.send_message(chat_id, "📥 **ভিডিও ফাইলটি পাঠান:**")

    elif step == 'video' and (message.video or message.document):
        file_id = message.video.file_id if message.video else message.document.file_id
        data = load_data()
        new_video = {
            "id": len(data.get('videos', [])) + 1,
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
        bot.reply_to(message, "🎉 **ভিডিও সফলভাবে আপলোড হয়েছে!**", reply_markup=get_admin_keyboard())

    elif step == 'welcome_video' and message.video:
        data = load_data()
        data['welcome_video'] = message.video.file_id
        save_data(data)
        del admin_state[chat_id]
        bot.send_message(chat_id, "✅ **ওয়েলকাম ভিডিও সেট হয়েছে!**", reply_markup=get_admin_keyboard())

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    t = threading.Thread(target=run_flask)
    t.daemon = True
    t.start()
    bot.infinity_polling(skip_pending=True, allowed_updates=['message', 'callback_query', 'my_chat_member', 'chat_member'])
