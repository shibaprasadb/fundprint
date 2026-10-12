"""Build a made-up CAMS-style detailed CAS PDF for tests and the browser spike.

Everything in it is invented (names, folio, PAN, amounts). It copies only the
layout casparser looks for: a CAMSCASWS marker, a statement period, folio and
scheme header lines, a transaction table, and closing balance / NAV lines.

Usage: python scripts/make_sample_pdf.py out.pdf [password] [--multi]
"""
import sys
from datetime import date, timedelta

from reportlab.lib.pagesizes import A4
from reportlab.lib.pdfencrypt import StandardEncryption
from reportlab.pdfgen import canvas

# (scheme line, isin, folio, [(date, description, amount, units, nav)], nav_now)
TODAY = date(2026, 10, 9)
COLS = {"Amount": 380, "Units": 440, "Price": 495, "Unit": 555}  # right edge of each numeric column


def months_ago(n):
    y, m = divmod(TODAY.year * 12 + TODAY.month - 1 - n, 12)
    return date(y, m + 1, 5)


def sip_rows(n_months, nav0, growth):
    rows, nav = [], nav0
    for k in range(n_months, 0, -1):
        nav *= 1 + growth
        rows.append((months_ago(k), "Systematic Investment Purchase", 5000.0, round(5000 / nav, 3), round(nav, 4)))
    return rows, nav * (1 + growth)


# one fund whose ISIN matches two rows in casparser's database, which forces the
# name-matching step (the part the browser build had to stand in for)
MULTI_MATCH_FUNDS = [
    ("Taurus Mutual Fund", "104LBDP-Taurus Short Term Income Fund - Regular Plan - IDCW Payout", "INF044D01583", "22222222", 12, 20.0, 0.004),
]


# a statement with many funds and rows, to check the app copes with a realistic size
BIG_FUNDS = [
    ("Bandhan Mutual Fund" if i % 2 == 0 else "ICICI Prudential Mutual Fund",
     ("GD203-Bandhan Flexi Cap Fund - Direct Plan Growth" if i % 2 == 0
      else "P8189-ICICI Prudential Nifty 50 Index Fund - Direct Plan Growth"),
     "INF194K01W62" if i % 2 == 0 else "INF109K012M7", f"3333{i:04d}", 70, 50.0 + i, 0.008 + i / 2000)
    for i in range(14)
]


def build(path, password=None, multi=False, big=False):
    enc = StandardEncryption(password) if password else None
    c = canvas.Canvas(path, pagesize=A4, encrypt=enc)
    w, h = A4
    y = h - 40

    def line(text, x=40, size=8):
        nonlocal y
        c.setFont("Helvetica", size)
        c.drawString(x, y, text)
        y -= 12

    # real statements carry this marker as a sideways watermark; one parser only
    # looks for it in vertical text, so draw it rotated
    c.saveState(); c.translate(15, h - 200); c.rotate(90)
    c.setFont("Helvetica", 6); c.drawString(0, 0, "CAMSCASWS"); c.restoreState()
    line("Consolidated Account Statement", size=12)
    line("01-Jan-2020 To 09-Oct-2026")
    # made-up investor block: casparser needs these four lines at the top left
    line("Email Id: test@example.com")
    line("Test Holder")
    line("1 Sample Street, Sample City 000000")
    line("Mobile: 9999999999")
    y -= 6
    funds = BIG_FUNDS if big else MULTI_MATCH_FUNDS if multi else [
        ("Bandhan Mutual Fund", "GD203-Bandhan Flexi Cap Fund - Direct Plan Growth", "INF194K01W62", "11111111", 40, 100.0, 0.011),
        ("ICICI Prudential Mutual Fund", "P8189-ICICI Prudential Nifty 50 Index Fund - Direct Plan Growth", "INF109K012M7", "11111111", 18, 50.0, 0.015),
    ]
    for amc, name, isin, folio, n, nav0, g in funds:
        line(amc, size=9)
        line(f"Folio No: {folio} / 0   PAN: ABCDE1234F   KYC: OK   PAN: OK")
        line("Test Holder")
        line(f"{name} - ISIN: {isin} (Advisor: DIRECT) Registrar : CAMS")
        line("Opening Unit Balance: 0.000")
        # transaction header with fixed column positions
        c.setFont("Helvetica-Bold", 8)
        c.drawString(40, y, "Date"); c.drawString(110, y, "Transaction")
        for label, xr in COLS.items():                      # numeric headers are right-aligned
            c.drawRightString(xr, y, label)
        c.drawRightString(COLS["Unit"], y - 9, "Balance")
        y -= 22
        rows, nav_now = sip_rows(n, nav0, g)
        bal = 0.0
        for d, desc, amt, units, nav in rows:
            bal += units
            if y < 80:
                c.showPage(); y = h - 40
            c.setFont("Helvetica", 8)
            c.drawString(40, y, d.strftime("%d-%b-%Y"))
            c.drawString(110, y, desc)
            for text, xr in [(f"{amt:,.2f}", COLS["Amount"]), (f"{units:,.3f}", COLS["Units"]), (f"{nav:,.4f}", COLS["Price"]), (f"{bal:,.3f}", COLS["Unit"])]:
                c.drawRightString(xr, y, text)
            y -= 12
        cost = sum(r[2] for r in rows)
        line(f"Closing Unit Balance: {bal:,.3f}")
        line(f"NAV on 09-Oct-2026: INR {nav_now:,.4f}")
        line(f"Total Cost Value: {cost:,.2f}")
        line(f"Valuation on 09-Oct-2026: INR {bal * nav_now:,.2f}")
        y -= 10
    c.save()


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a not in ("--multi", "--big")]
    build(args[0], args[1] if len(args) > 1 else None, multi="--multi" in sys.argv, big="--big" in sys.argv)
