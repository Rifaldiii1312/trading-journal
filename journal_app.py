import streamlit as st
import pandas as pd
import os
from datetime import datetime
import pytesseract
from PIL import Image
import re

DB_FILE = "trading_journal_10to30.csv"
IMG_DIR = "saved_screenshots"

if not os.path.exists(IMG_DIR):
    os.makedirs(IMG_DIR)

def load_data():
    if os.path.exists(DB_FILE):
        try:
            df = pd.read_csv(DB_FILE)
            if not df.empty:
                df["Tanggal"] = pd.to_datetime(df["Tanggal"]).dt.strftime("%Y-%m-%d")
            if "Screenshot" not in df.columns:
                df["Screenshot"] = "-"
            return df
        except:
            pass
    return pd.DataFrame(columns=["Tanggal", "Ticker", "Harga Beli", "Harga Jual", "Lot", "Net Profit/Loss", "Catatan", "Screenshot"])

def save_data(df):
    df.to_csv(DB_FILE, index=False)

# == 1. STYLE & THEME CUSTOMIZATION ==
st.set_page_config(page_title="Trade Summary", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #121212; color: #E0E0E0; }
    .stMetric { background-color: #1E1E1E; padding: 15px; border-radius: 8px; border: 1px solid #2D2D2D; }
    div[data-testid="stMetricValue"] { font-size: 24px !important; font-weight: bold; }
    .stat-box { background-color: #1A1A1A; padding: 20px; border-radius: 8px; border: 1px solid #2D2D2D; margin-bottom: 15px; }
    .green-text { color: #26a69a; font-weight: bold; }
    .red-text { color: #ef5350; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

st.title("📊 Trade Summary")
df_journal = load_data()

# == 2. STATS CALCULATIONS ==
MODAL_AWAL = 10000000
total_pnl = df_journal["Net Profit/Loss"].sum() if not df_journal.empty else 0
ekuitas_sekarang = MODAL_AWAL + total_pnl

total_trades = len(df_journal) if not df_journal.empty else 0
wins = len(df_journal[df_journal["Net Profit/Loss"] > 0]) if total_trades > 0 else 0
losses = len(df_journal[df_journal["Net Profit/Loss"] <= 0]) if total_trades > 0 else 0
win_rate = (wins / total_trades * 100) if total_trades > 0 else 0.0

max_profit = df_journal["Net Profit/Loss"].max() if total_trades > 0 and wins > 0 else 0
max_loss = df_journal["Net Profit/Loss"].min() if total_trades > 0 and losses > 0 else 0

# == 3. LAYOUT UTAMA ==
col_left, col_right = st.columns([1, 2])

with col_left:
    st.markdown("### Performance Overview")
    st.markdown(f"""
    <div class="stat-box">
        <p style='margin-bottom:2px; color:#888;'>Win Rate</p>
        <h2 style='color:#26a69a; margin-top:0;'>{win_rate:.2f}%</h2>
        <p style='font-size:14px; color:#aaa;'>{total_trades} Trades ({wins} Wins / {losses} Losses)</p>
    </div>
    """, unsafe_allow_html=True)
    
    c_p, c_l = st.columns(2)
    with c_p: st.markdown(f"<div class='stat-box'><span style='color:#888; font-size:13px;'>Max Profit</span><br><span class='green-text'>Rp {max_profit:,.0f}</span></div>", unsafe_allow_html=True)
    with c_l: st.markdown(f"<div class='stat-box'><span style='color:#888; font-size:13px;'>Max Loss</span><br><span class='red-text'>Rp {max_loss:,.0f}</span></div>", unsafe_allow_html=True)

with col_right:
    pnl_color = "green-text" if total_pnl >= 0 else "red-text"
    pnl_sign = "+" if total_pnl >= 0 else ""
    st.markdown(f"<div style='padding-left:10px;'><p style='margin-bottom:2px; color:#888;'>Total Realized Gain/Loss</p><h1 class='{pnl_color}' style='margin-top:0;'>{pnl_sign}Rp {total_pnl:,.0f}</h1></div>", unsafe_allow_html=True)
    
    if not df_journal.empty:
        df_sorted = df_journal.sort_values(by="Tanggal").copy()
        df_sorted["Kumulatif PnL"] = df_sorted["Net Profit/Loss"].cumsum()
        df_sorted["Saldo Ekuitas"] = MODAL_AWAL + df_sorted["Kumulatif PnL"]
        st.line_chart(df_sorted.set_index("Tanggal")[["Saldo Ekuitas"]], y="Saldo Ekuitas", use_container_width=True)
    else:
        st.info("Belum ada data. Silakan upload screenshot di bawah!")

st.markdown("---")

# == 4. AUTOMATIC SCANNER (LOKAL) ==
st.markdown("### 📸 Scan Bukti Transaksi (Instant Auto-Entry)")
uploaded_file = st.file_uploader("Upload screenshot dari aplikasi trading lu", type=["png", "jpg", "jpeg"])

if uploaded_file is not None:
    st.image(uploaded_file, caption="Preview Bukti", width=250)
    
    if st.button("🚀 Ekstrak Data & Simpan"):
        with st.spinner("Sistem sedang membaca teks gambar secara lokal..."):
            try:
                # Membaca gambar dengan OCR lokal tanpa API Key
                img = Image.open(uploaded_file)
                extracted_text = pytesseract.image_to_string(img)
                lines = [line.strip() for line in extracted_text.split("\n") if line.strip()]
                
                # --- 1. Deteksi Ticker Saham ---
                ticker = "UNKNOWN"
                for line in lines:
                    match = re.search(r'\b([A-Z]{4})\b', line)
                    if match and "LIMIT" not in line and "STATUS" not in line:
                        ticker = match.group(1)
                        break
                
                # --- 2. Deteksi Angka-angka Utama ---
                harga_jual = 0
                lot = 0
                net_pnl = 0
                
                # Mengumpulkan baris teks penting
                text_block = " ".join(lines).lower()
                
                # Ambil data Harga
                harga_match = re.search(r'harga\s*rp\s*([\d.]+)', text_block)
                if harga_match:
                    harga_jual = float(harga_match.group(1).replace(".", ""))
                
                # Ambil data Lot
                lot_match = re.search(r'lot\s*([\d.]+)', text_block)
                if lot_match:
                    lot = float(lot_match.group(1).replace(".", ""))
                    
                # Ambil data Net Profit/Loss Bersih dari kolom paling bawah Stockbit
                pnl_match = re.search(r'realized profit and loss.*?(-?rp\s*[\d.]+)', text_block)
                if pnl_match:
                    pnl_str = pnl_match.group(1).replace("rp", "").replace(".", "").replace(" ", "")
                    net_pnl = float(pnl_str)
                else:
                    # Fallback kalkulasi manual jika teks pnl tidak tertangkap sempurna
                    # Asumsi harga beli rata-rata diperkirakan dari nominal order bersih
                    net_pnl = 0 
                
                # Hitung estimasi harga beli dari data yang ada
                harga_beli = harga_jual - (net_pnl / (lot * 100)) if lot > 0 else harga_jual
                
                # Simpan file gambar fisik ke server
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                img_path = os.path.join(IMG_DIR, f"{timestamp}_{ticker}.png")
                with open(img_path, "wb") as f:
                    f.write(uploaded_file.getvalue())
                
                # Simpan ke DataFrame
                new_row = pd.DataFrame([{
                    "Tanggal": datetime.now().strftime("%Y-%m-%d"),
                    "Ticker": ticker,
                    "Harga Beli": round(harga_beli, 2),
                    "Harga Jual": harga_jual,
                    "Lot": lot,
                    "Net Profit/Loss": net_pnl,
                    "Catatan": "Auto-scanned via Screenshot",
                    "Screenshot": img_path
                }])
                
                df_journal = pd.concat([df_journal, new_row], ignore_index=True)
                save_data(df_journal)
                st.success(f"🔥 Selesai! Saham {ticker} ({lot} Lot) berhasil masuk jurnal.")
                st.rerun()
                
            except Exception as e:
                st.error(f"Sistem gagal melakukan parsing otomatis. Masalah: {e}")

# == 5. TABEL REKAP & LOG ==
st.markdown("---")
st.markdown("### 📋 Log Semua Transaksi")
if not df_journal.empty:
    for idx, row in df_journal.sort_index(ascending=False).iterrows():
        pnl_val = row['Net Profit/Loss']
        warna_pnl = "green" if pnl_val > 0 else "red"
        
        with st.expander(f"📅 {row['Tanggal']} | 📈 {row['Ticker']} | PnL: :{warna_pnl}[Rp {pnl_val:,.0f}]"):
            c_detail, c_img = st.columns([1, 1])
            with c_detail:
                st.write(f"**Harga Beli (Estimasi):** Rp {row['Harga Beli']:,.0f}")
                st.write(f"**Harga Jual:** Rp {row['Harga Jual']:,.0f}")
                st.write(f"**Jumlah Lot:** {row['Lot']} Lot")
                st.write(f"**Catatan:** {row['Catatan']}")
            with c_img:
                if "Screenshot" in row and row['Screenshot'] != "-" and os.path.exists(str(row['Screenshot'])):
                    st.image(str(row['Screenshot']), width=220)
else:
    st.caption("Belum ada riwayat transaksi.")
