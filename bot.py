import time
import re
import requests

# 1. Твой API токен бота в МАКС
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

BASE_URL = f"https://api.max.ru/bot{MAX_BOT_TOKEN}"

def send_message_to_channel(channel_id, text):
    """Отправка сообщения в канал МАКС"""
    url = f"{BASE_URL}/sendMessage"
    payload = {
        "chat_id": channel_id,
        "text": text
    }
    try:
        res = requests.post(url, json=payload)
        return res.status_code == 200
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
            else:
                print(f"❌ Ошибка отправки в [{channel_name}]")
            time.sleep(1)
        else:
            print(f"⚠️ Канал '{channel_name}' не найден в базе ID!")
            
    return count

def main():
    """Слушаем сообщения, приходящие боту в ЛС"""
    last_update_id = 0
    print("🚀 Бот-автопостер для МАКС запущен на Render и ждёт шаблонов!")
    
    while True:
        try:
            url = f"{BASE_URL}/getUpdates?offset={last_update_id + 1}&timeout=30"
            response = requests.get(url).json()
            
            if "result" in response:
                for update in response["result"]:
                    last_update_id = update["update_id"]
                    
                    if "message" in update and "text" in update["message"]:
                        chat_id = update["message"]["chat"]["id"]
                        msg_text = update["message"]["text"]
                        
                        print(f"\n📩 Получен новый шаблон от пользователя!")
                        posted_count = parse_and_distribute(msg_text)
                        
                        reply_url = f"{BASE_URL}/sendMessage"
                        requests.post(reply_url, json={
                            "chat_id": chat_id,
                            "text": f"🎉 Готово! Разослано постов: {posted_count} из 15."
                        })
        except Exception as e:
            print(f"Ошибка цикла: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
