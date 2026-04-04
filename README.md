# 🎯 nazBot Alpha 2.0
**Hybrid Sniper Dashboard & Long-Only DCA Bot for Binance Futures**

## 📌 Deskripsi Sistem
nazBot Alpha 2.0 adalah bot trading otomatis untuk Binance Futures yang didesain khusus untuk kondisi *bull market* atau *bear market* di area *major support*. Bot ini menggunakan strategi **LONG ONLY** dengan jaring pengaman berupa **DCA (Dollar Cost Averaging) Presisi 3 Lapis** tanpa menggunakan Stop Loss (Mode Survival/HODL).

Sistem ini berjalan dengan arsitektur *multi-threading* yang memisahkan mesin *trading* utama dengan *dashboard web* antarmuka (Flask) agar pemantauan berjalan *real-time* tanpa mengganggu proses pemindaian pasar.

---

## ⚙️ Parameter Trading & Manajemen Risiko

* **Mode Eksekusi:** LONG ONLY (Hanya mencari peluang pantulan/Buy).
* **Leverage:** Fixed **50x**.
    * *Auto-Adjust Feature:* Jika Binance menolak 50x (Error -4028) karena batasan koin, bot otomatis mendeteksi batas maksimal leverage koin tersebut (misal 20x atau 25x) dan menyesuaikan ukuran kuantitas (*quantity*) agar ekuivalen margin tetap sama.
* **Take Profit (TP):** **100% ROE** dari margin aktual. Dipasang saat *entry* pertama menggunakan order `TAKE_PROFIT_MARKET` (dengan *fallback* ke `LIMIT` jika gagal).
* **Stop Loss (SL):** **DISABLED** (Tidak ada cut loss otomatis).

---

## 💰 Strategi Margin & DCA (Dollar Cost Averaging)
Bot menggunakan sistem penambahan muatan (*average down*) bertahap berdasarkan persentase ROE (*Return on Equity*) yang minus. Alokasi dana dikunci dengan nominal USD absolut, bukan persentase lot, agar ketahanan dana sangat terukur.

* **Entry Awal:** $5 USDT.
* **DCA Tahap 1:** Tembak **$3 USDT** saat posisi menyentuh **-100% ROE**.
* **DCA Tahap 2:** Tembak **$3 USDT** saat posisi menyentuh **-150% ROE**.
* **DCA Tahap 3 (Max):** Tembak **$10 USDT** saat posisi menyentuh **-300% ROE**.

*Catatan: Bot memiliki toleransi pembacaan selisih margin untuk memastikan bot tidak menembak DCA dua kali di tahap yang sama akibat fluktuasi harga.*

---

## 📊 Analisis Teknikal (Strategi "4 Tembok Sniper")
Bot melakukan *entry* jika kondisi di bawah ini terpenuhi. Bot memadukan indikator dinamis (*Lagging*) dan indikator statis (*Leading*) sebagai tembok pantulan:

1. **Floor Detection (4 Tembok):** Bot akan mendeteksi apakah harga menyentuh salah satu dari tembok berikut (margin kedekatan 0.3%):
   * **Tembok Dinamis:** EMA 200, SMA 99, atau Bollinger Bands Lower (Window 20, Dev 2).
   * **Tembok Statis (Historical Support):** Titik harga terendah dari 100 *candle* terakhir (mengabaikan 5 *candle* terbaru).
2. **Candle Pattern (Rejection):**
   * Jika harga menyentuh salah satu tembok di atas, bot melihat *candle* sebelumnya.
   * *Candle* tersebut harus ditutup *Bullish* (Close > Open).
   * Harus memiliki ekor bawah (*lower shadow*) yang panjang. Rasio ekor dibanding badan *candle* minimal **2.0x untuk VIP** dan **0.8x untuk Altcoin**.
3. **Volume Exhaustion:** Volume *candle* sebelumnya harus lebih kecil dari rata-rata volume 5 periode terakhir (*Volume MA 5*), menandakan tekanan jual (*seller*) sudah melemah.

---

## 🗂️ Manajemen Portofolio (Alokasi Slot)
Bot membagi jatah pemindaian pasar menjadi dua kategori dengan *Timeframe* (TF) yang berbeda untuk diversifikasi risiko:

1.  **Koin VIP (Maksimal 6 Posisi Aktif)**
    * Koin: `BTCUSDT`, `ETHUSDT`, `SOLUSDT`, `BNBUSDT`, `ADAUSDT`, `DOTUSDT`.
    * Timeframe: Khusus **15m** (Lebih stabil).
2.  **Koin Altcoin (Maksimal 8 Posisi Aktif)**
    * Koin: Memindai Top 50 Altcoin berdasarkan volume harian tertinggi (mengabaikan koin VIP).
    * Timeframe: Agresif mencari peluang di multi-TF: **1m, 3m, 5m, 15m, 1h, 4h**.
    * Jika salah satu TF memberikan sinyal valid, bot akan *entry* dan melompati TF lainnya untuk koin tersebut.

---

## 📁 Struktur File Sistem

1.  `main.py`: File *launcher* utama. Menjalankan *Flask server* dan *Trading engine* secara paralel.
2.  `app.py`: Modul Dashboard Web UI.
    * Menampilkan saldo murni USDT, Net Profit, dan Floating PNL.
    * Memisahkan pemantauan koin ke dalam 2 tabel: **VIP Positions** dan **Altcoin Positions**.
    * Menampilkan badge informasi *Leverage Auto-Adjust*.
3.  `bot_logic.py`: Mesin *core trading*.
    * Berisi seluruh logika indikator teknikal (Pandas & TA-Lib) dan sistem 4 Tembok.
    * Sistem eksekusi order dengan perlindungan Error API (termasuk *Bypass* Error -4028 Leverage).
    * Mencetak *log* cerdas yang memberitahu alasan *entry* (apakah karena Tembok Dinamis atau Tembok Statis).

---

## 🛠️ Cara Instalasi (Disini saya pakai https://replit.com/ untuk host vps, kalian bisa gunakan sesuai selera)

1.  **Environment:** Pastikan Python 3.10+ terinstal.
2.  **API Keys:** Masukkan `BINANCE_API_KEY` dan `BINANCE_API_SECRET` ke dalam Secrets Replit atau `.env`.
3.  **Requirements:** `pip install -r requirements.txt`
4.  **Run:** Jalankan `python main.py` dan akses dashboard di port 8080.

---

## ⚠️ Disclaimer
*Trading Futures memiliki risiko tinggi. nazBot Alpha 2.0 adalah alat bantu teknis. Pengguna bertanggung jawab penuh atas konfigurasi leverage dan margin yang digunakan. Disarankan uji coba di Testnet terlebih dahulu.*
