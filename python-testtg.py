import requests

BOT_TOKEN = "8600824286:AAHUvA1Q9AQ0SgkbjX7AlJzvKly2bJ6hSe8"
CHAT_ID = "1215866388"

# Меняем http:// на socks5h://
PROXY = {
    "http": "socks5h://eYH8wA:RTF88s@145.85.163.75:8000",
    "https": "socks5h://eYH8wA:RTF88s@145.85.163.75:8000"
}

url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
payload = {"chat_id": CHAT_ID, "text": "🛠 SOCKS5 Прокси пробит! Связь установлена."}

print("Стучимся в серверы Telegram через SOCKS5...")
try:
    response = requests.post(url, json=payload, proxies=PROXY, timeout=15)
    print(f"Код ответа: {response.status_code}")
except Exception as e:
    print(f"Ошибка сети: {e}")