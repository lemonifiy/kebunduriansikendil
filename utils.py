from datetime import date
from sqlalchemy import func
from database import Account, JournalEntry, JournalLine, ClosingStatus

def format_rupiah(value):
    """Mengubah angka menjadi format mata uang Rupiah"""
    if value == 0:
        return "Rp 0"
    return f"Rp {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def is_year_closed(session, year: int) -> bool:
    """Mengecek apakah tahun buku sudah ditutup/disesuaikan"""
    status = (
        session.query(ClosingStatus)
        .filter(ClosingStatus.year == year, ClosingStatus.is_closed == True)
        .first()
    )
    return status is not None

def compute_trial_balance(session, year: int):
    """Menghitung neraca saldo berdasarkan jurnal umum"""
    accounts = session.query(Account).filter(Account.is_active == True).order_by(Account.code).all()
    rows = []
    total_debit = 0.0
    total_credit = 0.0

    for acc in accounts:
        lines = (
            session.query(JournalLine)
            .join(JournalEntry)
            .filter(
                JournalLine.account_id == acc.id,
                JournalEntry.date >= date(year, 1, 1),
                JournalEntry.date <= date(year, 12, 31),
                JournalEntry.is_adjustment == False,
            )
        )
        debit_sum = float(lines.filter(JournalLine.is_debit == True).with_entities(func.coalesce(func.sum(JournalLine.amount), 0)).scalar() or 0)
        credit_sum = float(lines.filter(JournalLine.is_debit == False).with_entities(func.coalesce(func.sum(JournalLine.amount), 0)).scalar() or 0)

        if debit_sum > 0 or credit_sum > 0:
            if debit_sum >= credit_sum:
                debit = debit_sum - credit_sum
                credit = 0.0
            else:
                debit = 0.0
                credit = credit_sum - debit_sum

            total_debit += debit
            total_credit += credit
            rows.append({
                "Kode Akun": acc.code, 
                "Nama Akun": acc.name, 
                "Debit": format_rupiah(debit), 
                "Kredit": format_rupiah(credit)
            })

    return rows, total_debit, total_credit

def get_income_statement_data(session, year: int):
    """Menghitung total pendapatan, beban, dan laba/rugi bersih"""
    revenue_accounts = session.query(Account).filter(Account.account_type == "revenue").all()
    expense_accounts = session.query(Account).filter(Account.account_type == "expense").all()

    def calc_total(accounts):
        total = 0.0
        for acc in accounts:
            lines = session.query(JournalLine).join(JournalEntry).filter(
                JournalLine.account_id == acc.id,
                JournalEntry.date >= date(year, 1, 1),
                JournalEntry.date <= date(year, 12, 31),
            )
            debit = float(lines.filter(JournalLine.is_debit == True).with_entities(func.coalesce(func.sum(JournalLine.amount), 0)).scalar() or 0)
            credit = float(lines.filter(JournalLine.is_debit == False).with_entities(func.coalesce(func.sum(JournalLine.amount), 0)).scalar() or 0)

            if acc.account_type == "revenue":
                total += credit - debit
            else:
                total += debit - credit
        return total

    total_revenue = calc_total(revenue_accounts)
    total_expense = calc_total(expense_accounts)
    net_income = total_revenue - total_expense
    return total_revenue, total_expense, net_income

def get_balance_sheet_data(session, year: int):
    """Menghitung total aset, liabilitas, dan ekuitas"""
    asset_accounts = session.query(Account).filter(Account.account_type == "asset").all()
    liability_accounts = session.query(Account).filter(Account.account_type == "liability").all()
    equity_accounts = session.query(Account).filter(Account.account_type == "equity").all()

    def calc_balance(accounts):
        total = 0.0
        for acc in accounts:
            lines = session.query(JournalLine).join(JournalEntry).filter(
                JournalLine.account_id == acc.id,
                JournalEntry.date >= date(year, 1, 1),
                JournalEntry.date <= date(year, 12, 31),
            )
            debit = float(lines.filter(JournalLine.is_debit == True).with_entities(func.coalesce(func.sum(JournalLine.amount), 0)).scalar() or 0)
            credit = float(lines.filter(JournalLine.is_debit == False).with_entities(func.coalesce(func.sum(JournalLine.amount), 0)).scalar() or 0)

            if acc.account_type == "asset":
                total += debit - credit
            else:
                total += credit - debit
        return total

    return calc_balance(asset_accounts), calc_balance(liability_accounts), calc_balance(equity_accounts)