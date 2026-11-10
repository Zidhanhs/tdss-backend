from flask import Flask, jsonify, request
from flask_cors import CORS
import yfinance as yf
import pandas as pd
import requests
import schedule
import time
import threading

app = Flask(__name__)
CORS(app)

TELEGRAM_TOKEN = '9056835986:AAEZzqcwJJ9KGxBPmmJZHQyNA_7khtFWUF4'
TELEGRAM_CHAT_ID = '7152729628'

WATCHLIST = {
    "TLKM.JK": {"name": "Telekomunikasi Indonesia Tbk", "syariah": True},
    "ICBP.JK": {"name": "Indofood CBP Sukses Makmur Tbk", "syariah": True},
    "UNVR.JK": {"name": "Unilever Indonesia Tbk", "syariah": True},
    "BBCA.JK": {"name": "Bank Central Asia Tbk", "syariah": False},
    "ASII.JK": {"name": "Astra International Tbk", "syariah": False}
}

# ==========================================
# FUNGSI 1: AUTO-SCANNER (BERJALAN DI LATAR BELAKANG)
# ==========================================
def run_auto_scanner():
    print("\n🔍 [AUTO-SCANNER] Memulai pemindaian pasar otomatis...")
    for ticker, info in WATCHLIST.items():
        try:
            df = yf.download(ticker, period="1y", interval="1d", progress=False)
            if df.empty or len(df) < 200: continue
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()
            df['EMA200'] = df['Close'].ewm(span=200, adjust=False).mean()
            df['MACD'] = df['Close'].ewm(span=12, adjust=False).mean() - df['Close'].ewm(span=26, adjust=False).mean()
            df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()
            df['VMA20'] = df['Volume'].rolling(window=20).mean()

            last_row = df.iloc[-1]
            current_price = float(last_row['Close'])

            trend = current_price > float(last_row['EMA50']) and current_price > float(last_row['EMA200'])
            macd = float(last_row['MACD']) > float(last_row['Signal_Line'])
            volume = float(last_row['Volume']) > float(last_row['VMA20'])

            score = 0
            if trend: score += 35
            if macd: score += 35
            if volume: score += 30

            # HANYA KIRIM ALERT JIKA SINYALNYA BAGUS (STRONG BUY ATAU HOLD)
            if score >= 40:
                signal = "STRONG BUY" if score >= 70 else "HOLD"
                
                pesan = f"""🤖 *AUTO-SCANNER TERDETEKSI!* 🤖
*{ticker}* - {info['name']}

*Rekomendasi:* {signal} 🟢
*Skor Teknikal:* {score}%
*Harga Saat Ini:* Rp {current_price:,.0f}

*Trading Plan:*
- Area Entry: Rp {current_price * 0.995:,.0f} - Rp {current_price * 1.005:,.0f}
- Target Profit: Rp {current_price * 1.05:,.0f}
- Stop Loss: Rp {current_price * 0.975:,.0f}

_Pemindaian Latar Belakang TDSS Engine_"""

                url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
                requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": pesan, "parse_mode": "Markdown"})
                print(f"✅ Alert otomatis {ticker} terkirim!")
                
        except Exception as e:
            print(f"❌ Error scanner {ticker}: {e}")
    print("✅ [AUTO-SCANNER] Pemindaian selesai. Menunggu jadwal berikutnya...\n")

def start_scheduler():
    # Berjalan otomatis setiap hari jam 09:15 pagi (waktu laptop/server)
    schedule.every().day.at("09:15").do(run_auto_scanner)
    
    while True:
        schedule.run_pending()
        time.sleep(1)

# ==========================================
# FUNGSI 2: API UNTUK WEB REACT (SAMA SEPERTI SEBELUMNYA)
# ==========================================
@app.route('/api/stocks', methods=['GET'])
def get_stocks():
    # (Kode ini sudah diringkas agar tetap jalan normal untuk Web)
    results = []
    for ticker, info in WATCHLIST.items():
        try:
            df = yf.download(ticker, period="1y", interval="1d", progress=False)
            if df.empty: continue
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()
            df['EMA200'] = df['Close'].ewm(span=200, adjust=False).mean()
            df['MACD'] = df['Close'].ewm(span=12, adjust=False).mean() - df['Close'].ewm(span=26, adjust=False).mean()
            df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()
            df['VMA20'] = df['Volume'].rolling(window=20).mean()
            last = df.iloc[-1]
            price = float(last['Close'])
            prev = float(df.iloc[-2]['Close'])
            trend = price > float(last['EMA50']) and price > float(last['EMA200'])
            macd = float(last['MACD']) > float(last['Signal_Line'])
            vol = float(last['Volume']) > float(last['VMA20'])
            score = (35 if trend else 0) + (35 if macd else 0) + (30 if vol else 0)
            sig = "STRONG BUY" if score >= 70 else "HOLD" if score >= 40 else "SELL"
            results.append({
                "ticker": ticker, "name": info['name'], "price": price, 
                "change": round(((price - prev) / prev) * 100, 2),
                "isSyariah": info['syariah'], "signal": sig, "score": score,
                "entryLow": price * 0.995 if sig != 'SELL' else 0, "entryHigh": price * 1.005 if sig != 'SELL' else 0,
                "tp": price * 1.05 if sig != 'SELL' else 0, "sl": price * 0.975 if sig != 'SELL' else 0,
                "rrRatio": "1 : 2.1" if sig != 'SELL' else "N/A",
                "checks": {"trend": trend, "macd": macd, "volume": vol, "syariah": info['syariah']},
                "chartData": [{"date": d.strftime('%d %b'), "price": float(r['Close']), "ema50": float(r['EMA50'])} for d, r in df.tail(30).iterrows()]
            })
        except Exception: pass
    return jsonify(results)

@app.route('/api/telegram', methods=['POST'])
def send_telegram():
    data = request.json
    pesan = f"🚨 *TDSS MANUAL ALERT: {data['ticker']}* 🚨\n🏢 {data['name']}\n\n*Rekomendasi:* {data['signal']}\n*Harga Saat Ini:* Rp {data['price']:,.0f}\n*Skor Teknikal:* {data['score']}%\n\n_Dikirim via Web TDSS_"
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={"chat_id": TELEGRAM_CHAT_ID, "text": pesan, "parse_mode": "Markdown"})
    return jsonify({"status": "success"})

if __name__ == '__main__':
    # Nyalakan Robot Auto-Scanner di dimensi latar belakang
    threading.Thread(target=start_scheduler, daemon=True).start()
    
    # Nyalakan API Server untuk Web
    app.run(port=5000, debug=True, use_reloader=False)