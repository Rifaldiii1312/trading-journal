import streamlit as st
import pandas as pd
import os
from datetime import datetime
import requests
import base64
import json
import re

# == 1. AI SETUP VIA OPENROUTER ==
# Masukkan API Key OpenRouter lu yang diawali sk-or-v1-...
OPENROUTER_API_KEY = "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" 

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

# == 2. STYLE & THEME CUSTOMIZATION ==
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

# == 3. PRO STATS CALCULATIONS ==
MODAL_AWAL = 10000000
total_pnl = df_journal["Net Profit/Loss"].sum() if not df_journal.empty else 0
ekuitas_sekarang = MODAL_AWAL + total_pnl

trades_jual = df_journal[df_journal["Aksi"] == "Jual"] if not df_journal.empty else pd.DataFrame()
total_trades = len(trades_jual)
wins = len(trades_jual[trades_jual["Net Profit/Loss"] > 0]) if total_trades > 0 else 0
losses = len(trades_jual[trades_jual["Net Profit/Loss"] <= 0]) if total_trades > 0 else 0
win_rate = (wins / total_trades * 100) if total_trades > 0 else 0.0

max_profit = trades_jual["Net Profit/Loss"].max() if total_trades > 0 and wins > 0 else 0
max_loss = trades_jual["Net Profit/Loss"].min() if total_trades > 0 and losses > 0 else 0
avg_profit = trades_jual[trades_jual["Net Profit/Loss"] > 0]["Net Profit/Loss"].mean() if wins > 0 else 0
avg_loss = trades_jual[trades_jual["Net Profit/Loss"] <= 0]["Net Profit/Loss"].mean() if losses > 0 else 0

# == 4. LAYOUT UTAMA (2 KOLOM BESAR) ==
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
    with c_p:
        st.markdown(f"""
        <div class="stat-box">
            <span style='color:#888; font-size:13px;'>Max Profit</span><br><span class="green-text">Rp {max_profit:,.0f}</span><br><br>
            <span style='color:#888; font-size:13px;'>Avg Profit</span><br><span class="green-text">Rp {avg_profit:,.0f}</span>
        </div>
        """, unsafe_allow_html=True)
    with c_l:
        st.markdown(f"""
        <div class="stat-box">
            <span style='color:#888; font-size:13px;'>Max Loss</span><br><span class="red-text">Rp {max_loss:,.0f}</span><br><br>
            <span style='color:#888; font-size:13px;'>Avg Loss</span><br><span class="red-text">Rp {avg_loss:,.0f}</span>
        </div>
        """, unsafe_allow_html=True)

with col_right:
    pnl_color = "green-text" if total_pnl >= 0 else "red-text"
    pnl_sign = "+" if total_pnl >= 0 else ""
    
    st.markdown(f"""
    <div style='padding-left:10px;'>
        <p style='margin-bottom:2px; color:#888;'>Total Realized Gain/Loss</p>
        <h1 class="{pnl_color}" style='margin-top:0;'>{pnl_sign}Rp {total_pnl:,.0f}</h1>
    </div>
    """, unsafe_allow_html=True)
    
    if not df_journal.empty:
        df_sorted = df_journal.sort_values(by="Tanggal").copy()
        df_sorted["Kumulatif PnL"] = df_sorted["Net Profit/Loss"].cumsum()
        df_sorted["Saldo Ekuitas"] = MODAL_AWAL + df_sorted["Kumulatif PnL"]
        chart_data = df_sorted[["Tanggal", "Saldo Ekuitas"]].set_index("Tanggal")
        st.line_chart(chart_data, y="Saldo Ekuitas", use_container_width=True)
    else:
        st.info("Belum ada data untuk grafik. Upload screenshot trading lu di bawah.")

st.markdown("---")

# == 5. LAYOUT BAWAH (TOP GAINER & IMAGE INPUT) ==
col_bottom_left, col_bottom_right = st.columns([1, 1])

with col_bottom_left:
    st.markdown("### 🏆 Top Gainer (Rp)")
    if not df_journal.empty and total_trades > 0:
        top_gainer = trades_jual.groupby("Ticker").agg(
            Trades=('Ticker', 'count'),
            PnL=('Net Profit/Loss', 'sum')
        ).sort_values(by="PnL", ascending=False)
        top_gainer["PnL"] = top_gainer["PnL"].apply(lambda x: f"Rp {x:,.0f}")
        st.dataframe(top_gainer, use_container_width=True)
    else:
        st.caption("Data top gainer kosong.")

with col_bottom_right:
    st.markdown("### 📸 Scan Screenshot Baru")
    uploaded_file = st.file_uploader("Upload screenshot transaksi di sini", type=["png", "jpg", "jpeg"])
    
    if uploaded_file is not None:
        bytes_data = uploaded_file.getvalue()
        base64_image = base64.b64encode(bytes_data).decode('utf-8')
        st.image(bytes_data, caption="Preview Porto", width=250)
        
        if st.button("🚀 Proses Masuk Jurnal"):
            with st.spinner("AI lagi membaca screenshot lu..."):
                try:
                    headers = {
                        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                        "Content-Type": "application/json"
                    }
                    
                    prompt = """
                    Analisis gambar screenshot trading ini. Ekstrak informasi penting dan kembalikan data HANYA dalam format JSON mentah wajib seperti ini:
                    {
                        "Ticker": "KODE SAHAM",
                        "Aksi": "Beli" atau "Jual",
                        "Harga Beli": angka_tanpa_titik_koma,
                        "Harga Jual": angka_tanpa_titik_koma_jika_beli_isi_0,
                        "Lot": angka_tanpa_titik_koma,
                        "Catatan": "Keterangan singkat"
                    }
                    Jangan ketik kata-kata lain di luar JSON ini.
                    """
                    
                    payload = {
                        "model": "google/gemini-2.5-flash:free",
                        "messages": [
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": prompt},
                                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                                ]
                            }
                        ]
                    }
                    
                    response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
                    res_json = response.json()
                    
                    # Cek validasi data dari OpenRouter
                    if 'choices' not in res_json:
                        st.error(f"Eror dari server OpenRouter (Kemungkinan kuota harian habis atau sibuk). Respon: {res_json}")
                    else:
                        ai_text = res_json['choices'][0]['message']['content'].strip()
                        
                        # Ambil teks JSON-nya saja jika AI nakal mengetik teks pembuka tambahan
                        json_match = re.search(r'\{.*\}', ai_text, re.DOTALL)
                        if json_match:
                            cleaned_text = json_match.group(0)
                        else:
                            cleaned_text = ai_text
                        
                        data_api = json.loads(cleaned_text)
                        
                        # Kalkulasi Net PnL otomatis
                        net_pnl = 0
                        harga_beli = float(data_api.get("Harga Beli", 0))
                        harga_jual = float(data_api.get("Harga Jual", 0))
                        lot = float(data_api.get("Lot", 0))
                        aksi = data_api.get("Aksi", "Beli")
                        ticker = data_api.get("Ticker", "UNKNOWN").upper()
                        
                        if aksi == "Jual" and harga_jual > 0:
                            pengali = 100 if lot >= 1 else 1
                            net_pnl = (harga_jual - harga_beli) * lot * pengali
                            net_pnl -= (harga_beli * lot * pengali + harga_jual * lot * pengali) * 0.002
                        
                        new_row = pd.DataFrame([{
                            "Tanggal": datetime.now().strftime("%Y-%m-%d"),
                            "Ticker": ticker,
                            "Aksi": aksi,
                            "Harga Beli": harga_beli,
                            "Harga Jual": harga_jual,
                            "Lot": lot,
                            "Net Profit/Loss": net_pnl,
                            "Catatan": data_api.get("Catatan", "Sukses via AI")
                        }])
                        
                        df_journal = pd.concat([df_journal, new_row], ignore_index=True)
                        save_data(df_journal)
                        st.success(f"Berhasil mencatat transaksi: {ticker} ({aksi})!")
                        st.rerun()
                except Exception as e:
                    st.error(f"Gagal memproses gambar. Detail Masalah: {e}")
