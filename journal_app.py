import streamlit as st
import pandas as pd
import os
from datetime import datetime
import google.generativeai as genai
from PIL import Image
import json

# == 1. CONFIGURATION & AI SETUP ==
GEMINI_API_KEY = "AQ.Ab8RN6IkO8MceS6LfQtRDYl57T5IEBfFKmUZ3Jabg0V-_82dqg"  # <-- MASUKIN API KEY LU DI SINI
genai.configure(api_key=GEMINI_API_KEY)

DB_FILE = "trading_journal_10to30.csv"

def load_data():
    if os.path.exists(DB_FILE):
        df = pd.read_csv(DB_FILE)
        df["Tanggal"] = pd.to_datetime(df["Tanggal"]).dt.strftime("%Y-%m-%d")
        return df
    else:
        return pd.DataFrame(columns=["Tanggal", "Ticker", "Aksi", "Harga Beli", "Harga Jual", "Lot", "Net Profit/Loss", "Catatan"])

def save_data(df):
    df.to_csv(DB_FILE, index=False)

# == 2. STREAMLIT UI SETUP ==
st.set_page_config(page_title="Road to 30M", layout="wide")
st.title("📈 AI Trading Journal: Road to 30 Juta")
st.caption("Modal Awal: Rp 10.000.000 | Target: Rp 30.000.000")

df_journal = load_data()

# == 3. FINANCIAL CALCULATIONS ==
MODAL_AWAL = 10000000
TARGET_AKHIR = 30000000
total_pnl = df_journal["Net Profit/Loss"].sum() if not df_journal.empty else 0
ekuitas_sekarang = MODAL_AWAL + total_pnl
progres_persen = min(max((ekuitas_sekarang - MODAL_AWAL) / (TARGET_AKHIR - MODAL_AWAL), 0.0), 1.0)

# Dashboard Metrics
col1, col2, col3, col4 = st.columns(4)
col1.metric("Ekuitas Sekarang", f"Rp {ekuitas_sekarang:,.0f}")
col2.metric("Total PnL", f"Rp {total_pnl:,.0f}", delta=f"{total_pnl:,.0f}")
col3.metric("Sisa Target", f"Rp {max(TARGET_AKHIR - ekuitas_sekarang, 0):,.0f}")

if not df_journal.empty and len(df_journal[df_journal["Aksi"] == "Jual"]) > 0:
    trades_jual = df_journal[df_journal["Aksi"] == "Jual"]
    win_rate = (len(trades_jual[trades_jual["Net Profit/Loss"] > 0]) / len(trades_jual)) * 100
    col4.metric("Win Rate", f"{win_rate:.1f}%")
else:
    col4.metric("Win Rate", "0%")

st.progress(progres_persen, text=f"Progress Target: {progres_persen*100:.1f}%")

# == 4. GRAFIK VISUALISASI REAL-TIME ==
st.markdown("### 📊 Tren Pertumbuhan Modal")
if not df_journal.empty:
    # Urutkan berdasarkan tanggal untuk dapet grafik akumulasi yang benar
    df_sorted = df_journal.sort_values(by="Tanggal").copy()
    df_sorted["Kumulatif PnL"] = df_sorted["Net Profit/Loss"].cumsum()
    df_sorted["Saldo Ekuitas"] = MODAL_AWAL + df_sorted["Kumulatif PnL"]
    
    # Bikin data frame terpisah khusus grafik biar rapi
    chart_data = df_sorted[["Tanggal", "Saldo Ekuitas"]].set_index("Tanggal")
    st.line_chart(chart_data, y="Saldo Ekuitas", use_container_width=True)
else:
    st.info("Grafik akan muncul otomatis setelah lu upload transaksi pertama!")

st.markdown("---")

# == 5. INPUT VIA AI SCREENSHOT & MANUAL ==
st.subheader("📸 Input Jurnal via Screenshot AI")
uploaded_file = st.file_uploader("Upload screenshot portfolio / bukti trade lu di sini", type=["png", "jpg", "jpeg"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="Preview Screenshot", width=300)
    
    if st.button("🚀 Biarkan AI Analisis & Simpan"):
        with st.spinner("AI Gemini lagi ngebaca screenshot lu..."):
            try:
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                prompt = """
                Analisis gambar screenshot trading ini (bisa berupa saham atau kripto). 
                Ekstrak informasi penting dan kembalikan data HANYA dalam format JSON mentah tanpa format markdown seperti berikut:
                {
                    "Ticker": "KODE ASET SAJA",
                    "Aksi": "Beli" atau "Jual",
                    "Harga Beli": angka_saja,
                    "Harga Jual": angka_saja_jika_jual_jika_beli_isi_0,
                    "Lot": angka_saja,
                    "Catatan": "Ringkasan transaksi otomatis oleh AI"
                }
                Pastikan hanya mengembalikan JSON yang valid agar bisa diparsing.
                """
                
                response = model.generate_content([prompt, image])
                cleaned_text = response.text.strip().replace("```json", "").replace("```", "")
                data_api = json.loads(cleaned_text)
                
                # Hitung otomatis Net PnL jika aksi Jual
                net_pnl = 0
                if data_api["Aksi"] == "Jual" and data_api["Harga Jual"] > 0:
                    pengali = 100 if data_api["Lot"] >= 1 else 1
                    net_pnl = (data_api["Harga Jual"] - data_api["Harga Beli"]) * data_api["Lot"] * pengali
                    net_pnl -= (data_api["Harga Beli"] * data_api["Lot"] * pengali + data_api["Harga Jual"] * data_api["Lot"] * pengali) * 0.002
                
                new_row = pd.DataFrame([{
                    "Tanggal": datetime.now().strftime("%Y-%m-%d"),
                    "Ticker": data_api["Ticker"],
                    "Aksi": data_api["Aksi"],
                    "Harga Beli": data_api["Harga Beli"],
                    "Harga Jual": data_api["Harga Jual"],
                    "Lot": data_api["Lot"],
                    "Net Profit/Loss": net_pnl,
                    "Catatan": data_api["Catatan"]
                }])
                
                df_journal = pd.concat([df_journal, new_row], ignore_index=True)
                save_data(df_journal)
                st.success(f"Berhasil! AI mendeteksi trade {data_api['Ticker']} ({data_api['Aksi']}) dan sudah disimpan ke jurnal.")
                st.rerun()
                
            except Exception as e:
                st.error(f"Gagal membaca gambar. Pastikan gambar jelas. Error: {e}")

# == 6. HISTORY TABLE ==
st.markdown("---")
st.subheader("📜 Riwayat Trading")
if not df_journal.empty:
    st.dataframe(df_journal.sort_index(ascending=False), use_container_width=True)
else:
    st.info("Belum ada transaksi.")