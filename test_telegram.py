import requests

# Masukkan HTTP API Token dari @BotFather dan Chat ID dari @userinfobot
BOT_TOKEN = "9056835986:AAEZzqcwJJ9KGxBPmmJZHQyNA_7khtFWUF4"
CHAT_ID = "7152729628"

def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        print("✅ Notifikasi berhasil terkirim ke Telegram!")
    else:
        print(f"❌ Gagal mengirim notifikasi: {response.text}")

# Pesan Uji Coba Sinyal
pesan_test = """
🚀 *TDSS SIGNAL ALERT (TEST)*

📈 *TLKM.JK (Telekomunikasi Indonesia)*
 status: ☪ *SYARIAH*
 Sinyal: *STRONG BUY*
 Area Beli: Rp 3.800 - Rp 3.850
 Target Profit: Rp 4.050 (+5.2%)
 Stop Loss: Rp 3.720 (-2.6%)

_Pesan ini dikirim otomatis dari sistem TDSS kamu._
"""

send_telegram_alert(pesan_test)