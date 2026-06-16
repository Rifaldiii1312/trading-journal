import streamlit as st
import pandas as pd
import os
from datetime import datetime

DB_FILE = "trading_journal_10to30.csv"
IMG_DIR = "saved_screenshots"

# Bikin folder buat nyimpen gambar kalau belum ada
if not os.path.exists(IMG_DIR):
    os.makedirs(IMG_DIR)

def load_data():
    if os.path.exists(DB_FILE):
        try:
            df = pd.read_csv(DB_FILE)
            if not df.empty:
                df["Tanggal"] = pd.to_datetime(df["Tanggal"]).dt.strftime("%Y-%m-%d")
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

# == 2. PRO STATS CALCULATIONS ==
MODAL_AWAL = 10000000
total_pnl = df_journal["Net Profit/Loss"].sum() if not df_journal.empty else 0
ekuitas_sekarang = MODAL_AWAL + total_pnl

total_trades = len(df_journal) if not df_journal.empty else 0
wins = len(df_journal[df_journal["Net Profit/Loss"] > 0]) if total_trades > 0 else 0
losses = len(df_journal[df_journal["Net Profit/Loss"] <= 0]) if total_trades > 0 else 0
win_rate = (wins / total_trades * 100) if total_trades > 0 else 0.0

max_profit = df_journal["Net Profit/Loss"].max() if total_trades > 0 and wins > 0 else 0
max_loss = df_journal["Net Profit/Loss"].min() if total_trades > 0 and losses > 0 else 0
avg_profit = df_journal[df_journal["Net Profit/Loss"] > 0]["Net Profit/Loss"].mean() if wins > 0 else 0
avg_loss = df_journal[df_journal["Net Profit/Loss"] <= 0]["Net Profit/Loss"].mean() if losses > 0 else 0

# == 3. LAYOUT UTAMA (2 KOLOM BESAR) ==
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
        st.info("Belum ada data transaksi. Yuk input hasil trade lu di bawah!")

st.markdown("---")

# == 4. LAYOUT BAWAH (TOP GAINER & INPUT FORM) ==
col_bottom_left, col_bottom_right = st.columns([1, 1])

with col_bottom_left:
    st.markdown("### 🏆 Top Gainer (Rp)")
    if not df_journal.empty:
        top_gainer = df_journal.groupby("Ticker").agg(
            Trades=('Ticker', 'count'),
            PnL=('Net Profit/Loss', 'sum')
        ).sort_values(by="PnL", ascending=False)
        top_gainer["PnL"] = top_gainer["PnL"].apply(lambda x: f"Rp {x:,.0f}")
        st.dataframe(top_gainer, use_container_width=True)
    else:
        st.caption("Data top gainer kosong.")

with col_bottom_right:
    st.markdown("### ✍️ Catat Trade Baru (+ Bukti Screenshot)")
    
    with st.form("trade_form", clear_on_submit=True):
        ticker_input = st.text_input("Kode Saham / Aset", placeholder="Contoh: BBRI, GOTO").upper()
        
        c1, c2 = st.columns(2)
        with c1:
            harga_beli_input = st.number_input("Harga Beli (Avg)", min_value=1, value=100)
        with c2:
            harga_jual_input = st.number_input("Harga Jual (Avg)", min_value=1, value=110)
            
        lot_input = st.number_input("Jumlah Lot", min_value=1, value=1)
        catatan_input = st.text_input("Catatan / Analisa Singkat", placeholder="Contoh: Profit taking / Breakout")
        
        # Kolom Upload Screenshot sebagai arsip fisik
        uploaded_file = st.file_uploader("Lampirkan Screenshot Porto (Wajib/Opsional)", type=["png", "jpg", "jpeg"])
        
        submit_btn = st.form_submit_button(label="💾 Simpan ke Jurnal")
        
        if submit_btn:
            if ticker_input == "":
                st.error("Kode saham gak boleh kosong, bro!")
            else:
                net_pnl = (harga_jual_input - harga_beli_input) * lot_input * 100
                fee_estimasi = (harga_beli_input * lot_input * 100 + harga_jual_input * lot_input * 100) * 0.003
                net_pnl -= fee_estimasi
                
                # Proses simpan file gambar ke folder lokal server
                img_path = "-"
                if uploaded_file is not None:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    img_name = f"{timestamp}_{ticker_input}.png"
                    img_path = os.path.join(IMG_DIR, img_name)
                    with open(img_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                
                new_row = pd.DataFrame([{
                    "Tanggal": datetime.now().strftime("%Y-%m-%d"),
                    "Ticker": ticker_input,
                    "Harga Beli": float(harga_beli_input),
                    "Harga Jual": float(harga_jual_input),
                    "Lot": float(lot_input),
                    "Net Profit/Loss": net_pnl,
                    "Catatan": catatan_input if catatan_input else "Trade Closed",
                    "Screenshot": img_path
                }])
                
                df_journal = pd.concat([df_journal, new_row], ignore_index=True)
                save_data(df_journal)
                st.success(f"Mantap! Data trade {ticker_input} beserta screenshot berhasil diarsipkan.")
                st.rerun()

# == 5. TABEL REKAP + FITUR LIHAT BUKTI SCREENSHOT ==
st.markdown("---")
st.markdown("### 📋 Log Semua Transaksi & Arsip Gambar")
if not df_journal.empty:
    # Kita pakai looping biar user bisa milih mau lihat gambar mana
    for idx, row in df_journal.sort_index(ascending=False).iterrows():
        pnl_val = row['Net Profit/Loss']
        warna_pnl = "green" if pnl_val > 0 else "red"
        
        # Desain baris log yang elegan
        with st.expander(f"📅 {row['Tanggal']} | 📈 {row['Ticker']} | PnL: : {warna_pnl}[Rp {pnl_val:,.0f}]"):
            c_detail, c_img = st.columns([1, 1])
            with c_detail:
                st.write(f"**Harga Beli:** Rp {row['Harga Beli']:,.0f}")
                st.write(f"**Harga Jual:** Rp {row['Harga Jual']:,.0f}")
                st.write(f"**Jumlah Lot:** {row['Lot']} Lot")
                st.write(f"**Catatan:** {row['Catatan']}")
            with c_img:
                if row['Screenshot'] != "-" and os.path.exists(str(row['Screenshot'])):
                    st.image(str(row['Screenshot']), caption="Bukti Transaksi Porto", width=250)
                else:
                    st.caption("Gak ada screenshot yang dilampirkan.")
else:
    st.caption("Belum ada riwayat transaksi yang tercatat.")
