import re
import os
import json
import time
import requests
import urllib3
from flask import Flask, request, jsonify
from datetime import datetime

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

# Канал для ногтей
NAILS_CHANNEL_ID = -78143961564416

# Слоты для ногтей
NAILS_SLOTS = ["11:00", "13:00", "15:00", "17:00", "19:00", "21:00"]

# Подпись для ногтей
NAILS_CAPTION = "<b>Гламурный Маникюр 💅 НОГТИ</b>\n<a href='https://max.ru/channel_glamour_manic'>Подписаться</a>"

API_URL = "https://platform-api2.max.ru"
HEADERS = {"Authorization": MAX_BOT_TOKEN}

ADMIN_USER_ID = 68399360
WEBHOOK_SECRET = "your_secret_here_change_me"

# ==== ХРАНИЛИЩА ====
scheduled_posts = {}
processed_mids = set()

# Очередь для ногтей: список токенов
nails_queue = []

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
        if res.status_code == 200:
            return True
        else:
            print(f"❌ Ошибка {res.status_code}: {res.text}", flush=True)
            return False
    except Exception as e:
        print(f"Ошибка при отправке в {channel_id}: {e}", flush=True)
        return False

def send_nails_post(token):
    """Отправка поста с ногтями (фото + подпись) в канал"""
    url = f"{API_URL}/messages"
    params = {"chat_id": NAILS_CHANNEL_ID}
    payload = {
        "text": NAILS_CAPTION,
        "format": "html",
        "attachments": [
            {
                "type": "image",
                "payload": {"token": token}
            }
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
    global processed_mids, nails_queue
    
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
        
        # 🔒 ЗАЩИТА ОТ ДУБЛИКАТОВ
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
        
        # ==== ПРОВЕРКА: ЕСТЬ ЛИ ФОТО? ====
        attachments = message.get("body", {}).get("attachments", [])
        photo_token = None
        
        for att in attachments:
            if att.get("type") == "image":
                # Берём token напрямую из payload — MAX уже загрузил фото!
                photo_token = att.get("payload", {}).get("token")
                if photo_token:
                    print(f"📸 Получен token фото: {photo_token[:50]}...", flush=True)
                break
        
        if photo_token:
            nails_queue.append(photo_token)
            send_message_to_user(chat_id, f"✅ Фото добавлено в очередь ногтей. В очереди: {len(nails_queue)} шт.")
            print(f"📋 В очереди ногтей: {len(nails_queue)} шт.", flush=True)
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
    global scheduled_posts, nails_queue
    now = datetime.now().strftime("%H:%M")
    
    # Обычные отложенные посты
    if now in scheduled_posts:
        print(f"⏰ Время {now}! Публикую отложенные посты...", flush=True)
        for post_data in scheduled_posts[now]:
            parse_and_distribute(post_data)
        del scheduled_posts[now]
        print(f"✅ Отложенные посты за {now} опубликованы", flush=True)
    
    # ==== НОГТИ ====
    if now in NAILS_SLOTS and nails_queue:
        print(f"💅 Время {now}! Публикую ногти...", flush=True)
        token = nails_queue.pop(0)
        success = send_nails_post(token)
        if success:
            print(f"✅ Ногти опубликованы, в очереди осталось: {len(nails_queue)}", flush=True)
        else:
            nails_queue.insert(0, token)
            print(f"❌ Не удалось опубликовать ногти, вернул в очередь", flush=True)
    
    return jsonify({"ok": True, "time": now, "nails_in_queue": len(nails_queue)}), 200

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
    app.run(host='0.0.0.0', port=port)
