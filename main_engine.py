import yfinance as yf
import pandas as pd
import requests

# ==========================================
# CONFIGURATION & TELEGRAM CREDENTIALS
# ==========================================
BOT_TOKEN = "9056835986:AAEZzqcwJJ9KGxBPmmJZHQyNA_7khtFWUF4"
CHAT_ID = "7152729628"

# SETTING FILTER NOTIFIKASI
ENABLE_BUY_ALERT = True   # Kirim notifikasi jika sinyal STRONG BUY
ENABLE_SELL_ALERT = True  # Kirim notifikasi jika sinyal SELL / EXIT
ONLY_SYARIAH = True       # Hanya analisis saham Syariah

# Daftar Saham yang Dipantau & Status Syariah
WATCHLIST = {
    "TLKM.JK": {"name": "Telekomunikasi Indonesia", "syariah": True},
    "ICBP.JK": {"name": "Indofood CBP", "syariah": True},
    "UNVR.JK": {"name": "Unilever Indonesia", "syariah": True},
    "BBCA.JK": {"name": "Bank Central Asia", "syariah": False},
    "ASII.JK": {"name": "Astra International", "syariah": False}
}

# ==========================================
# FUNCTION: SEND TELEGRAM NOTIFICATION
# ==========================================
def send_telegram_alert(ticker, name, is_syariah, signal, price, entry_low, entry_high, tp, sl, score, exit_reason=""):
    syariah_status = "☪ *SYARIAH (DES/OJK)*" if is_syariah else "⚠️ *NON-SYARIAH*"
    
    if signal == "STRONG BUY":
        pesan = f"""
🚀 *TDSS STRONG BUY ALERT*

📈 *{name} ({ticker})*
Status: {syariah_status}
Sinyal Eksekusi: *STRONG BUY* (Skor: {score}%)

💵 *Harga Terakhir:* Rp {price:,.0f}
🎯 *Area Beli (Entry):* Rp {entry_low:,.0f} - Rp {entry_high:,.0f}
🚀 *Target Profit (TP):* Rp {tp:,.0f} (+5%)
🛡️ *Stop Loss (SL):* Rp {sl:,.0f} (-2.5%)

_Dianalisis otomatis oleh sistem TDSS_
"""
    elif signal == "SELL":
        pesan = f"""
🔻 *TDSS EXIT / SELL ALERT*

📉 *{name} ({ticker})*
Status: {syariah_status}
Sinyal Eksekusi: *SELL / EXIT* (Skor: {score}%)

💵 *Harga Terakhir:* Rp {price:,.0f}
⚠️ *Alasan Keluar:* {exit_reason}

💡 *Saran Tindakan:* Pertimbangkan untuk amankan profit (Take Profit) atau lakukan pembatasan risiko (Cut Loss) di aplikasi Bibit kamu.

_Dianalisis otomatis oleh sistem TDSS_
"""

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": pesan, "parse_mode": "Markdown"}
    requests.post(url, json=payload)

# ==========================================
# FUNCTION: TECHNICAL ANALYSIS ENGINE
# ==========================================
def analyze_stock(ticker, info):
    if ONLY_SYARIAH and not info['syariah']:
        print(f"⏩ Melewati {ticker} (Bukan Saham Syariah)")
        return

    print(f"📊 Menganalisis data saham: {ticker}...")
    
    df = yf.download(ticker, period="1y", interval="1d", progress=False)
    
    if df.empty or len(df) < 200:
        print(f"❌ Data tidak cukup untuk {ticker}")
        return

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    # 1. Indikator EMA 50 & EMA 200
    df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()
    df['EMA200'] = df['Close'].ewm(span=200, adjust=False).mean()

    # 2. Indikator MACD (12, 26, 9)
    ema12 = df['Close'].ewm(span=12, adjust=False).mean()
    ema26 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = ema12 - ema26
    df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()

    # 3. Indikator Volume Moving Average (VMA 20)
    df['VMA20'] = df['Volume'].rolling(window=20).mean()

    last_row = df.iloc[-1]
    prev_row = df.iloc[-2]
    current_price = float(last_row['Close'])

    score = 0
    exit_reasons = []

    # Check 1: Trend Filter
    is_above_ema = current_price > float(last_row['EMA50']) and current_price > float(last_row['EMA200'])
    if is_above_ema:
        score += 35
    else:
        exit_reasons.append("Harga di bawah garis EMA 50/200 (Tren Melemahn/Bearish)")

    # Check 2: MACD Momentum
    is_macd_bullish = float(last_row['MACD']) > float(last_row['Signal_Line'])
    if is_macd_bullish:
        score += 35
    else:
        exit_reasons.append("MACD Bearish / Dead Cross")

    # Check 3: Volume Spike
    if float(last_row['Volume']) > float(last_row['VMA20']):
        score += 30

    # Penentuan Sinyal Akhir
    if score >= 70:
        signal = "STRONG BUY"
    elif score >= 40:
        signal = "HOLD"
    else:
        signal = "SELL"

    print(f"🔍 {ticker}: Sinyal = {signal} (Skor: {score}%)")

    # Filter Pengiriman Notifikasi Telegram
    if signal == "STRONG BUY" and ENABLE_BUY_ALERT:
        entry_low = current_price * 0.995
        entry_high = current_price * 1.005
        tp = current_price * 1.05
        sl = current_price * 0.975

        send_telegram_alert(
            ticker=ticker, name=info['name'], is_syariah=info['syariah'],
            signal=signal, price=current_price, entry_low=entry_low,
            entry_high=entry_high, tp=tp, sl=sl, score=score
        )
        print(f"📩 Notifikasi STRONG BUY untuk {ticker} dikirim!")

    elif signal == "SELL" and ENABLE_SELL_ALERT:
        reason_text = " & ".join(exit_reasons) if exit_reasons else "Indikator teknikal melemah"
        
        send_telegram_alert(
            ticker=ticker, name=info['name'], is_syariah=info['syariah'],
            signal=signal, price=current_price, entry_low=0, entry_high=0,
            tp=0, sl=0, score=score, exit_reason=reason_text
        )
        print(f"📩 Notifikasi SELL / EXIT untuk {ticker} dikirim!")

# ==========================================
# MAIN EXECUTION
# ==========================================
if __name__ == "__main__":
    print("🚀 Memulai Scanning Sinyal Saham (BUY & SELL Alert Mode)...\n")
    for ticker, info in WATCHLIST.items():
        analyze_stock(ticker, info)
    print("\n🎉 Scanning Selesai!")