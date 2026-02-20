#!/usr/bin/env python3
"""
Convert TD365 PDF statement to CSV format for import into Trading Analyzer.

Usage:
    python convert_td365_pdf.py <input.pdf> [output.csv]

If output.csv is not specified, it will use the same name as input with .csv extension.
"""

import csv
import gc
import re
import sys
from datetime import datetime
from pathlib import Path

try:
    import pdfplumber
except ImportError:
    print("Error: pdfplumber is required. Install with: pip install pdfplumber")
    sys.exit(1)


# Pattern: DD/MM/YYYY HH:MM:SS RefNum Buy/Sell Stake Open/Close Market Currency Price P/L P/L
TRADE_PATTERN = re.compile(
    r"^(\d{2}/\d{2}/\d{4})\s+(\d{2}:\d{2}:\d{2})\s+(\d+)\s+(Buy|Sell)\s+([-\d.]+)\s+(Open|Close)\s+(.+?)\s+(DKK|SEK|EUR|USD|GBP|NOK)\s+([\d.]+)\s+([-\d.]+)\s+([-\d.]+)$"
)


def parse_trade_line(line: str) -> dict | None:
    """Parse a single trade line from the PDF text."""
    match = TRADE_PATTERN.match(line.strip())
    if not match:
        return None

    (
        date_str,
        time_str,
        ref,
        action,
        stake,
        open_close,
        market,
        currency,
        price,
        pl1,
        pl2,
    ) = match.groups()

    # Parse datetime
    dt = datetime.strptime(f"{date_str} {time_str}", "%d/%m/%Y %H:%M:%S")

    return {
        "datetime": dt,
        "ref": ref,
        "action": action,
        "stake": float(stake),
        "open_close": open_close,
        "market": market.strip(),
        "currency": currency,
        "price": float(price),
        "pl": float(pl1),
    }


def extract_trades_from_page(page) -> list[dict]:
    """Extract trades from a single PDF page."""
    trades = []
    text = page.extract_text()
    if not text:
        return trades

    for line in text.split("\n"):
        trade = parse_trade_line(line)
        if trade:
            trades.append(trade)

    return trades


def process_pdf_incrementally(pdf_path: str):
    """Generator that yields trades page by page to avoid memory issues."""
    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        print(f"Processing {total_pages} pages...")

        for i, page in enumerate(pdf.pages):
            if (i + 1) % 100 == 0:
                print(f"  Processed {i + 1}/{total_pages} pages...")

            trades = extract_trades_from_page(page)
            for trade in trades:
                yield trade

            # Force garbage collection periodically to free memory
            if (i + 1) % 50 == 0:
                gc.collect()


def pair_trades_streaming(trades_iter) -> list[dict]:
    """
    Pair Open and Close trades by reference number.
    Accumulates only what's needed for pairing.
    """
    # Store open trades waiting for their close
    open_trades = {}
    # Completed paired trades
    paired = []

    for trade in trades_iter:
        ref = trade["ref"]

        if trade["open_close"] == "Open":
            if ref not in open_trades:
                open_trades[ref] = []
            open_trades[ref].append(trade)
        else:  # Close
            if ref in open_trades and open_trades[ref]:
                open_trade = open_trades[ref].pop(0)
                if not open_trades[ref]:
                    del open_trades[ref]

                paired.append(
                    {
                        "ref": ref,
                        "market": open_trade["market"],
                        "currency": open_trade["currency"],
                        "action": open_trade["action"],
                        "stake": abs(open_trade["stake"]),
                        "open_datetime": open_trade["datetime"],
                        "open_price": open_trade["price"],
                        "close_datetime": trade["datetime"],
                        "close_price": trade["price"],
                        "pl": trade["pl"],
                    }
                )

    # Handle any remaining open trades (still open positions)
    for ref, open_list in open_trades.items():
        for t in open_list:
            paired.append(
                {
                    "ref": ref,
                    "market": t["market"],
                    "currency": t["currency"],
                    "action": t["action"],
                    "stake": abs(t["stake"]),
                    "open_datetime": t["datetime"],
                    "open_price": t["price"],
                    "close_datetime": None,
                    "close_price": None,
                    "pl": 0.0,
                }
            )

    # Sort by close datetime (or open if no close)
    paired.sort(key=lambda x: x["close_datetime"] or x["open_datetime"])

    return paired


def generate_csv(
    paired_trades: list[dict], output_path: str, starting_balance: float = 0.0
):
    """Generate CSV in the Trading Analyzer import format."""

    # Calculate running balance
    balance = starting_balance

    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        # Header matching the expected import format
        writer.writerow(
            [
                "Transaction Date",
                "Serial / Ref. No.",
                "Action",
                "Description",
                "Amount",
                "Open Period",
                "Opening",
                "Closing",
                "P/L",
                "Status",
                "Balance",
                "Currency",
            ]
        )

        for trade in paired_trades:
            if trade["close_datetime"] is None:
                # Skip open trades without close
                continue

            balance += trade["pl"]

            # Format datetime as expected
            trans_date = trade["close_datetime"].strftime("%Y-%m-%d %H:%M:%S")
            open_period = trade["open_datetime"].strftime("%Y-%m-%d %H:%M:%S")

            writer.writerow(
                [
                    trans_date,
                    trade["ref"],
                    trade["action"],
                    trade["market"],
                    f"{trade['stake']:.6f}",
                    open_period,
                    f"{trade['open_price']:.6f}",
                    f"{trade['close_price']:.6f}",
                    f"{trade['pl']:.2f}",
                    "Closed",
                    f"{balance:.2f}",
                    trade["currency"],
                ]
            )


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    input_path = sys.argv[1]

    if len(sys.argv) >= 3:
        output_path = sys.argv[2]
    else:
        output_path = str(Path(input_path).with_suffix(".csv"))

    if not Path(input_path).exists():
        print(f"Error: File not found: {input_path}")
        sys.exit(1)

    print(f"Reading PDF: {input_path}")

    # Process incrementally to handle large PDFs
    trades_iter = process_pdf_incrementally(input_path)
    paired = pair_trades_streaming(trades_iter)

    print(f"Paired into {len(paired)} complete transactions")

    # Count closed vs open
    closed_count = sum(1 for t in paired if t["close_datetime"] is not None)
    open_count = len(paired) - closed_count
    print(f"  Closed: {closed_count}, Still open: {open_count}")

    generate_csv(paired, output_path)
    print(f"CSV written to: {output_path}")


if __name__ == "__main__":
    main()
