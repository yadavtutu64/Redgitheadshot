try:
    import telebot
except ModuleNotFoundError:
    raise SystemExit("Required module 'telebot' not found. Install it with: pip install pyTelegramBotAPI")

import requests
import json
import io
import os
import re
import time
import threading
from concurrent.futures import ThreadPoolExecutor

# --- CONFIGURATION ---
API_TOKEN = '8847226762:AAHTRkQpHyUeExS4smh8U07tZZgrYQDY6aU'
ADMIN_ID = 5587310035  # Replace with your actual Telegram User ID
bot = telebot.TeleBot(API_TOKEN, threaded=True, num_threads=10)

# Set Bot Commands Menu
bot.set_my_commands([
    telebot.types.BotCommand("start", "Initialize System Interface"),
    telebot.types.BotCommand("batchlist", "Download Global Batch List"),
    telebot.types.BotCommand("idall", "Turbo Sync All Batches"),
    telebot.types.BotCommand("updateall", "Force Update Global Database"),
    telebot.types.BotCommand("htmlall", "Generate All HTML Interfaces"),
    telebot.types.BotCommand("send", "Send Batch Content to Group (Admin Only)"),
    telebot.types.BotCommand("sendtgroup", "Premium Batch Deployment (Photo Style)"),
    telebot.types.BotCommand("clearchat", "Purge Recent Messages (Admin Only)"),
    telebot.types.BotCommand("broadcast", "Send Message to All Users (Admin)"),
    telebot.types.BotCommand("status", "System Diagnostic Report"),
    telebot.types.BotCommand("stopall", "Emergency System Shutdown")
])

# --- UTILITIES ---
def is_admin(user_id):
    return user_id == ADMIN_ID

def save_user(user_id):
    """Stores user ID for broadcasting"""
    filename = "users.json"
    users = []
    if os.path.exists(filename):
        try:
            with open(filename, "r") as f: users = json.load(f)
        except: pass
    if user_id not in users:
        users.append(user_id)
        with open(filename, "w") as f: json.dump(users, f)

def safe_call(func, *args, **kwargs):
    """Wrapper to handle Telegram Rate Limits (Error 429)"""
    max_retries = 5
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except telebot.apihelper.ApiTelegramException as e:
            if e.error_code == 429:
                wait_time = int(re.search(r'\d+', e.description).group()) + 2
                print(f"⚠️ [RATE_LIMIT] Sleeping for {wait_time}s...")
                time.sleep(wait_time)
                continue
            raise e
        except Exception as e:
            if attempt == max_retries - 1: raise e
            time.sleep(2)
    return None

# KGS API Base URL
API_BASE = "https://api.thescholarverse.site/kgs/api"
KGS_DIR = "kgs"

if not os.path.exists(KGS_DIR):
    os.makedirs(KGS_DIR)

# --- CORE UTILITIES ---

def fetch_json(url):
    """Fast fetch helper with retries and optimized timeout"""
    for _ in range(3):
        try:
            response = requests.get(url, timeout=15)
            if response.status_code == 200:
                return response.json()
        except:
            time.sleep(0.5)
    return None

def update_master_json(batch_data):
    """Saves/Updates batch data in master_data.json"""
    filename = "master_data.json"
    all_data = []
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                all_data = json.load(f)
        except: pass

    batch_id = str(batch_data.get('id'))
    found_idx = -1
    for i, item in enumerate(all_data):
        if str(item.get('id')) == batch_id:
            found_idx = i
            break

    if found_idx != -1: all_data[found_idx] = batch_data
    else: all_data.append(batch_data)

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(all_data, f, indent=4, ensure_ascii=False)

def get_saved_ids():
    """Returns list of cached batch IDs"""
    return [f.replace('id', '').replace('.json', '') for f in os.listdir(KGS_DIR) if f.endswith('.json')]

def generate_html_string(batch_data, bid):
    """Generates the modern HTML interface string"""
    title = batch_data.get('title', 'Unknown Batch')
    image = batch_data.get('image', '')

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title} - KGS-X</title>
        <style>
            :root {{ --bg: #0a0a0c; --card-bg: #141417; --accent: #00d4ff; --text: #e0e0e0; --secondary: #888888; --hover: #1e1e24; }}
            body {{ background: var(--bg); color: var(--text); font-family: 'Segoe UI', sans-serif; margin: 0; padding: 10px; }}
            .header {{ text-align: center; margin-bottom: 20px; padding: 20px; background: var(--card-bg); border-radius: 15px; border: 1px solid #333; }}
            .header img {{ max-width: 150px; border-radius: 10px; margin-bottom: 10px; box-shadow: 0 0 20px rgba(0,212,255,0.2); }}
            .subject-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 10px; margin-bottom: 20px; }}
            .subject-btn {{ background: var(--card-bg); border: 1px solid #333; color: var(--text); padding: 15px; border-radius: 10px; text-align: center; cursor: pointer; transition: 0.3s; min-height: 60px; display: flex; align-items: center; justify-content: center; }}
            .subject-btn:hover {{ border-color: var(--accent); background: var(--hover); }}
            .subject-btn.active {{ background: var(--accent); color: #000; font-weight: bold; border-color: var(--accent); }}
            .video-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 12px; margin-top: 20px; }}
            .video-card {{ background: var(--card-bg); border-radius: 10px; overflow: hidden; border: 1px solid #222; display: flex; flex-direction: column; transition: 0.3s; }}
            .video-card:hover {{ border-color: var(--accent); transform: translateY(-3px); }}
            .thumbnail {{ position: relative; width: 100%; padding-top: 56.25%; background: #1a1a1e; }}
            .thumbnail img {{ position: absolute; top: 0; left: 0; width: 100%; height: 100%; object-fit: cover; }}
            .info {{ padding: 10px; flex-grow: 1; }}
            .info h3 {{ font-size: 0.85rem; margin: 0 0 8px 0; height: 2.8em; overflow: hidden; color: #fff; }}
            .btns {{ display: grid; grid-template-columns: 1fr 1fr; gap: 5px; }}
            .btn {{ padding: 6px; border-radius: 5px; text-decoration: none; font-size: 0.75rem; font-weight: bold; text-align: center; }}
            .btn-n {{ background: #333; color: white; }}
            .btn-h {{ background: var(--accent); color: #000; }}
            .btn-p {{ background: #ff9f43; color: #000; grid-column: span 2; margin-top: 2px; }}
            .btn-s {{ background: #1dd1a1; color: #000; margin-bottom: 10px; width: 100%; display: block; }}
            .content-section {{ display: none; animation: fadeIn 0.4s ease; }}
            @keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(10px); }} to {{ opacity: 1; transform: translateY(0); }} }}
            #placeholder {{ text-align: center; padding: 40px; color: var(--secondary); background: var(--card-bg); border-radius: 15px; border: 1px dashed #444; }}
        </style>
    </head>
    <body>
        <div class="header"><img src="{image}" onerror="this.style.display='none'"><h1>{title}</h1><p>ID: {bid} | Generated: {time.ctime()}</p></div>
        <div class="subject-grid">
    """
    for i, room in enumerate(batch_data.get('classrooms', [])):
        html_content += f'<div class="subject-btn" onclick="showSubj(\'s-{i}\', this)">{room.get("name", "Untitled")}</div>'

    html_content += '</div><div id="placeholder">Select a subject to initialize stream protocols</div><div id="content">'

    for i, room in enumerate(batch_data.get('classrooms', [])):
        html_content += f'<div id="s-{i}" class="content-section">'

        # Add Subject-level Notes
        subj_notes = room.get('subject_notes', [])
        if subj_notes:
            html_content += '<div style="margin-bottom: 20px; padding: 15px; background: var(--card-bg); border-radius: 10px; border: 1px solid #333;">'
            html_content += '<h3 style="margin-top: 0; color: var(--accent); font-size: 1rem;">📚 SUBJECT RESOURCES</h3>'
            for sn in subj_notes:
                html_content += f'<a href="{sn.get("url")}" class="btn btn-s" target="_blank">📄 {sn.get("title", "SUBJECT NOTES")}</a>'
            html_content += '</div>'

        html_content += '<div class="video-grid">'
        for v in room.get('video_content', []):
            t = v.get('name') or v.get('title', 'Untitled Resource')
            img = v.get('thumbnail') or v.get('image') or 'https://placehold.co/400x225/141417/00d4ff?text=KGS+X'
            html_content += f"""
            <div class="video-card">
                <div class="thumbnail"><img src="{img}" onerror="this.src='https://placehold.co/400x225/141417/00d4ff?text=KGS+X'"></div>
                <div class="info"><h3>{t}</h3><div class="btns">
                    {"<a href='"+v.get('video_url','')+"' class='btn btn-n' target='_blank'>NORMAL</a>" if v.get('video_url') else ""}
                    {"<a href='"+v.get('hd_video_url','')+"' class='btn btn-h' target='_blank'>HD TURBO</a>" if v.get('hd_video_url') else ""}
            """
            for p in (v.get('pdfs') or []):
                html_content += f'<a href="{p.get("url")}" class="btn btn-p" target="_blank">📄 {p.get("title", "NOTES")}</a>'
            html_content += "</div></div></div>"
        html_content += "</div></div>"

    html_content += """
        </div>
        <script>
            function showSubj(id, btn) {
                document.getElementById('placeholder').style.display='none';
                document.querySelectorAll('.content-section').forEach(s => s.style.display='none');
                document.querySelectorAll('.subject-btn').forEach(b => b.classList.remove('active'));
                document.getElementById(id).style.display='block';
                btn.classList.add('active');
            }
        </script>
    </body></html>
    """
    return html_content

def process_video_turbo(v):
    """Worker for parallel metadata extraction"""
    v_links = fetch_json(f"{API_BASE}?type=video-url&id={v['id']}")
    if v_links:
        v.update({
            "video_url": v_links.get('video_url', ''),
            "hd_video_url": v_links.get('hd_video_url', ''),
            "thumbnail": v_links.get('image') or v_links.get('thumbnail') or v.get('image'),
            "pdfs": v_links.get('pdfs', [])
        })
    return v

def deep_sync_logic(bid, status_msg=None, chat_id=None):
    """Turbo-charged deep sync using multi-threading"""
    batch_data = fetch_json(f"{API_BASE}?type=subjects&id={bid}")
    if not batch_data or 'classrooms' not in batch_data: return None

    slug = batch_data.get('slug', '')
    classrooms = batch_data.get('classrooms', [])
    full_classrooms = []

    for classroom in classrooms:
        cid = classroom.get('id')
        cname = classroom.get('name', 'Unknown')
        if status_msg:
            try: bot.edit_message_text(f"📥 `[TURBO_SYNC]` Protocol: `{cname[:20]}...`", chat_id, status_msg.message_id)
            except: pass

        v_list = fetch_json(f"{API_BASE}?type=videos&slug={slug}&lesson_id={cid}")
        videos = v_list.get('videos', []) if v_list else []

        # Parallel execution for massive speed boost
        if videos:
            with ThreadPoolExecutor(max_workers=20) as executor:
                videos = list(executor.map(process_video_turbo, videos))

        # Fetch Subject-level Notes
        notes_data = fetch_json(f"{API_BASE}?type=notes&course_id={bid}&lesson_id={cid}")
        # Fix: ensure we are getting the right list from notes_data
        classroom['subject_notes'] = []
        if notes_data:
            # Check common keys like 'notes' or 'data'
            classroom['subject_notes'] = notes_data.get('notes') or notes_data.get('data') or []

        classroom['video_content'] = videos
        full_classrooms.append(classroom)

    batch_data['classrooms'] = full_classrooms
    save_path = os.path.join(KGS_DIR, f"id{bid}.json")
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(batch_data, f, indent=4, ensure_ascii=False)
    update_master_json(batch_data)
    return batch_data

# --- BOT HANDLERS ---

@bot.message_handler(commands=['start', 'help'])
def start(message):
    save_user(message.from_user.id)
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "👋 **Welcome to KGS-X Interface.**\n\nYour ID has been registered. You can send messages here to contact the administrator.")
        return
    ui = (
        "💠 **KGS-X PROTOCOL // V4.2 ADMIN**\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "📡 **ENGINE:** `MULTI_THREADED_ASYNC`\n"
        "🛡️ **ACCESS:** `ADMIN_ONLY`\n\n"
        "🛠️ **CORE PROTOCOLS:**\n"
        "1️⃣ `/[batchid]` - `DEEP_EXTRACT` (Save JSON)\n"
        "2️⃣ `/send[id]` - `MASS_DEPLOY` (Text Style)\n"
        "3️⃣ `/sendtgroup[id]` - `PREMIUM_DEPLOY` (Photo Style)\n"
        "4️⃣ `/html[id]` - `HTML_COMPILER` (UI Interface)\n"
        "5️⃣ `/today[id]` - `LIVE_FEED` (Real-time)\n"
        "6️⃣ `/batchlist` - `GLOBAL_LIST` (batch.json)\n"
        "7️⃣ `/idall` - `MASS_SYNC` (All Batches)\n"
        "8️⃣ `/updateall` - `FORCE_UPDATE` (Database Refresh)\n"
        "9️⃣ `/htmlall` - `MASS_HTML` (Global Compile)\n\n"
        "📂 **DATABASE:** `./kgs/`"
    )
    bot.reply_to(message, ui, parse_mode='Markdown')

@bot.message_handler(commands=['batchlist'])
def get_batch_list(message):
    if not is_admin(message.from_user.id): return
    sm = bot.reply_to(message, "📂 `[FETCHING]` Global Batch Stream...")
    data = fetch_json(f"{API_BASE}?type=batches")
    if data:
        with open("batch.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        with open("batch.json", "rb") as f:
            bot.send_document(message.chat.id, f, caption=f"✅ `[SUCCESS]` Total Batches: `{len(data)}`")
        bot.delete_message(message.chat.id, sm.message_id)
    else: bot.edit_message_text("❌ `[ERROR]` Stream Failed.", message.chat.id, sm.message_id)

@bot.message_handler(regexp=r'^/send\d+')
def handle_send_command(message):
    if not is_admin(message.from_user.id): return
    bid = message.text.lower().replace('/send', '').strip()
    if not bid.isdigit(): return

    sm = bot.reply_to(message, f"🚀 `[DEPLOYING]` Initializing Mass Upload for Batch: `{bid}`...")

    file_path = os.path.join(KGS_DIR, f"id{bid}.json")
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = deep_sync_logic(bid, sm, message.chat.id)
        if not data:
            bot.edit_message_text("❌ `[ERROR]` Resource extraction failed.", message.chat.id, sm.message_id)
            return

    # 1. Send Batch Header
    title = data.get('title', 'Unknown Batch')
    image = data.get('image', '')
    header_cap = f"🎓 **BATCH DEPLOYED**\n━━━━━━━━━━━━━━━━━━━━\n📝 **NAME:** `{title}`\n🆔 **ID:** `{bid}`\n📦 **UNITS:** `{len(data.get('classrooms', []))}` Subjects"

    if image:
        bot.send_photo(message.chat.id, image, caption=header_cap, parse_mode='Markdown')
    else:
        bot.send_message(message.chat.id, header_cap, parse_mode='Markdown')

    # 2. Deploy Content
    for room in data.get('classrooms', []):
        cname = room.get('name', 'Unknown')
        bot.send_message(message.chat.id, f"📚 **SUBJECT:** `{cname}`\n━━━━━━━━━━━━━━", parse_mode='Markdown')

        # Subject Notes
        for sn in room.get('subject_notes', []):
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(telebot.types.InlineKeyboardButton("📄 VIEW NOTES", url=sn.get('url')))
            bot.send_message(message.chat.id, f"📙 **RESOURCES:** `{sn.get('title')}`", reply_markup=markup)

        # Videos
        for v in room.get('video_content', []):
            v_title = v.get('name') or v.get('title', 'Untitled')
            v_id = v.get('id')
            v_img = v.get('thumbnail') or v.get('image')

            v_cap = f"🎬 **RESOURCE:** `{v_title}`\n🆔 **ID:** `{v_id}`"
            for p in (v.get('pdfs') or []):
                v_cap += f"\n└ [📄 {p.get('title')}]({p.get('url')})"

            markup = telebot.types.InlineKeyboardMarkup()
            if v.get('video_url'): markup.add(telebot.types.InlineKeyboardButton("⚡ NORMAL", url=v['video_url']))
            if v.get('hd_video_url'): markup.add(telebot.types.InlineKeyboardButton("🚀 HD TURBO", url=v['hd_video_url']))

            try:
                if v_img: bot.send_photo(message.chat.id, v_img, caption=v_cap, reply_markup=markup, parse_mode='Markdown')
                else: bot.send_message(message.chat.id, v_cap, reply_markup=markup, parse_mode='Markdown', disable_web_page_preview=True)
                time.sleep(1) # Anti-flood protection
            except: continue

    bot.send_message(message.chat.id, "✅ `[SUCCESS]` **Batch Deployment Protocol Complete.**")
    bot.delete_message(message.chat.id, sm.message_id)

@bot.message_handler(regexp=r'^/sendtgroup\d+')
def handle_sendtgroup_command(message):
    if not is_admin(message.from_user.id): return
    bid = message.text.lower().replace('/sendtgroup', '').strip()
    if not bid.isdigit(): return

    sm = bot.reply_to(message, f"🚀 `[PREMIUM_DEPLOY]` Initializing Photo-Style Upload for Batch: `{bid}`...")

    file_path = os.path.join(KGS_DIR, f"id{bid}.json")
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = deep_sync_logic(bid, sm, message.chat.id)
        if not data:
            bot.edit_message_text("❌ `[ERROR]` Resource extraction failed.", message.chat.id, sm.message_id)
            return

    # 1. Send Premium Batch Header (Photo Style)
    title = data.get('title', 'Unknown Batch')
    image = data.get('image', '')
    if isinstance(image, dict):
        image = image.get('url') or image.get('link') or ''

    upload_by = "MADXT2Z"

    header_cap = (
        f"🏷️ **Index ID :** `{bid}`\n\n"
        f"🖼️ **Title :** `{title}`\n\n"
        f"📚 **Batch :** `{title}`\n\n"
        f"🎓 **Upload By :** {upload_by}"
    )

    if image:
        safe_call(bot.send_photo, message.chat.id, image, caption=header_cap, parse_mode='Markdown')
    else:
        safe_call(bot.send_message, message.chat.id, header_cap, parse_mode='Markdown')

    # 2. Subject List Message
    rooms = data.get('classrooms', [])
    subj_list_msg = "📚 **SUBJECT LIST**\n━━━━━━━━━━━━━━\n"
    for idx, room in enumerate(rooms):
        subj_list_msg += f"{idx+1}. `{room.get('name', 'Unknown')}`\n"
    safe_call(bot.send_message, message.chat.id, subj_list_msg, parse_mode='Markdown')

    for room in rooms:
        cname = room.get('name', 'Unknown')
        safe_call(bot.send_message, message.chat.id, f"📂 **SECTION:** `{cname}`\n━━━━━━━━━━━━━━", parse_mode='Markdown')

        # Subject Notes as buttons
        for sn in room.get('subject_notes', []):
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(telebot.types.InlineKeyboardButton("📄 VIEW NOTES", url=sn.get('url')))
            safe_call(bot.send_message, message.chat.id, f"📙 **RESOURCES:** `{sn.get('title')}`", reply_markup=markup)

        # Videos
        for v in room.get('video_content', []):
            v_title = v.get('name') or v.get('title', 'Untitled')
            v_id = v.get('id')
            v_img = v.get('thumbnail') or v.get('image') or 'https://placehold.co/400x225/141417/00d4ff?text=KGS+X'

            if isinstance(v_img, dict):
                v_img = v_img.get('url') or v_img.get('link') or 'https://placehold.co/400x225/141417/00d4ff?text=KGS+X'

            v_cap = f"🎬 **RESOURCE:** `{v_title}`\n🆔 **ID:** `{v_id}`"

            markup = telebot.types.InlineKeyboardMarkup()
            # Video Buttons
            row1 = []
            if v.get('video_url'): row1.append(telebot.types.InlineKeyboardButton("⚡ NORMAL", url=v['video_url']))
            if v.get('hd_video_url'): row1.append(telebot.types.InlineKeyboardButton("🚀 HD TURBO", url=v['hd_video_url']))
            if row1: markup.row(*row1)

            # PDF Buttons
            for p in (v.get('pdfs') or []):
                markup.add(telebot.types.InlineKeyboardButton(f"📄 {p.get('title', 'NOTES')}", url=p.get('url')))

            # Send Resource (Photo with fallback)
            try:
                safe_call(bot.send_photo, message.chat.id, v_img, caption=v_cap, reply_markup=markup, parse_mode='Markdown')
                time.sleep(2) # Increased delay for safety
            except:
                safe_call(bot.send_message, message.chat.id, v_cap, reply_markup=markup, parse_mode='Markdown', disable_web_page_preview=True)
                time.sleep(1.5)

    safe_call(bot.send_message, message.chat.id, "✅ `[SUCCESS]` **Premium Batch Deployment Complete.**")
    bot.delete_message(message.chat.id, sm.message_id)

@bot.message_handler(regexp=r'^/id\d+-\d+$')
def handle_range_id(message):
    if not is_admin(message.from_user.id): return
    try:
        range_str = message.text.lower().replace('/id', '').strip()
        start_id, end_id = map(int, range_str.split('-'))

        if start_id > end_id:
            bot.reply_to(message, "❌ `[ERROR]` Start ID must be less than End ID.")
            return

        total_batches = end_id - start_id + 1
        status_msg = bot.reply_to(message, f"🌀 `[RANGE_SYNC]` Initializing protocol for `{total_batches}` units...")

        for i, bid in enumerate(range(start_id, end_id + 1)):
            try:
                progress = int(((i + 1) / total_batches) * 100)

                # Fast check cache
                file_path = os.path.join(KGS_DIR, f"id{bid}.json")
                if os.path.exists(file_path):
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    bot.edit_message_text(
                        f"📁 `[CACHE]` **ID:** `{bid}` | `{data.get('title', 'Unknown')[:20]}`\n"
                        f"📊 **Progress:** `{progress}%` `[COMPLETE]`",
                        message.chat.id, status_msg.message_id, parse_mode='Markdown'
                    )
                    continue

                # Sync if not cached
                bot.edit_message_text(
                    f"🌀 `[SYNCING]` **ID:** `{bid}`\n"
                    f"📂 **Status:** `Extracting Subject Data...`\n"
                    f"📊 **Progress:** `{progress}%`",
                    message.chat.id, status_msg.message_id, parse_mode='Markdown'
                )

                # Fetch basic data to get Title
                batch_data = fetch_json(f"{API_BASE}?type=subjects&id={bid}")
                if not batch_data or 'classrooms' not in batch_data:
                    continue

                title = batch_data.get('title', 'Unknown')
                bot.edit_message_text(
                    f"📥 `[DEEP_EXTRACT]` **ID:** `{bid}` | `{title[:20]}`\n"
                    f"📚 **Protocol:** `Full Deep Sync`\n"
                    f"📊 **Progress:** `{progress}%`",
                    message.chat.id, status_msg.message_id, parse_mode='Markdown'
                )

                # Execute Turbo Sync
                deep_sync_logic(bid)

            except Exception as e:
                print(f"Error in range sync for {bid}: {e}")
                continue

        bot.edit_message_text(f"✅ `[SUCCESS]` Range Sync complete from `{start_id}` to `{end_id}`.", message.chat.id, status_msg.message_id)

    except Exception as e:
        bot.reply_to(message, f"❌ `[CRITICAL_ERROR]` Invalid format. Use: `/id1-20`")

@bot.message_handler(regexp=r'^/id\d+$|^/\d+$')
def handle_id(message):
    if not is_admin(message.from_user.id): return
    bid = re.sub(r'/id|/', '', message.text.lower()).strip()
    if not bid.isdigit(): return

    if bid in get_saved_ids():
        with open(f"kgs/id{bid}.json", "rb") as f:
            bot.send_document(message.chat.id, f, caption=f"📁 `[CACHE]` Batch {bid} found.")
        return

    sm = bot.reply_to(message, f"🌀 `[EXECUTING]` **Initializing Turbo-Sync for Batch:** `{bid}`...")
    data = deep_sync_logic(bid, sm, message.chat.id)

    if data:
        with open(f"kgs/id{bid}.json", "rb") as f:
            bot.send_document(message.chat.id, f, caption=f"✅ `[SUCCESS]` Batch {bid} Decrypted & Saved.")
        bot.delete_message(message.chat.id, sm.message_id)
    else: bot.edit_message_text("❌ `[ERROR]` Extraction Failed.", message.chat.id, sm.message_id)

@bot.message_handler(regexp=r'/html\s*\d+')
def handle_html_cmd(message):
    if not is_admin(message.from_user.id): return
    # Extract ID correctly from /html1067 or /html 1067
    bid = re.sub(r'/html', '', message.text.lower()).strip()
    if not bid.isdigit(): return

    file_path = os.path.join(KGS_DIR, f"id{bid}.json")

    # Fast Load: Check cache first
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        bot.send_chat_action(message.chat.id, 'upload_document')
    else:
        # If not cached, Turbo Sync first
        sm = bot.reply_to(message, f"🌀 `[IN_PROGRESS]` Batch `{bid}` data missing. Initializing Turbo-Sync...")
        data = deep_sync_logic(bid, sm, message.chat.id)
        if not data:
            bot.edit_message_text("❌ `[ERROR]` Resource extraction failed.", message.chat.id, status_msg.message_id)
            return
        bot.delete_message(message.chat.id, sm.message_id)

    # Generate HTML from data
    html = generate_html_string(data, bid)
    buf = io.BytesIO(html.encode('utf-8'))
    buf.name = f"Batch_{bid}_KGSX.html"

    bot.send_document(
        message.chat.id,
        buf,
        caption=f"📄 **HTML INTERFACE READY**\n━━━━━━━━━━━━━━━━━━━━\n🎓 **BATCH:** `{data.get('title')}`\n🆔 **ID:** `{bid}`",
        parse_mode='Markdown'
    )

@bot.message_handler(commands=['idall'])
def id_all(message):
    if not is_admin(message.from_user.id): return
    sm = bot.reply_to(message, "⚙️ `[GLOBAL_MASS_SYNC]` Starting Turbo Sequence...")
    batches = fetch_json(f"{API_BASE}?type=batches") or []
    saved = get_saved_ids()
    total = len(batches)
    for i, b in enumerate(batches):
        bid = str(b.get('id'))
        if bid in saved: continue
        try:
            bot.edit_message_text(f"🚀 `[PROCESS]` Turbo Sync [{i+1}/{total}]: `{b.get('title')[:20]}`", message.chat.id, sm.message_id)
            deep_sync_logic(bid)
        except: continue
    bot.edit_message_text(f"✅ `[COMPLETE]` Mass Sync Finished for `{total}` batches.", message.chat.id, sm.message_id)

@bot.message_handler(commands=['updateall'])
def update_all(message):
    if not is_admin(message.from_user.id): return
    sm = bot.reply_to(message, "🔄 `[FORCE_REFRESH]` Initializing Global Database Update...")
    batches = fetch_json(f"{API_BASE}?type=batches") or []
    total = len(batches)
    for i, b in enumerate(batches):
        bid = str(b.get('id'))
        try:
            bot.edit_message_text(f"⚙️ `[UPDATING]` [{i+1}/{total}]: `{b.get('title')[:20]}`", message.chat.id, sm.message_id)
            deep_sync_logic(bid) # Overwrites existing files with latest data
        except: continue
    bot.edit_message_text(f"✅ `[SUCCESS]` All `{total}` batches have been force-updated.", message.chat.id, sm.message_id)

@bot.message_handler(commands=['htmlall'])
def html_all(message):
    if not is_admin(message.from_user.id): return
    sm = bot.reply_to(message, "⚙️ `[GLOBAL_HTML_SYNC]` Compiling UI for all resources...")
    batches = fetch_json(f"{API_BASE}?type=batches") or []
    total = len(batches)
    for i, b in enumerate(batches):
        try:
            bid = str(b.get('id'))
            bot.edit_message_text(f"📄 `[COMPILE]` [{i+1}/{total}]: `{b.get('title')[:20]}`", message.chat.id, sm.message_id)
            file_path = f"kgs/id{bid}.json"
            if not os.path.exists(file_path):
                data = deep_sync_logic(bid)
            else:
                with open(file_path, "r", encoding="utf-8") as f: data = json.load(f)

            if data:
                html = generate_html_string(data, bid)
                buf = io.BytesIO(html.encode('utf-8'))
                buf.name = f"Batch_{bid}_KGSX.html"
                bot.send_document(message.chat.id, buf, caption=f"📄 `[PAYLOAD]` Compiled: {b.get('title')}")
                time.sleep(0.5)
        except: continue
    bot.edit_message_text("✅ `[FINALIZE]` Global HTML compilation complete.", message.chat.id, sm.message_id)

@bot.message_handler(regexp=r'/video\s*\d+|/video\d+')
def handle_v(message):
    if not is_admin(message.from_user.id): return
    vid_id = re.sub(r'/video', '', message.text.lower()).strip()
    sm = bot.reply_to(message, f"🎥 `[BYPASSING]` Resource ID: {vid_id}...")
    data = fetch_json(f"{API_BASE}?type=video-url&id={vid_id}")
    if data:
        img = data.get('image') or data.get('thumbnail')
        cap = f"🎬 **RESOURCE DETECTED**\n━━━━━━━━━━━━━━━━━━━━\n📝 **TITLE:** `{data.get('title')}`\n🆔 **ID:** `{vid_id}`\n"
        for p in data.get('pdfs', []): cap += f"└ [📄 {p.get('title')}]({p.get('url')})\n"
        markup = telebot.types.InlineKeyboardMarkup()
        if data.get('video_url'): markup.add(telebot.types.InlineKeyboardButton("⚡ NORMAL STREAM", url=data['video_url']))
        if data.get('hd_video_url'): markup.add(telebot.types.InlineKeyboardButton("🚀 HD BYPASS", url=data['hd_video_url']))
        if img: bot.send_photo(message.chat.id, img, caption=cap, reply_markup=markup, parse_mode='Markdown')
        else: bot.send_message(message.chat.id, cap, reply_markup=markup, parse_mode='Markdown')
        bot.delete_message(message.chat.id, sm.message_id)
    else: bot.edit_message_text("❌ `[ERROR]` Link Blocked or Invalid.", message.chat.id, sm.message_id)

@bot.message_handler(regexp=r'/today\d+')
def today(message):
    if not is_admin(message.from_user.id): return
    bid = message.text.lower().replace('/today', '').strip()
    data = fetch_json(f"{API_BASE}?type=today&id={bid}")
    classes = (data.get('todayclasses', []) or data.get('live_classes', [])) if data else []
    if not classes: bot.reply_to(message, "✨ `[EMPTY]` No scheduled streams."); return
    for item in classes:
        markup = telebot.types.InlineKeyboardMarkup()
        if item.get('video_url'): markup.add(telebot.types.InlineKeyboardButton("📱 PLAY", url=item['video_url']))
        bot.send_message(message.chat.id, f"🎬 **TODAY'S FEED:** `{item.get('name')}`\n🆔 **RESOURCE ID:** `{item.get('id')}`", reply_markup=markup)

@bot.message_handler(commands=['dashboard'])
def generate_master_dashboard(message):
    if not is_admin(message.from_user.id): return
    sm = bot.reply_to(message, "🛠️ `[INITIALIZING]` Compiling Master Global Dashboard...")

    saved_ids = get_saved_ids()
    all_batches_data = []

    for bid in saved_ids:
        try:
            with open(os.path.join(KGS_DIR, f"id{bid}.json"), "r", encoding="utf-8") as f:
                all_batches_data.append(json.load(f))
        except: continue

    if not all_batches_data:
        bot.edit_message_text("❌ `[ERROR]` Database is empty. Sync some batches first.", message.chat.id, sm.message_id)
        return

    # Master Dashboard UI logic (as previously defined)
    master_html = f"<!DOCTYPE html><html><head><title>KGS-X MASTER</title></head><body><h1>KGS-X Dashboard</h1><script>const data = {json.dumps(all_batches_data)}; console.log(data);</script></body></html>"

    buf = io.BytesIO(master_html.encode('utf-8'))
    buf.name = "KGSX_Master_Dashboard.html"
    bot.send_document(message.chat.id, buf, caption=f"📊 **MASTER DASHBOARD READY**")
    bot.delete_message(message.chat.id, sm.message_id)

@bot.message_handler(commands=['clearchat'])
def clear_chat(message):
    if not is_admin(message.from_user.id): return

    # Check if bot has permission to delete in group
    try:
        status_msg = bot.reply_to(message, "💣 `[PURGING]` Initializing chat wipe protocols...")

        # Deleting last 100 messages (Telegram limit for bots usually)
        # Note: Bots can only delete messages sent by them or anyone if they are admin.
        # This will try to delete from the current message ID backwards.
        curr_id = message.message_id
        deleted_count = 0

        for i in range(curr_id, curr_id - 100, -1):
            try:
                bot.delete_message(message.chat.id, i)
                deleted_count += 1
            except: continue

        bot.send_message(message.chat.id, f"✅ `[SUCCESS]` **Purged {deleted_count} data packets.**")
    except Exception as e:
        bot.reply_to(message, f"❌ `[ERROR]` **Purge Failed:** `{str(e)}`")

@bot.message_handler(commands=['broadcast'])
def handle_broadcast(message):
    if not is_admin(message.from_user.id): return
    query = message.text.replace('/broadcast', '').strip()
    if not query:
        bot.reply_to(message, "❌ `[ERROR]` Use: `/broadcast Your Message`")
        return

    filename = "users.json"
    users = []
    if os.path.exists(filename):
        with open(filename, "r") as f: users = json.load(f)

    bot.reply_to(message, f"📡 `[BROADCASTING]` Target: `{len(users)}` units...")
    success = 0
    for user_id in users:
        try:
            bot.send_message(user_id, f"📢 **SYSTEM BROADCAST**\n━━━━━━━━━━━━━━\n\n{query}")
            success += 1
            time.sleep(0.05)
        except: continue
    bot.send_message(message.chat.id, f"✅ `[SUCCESS]` Broadcast complete to `{success}` users.")

@bot.message_handler(func=lambda message: not is_admin(message.from_user.id))
def forward_user_msg(message):
    save_user(message.from_user.id)
    if message.text and message.text.startswith('/'): return

    admin_text = (
        f"📩 **NEW USER MESSAGE**\n"
        f"━━━━━━━━━━━━━━\n"
        f"👤 **Name:** `{message.from_user.first_name}`\n"
        f"🆔 **ID:** `{message.from_user.id}`\n\n"
        f"💬 **Message:** {message.text}"
    )
    bot.send_message(ADMIN_ID, admin_text)
    bot.reply_to(message, "✅ Your message has been sent to the admin.")

@bot.message_handler(func=lambda message: is_admin(message.from_user.id) and message.reply_to_message)
def admin_reply_handler(message):
    # If admin replies to a message that has user ID
    try:
        reply_text = message.reply_to_message.text
        if "🆔 ID:" in reply_text:
            user_id = int(re.search(r'🆔 ID: `(\d+)`', reply_text).group(1))
            bot.send_message(user_id, f"👨‍💻 **ADMIN REPLY:**\n\n{message.text}")
            bot.reply_to(message, "✅ Reply delivered.")
    except Exception as e:
        print(f"Reply Error: {e}")

@bot.message_handler(commands=['status'])
def status(message):
    if not is_admin(message.from_user.id): return
    files = len(os.listdir(KGS_DIR))
    bot.reply_to(message, f"📊 **SYSTEM STATUS REPORT**\n━━━━━━━━━━━━━━\n📂 Cached Units: `{files}`\n📡 Server: `CONNECTED` \n🛡️ Protection: `ACTIVE`", parse_mode='Markdown')

@bot.message_handler(commands=['stopall'])
def stop(message):
    if not is_admin(message.from_user.id): return
    bot.reply_to(message, "🛑 `[TERMINATED]` System shutdown initiated.")
    os._exit(0)

if __name__ == "__main__":
    print("🤖 [SYSTEM] KGS-X Interface v4.0 Turbo Online.")
    try:
        bot.remove_webhook() # Purane connection clear karein
        print("📡 Connection established. Ready for commands...")
        bot.infinity_polling(timeout=60, long_polling_timeout=20)
    except Exception as e:
        print(f"🛑 Critical System Error: {e}")
        time.sleep(5)
        os._exit(1)
