import re
import os
import json
import time
import requests
import urllib3
from flask import Flask, request, jsonify
from datetime import datetime, timedelta

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

print("🔧 СКРИПТ ЗАПУЩЕН, начало выполнения", flush=True)

MAX_BOT_TOKEN = "f9LHodD0cOLbabfFYsoiZq6EjnWBOC3L1J2g8avgAzs_KETkBsK0POzMM_CcL3tsbBCHwl4DXoPy0aZWh5nx"

CHANNELS = {
    "тебе знак": -78584619664640,
    "аня": -78584626349312,
    "вика": -78573540082944,
    "соня": -78491128825088,
    "саша": -78586861651200,
    "полина": -78573536412928,
    "маша": -78586876986624,
    "юля": -78586842973440,
    "таня": -78586870039808,
    "диана": -78586852672768,
    "лера": -78573528548608,
    "даша": -78586832815360,
    "катя": -78573444007168,
    "арина": -78586811712768,
    "настя": -78584631723264,
    "тестовый калл": -78989554222336
}

# ==== НАСТРОЙКИ НОГТЕЙ ====
# Ногти идут в БОЕВОЙ канал «Гламурный Маникюр»
NAILS_CHANNEL_ID = -78143961564416

NAILS_SLOTS = ["11:00", "13:00", "15:00", "17:00", "19:00", "21:00"]
NAILS_CAPTION = "<b>Гламурный Маникюр 💅 НОГТИ</b>\n<a href='https://max.ru/channel_glamour_manic'>Подписаться</a>"

API_URL = "https://platform-api2.max.ru"
HEADERS = {"Authorization": MAX_BOT_TOKEN}

# ==== SUPABASE ====
SUPABASE_URL = "https://ehhajdubxnarrwamypar.supabase.co"
SUPABASE_KEY = "sb_publishable_XxGXgOoCNiVPSxKlFzF7Zg_8OoWiprm"
SUPABASE_HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

ADMIN_USER_ID = 68399360
WEBHOOK_SECRET = "your_secret_here_change_me"

# Часовой пояс (UTC+5)
TIMEZONE_OFFSET = 5

scheduled_posts = {}
processed_mids = set()

# ==== ФУНКЦИИ SUPABASE ====
def supabase_add_nail(token):
    url = f"{SUPABASE_URL}/rest/v1/nails"
    payload = {"token": token}
    try:
        res = requests.post(url, headers=SUPABASE_HEADERS, json=payload, verify=False)
        if res.status_code in (200, 201):
            print(f"✅ Токен добавлен в Supabase", flush=True)
            return True
        else:
            print(f"❌ Ошибка Supabase add: {res.status_code} - {res.text}", flush=True)
            return False
    except Exception as e:
        print(f"❌ Ошибка Supabase: {e}", flush=True)
        return False

def supabase_get_first_nail():
    url = f"{SUPABASE_URL}/rest/v1/nails?select=id,token&order=id.asc&limit=1"
    try:
        res = requests.get(url, headers=SUPABASE_HEADERS, verify=False)
        if res.status_code == 200:
            data = res.json()
            if data and len(data) > 0:
                return data[0]
        return None
    except Exception as e:
        print(f"❌ Ошибка Supabase get: {e}", flush=True)
        return None

def supabase_delete_nail(nail_id):
    url = f"{SUPABASE_URL}/rest/v1/nails?id=eq.{nail_id}"
    try:
        res = requests.delete(url, headers=SUPABASE_HEADERS, verify=False)
        if res.status_code in (200, 204):
            print(f"✅ Токен удалён из Supabase", flush=True)
            return True
        else:
            print(f"❌ Ошибка Supabase delete: {res.status_code} - {res.text}", flush=True)
            return False
    except Exception as e:
        print(f"❌ Ошибка Supabase delete: {e}", flush=True)
        return False

def supabase_count_nails():
    url = f"{SUPABASE_URL}/rest/v1/nails?select=id"
    try:
        res = requests.get(url, headers=SUPABASE_HEADERS, verify=False)
        if res.status_code == 200:
            return len(res.json())
        return 0
    except Exception as e:
        print(f"❌ Ошибка Supabase count: {e}", flush=True)
        return 0

# ==== ОТПРАВКА В MAX ====
def send_message_to_channel(channel_id, text):
    url = f"{API_URL}/messages"
    params = {"chat_id": channel_id}
    
    has_html = bool(re.search(r"<(?:b|strong|i|em|u|ins|s|del|code|pre|a)(?:\s+[^>]*)?>", text, re.IGNORECASE))
    has_markdown = bool(re.search(r"(\*\*[^\n]+\*\*|__[^\n]+__|`[^\n]+`|\[[^\]]+\]\([^\)]+\))", text))
    
    payload = {"text": text}
    if has_html:
        payload["format"] = "html"
    elif has_markdown:
        payload["format"] = "markdown"
    
    try:
        res = requests.post(url, headers=HEADERS, params=params, json=payload, verify=False)
        print(f"📤 Отправка в {channel_id}: статус {res.status_code}", flush=True)
        return res.status_code == 200
    except Exception as e:
        print(f"Ошибка при отправке в {channel_id}: {e}", flush=True)
        return False

def send_nails_post(token):
    url = f"{API_URL}/messages"
    params = {"chat_id": NAILS_CHANNEL_ID}
    payload = {
        "text": NAILS_CAPTION,
        "format": "html",
        "attachments": [
            {"type": "image", "payload": {"token": token}}
        ]
    }
    try:
        res = requests.post(url, headers=HEADERS, params=params, json=payload, verify=False)
        print(f"📤 Отправка ногтей в {NAILS_CHANNEL_ID}: статус {res.status_code}", flush=True)
        if res.status_code == 200:
            return True
        else:
            print(f"❌ Ошибка {res.status_code}: {res.text}", flush=True)
            return False
    except Exception as e:
        print(f"Ошибка при отправке ногтей: {e}", flush=True)
        return False

def parse_and_distribute(full_text):
    lines = full_text.strip().split('\n')
    count = 0
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        match = re.match(r'^\((.+?)\)$', line)
        if match:
            channel_name = match.group(1).strip().lower()
            post_lines = []
            i += 1
            while i < len(lines):
                next_line = lines[i].strip()
                if re.match(r'^\((.+?)\)$', next_line):
                    break
                if next_line:
                    post_lines.append(next_line)
                i += 1
            clean_post = ' '.join(post_lines).strip()
            if channel_name in CHANNELS and clean_post:
                channel_id = CHANNELS[channel_name]
                success = send_message_to_channel(channel_id, clean_post)
                if success:
                    print(f"✅ Успешно выложено в [{channel_name}]: {clean_post[:50]}", flush=True)
                    count += 1
            elif channel_name not in CHANNELS:
                print(f"⚠️ Канал '{channel_name}' не найден!", flush=True)
        else:
            i += 1
    return count

def format_horoscope(text):
    lines = text.strip().split('\n')
    formatted_lines = []
    for line in lines:
        line = line.strip()
        if not line:
            formatted_lines.append('')
            continue
        if re.match(r'^[♈♉♊♋♌♍♎♏♐♑♒♓]', line):
            formatted_lines.append(f"<b>{line}</b>")
        elif line.startswith('🌞'):
            formatted_lines.append(f"<b>{line}</b>")
        else:
            formatted_lines.append(line)
    return '\n'.join(formatted_lines)

def format_recipe(text):
    lines = text.strip().split('\n')
    if not lines:
        return text
    title = ""
    start_idx = 0
    for i, line in enumerate(lines):
        if line.strip():
            title = line.strip()
            start_idx = i + 1
            break
    emoji_match = re.search(r'([\U0001F300-\U0001FAFF\u2600-\u27BF]+)\s*$', title)
    if emoji_match:
        emoji = emoji_match.group(1)
        title = title[:emoji_match.start()].strip()
        title = f"{emoji} {title}"
    ingredients = []
    stop_words = ['приготовление', 'выпекаем', '🔥', '❤️', 'понравилось', 'поделись', 'поделитесь', 'подписаться', 'рецепты', '🥘']
    for line in lines[start_idx:]:
        line_stripped = line.strip()
        if not line_stripped:
            continue
        lower_line = line_stripped.lower()
        if any(sw in lower_line for sw in stop_words):
            break
        if 'ингредиент' in lower_line:
            continue
        ingredients.append(line_stripped)
    result = f"<b>{title}</b>\n\n"
    result += "<b>📝 Ингредиенты:</b>\n\n"
    result += '\n'.join(ingredients) + "\n\n"
    result += "<i>🥰 Понравилось?</i>\n"
    result += "<b>Поделись с другом!</b>\n\n"
    result += "<b><a href='https://max.ru/channel_recept_every_day'>Рецепты на Каждый день 🥗</a></b>"
    return result

def send_message_to_user(chat_id, text):
    url = f"{API_URL}/messages"
    params = {"chat_id": chat_id}
    try:
        requests.post(url, headers=HEADERS, params=params, json={"text": text, "format": "html"}, verify=False)
    except Exception as e:
        print(f"Ошибка отправки в ЛС: {e}", flush=True)

# ==== ВЕБХУК ====
@app.route('/webhook', methods=['POST'])
def webhook():
    global processed_mids
    
    secret_header = request.headers.get('X-Max-Bot-Api-Secret')
    if secret_header != WEBHOOK_SECRET:
        print(f"⛔ Неверный секрет: {secret_header}", flush=True)
        return jsonify({"ok": False}), 401
    
    data = request.json
    print(f"📥 Получен вебхук: {json.dumps(data, ensure_ascii=False)[:500]}", flush=True)
    
    update_type = data.get("update_type")
    
    if update_type == "message_created":
        message = data.get("message", {})
        mid = message.get("body", {}).get("mid", "")
        
        if mid in processed_mids:
            print(f"⏭️ Дубликат {mid}, пропускаю", flush=True)
            return jsonify({"ok": True}), 200
        processed_mids.add(mid)
        
        if len(processed_mids) > 1000:
            processed_mids.clear()
            print("🧹 Очистил processed_mids", flush=True)
        
        chat_id = message.get("recipient", {}).get("chat_id")
        sender_id = message.get("sender", {}).get("user_id")
        msg_text = message.get("body", {}).get("text", "")
        
        if sender_id != ADMIN_USER_ID:
            print(f"⛔ Игнорирую постороннего (ID: {sender_id})", flush=True)
            return jsonify({"ok": True}), 200
        
        attachments = message.get("body", {}).get("attachments", [])
        photo_token = None
        
        for att in attachments:
            if att.get("type") == "image":
                photo_token = att.get("payload", {}).get("token")
                if photo_token:
                    print(f"📸 Получен token фото: {photo_token[:50]}...", flush=True)
                break
        
        if photo_token:
            supabase_add_nail(photo_token)
            count = supabase_count_nails()
            send_message_to_user(chat_id, f"✅ Фото добавлено в очередь ногтей. В очереди: {count} шт.")
            return jsonify({"ok": True}), 200
        
        if msg_text and chat_id:
            print(f"📩 Получен шаблон!", flush=True)
            
            if msg_text.strip().startswith('('):
                posted_count = parse_and_distribute(msg_text)
                send_message_to_user(chat_id, f"🎉 Готово! Разослано постов: {posted_count} из 15.")
                return jsonify({"ok": True}), 200
            
            if re.match(r'^[♈♉♊♋♌♍♎♏♐♑♒♓]', msg_text.strip()):
                formatted_text = format_horoscope(msg_text)
                send_message_to_user(chat_id, formatted_text)
                print(f"✅ Гороскоп отправлен в ЛС", flush=True)
                return jsonify({"ok": True}), 200
            
            formatted_text = format_recipe(msg_text)
            send_message_to_user(chat_id, formatted_text)
            print(f"✅ Рецепт отправлен в ЛС", flush=True)
    
    elif update_type == "bot_started":
        print(f"🤖 Бот запущен пользователем", flush=True)
    
    return jsonify({"ok": True}), 200

# ==== ПЛАНИРОВЩИК ====
@app.route('/cron', methods=['GET'])
def cron():
    global scheduled_posts
    now = (datetime.utcnow() + timedelta(hours=TIMEZONE_OFFSET)).strftime("%H:%M")
    
    if now in scheduled_posts:
        print(f"⏰ Время {now}! Публикую отложенные посты...", flush=True)
        for post_data in scheduled_posts[now]:
            parse_and_distribute(post_data)
        del scheduled_posts[now]
        print(f"✅ Отложенные посты за {now} опубликованы", flush=True)
    
    if now in NAILS_SLOTS:
        nail = supabase_get_first_nail()
        if nail:
            print(f"💅 Время {now}! Публикую ногти (id={nail['id']})...", flush=True)
            success = send_nails_post(nail['token'])
            if success:
                supabase_delete_nail(nail['id'])
                count = supabase_count_nails()
                print(f"✅ Ногти опубликованы, в очереди осталось: {count}", flush=True)
            else:
                print(f"❌ Не удалось опубликовать ногти, оставляю в очереди", flush=True)
        else:
            print(f"💅 Время {now}! Очередь ногтей пуста", flush=True)
    
    count = supabase_count_nails()
    return jsonify({"ok": True, "time": now, "nails_in_queue": count}), 200

@app.route('/schedule', methods=['POST'])
def schedule():
    global scheduled_posts
    data = request.json
    time_slot = data.get("time")
    post_text = data.get("text")
    
    if time_slot and post_text:
        if time_slot not in scheduled_posts:
            scheduled_posts[time_slot] = []
        scheduled_posts[time_slot].append(post_text)
        print(f"📅 Сохранён пост на {time_slot}", flush=True)
        return jsonify({"ok": True}), 200
    
    return jsonify({"ok": False, "error": "Missing time or text"}), 400

@app.route('/health', methods=['GET'])
def health():
    return "Bot is running!"

@app.route('/', methods=['GET'])
def index():
    return "Bot is running!"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"🌐 Flask сервер стартует на порту {port}", flush=True)
    print(f"🎯 Канал ногтей: {NAILS_CHANNEL_ID} (боевой)", flush=True)
    app.run(host='0.0.0.0', port=port)
