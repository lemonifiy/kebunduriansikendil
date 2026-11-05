import streamlit as st
import pandas as pd
from datetime import date
from database import get_session, Account, JournalEntry, JournalLine, Company
from auth import authenticate_email
from utils import (
    format_rupiah,
    compute_trial_balance,
    get_income_statement_data,
    get_balance_sheet_data,
)

st.set_page_config(
    page_title="Kebun Durian Sikendil",
    page_icon="🌳",
    layout="wide",
)

# Inisialisasi Session State untuk Login
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["user_email"] = ""
    st.session_state["user_name"] = ""

def login_screen():
    st.markdown("<h2 style='text-align: center;'>🌳 Login Menu - Kebun Durian Sikendil</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: gray;'>Sistem Informasi Akuntansi Perusahaan Dagang</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            email = st.text_input("Email / Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Masuk Sistem", use_container_width=True)

            if submit:
                user = authenticate_email(email, password)
                if user:
                    st.session_state["logged_in"] = True
                    st.session_state["user_email"] = user.email
                    st.session_state["user_name"] = f"{user.first_name} {user.last_name}".strip() or user.username
                    st.success("Login berhasil! Memuat sistem...")
                    st.rerun()
                else:
                    st.error("Email atau password salah, atau akun non-aktif.")

def main_app():
    # Sidebar
    st.sidebar.markdown("<div style='text-align:center;'>", unsafe_allow_html=True)
    st.sidebar.markdown("### 🌳 Kebun Durian Sikendil")
    st.sidebar.markdown(f"**Pengguna:** {st.session_state['user_name']}")
    st.sidebar.markdown("</div>", unsafe_allow_html=True)
    st.sidebar.markdown("---")

    
    menu = st.sidebar.radio("Navigasi Utama", ["Dashboard", "Master Akun", "Jurnal Umum", "Buku Besar", "Laporan Keuangan"])
    

    if st.sidebar.button("Keluar (Logout)", use_container_width=True):
        st.session_state["logged_in"] = False
        st.rerun()

    with get_session() as session:
        if menu == "Dashboard":
            st.title("📊 Dashboard - Kebun Durian Sikendil")
            st.write("Selamat datang di Sistem Informasi Akuntansi perusahaan dagang Kebun Durian Sikendil.")
            
            total_accounts = session.query(Account).count()
            total_journals = session.query(JournalEntry).count()

            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Akun Terdaftar", total_accounts)
            with col2:
                st.metric("Total Transaksi Jurnal", total_journals)

        elif menu == "Master Akun":
            st.title("📂 Daftar Akun (Chart of Accounts)")
            accounts = session.query(Account).order_by(Account.code).all()
            data = [{"Kode": a.code, "Nama Akun": a.name, "Tipe": a.account_type, "Aktif": a.is_active} for a in accounts]
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True)

        elif menu == "Jurnal Umum":
            st.title("📝 Manajemen & Input Jurnal Umum")
            
            # Membuat tab di dalam menu Jurnal Umum
            tab_input, tab_list = st.tabs(["Input Transaksi Baru", "Daftar & Hapus Transaksi"])
            
            with tab_input:
                with st.form("journal_form"):
                    date_val = st.date_input("Tanggal Transaksi", value=date.today())
                    number_val = st.text_input("Nomor Bukti / Ref", value="TRX-002")
                    desc_val = st.text_area("Keterangan Transaksi")
                    
                    st.markdown("---")
                    st.subheader("Baris Jurnal (Debit & Kredit)")
                    accounts = session.query(Account).all()
                    acc_options = {f"{a.code} - {a.name}": a.id for a in accounts}

                    # Baris Debit
                    col1, col2, col3 = st.columns([2, 1, 1])
                    with col1:
                        acc_d = st.selectbox("Akun Debit", list(acc_options.keys()), key="acc_d")
                    with col3:
                        amt_d = st.number_input("Jumlah Debit (Rp)", min_value=0.0, step=1000.0, key="amt_d")

                    # Baris Kredit
                    col1, col2, col3 = st.columns([2, 1, 1])
                    with col1:
                        acc_c = st.selectbox("Akun Kredit", list(acc_options.keys()), key="acc_c")
                    with col3:
                        amt_c = st.number_input("Jumlah Kredit (Rp)", min_value=0.0, step=1000.0, key="amt_c")

                    submitted = st.form_submit_button("Simpan Transaksi Jurnal")
                    if submitted:
                        if amt_d != amt_c or amt_d == 0:
                            st.error("Total Debit dan Kredit harus seimbang (balance) dan tidak boleh nol!")
                        else:
                            entry = JournalEntry(
                                date=date_val,
                                number=number_val,
                                description=desc_val,
                                is_adjustment=False
                            )
                            session.add(entry)
                            session.flush()

                            line_d = JournalLine(entry_id=entry.id, account_id=acc_options[acc_d], is_debit=True, amount=amt_d)
                            line_c = JournalLine(entry_id=entry.id, account_id=acc_options[acc_c], is_debit=False, amount=amt_c)
                            session.add_all([line_d, line_c])
                            session.commit()
                            st.success("Transaksi jurnal berhasil disimpan!")
                            st.rerun()

            with tab_list:
                st.subheader("Daftar Transaksi Tercatat")
                entries = session.query(JournalEntry).order_by(JournalEntry.date.desc()).all()
                
                if entries:
                    for ent in entries:
                        with st.expander(f"[{ent.date}] {ent.number} - {ent.description}"):
                            st.write(f"**ID Transaksi:** {ent.id}")
                            st.write(f"**Keterangan:** {ent.description}")
                            
                            # Menampilkan rincian baris jurnal
                            lines = session.query(JournalLine).filter(JournalLine.entry_id == ent.id).all()
                            line_data = []
                            for ln in lines:
                                line_data.append({
                                    "Akun": f"{ln.account.code} - {ln.account.name}",
                                    "Debit": format_rupiah(ln.amount) if ln.is_debit else "Rp 0",
                                    "Kredit": format_rupiah(ln.amount) if not ln.is_debit else "Rp 0"
                                })
                            st.dataframe(pd.DataFrame(line_data), use_container_width=True)
                            
                            # Tombol Hapus Transaksi
                            if st.button(f"Hapus Transaksi {ent.number}", key=f"del_{ent.id}"):
                                # Hapus baris jurnal terlebih dahulu, lalu hapus ent utama
                                session.query(JournalLine).filter(JournalLine.entry_id == ent.id).delete()
                                session.delete(ent)
                                session.commit()
                                st.success(f"Transaksi {ent.number} berhasil dihapus!")
                                st.rerun()
                else:
                    st.info("Belum ada transaksi yang tercatat.")

        elif menu == "Buku Besar":
            st.title("📖 Buku Besar (General Ledger)")
            accounts = session.query(Account).order_by(Account.code).all()
            acc_choice = st.selectbox("Pilih Akun", accounts, format_func=lambda a: f"{a.code} - {a.name}")
            
            if acc_choice:
                lines = session.query(JournalLine).join(JournalEntry).filter(JournalLine.account_id == acc_choice.id).order_by(JournalEntry.date).all()
                ledger_data = []
                running_balance = 0.0
                for l in lines:
                    d_amt = float(l.amount) if l.is_debit else 0.0
                    c_amt = float(l.amount) if not l.is_debit else 0.0
                    if acc_choice.account_type in ["asset", "expense"]:
                        running_balance += d_amt - c_amt
                    else:
                        running_balance += c_amt - d_amt

                    ledger_data.append({
                        "Tanggal": l.entry.date,
                        "No Bukti": l.entry.number,
                        "Keterangan": l.entry.description,
                        "Debit": format_rupiah(d_amt),
                        "Kredit": format_rupiah(c_amt),
                        "Saldo": format_rupiah(running_balance)
                    })
                if ledger_data:
                    st.dataframe(pd.DataFrame(ledger_data), use_container_width=True)
                else:
                    st.info("Belum ada transaksi untuk akun ini.")

        elif menu == "Laporan Keuangan":
            st.title("📈 Laporan Keuangan")
            year = st.selectbox("Pilih Tahun Buku", [2025, 2026, 2027], index=1)
            
            tab1, tab2, tab3 = st.tabs(["Neraca Saldo", "Laporan Laba Rugi", "Laporan Posisi Keuangan (Neraca)"])
            
            with tab1:
                st.subheader(f"Neraca Saldo Per Tahun {year}")
                rows, tot_d, tot_c = compute_trial_balance(session, year)
                if rows:
                    df_tb = pd.DataFrame(rows)
                    st.dataframe(df_tb, use_container_width=True)
                    st.markdown(f"**Total Debit:** {format_rupiah(tot_d)} | **Total Kredit:** {format_rupiah(tot_c)}")
                else:
                    st.info("Belum ada data transaksi pada tahun ini.")

            with tab2:
                st.subheader(f"Laporan Laba Rugi Tahun {year}")
                rev, exp, net = get_income_statement_data(session, year)
                st.metric("Total Pendapatan", format_rupiah(rev))
                st.metric("Total Beban", format_rupiah(exp))
                st.metric("Laba / Rugi Bersih", format_rupiah(net))

            with tab3:
                st.subheader(f"Laporan Posisi Keuangan (Neraca) Tahun {year}")
                assets, liabilities, equity = get_balance_sheet_data(session, year)
                _, _, net_inc = get_income_statement_data(session, year)
                total_equity = equity + net_inc

                st.metric("Total Aset", format_rupiah(assets))
                st.metric("Total Liabilitas (Kewajiban)", format_rupiah(liabilities))
                st.metric("Total Ekuitas (Modal + Laba Ditahan)", format_rupiah(total_equity))

if not st.session_state["logged_in"]:
    login_screen()
else:
    main_app()
    