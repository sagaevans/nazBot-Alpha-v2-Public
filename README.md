# 🎯 nazBot Beta v1.0 — Binance Futures Sniper Bot

**nazBot Beta v1.0** adalah sistem trading otomatis berbasis Python yang dirancang khusus untuk pasar Binance Futures. Bot ini menggunakan pendekatan "Sniper" yang sangat disiplin, menggabungkan konfluensi teknikal tingkat tinggi dengan manajemen risiko dinamis untuk menjaga keamanan modal $5000.

---

## 🚀 Fitur Utama (Beta v1.0)

### 1. Strategi "4 Walls" (Core Engine)
Bot hanya akan melakukan entry jika harga membentur salah satu dari "Dinding Pertahanan":
* **Dynamic Wall:** EMA200, MA99, atau Lower Bollinger Band.
* **Static Support:** Area harga terendah (Low) dalam rentang 100 candle terakhir.
* **Confirmation:** Ditambah dengan filter *Volume Exhaustion*, *Shadow Rejection* (ekor candle panjang), dan *RSI Oversold* (< 35).

### 2. Hybrid Timeframe Strategy (New)
Sistem pembagian kuota untuk efisiensi dan kecepatan profit:
* **4 Slot Altcoin Agresif:** Menggunakan Timeframe **5m** untuk eksekusi cepat (Scalping).
* **4 Slot Altcoin Stabil:** Menggunakan Timeframe **15m ke atas** untuk trend yang lebih terjaga.
* **8 Slot VIP:** (BTC, ETH, SOL, dll) dipantau pada timeframe multi (15m, 1h, 4h).

### 3. Logika DCA Dinamis (Tabel Excel Logic)
Manajemen anti-bengkak margin yang menyesuaikan dengan Leverage (Default 50x):
* **DCA 1:** Aktif saat harga turun **2%** (ROE -100% di 50x) | Suntikan: 50% Margin Awal.
* **DCA 2:** Aktif saat harga turun **3%** (ROE -150% di 50x) | Suntikan: 50% Margin Awal.
* **DCA 3:** Aktif saat harga turun **4%** (ROE -200% di 50x) | Suntikan: 100% Margin Awal.

### 4. Smart Trend Filter
Mencegah *Entry* saat market sedang terjun bebas (*Falling Knife*). Bot hanya akan melakukan **LONG** jika harga berada di atas **EMA200 (15m)** untuk koin Altcoin.

---

## 📊 Dashboard & Monitoring

Bot dilengkapi dengan Web Dashboard (Flask) yang menyediakan data real-time:
* **Wallet Summary:** Saldo USDT aktif, Net Profit, dan Total Ekuitas.
* **Termometer ROE:** Menampilkan "Akumulasi ROE Margin" secara murni untuk melihat total beban posisi aktif.
* **Papan Skor (Success History):** Mencatat setiap koin yang berhasil Take Profit (TP 50%) lengkap dengan waktu eksekusi.
* **Panic Button:** Fitur "Close All Positions" untuk menutup semua posisi secara instan jika diperlukan.

---

## 🛠️ Spesifikasi Teknis

* **Bahasa:** Python 3.10+
* **Library Utama:** `python-binance`, `pandas`, `ta` (Technical Analysis Library), `Flask`.
* **Environment:** Optimal dijalankan di Replit (mendukung mode 24/7).
* **Koneksi:** Menggunakan `ThreadPoolExecutor` untuk pemindaian 50+ koin secara simultan (Parallel Scanning).

---

## 📝 Cara Penggunaan

1.  **API Setup:** Masukkan `BINANCE_API_KEY` dan `BINANCE_API_SECRET` ke dalam Secrets/Environment Variables.
2.  **Initial Setup:** Jalankan `main.py`. Bot akan memulai server dashboard di port 8080.
3.  **Activation:** Buka dashboard melalui link `.replit.dev`, lalu klik **START BOT**.
4.  **Monitoring:** Pantau console untuk log "Heartbeat" setiap 60 detik untuk memastikan sistem OK.

---

## 🛡️ Manajemen Risiko (Safety First)
* **No Stop Loss (Sniper Mode):** Mengandalkan kekuatan DCA di level psikologis dan filter trend EMA200.
* **Dynamic Margin Balancing:** Bot secara otomatis menyesuaikan jumlah koin yang dibeli (Quantity) berdasarkan leverage maksimal yang diizinkan Binance untuk setiap simbol.
* **Rate Limiter:** Proteksi bawaan agar akun tidak terkena *ban* API Binance akibat request yang terlalu cepat.


## 🛠️ Cara Instalasi (Telah diuji di Replit)

1.  **Environment:** Pastikan Python 3.10+ terinstal.
2.  **API Keys:** Masukkan `BINANCE_API_KEY` dan `BINANCE_API_SECRET` ke dalam *Secrets* Replit atau file `.env`.
3.  **Requirements:** Jalankan `pip install -r requirements.txt` (Pastikan `pandas`, `numpy`, `ta`, `python-binance`, dan `flask` tercantum).
4.  **Run:** Jalankan `python main.py` dan akses dashboard di port 8080.

---

## ⚠️ Disclaimer
*Trading Futures memiliki risiko tinggi. nazBot Alpha 4.0 adalah alat bantu teknis. Pengguna bertanggung jawab penuh atas konfigurasi leverage dan margin yang digunakan. Sangat disarankan untuk melakukan uji coba secara menyeluruh di Testnet Binance sebelum digunakan di akun Real.*
