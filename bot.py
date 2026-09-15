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

# Минимальный веб-сервер
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
    "настя": -78584631723264
}

API_URL = "https://platform-api2.max.ru"
HEADERS = {"Authorization": MAX_BOT_TOKEN}

def send_message_to_channel(channel_id, text):
    url = f"{API_URL}/messages"
    params = {"chat_id": channel_id}
    payload = {"text": text}
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
    pattern = r'\((.*?)\)\s*\n([^()]+)'
    matches = re.findall(pattern, full_text)
    print(f"🔍 Найдено совпадений: {len(matches)}", flush=True)
    
    count = 0
    for channel_raw, post_text in matches:
        channel_name = channel_raw.strip().lower()
        clean_post = post_text.strip()
        print(f"🔎 Канал: '{channel_name}', текст: '{clean_post[:50]}'", flush=True)
        
        if channel_name in CHANNELS:
            channel_id = CHANNELS[channel_name]
            success = send_message_to_channel(channel_id, clean_post)
            if success:
                print(f"✅ Успешно выложено в [{channel_name}]", flush=True)
                count += 1
            time.sleep(1)
        else:
            print(f"⚠️ Канал '{channel_name}' не найден!", flush=True)
            
    return count

def bot_loop():
    marker = None
    print("🚀 bot_loop() НАЧАЛ РАБОТУ", flush=True)
    
    # --- УДАЛЯЕМ WEBHOOK-ПОДПИСКИ (чтобы работал Long Polling) ---
    print("🧹 Проверяю и удаляю webhook-подписки...", flush=True)
    try:
        subs_res = requests.get(f"{API_URL}/subscriptions", headers=HEADERS, verify=False)
        print(f"📋 Ответ /subscriptions: {subs_res.status_code} - {subs_res.text[:500]}", flush=True)
        subs_data = subs_res.json()
        if "subscriptions" in subs_data and subs_data["subscriptions"]:
            for sub in subs_data["subscriptions"]:
                url_to_del = sub.get("url")
                if url_to_del:
                    del_res = requests.delete(f"{API_URL}/subscriptions", headers=HEADERS, params={"url": url_to_del}, verify=False)
                    print(f"🗑️ Удалена подписка {url_to_del}: {del_res.status_code}", flush=True)
        else:
            print("✅ Активных webhook-подписок нет", flush=True)
    except Exception as e:
        print(f"⚠️ Ошибка при удалении подписок: {e}", flush=True)
    # -----------------------------------------------------------
    
    while True:
        try:
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
                        chat_id = message.get("recipient", {}).get("chat_id")
                        msg_text = message.get("body", {}).get("text", "")
                        
                        if msg_text and chat_id:
                            print(f"📩 Получен шаблон!", flush=True)
                            posted_count = parse_and_distribute(msg_text)
                            
                            requests.post(f"{API_URL}/messages", headers=HEADERS,
                                          params={"chat_id": chat_id},
                                          json={"text": f"🎉 Готово! Разослано постов: {posted_count} из 15."},
                                          verify=False)
        except Exception as e:
            print(f"❌ Ошибка цикла: {e}", flush=True)
            time.sleep(5)

if __name__ == "__main__":
    print("🔧 Запускаю веб-сервер в фоне и бота в основном потоке", flush=True)
    Thread(target=run_web_server, daemon=True).start()
    print("🔧 Веб-сервер запущен, теперь запускаю bot_loop()", flush=True)
    bot_loop()
