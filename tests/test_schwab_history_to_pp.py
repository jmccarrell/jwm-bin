"""Tests for bin/schwab-history-to-pp, on made-up accounts and amounts only.

    uv run --with pytest pytest tests
"""

import datetime as dt
import importlib.machinery
import importlib.util
import json
from decimal import Decimal as D
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "bin" / "schwab-history-to-pp"
loader = importlib.machinery.SourceFileLoader("schwab_history_to_pp", str(SCRIPT))
spec = importlib.util.spec_from_loader(loader.name, loader)
s = importlib.util.module_from_spec(spec)
loader.exec_module(s)


def row(date, action, symbol="", qty="", price="", fees="", amount="", desc=""):
    return {"Date": date, "Action": action, "Symbol": symbol, "Description": desc or symbol,
            "Quantity": qty, "Price": price, "Fees & Comm": fees, "Amount": amount,
            "AcctgRuleCd": "2"}


def history(tmp_path, name, rows, start="01/03/2022", end="12/30/2022"):
    p = tmp_path / name
    p.write_text(json.dumps({"FromDate": start, "ToDate": end, "TotalTransactionsAmount": "",
                             "TotalFeesAndCommAmount": "", "BrokerageTransactions": rows}))
    return p


def txns(*rows):
    return [s.txn(r) for r in rows]


#
# reading History rows
#

def test_txn_reads_signs_dates_and_thousands():
    t = s.txn(row("02/27/2025 as of 01/28/2025", "Sell", "ABC", "1,200", "$10.50", "$0.77",
                  "$12,599.23"))
    assert t.date == dt.date(2025, 2, 27)
    assert t.as_of == dt.date(2025, 1, 28)
    assert t.amount == D("12599.23")
    assert t.fees == D("0.77")
    assert t.shares == D("-1200")


def test_symbol_comes_from_description_when_blank():
    t = s.txn(row("03/14/2022", "Cash Dividend", amount="$31.40",
                  desc="TDA TRAN - ORDINARY DIVIDEND (SHV)"))
    assert t.symbol == "SHV"


@pytest.mark.parametrize("action,qty,expect", [
    ("Buy", "10", "10"), ("Reinvest Shares", "0.5", "0.5"), ("Sell", "10", "-10"),
    ("Stock Split", "9", "9"), ("Journal", "-3", "-3"), ("Journaled Shares", "-3", "-3"),
    ("Internal Transfer", "3", "3"), ("Cash Dividend", "", "0"),
])
def test_share_effect_by_action(action, qty, expect):
    assert s.txn(row("01/04/2022", action, "ABC", qty, amount="")).shares == D(expect)


def test_unknown_action_fails_naming_it():
    with pytest.raises(ValueError, match="Spin Off"):
        s.txn(row("01/04/2022", "Spin Off", "ABC"))


#
# converting to Portfolio Performance rows
#

def test_trades_and_reinvestment():
    p, a, _ = s.convert(txns(
        row("01/04/2022", "Buy", "ABC", "10", "$10", "", "-$100.00"),
        row("01/05/2022", "Sell", "ABC", "4", "$12", "$0.10", "$47.90"),
        row("01/06/2022", "Qual Div Reinvest", "ABC", amount="$3.00"),
        row("01/07/2022", "Reinvest Shares", "ABC", "0.25", "$12", "", "-$3.00"),
    ), "acct")
    assert [(r["Type"], r["Shares"], r["Value"], r.get("Fees", "")) for r in p] == [
        ("Buy", "10", "100.00", ""), ("Sell", "4", "47.90", "0.10"), ("Buy", "0.25", "3.00", "")]
    assert [(r["Type"], r["Value"], r["Ticker Symbol"]) for r in a] == [("Dividend", "3.00", "ABC")]
    assert all(r["Securities Account"] == "acct" and r["Cash Account"] == "acct" for r in p)


def test_security_name_skips_td_ameritrade_narration():
    p, a, _ = s.convert(txns(
        row("01/04/2022", "Reinvest Shares", "SHV", "1", amount="-$110.00",
            desc="TDA TRAN - Bought 1 (SHV) @110.0000"),
        row("01/04/2022", "Cash Dividend", amount="$110.00", desc="TDA TRAN - ORDINARY DIVIDEND (SHV)"),
        row("09/08/2022", "Reinvest Dividend", "SHV", amount="$5.00", desc="ISHARES SHORT TREASURY BOND ETF"),
        row("01/05/2022", "Buy", "ZZZ", "1", amount="-$1.00", desc="TDA TRAN - Bought 1 (ZZZ) @1"),
    ), "acct")
    assert {r["Ticker Symbol"]: r["Security Name"] for r in p + a} == {
        "SHV": "ISHARES SHORT TREASURY BOND ETF", "ZZZ": "ZZZ"}


def test_cash_flows():
    _, a, _ = s.convert(txns(
        row("01/04/2022", "MoneyLink Deposit", amount="$500.00"),
        row("01/05/2022", "MoneyLink Transfer", amount="-$200.00"),
        row("01/05/2022", "MoneyLink Transfer", amount="$50.00"),
        row("01/06/2022", "Tax Withholding", amount="-$20.00", desc="STATE TAX W/H IRA"),
        row("01/07/2022", "Bank Interest", amount="$0.16"),
        row("01/07/2022", "Credit Interest", amount="$0.32"),
        row("01/07/2022", "Bond Interest", amount="$1.10"),
    ), "acct")
    assert [(r["Type"], r["Value"]) for r in a] == [
        ("Deposit", "500.00"), ("Withdrawal", "200.00"), ("Deposit", "50.00"),
        ("Withdrawal", "20.00"), ("Interest", "0.16"), ("Interest", "0.32"), ("Interest", "1.10")]


def test_stock_split_is_a_zero_value_delivery():
    p, _, _ = s.convert(txns(row("06/10/2024 as of 06/07/2024", "Stock Split", "ABC", "90",
                                 "$12.00")), "acct")
    assert [(r["Type"], r["Shares"], r["Value"]) for r in p] == [("Delivery (Inbound)", "90", "0.00")]


def test_div_adjustment_cancels_the_dividend_it_reverses():
    _, a, notes = s.convert(txns(
        row("01/28/2025", "Pr Yr Cash Div", "ABC", amount="$15.00"),
        row("02/27/2025 as of 01/28/2025", "Cash Dividend", "ABC", amount="$15.00"),
        row("02/28/2025 as of 01/28/2025", "Div Adjustment", "ABC", amount="-$15.00"),
    ), "acct")
    assert [(r["Date"], r["Value"]) for r in a] == [("2025-01-28", "15.00")]
    assert any("Div Adjustment" in n for n in notes)


def test_div_adjustment_without_a_match_fails():
    with pytest.raises(ValueError, match="Div Adjustment"):
        s.convert(txns(row("02/28/2025", "Div Adjustment", "ABC", amount="-$15.00")), "acct")


def test_transfers_that_net_to_zero_produce_nothing():
    p, a, notes = s.convert(txns(
        row("05/09/2022", "Journaled Shares", "ABC", "-100"),
        row("05/09/2022", "Internal Transfer", "ABC", "100"),
        row("05/09/2022", "Journaled Shares", amount="-$4.00"),
        row("05/09/2022", "Internal Transfer", amount="$4.00"),
        row("06/01/2022", "Journal", "ABC", "-100"),
        row("06/01/2022", "Journal", "ABC", "100"),
    ), "acct")
    assert p == [] and a == []
    assert sum("net to zero" in n for n in notes) == 3


def test_unpaired_cash_journal_is_a_deposit():
    _, a, notes = s.convert(txns(row("05/02/2022", "Journal", amount="$1,000.00",
                                     desc="ROLLOVER IN")), "acct")
    assert [(r["Type"], r["Value"]) for r in a] == [("Deposit", "1000.00")]
    assert any("Deposit" in n for n in notes)


def test_unpaired_share_journal_fails():
    with pytest.raises(ValueError, match="ABC"):
        s.convert(txns(row("06/01/2022", "Journal", "ABC", "-100")), "acct")


#
# positions files
#

SCHWAB = '''"Positions for GROUP as of 04:48 PM ET, 03/04/2022"

"acct-b ...111"
"Symbol","Description","Qty (Quantity)","Price","Mkt Val (Market Value)","Asset Type",
"ABC","ABC INC","1,200","10.00","$12,000.00","Equity",
"Cash & Cash Investments","--","--","--","$55.10","Cash and Money Market",
"Positions Total","","--","--","$12,055.10","--",


"acct-a ...222"
"Symbol","Description","Quantity","Price","Market Value","Asset Type"
"XYZ","XYZ ETF","2.5","$4.00","$10.00","ETFs"
"Cash & Cash Investments","--","--","--","$1.00","Cash and Money Market"
"Positions Total","","--","--","$11.00","--"
'''

TDA = '''Sat Mar 26 2022 2:14:58 pm ET
"Account:"\tacct-a\t

Stocks
Current Value:\t$1.00\t"$0.00"\t"0.00%"
View:\tStock (default)

Symbol\tQty\tPrice\tChg ($)\tCost\tMkt value\tMaint req\tGain ($)\tGain (%)\t
"XYZ"\t"1,234.567"\t"110.00"\t"0.00"\t"1.00"\t"1.00"\t"0.00"\t"0.00"\t"0.00%"\t



***END OF FILE***
'''


def test_reads_schwab_positions_for_every_account(tmp_path):
    f = tmp_path / "Group-Positions-2022-03-04-164843.csv"
    f.write_text(SCHWAB)
    snaps = s.read_positions(f)
    assert [(x.name, x.digits, x.date, x.holdings, x.cash) for x in snaps] == [
        ("acct-b", "111", dt.date(2022, 3, 4), {"ABC": D("1200")}, D("55.10")),
        ("acct-a", "222", dt.date(2022, 3, 4), {"XYZ": D("2.5")}, D("1.00")),
    ]


def test_reads_tda_positions_without_cash(tmp_path):
    f = tmp_path / "Positions_acct-a_Stocks_2022_03_26.xls"
    f.write_text(TDA)
    [x] = s.read_positions(f)
    assert (x.name, x.digits, x.date, x.holdings, x.cash) == (
        "acct-a", "", dt.date(2022, 3, 26), {"XYZ": D("1234.567")}, None)


def test_snapshot_belongs_to_account_by_number_or_name():
    snap = s.Snapshot("old-nick", "111", dt.date(2022, 1, 1), {}, None, Path("x"))
    assert s.belongs(snap, "acct-b", "111")
    tda = s.Snapshot("acct-a", "", dt.date(2022, 1, 1), {}, None, Path("x"))
    assert s.belongs(tda, "acct-a", "222") and not s.belongs(tda, "acct-b", "111")


#
# rolling back, replaying and checking
#

def test_roll_back_from_a_snapshot_to_the_start():
    rows = txns(
        row("01/04/2022", "Buy", "ABC", "10", amount="-$100.00"),
        row("01/05/2022", "Sell", "XYZ", "5", amount="$60.00"),
        row("03/10/2022", "Buy", "ABC", "1", amount="-$11.00"),  # after the snapshot: ignored
    )
    snap = s.Snapshot("a", "1", dt.date(2022, 3, 4), {"ABC": D("10"), "XYZ": D("1")}, D("10"), Path("x"))
    holdings, cash = s.roll_back(rows, snap)
    assert holdings == {"XYZ": D("6")}
    assert cash == D("50")


def test_replay_fails_on_a_negative_holding():
    rows = txns(row("01/05/2022", "Sell", "XYZ", "5", amount="$60.00"))
    with pytest.raises(ValueError, match="XYZ.*2022-01-05"):
        s.replay(rows, {}, D(0), dt.date(2022, 12, 30))


def test_check_lists_mismatches_but_accepts_matches():
    rows = txns(row("01/04/2022", "Buy", "ABC", "10", amount="-$100.00"))
    good = s.Snapshot("a", "1", dt.date(2022, 1, 7), {"ABC": D("10")}, D("0"), Path("good"))
    bad = s.Snapshot("a", "1", dt.date(2022, 1, 8), {"ABC": D("9")}, D("5"), Path("bad"))
    results = s.check(rows, {}, D(100), [good, bad])
    assert results[0][1:] == ([], False)
    assert results[1][1] == ["ABC: replay 10, file 9", "cash: replay 0.00, file 5.00"]


def test_check_accepts_a_file_that_matches_the_day_before():
    rows = txns(row("01/07/2022", "Buy", "ABC", "10", amount="-$100.00"))
    saved_early = s.Snapshot("a", "1", dt.date(2022, 1, 7), {}, D("100"), Path("early"))
    assert s.check(rows, {}, D(100), [saved_early])[0][1:] == ([], True)


def test_yearly_totals_from_json_and_output_agree():
    rows = txns(
        row("01/04/2022", "Buy", "ABC", "10", amount="-$100.00"),
        row("01/05/2022", "Sell", "ABC", "4", fees="$0.10", amount="$47.90"),
        row("01/06/2022", "Cash Dividend", "ABC", amount="$3.00"),
        row("02/27/2022 as of 01/28/2022", "Cash Dividend", "ABC", amount="$15.00"),
        row("02/28/2022 as of 01/28/2022", "Div Adjustment", "ABC", amount="-$15.00"),
        row("01/07/2022", "MoneyLink Deposit", amount="$500.00"),
        row("01/08/2022", "Journal", amount="$70.00"),
        row("01/09/2022", "Tax Withholding", amount="-$20.00"),
        row("01/10/2022", "Bank Interest", amount="$0.16"),
    )
    p, a, _ = s.convert(rows, "acct")
    assert s.totals_from_json(rows) == s.totals_from_output(p, a)
    assert s.totals_from_json(rows)[(2022, "deposits")] == D("570.00")


# End to end, without Tiingo.
def test_run_writes_both_csvs_with_an_opening_position(tmp_path, monkeypatch):
    hist = history(tmp_path, "acct-a_XXX222_Transactions_20221231-120000.json", [
        row("01/04/2022", "Buy", "XYZ", "1", amount="-$4.00"),
    ])
    pos = tmp_path / "positions"
    pos.mkdir()
    (pos / "Group-Positions-2022-03-04-164843.csv").write_text(SCHWAB)
    out = tmp_path / "out"
    monkeypatch.setattr(s, "close_on", lambda symbol, day: D("3.50"))
    s.run([hist], [pos], out, force=False)
    portfolio = (out / "portfolio-transactions.csv").read_text().splitlines()
    account = (out / "account-transactions.csv").read_text().splitlines()
    assert portfolio[1].startswith("2022-01-03,,Delivery (Inbound),5.25,USD,1.5,")
    assert account[1].startswith("2022-01-03,Deposit,5.00,USD")
