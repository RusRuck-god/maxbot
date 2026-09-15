import time
import re
import os
import json
import requests
import urllib3
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

# Отключаем предупреждения об SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Минимальный веб-сервер, чтобы Render работал БЕСПЛАТНО
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running!")

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), SimpleHTTPRequestHandler)
    server.serve_forever()

# 1. Твой API токен бота в MAX
MAX_BOT_TOKEN = "f9LHodD0cOLbabfFYsoiZq6EjnWBOC3L1J2g8avgAzs_KETkBsK0POzMM_CcL3tsbBCHwl4DXoPy0aZWh5nx"

# 2. База каналов и их ID
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
    "настя": -78584631723264
}

# 3. ПРАВИЛЬНЫЙ домен API
API_URL = "https://platform-api2.max.ru"

# 4. Токен в заголовке
HEADERS = {"Authorization": MAX_BOT_TOKEN}

def send_message_to_channel(channel_id, text):
    """Отправка сообщения в канал MAX"""
    url = f"{API_URL}/messages"
    params = {"chat_id": channel_id}
    payload = {"text": text}
    try:
        res = requests.post(url, headers=HEADERS, params=params, json=payload, verify=False)
        if res.status_code == 200:
            print(f"✅ Отправлено в {channel_id}")
            return True
        else:
            print(f"❌ Ошибка {res.status_code}: {res.text}")
            return False
    except Exception as e:
        print(f"Ошибка при отправке в {channel_id}: {e}")
        return False

def parse_and_distribute(full_text):
    """Разбор шаблона по каналам"""
    pattern = r'\((.*?)\)\s*\n([^()]+)'
    matches = re.findall(pattern, full_text)
    
    count = 0
    for channel_raw, post_text in matches:
        channel_name = channel_raw.strip().lower()
        clean_post = post_text.strip()
        
        if channel_name in CHANNELS:
            channel_id = CHANNELS[channel_name]
            success = send_message_to_channel(channel_id, clean_post)
            if success:
                print(f"✅ Успешно выложено в [{channel_name}]: {clean_post}")
                count += 1
            time.sleep(1)
        else:
            print(f"⚠️ Канал '{channel_name}' не найден!")
            
    return count

def bot_loop():
    marker = None
    print("🚀 Бот-автопостер для MAX запущен на Render!")
    print("🔄 Начинаю цикл опроса /updates...")
    
    while True:
        try:
            print("⏳ Отправляю запрос к /updates...")
            params = {"timeout": 30}
            if marker:
                params["marker"] = marker
            
            res = requests.get(f"{API_URL}/updates", headers=HEADERS, params=params, verify=False)
            print(f"📡 Ответ API: {res.status_code}")
            
            if res.status_code != 200:
                print(f"Ошибка API: {res.status_code}")
                time.sleep(5)
                continue
            
            data = res.json()
            print(f"📦 Данные: {json.dumps(data, ensure_ascii=False)[:500]}")
            
            if "updates" in data:
                for update in data["updates"]:
                    print("\n" + "=" * 60)
                    print("ПОЛУЧЕНО ОБНОВЛЕНИЕ:")
                    print(json.dumps(update, indent=2, ensure_ascii=False))
                    print("=" * 60)
                    
                    if "marker" in data:
                        marker = data["marker"]
                    
                    # Обрабатываем текстовые сообщения
                    if update.get("update_type") == "message_created":
                        message = update.get("message", {})
                        chat_id = message.get("recipient", {}).get("chat_id")
                        msg_text = message.get("body", {}).get("text", "")
                        
                        if msg_text and chat_id:
                            print(f"\n📩 Получен шаблон!")
                            posted_count = parse_and_distribute(msg_text)
                            
                            # Отвечаем в ЛС
                            requests.post(f"{API_URL}/messages", headers=HEADERS,
                                          params={"chat_id": chat_id},
                                          json={"text": f"🎉 Готово! Разослано постов: {posted_count} из 15."},
                                          verify=False)
        except Exception as e:
            print(f"Ошибка цикла: {e}")
            time.sleep(5)

if __name__ == "__main__":
    Thread(target=run_web_server, daemon=True).start()
    bot_loop()
