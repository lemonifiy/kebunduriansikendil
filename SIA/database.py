from datetime import datetime
import streamlit as st
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, scoped_session
from contextlib import contextmanager

# Membaca konfigurasi database dari .streamlit/secrets.toml
DATABASE_URL = st.secrets["DATABASE_URL"]

engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = scoped_session(sessionmaker(bind=engine, autoflush=False, autocommit=False))
Base = declarative_base()


class User(Base):
    __tablename__ = "auth_user"

    id = Column(Integer, primary_key=True)
    password = Column(String(128), nullable=False)
    last_login = Column(DateTime)
    is_superuser = Column(Boolean, default=False)
    username = Column(String(150), nullable=False)
    first_name = Column(String(150), default="")
    last_name = Column(String(150), default="")
    email = Column(String(254), default="")
    is_staff = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    date_joined = Column(DateTime)


class Company(Base):
    __tablename__ = "accounting_company"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), default="Kebun Durian Sikendil")
    logo = Column(String(100), nullable=True)
    currency = Column(String(10), default="IDR")


class Account(Base):
    __tablename__ = "accounting_account"

    id = Column(Integer, primary_key=True)
    code = Column(String(20), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    account_type = Column(String(20), nullable=False)  # asset, liability, equity, prive, revenue, expense
    is_active = Column(Boolean, default=True)

    def __repr__(self):
        return f"{self.code} {self.name}"


class JournalEntry(Base):
    __tablename__ = "accounting_journalentry"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("accounting_company.id"), nullable=True)
    date = Column(Date, nullable=False)
    number = Column(String(100), nullable=False)
    description = Column(String, nullable=False)
    is_adjustment = Column(Boolean, default=False)
    created_by_id = Column(Integer, ForeignKey("auth_user.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    company = relationship("Company")
    created_by = relationship("User")
    lines = relationship("JournalLine", back_populates="entry", cascade="all, delete-orphan")


class JournalLine(Base):
    __tablename__ = "accounting_journalline"

    id = Column(Integer, primary_key=True)
    entry_id = Column(Integer, ForeignKey("accounting_journalentry.id"), nullable=False)
    account_id = Column(Integer, ForeignKey("accounting_account.id"), nullable=False)
    is_debit = Column(Boolean, nullable=False)
    amount = Column(Numeric(18, 2), nullable=False)
    tax_ppn = Column(Numeric(18, 2), nullable=True)

    entry = relationship("JournalEntry", back_populates="lines")
    account = relationship("Account")

    def __repr__(self):
        side = "D" if self.is_debit else "K"
        return f"{self.entry.number} {self.account} {side} {self.amount}"


class ClosingStatus(Base):
    __tablename__ = "accounting_closingstatus"

    id = Column(Integer, primary_key=True)
    year = Column(Integer, unique=True, nullable=False)
    is_closed = Column(Boolean, default=False)
    closed_at = Column(DateTime, default=datetime.utcnow)


@contextmanager
def get_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

# Fungsi untuk otomatis membuat tabel database saat aplikasi pertama kali dijalankan
def init_db():
    Base.metadata.create_all(bind=engine)
    
    # Tambahkan akun default & user admin jika tabel masih kosong
    with get_session() as session:
        # Cek apakah akun sudah ada
        if session.query(Account).count() == 0:
            default_accounts = [
                Account(code="111", name="Kas", account_type="asset"),
                Account(code="112", name="Piutang Usaha", account_type="asset"),
                Account(code="113", name="Persediaan Durian", account_type="asset"),
                Account(code="211", name="Utang Usaha", account_type="liability"),
                Account(code="311", name="Modal Saham", account_type="equity"),
                Account(code="411", name="Pendapatan Penjualan Durian", account_type="revenue"),
                Account(code="511", name="Beban Operasional", account_type="expense"),
            ]
            session.add_all(default_accounts)
            session.commit()

        # Cek apakah user admin/superuser ada (password hash Django untuk 'admin123')
        # Format pbkdf2_sha256$600000$salt$hash
        if session.query(User).count() == 0:
            admin_user = User(
                username="admin",
                email="admin@sikendil.com",
                first_name="Admin",
                last_name="Sikendil",
                is_superuser=True,
                is_staff=True,
                is_active=True,
                password="pbkdf2_sha256$600000$P9G9h55B53Z9$c5qV1w8k2J4mN6p7Q9rS1tU3vW5xY7zA9bC2dE4fG6h=" # Password dummy/placeholder awal
            )
            session.add(admin_user)
            session.commit()

# Jalankan inisialisasi
init_db()