"""Tests for bin/tda-statements-to-pp, on made-up rows and amounts only.

    uv run --with pytest pytest tests
"""

import datetime as dt
import importlib.machinery
import importlib.util
from decimal import Decimal as D
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "bin" / "tda-statements-to-pp"
loader = importlib.machinery.SourceFileLoader("tda_statements_to_pp", str(SCRIPT))
spec = importlib.util.spec_from_loader(loader.name, loader)
t = importlib.util.module_from_spec(spec)
loader.exec_module(t)

PAD = " " * 60  # continuation lines sit under the description column


def test_rows_survive_the_layout_quirks():
    rows = t.parse_rows([
        # a long name runs into its symbol with one space
        "03/02/16 03/07/16     Cash   Sell - Securities Sold         EXAMPLE HOLDING CORP XMPL"
        "              1,100-   $ 20.00   $ 21,990.01    22,000.00",
        PAD + "COM",
        PAD + "Commission/Fee 9.99",
        # a reinvested dividend's fractional quantity wraps onto the second line
        "08/07/23   08/09/23   Cash   Buy - Securities Purchased     EXAMPLE TRUST"
        "                    ABCD                 110.0000      (123.45)      7,876.55",
        PAD + "SHORT BOND ETF                                       2.5",
    ])
    assert [(r.symbol, r.qty) for r in rows] == [("XMPL", D("-1100")), ("ABCD", D("2.5"))]
    assert rows[0].fees() == D("9.99")


def statement(rows, interest="0"):
    return t.Statement(month="2015-03", path=Path("x"), rows=rows, summary={}, positions={},
                       deposit_account=D(0), deposit_interest=D(interest))


def row(type_, desc="", symbol="-", qty=None, amount="0", extra=()):
    return t.Row(trade=dt.date(2015, 3, 10), type=type_, description=desc, symbol=symbol,
                 qty=None if qty is None else D(qty), amount=D(amount), extra=list(extra))


def test_deposit_interest_comes_from_the_income_summary():
    # Most of the deposit account's interest is credited inside it with no activity row,
    # so the month's IDA Interest replaces the Div/Int - Other row rather than adding to it.
    booked = statement([
        row("Div/Int - Other", "FDIC INSURED DEPOSIT", "MMDA1", amount="0.03"),
        row("Journal - Other", "PURCHASE FDIC INSURED", amount="-500.00"),
    ], interest="0.50").booked()
    assert [(r.type, r.trade, r.amount) for r in booked] == [
        ("IDA Interest", dt.date(2015, 3, 31), D("0.50"))]


@pytest.mark.parametrize("r,expect", [
    (row("Journal - Other", "Courtesy Credit", amount="5.00"), ("account", "Fees Refund", "")),
    (row("Received - Other", "EXAMPLE CORP", "XMPL", qty="200"),
     ("portfolio", "Delivery (Inbound)", "XMPL")),
    (row("Buy - Securities Purchased", "VONAGE HOLDINGS CORP", "VG", qty="10", amount="-100.00"),
     ("portfolio", "Buy", "US000000002908")),
])
def test_mapping_decisions(r, expect):
    portfolio, cash = t.convert([r], "acct", {})
    (side, out), = [("portfolio", x) for x in portfolio] + [("account", x) for x in cash]
    assert (side, out["Type"], out.get("Ticker Symbol", "")) == expect
