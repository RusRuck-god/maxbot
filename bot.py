import time
import re
import os
import json
import requests
import urllib3
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

print("🔧 СКРИПТ ЗАПУЩЕН, начало выполнения", flush=True)

class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running!")

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    print(f"🌐 Веб-сервер стартует на порту {port}", flush=True)
    server = HTTPServer(('0.0.0.0', port), SimpleHTTPRequestHandler)
    server.serve_forever()

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

API_URL = "https://platform-api2.max.ru"
HEADERS = {"Authorization": MAX_BOT_TOKEN}

def remove_webhooks():
    print("🧹 Проверяю webhook-подписки...", flush=True)
    try:
        subs_res = requests.get(f"{API_URL}/subscriptions", headers=HEADERS, verify=False)
        subs_data = subs_res.json()
        if "subscriptions" in subs_data and subs_data["subscriptions"]:
            for sub in subs_data["subscriptions"]:
                url_to_del = sub.get("url")
                if url_to_del:
                    del_res = requests.delete(f"{API_URL}/subscriptions", headers=HEADERS, params={"url": url_to_del}, verify=False)
                    print(f"🗑️ Удалена подписка {url_to_del}: {del_res.status_code}", flush=True)
        else:
            print("✅ Подписок нет", flush=True)
    except Exception as e:
        print(f"⚠️ Ошибка при удалении подписок: {e}", flush=True)

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
                time.sleep(1)
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
    """Форматирует рецепт: жирное название, ингредиенты, ссылка на канал"""
    lines = text.strip().split('\n')
    if not lines:
        return text
    
    # Название - первая непустая строка
    title = ""
    start_idx = 0
    for i, line in enumerate(lines):
        if line.strip():
            title = line.strip()
            start_idx = i + 1
            break
    
    # Ищем ингредиенты (до "Приготовление", "Выпекаем", "🔥", "❤️", "Понравилось" и т.д.)
    ingredients = []
    stop_words = ['приготовление', 'выпекаем', '🔥', '❤️', 'понравилось', 'поделись', 'поделитесь', 'подписаться', 'рецепты', '🥘']
    
    for line in lines[start_idx:]:
        line_stripped = line.strip()
        if not line_stripped:
            continue
        
        # Проверяем стоп-слова
        lower_line = line_stripped.lower()
        if any(sw in lower_line for sw in stop_words):
            break
        
        # Пропускаем строки "Ингредиенты:" (мы добавим свою)
        if 'ингредиент' in lower_line:
            continue
        
        ingredients.append(line_stripped)
    
    # Собираем пост
    result = f"<b>{title}</b>\n\n"
    result += "<b>📝 Ингредиенты:</b>\n\n"
    result += '\n'.join(ingredients) + "\n\n"
    result += "<i>🥰 Понравилось?</i>\n"
    result += "<b>Поделись с другом!</b>\n\n"
    result += "<b>Рецепты на Каждый день 🥗</b> <a href='https://max.ru/channel_recept_every_day'>Подписаться</a>"
    
    return result

def bot_loop():
    marker = None
    processed_mids = set()
    print("🚀 bot_loop() НАЧАЛ РАБОТУ", flush=True)
    
    remove_webhooks()
    
    counter = 0
    while True:
        try:
            counter += 1
            if counter % 10 == 0:
                remove_webhooks()
            
            print("⏳ Запрос к /updates...", flush=True)
            params = {"timeout": 30}
            if marker:
                params["marker"] = marker
            
            res = requests.get(f"{API_URL}/updates", headers=HEADERS, params=params, verify=False)
            print(f"📡 Ответ API: {res.status_code}", flush=True)
            
            if res.status_code != 200:
                print(f"Ошибка API: {res.status_code}", flush=True)
                time.sleep(5)
                continue
            
            data = res.json()
            print(f"📦 Данные: {json.dumps(data, ensure_ascii=False)[:300]}", flush=True)
            
            if "updates" in data:
                for update in data["updates"]:
                    print("=" * 60, flush=True)
                    print(json.dumps(update, indent=2, ensure_ascii=False), flush=True)
                    print("=" * 60, flush=True)
                    
                    if "marker" in data:
                        marker = data["marker"]
                    
                    if update.get("update_type") == "message_created":
                        message = update.get("message", {})
                        mid = message.get("body", {}).get("mid", "")
                        
                        if mid in processed_mids:
                            print(f"⏭️ Дубликат {mid}, пропускаю", flush=True)
                            continue
                        processed_mids.add(mid)
                        
                        if len(processed_mids) > 1000:
                            processed_mids.clear()
                            print("🧹 Очистил processed_mids", flush=True)
                        
                        chat_id = message.get("recipient", {}).get("chat_id")
                        sender_id = message.get("sender", {}).get("user_id")
                        msg_text = message.get("body", {}).get("text", "")
                        
                        if sender_id != 68399360:
                            print(f"⛔ Игнорирую постороннего (ID: {sender_id})", flush=True)
                            continue
                        
                        if msg_text and chat_id:
                            print(f"📩 Получен шаблон!", flush=True)
                            
                            # 1. Если начинается с ( - это шаблон для каналов
                            if msg_text.strip().startswith('('):
                                posted_count = parse_and_distribute(msg_text)
                                requests.post(f"{API_URL}/messages", headers=HEADERS,
                                              params={"chat_id": chat_id},
                                              json={"text": f"🎉 Готово! Разослано постов: {posted_count} из 15."},
                                              verify=False)
                                continue
                            
                            # 2. Если начинается со знака зодиака - это гороскоп
                            if re.match(r'^[♈♉♊♋♌♍♎♏♐♑♒♓]', msg_text.strip()):
                                formatted_text = format_horoscope(msg_text)
                                requests.post(f"{API_URL}/messages", headers=HEADERS,
                                              params={"chat_id": chat_id},
                                              json={"text": formatted_text, "format": "html"},
                                              verify=False)
                                print(f"✅ Гороскоп отправлен в ЛС", flush=True)
                                continue
                            
                            # 3. Иначе - это рецепт
                            formatted_text = format_recipe(msg_text)
                            requests.post(f"{API_URL}/messages", headers=HEADERS,
                                          params={"chat_id": chat_id},
                                          json={"text": formatted_text, "format": "html"},
                                          verify=False)
                            print(f"✅ Рецепт отправлен в ЛС", flush=True)
                            
        except Exception as e:
            print(f"❌ Ошибка цикла: {e}", flush=True)
            time.sleep(5)

if __name__ == "__main__":
    print("🔧 Запускаю веб-сервер в фоне и бота в основном потоке", flush=True)
    Thread(target=run_web_server, daemon=True).start()
    print("🔧 Веб-сервер запущен, теперь запускаю bot_loop()", flush=True)
    bot_loop()
