import streamlit as st
import pandas as pd
import os
from datetime import datetime

DB_FILE = "trading_journal_10to30.csv"

def load_data():
    if os.path.exists(DB_FILE):
        try:
            df = pd.read_csv(DB_FILE)
            if not df.empty:
                df["Tanggal"] = pd.to_datetime(df["Tanggal"]).dt.strftime("%Y-%m-%d")
            return df
        except:
            pass
    return pd.DataFrame(columns=["Tanggal", "Ticker", "Harga Beli", "Harga Jual", "Lot", "Net Profit/Loss", "Catatan"])

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
    st.markdown("### ✍️ Catat Trade Baru (Setelah Sell)")
    
    with st.form("trade_form", clear_on_submit=True):
        ticker_input = st.text_input("Kode Saham / Aset", placeholder="Contoh: BBRI, GOTO").upper()
        
        c1, c2 = st.columns(2)
        with c1:
            harga_beli_input = st.number_input("Harga Beli (Avg)", min_value=1, value=100)
        with c2:
            harga_jual_input = st.number_input("Harga Jual (Avg)", min_value=1, value=110)
            
        lot_input = st.number_input("Jumlah Lot", min_value=1, value=1)
        catatan_input = st.text_input("Catatan / Analisa Singkat", placeholder="Contoh: Profit taking / Cut loss terpaksa")
        
        uploaded_file = st.file_uploader("Lampirkan Screenshot Porto (Opsional)", type=["png", "jpg", "jpeg"])
        
        submit_btn = st.form_submit_button(label="💾 Simpan ke Jurnal")
        
        if submit_btn:
            if ticker_input == "":
                st.error("Kode saham gak boleh kosong, bro!")
            else:
                # Rumus profit bersih langsung hitung (Jual - Beli) * Lot * 100 lembar
                net_pnl = (harga_jual_input - harga_beli_input) * lot_input * 100
                
                # Potong biaya fee beli + jual broker (estimasi total sekitar 0.3%)
                fee_estimasi = (harga_beli_input * lot_input * 100 + harga_jual_input * lot_input * 100) * 0.003
                net_pnl -= fee_estimasi
                
                new_row = pd.DataFrame([{
                    "Tanggal": datetime.now().strftime("%Y-%m-%d"),
                    "Ticker": ticker_input,
                    "Harga Beli": float(harga_beli_input),
                    "Harga Jual": float(harga_jual_input),
                    "Lot": float(lot_input),
                    "Net Profit/Loss": net_pnl,
                    "Catatan": catatan_input if catatan_input else "Trade Closed"
                }])
                
                df_journal = pd.concat([df_journal, new_row], ignore_index=True)
                save_data(df_journal)
                st.success(f"Mantap! Data trade {ticker_input} langsung masuk hitungan.")
                st.rerun()

# == 5. TABEL REKAP SEMUA TRANSAKSI DI BAGIAN PALING BAWAH ==
st.markdown("### 📋 Log Semua Transaksi")
if not df_journal.empty:
    display_df = df_journal.copy()
    display_df["Net Profit/Loss"] = display_df["Net Profit/Loss"].apply(lambda x: f"Rp {x:,.0f}")
    st.dataframe(display_df.sort_values(by="Tanggal", ascending=False), use_container_width=True)
else:
    st.caption("Belum ada riwayat transaksi yang tercatat.")
