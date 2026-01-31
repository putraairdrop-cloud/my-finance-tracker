import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime
import io

# --- KONFIGURASI PATH ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "keuangan.db")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")

# --- KONFIGURASI LOGIN ---
PASSWORD_AKSES = "rahasia123" # Ganti sesuai keinginan lo bro

def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        st.title("?? Fin-Dewade Login")
        pwd = st.text_input("Masukkan Password:", type="password")
        if st.button("Masuk"):
            if pwd == PASSWORD_AKSES:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Password salah, Bro!")
        return False
    return True

# --- DATABASE LOGIC ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS transaksi 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  tanggal TEXT, tipe TEXT, kategori TEXT, 
                  jumlah REAL, keterangan TEXT, struk_path TEXT)''')
    conn.commit()
    conn.close()

# --- MAIN APP ---
if check_password():
    init_db()
    st.sidebar.title("?? Fin-Dewade v1.0")
    menu = ["Input Transaksi", "Dashboard Bulanan", "Riwayat Struk"]
    choice = st.sidebar.selectbox("Pilih Menu", menu)

    # KONEKSI DB
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)

    if choice == "Input Transaksi":
        st.subheader("Tambah Catatan Baru")
        with st.form("form_transaksi", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                tgl = st.date_input("Tanggal", datetime.now())
                tipe = st.selectbox("Tipe", ["Pengeluaran", "Pemasukan"])
                kategori = st.text_input("Kategori", placeholder="Misal: Crypto, Makanan, Gym")
            with col2:
                jumlah = st.number_input("Jumlah (Rp)", min_value=0, step=1000)
                keterangan = st.text_area("Keterangan")
                uploaded_file = st.file_uploader("Upload Struk", type=['jpg', 'png', 'jpeg'])
            
            if st.form_submit_button("Simpan Transaksi"):
                path_struk = "None"
                if uploaded_file:
                    if not os.path.exists(UPLOAD_DIR): os.makedirs(UPLOAD_DIR)
                    nama_file = f"{tgl}_{uploaded_file.name}"
                    path_struk = os.path.join(UPLOAD_DIR, nama_file)
                    with open(path_struk, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                
                c = conn.cursor()
                c.execute("INSERT INTO transaksi (tanggal, tipe, kategori, jumlah, keterangan, struk_path) VALUES (?,?,?,?,?,?)",
                          (tgl.strftime("%Y-%m-%d"), tipe, kategori.capitalize(), jumlah, keterangan, path_struk))
                conn.commit()
                st.success(f"? Berhasil mencatat {tipe}!")

    elif choice == "Dashboard Bulanan":
        st.subheader("Analisis Keuangan")
        df = pd.read_sql_query("SELECT * FROM transaksi", conn)
        
        if not df.empty:
            df['tanggal'] = pd.to_datetime(df['tanggal'])
            df['bulan_tahun'] = df['tanggal'].dt.to_period('M').astype(str)
            
            list_bulan = sorted(df['bulan_tahun'].unique(), reverse=True)
            bulan_pilih = st.selectbox("Pilih Bulan", list_bulan)
            
            df_filtered = df[df['bulan_tahun'] == bulan_pilih].copy()
            
            # Ringkasan
            in_sum = df_filtered[df_filtered['tipe'] == "Pemasukan"]['jumlah'].sum()
            out_sum = df_filtered[df_filtered['tipe'] == "Pengeluaran"]['jumlah'].sum()
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Pemasukan", f"Rp {in_sum:,.0f}")
            c2.metric("Total Pengeluaran", f"Rp {out_sum:,.0f}")
            c3.metric("Saldo", f"Rp {in_sum - out_sum:,.0f}")
            
            st.write("---")
            st.write(f"### Detail Transaksi - {bulan_pilih}")
            st.dataframe(df_filtered[['tanggal', 'tipe', 'kategori', 'jumlah', 'keterangan']], use_container_width=True)

            # Fitur Export Excel
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_filtered.to_excel(writer, index=False, sheet_name='Laporan')
            
            st.download_button(
                label="?? Download Laporan (Excel)",
                data=output.getvalue(),
                file_name=f"Laporan_{bulan_pilih}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.info("Belum ada data transaksi.")

    elif choice == "Riwayat Struk":
        st.subheader("Daftar Struk Terupload")
        df = pd.read_sql_query("SELECT tanggal, kategori, jumlah, struk_path FROM transaksi WHERE struk_path != 'None'", conn)
        if not df.empty:
            for index, row in df.iterrows():
                with st.expander(f"{row['tanggal']} - {row['kategori']} (Rp {row['jumlah']:,.0f})"):
                    st.image(row['struk_path'])
        else:
            st.info("Belum ada struk yang diupload.")
    
    conn.close()
