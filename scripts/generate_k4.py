#!/usr/bin/env python3
"""
Generate K4 SRU files for Swedish tax declaration.

Run from the project root:
    python scripts/generate_k4.py

Edit the CONFIGURATION section below before running.
Output: BLANKETTER.SRU and INFO.SRU in the current directory.
Upload BLANKETTER.SRU at skatteverket.se → Inkomstdeklaration 1 → Importera K4.
"""

import os
import re
import sqlite3
from datetime import datetime

# ── CONFIGURATION ─────────────────────────────────────────────────────────────

YEAR = 2025

# Average annual EUR/SEK and DKK/SEK rates for 2025.
# Verify at: https://www.riksbank.se/sv/statistik/sokrantor/
EUR_SEK = 11.10
DKK_SEK = 1.49

OUTPUT_DIR = "."

# ── SECTION CLASSIFICATION ────────────────────────────────────────────────────
# Instruments listed here → K4 Section D (råvaror/commodities).
# All others → Section A (marknadsnoterade aktieindex/aktier).
SECTION_D_INSTRUMENTS = {
    "Gold (per 0.1)",
}

# ─────────────────────────────────────────────────────────────────────────────

DB_PATH = os.path.expanduser(
    "~/Library/Application Support/TradingAnalyzer/trading.db"
)

# Trade Nation actions that represent closed positions or financing costs.
# Fund payable/receivable are deposits/withdrawals — excluded.
TRADE_ACTIONS = (
    "Trade Receivable",
    "Trade Payable",
    "Funding Charges",
    "Buy",    # TD365
    "Sell",   # TD365
)


def to_sek(amount: float, currency: str) -> float:
    rates = {"SEK": 1.0, "EUR": EUR_SEK, "DKK": DKK_SEK}
    if currency not in rates:
        raise ValueError(f"Unknown currency: {currency}")
    return amount * rates[currency]


def list_accounts() -> list[tuple]:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT account_id, account_name, broker_name, currency FROM accounts ORDER BY account_id")
    rows = cur.fetchall()
    conn.close()
    return rows


def prompt_personnummer() -> str:
    while True:
        pnr = input("Personnummer (12 siffror, utan bindestreck, t.ex. 197001011234): ").strip()
        if re.fullmatch(r"\d{12}", pnr):
            return pnr
        print("  Ogiltigt format — ange exakt 12 siffror.")


def prompt_name() -> str:
    while True:
        name = input("Namn (Förnamn Efternamn): ").strip()
        if name:
            return name
        print("  Namn får inte vara tomt.")


def prompt_accounts(accounts: list[tuple]) -> list[int]:
    print("\nTillgängliga konton:")
    for acc_id, acc_name, broker, currency in accounts:
        print(f"  [{acc_id}] {acc_name}  ({broker}, {currency})")
    print("  [A] Alla konton")
    while True:
        raw = input("\nVälj konton (kommaseparerade siffror eller A för alla): ").strip().upper()
        if raw == "A":
            return [acc_id for acc_id, *_ in accounts]
        parts = [p.strip() for p in raw.split(",")]
        valid_ids = {acc_id for acc_id, *_ in accounts}
        try:
            chosen = [int(p) for p in parts if p]
            if chosen and all(c in valid_ids for c in chosen):
                return chosen
        except ValueError:
            pass
        print("  Ogiltigt val — ange t.ex. 1,2 eller A.")


def fetch_pl_by_instrument(account_ids: list[int]) -> list[tuple]:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    action_ph = ",".join("?" * len(TRADE_ACTIONS))
    account_ph = ",".join("?" * len(account_ids))
    cur.execute(
        f"""
        SELECT "Description", "Currency", SUM("P/L")
        FROM broker_transactions
        WHERE "Transaction Date" >= ?
          AND "Transaction Date" < ?
          AND "P/L" IS NOT NULL AND "P/L" != 0
          AND "Action" IN ({action_ph})
          AND account_id IN ({account_ph})
        GROUP BY "Description", "Currency"
        ORDER BY "Description", "Currency"
        """,
        (f"{YEAR}-01-01", f"{YEAR + 1}-01-01", *TRADE_ACTIONS, *account_ids),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def aggregate_to_sek(rows: list[tuple]) -> dict[str, int]:
    """Sum P/L per instrument across all currencies, convert to whole SEK."""
    totals: dict[str, float] = {}
    for description, currency, pl in rows:
        totals[description] = totals.get(description, 0.0) + to_sek(pl, currency)
    return {k: round(v) for k, v in sorted(totals.items())}


def _sru_entry_lines(row_num: int, section_prefix: int, name: str, pl_sek: int) -> list[str]:
    base = section_prefix * 10 + row_num
    lines = [
        f"#UPPGIFT {base}0 1",           # antal
        f"#UPPGIFT {base}1 {name}",      # beteckning
    ]
    if pl_sek >= 0:
        lines += [
            f"#UPPGIFT {base}2 {pl_sek}",    # försäljningspris
            f"#UPPGIFT {base}3 0",            # omkostnadsbelopp
            f"#UPPGIFT {base}4 {pl_sek}",    # vinst
        ]
    else:
        loss = -pl_sek
        lines += [
            f"#UPPGIFT {base}2 0",            # försäljningspris
            f"#UPPGIFT {base}3 {loss}",       # omkostnadsbelopp
            f"#UPPGIFT {base}5 {loss}",       # förlust
        ]
    return lines


def build_blanketter(
    section_a: dict[str, int],
    section_d: dict[str, int],
    personnummer: str,
    name: str,
) -> str:
    if len(section_a) > 9:
        raise ValueError(
            f"Section A has {len(section_a)} instruments but K4 allows 9 per form. "
            "Split manually or combine instruments."
        )
    if len(section_d) > 7:
        raise ValueError(
            f"Section D has {len(section_d)} instruments but K4 allows 7 per form. "
            "Split manually or combine instruments."
        )

    now = datetime.now()
    lines = [
        f"#BLANKETT K4-{YEAR}P4",
        f"#IDENTITET {personnummer} {now.strftime('%Y%m%d')} {now.strftime('%H%M%S')}",
        f"#NAMN {name}",
    ]

    if section_a:
        lines.append(f"#UPPGIFT 7011 {len(section_a)}")
        for i, (instrument, pl) in enumerate(section_a.items(), start=1):
            lines.extend(_sru_entry_lines(i, 31, instrument, pl))

    if section_d:
        lines.append(f"#UPPGIFT 7014 {len(section_d)}")
        for i, (instrument, pl) in enumerate(section_d.items(), start=1):
            lines.extend(_sru_entry_lines(i, 34, instrument, pl))

    lines += ["#BLANKETTSLUT", "#FIL_SLUT"]
    return "\n".join(lines) + "\n"


def build_info(personnummer: str, name: str) -> str:
    now = datetime.now()
    lines = [
        "#DATABESKRIVNING_START",
        "#PRODUKT TradingAnalyzer",
        f"#SKAPAD {now.strftime('%Y%m%d')}",
        "#PROGRAM TradingAnalyzer",
        f"#ORGNR {personnummer}",
        f"#NAMN {name}",
        "#DATABESKRIVNING_SLUT",
        "#MEDGIVANDE_START",
        f"#ORGNR {personnummer}",
        "#MEDGIVANDE_SLUT",
    ]
    return "\n".join(lines) + "\n"


def print_preview(section_a: dict[str, int], section_d: dict[str, int]) -> None:
    print(f"\nK4 {YEAR} — Preview")
    print("=" * 60)
    print(f"\nExchange rates used:  EUR/SEK = {EUR_SEK},  DKK/SEK = {DKK_SEK}")

    print(f"\nSection A — Marknadsnoterade aktieindex/aktier ({len(section_a)} rader):")
    for name, pl in section_a.items():
        tag = "VINST  " if pl >= 0 else "FÖRLUST"
        print(f"  {tag}  {abs(pl):>10,} SEK   {name}")

    print(f"\nSection D — Råvaror/övriga tillgångar ({len(section_d)} rader):")
    for name, pl in section_d.items():
        tag = "VINST  " if pl >= 0 else "FÖRLUST"
        print(f"  {tag}  {abs(pl):>10,} SEK   {name}")

    net_a = sum(section_a.values())
    net_d = sum(section_d.values())
    print(f"\n  Section A netto:  {net_a:+,} SEK")
    print(f"  Section D netto:  {net_d:+,} SEK")
    print(f"  Totalt netto:     {net_a + net_d:+,} SEK\n")


def main() -> None:
    print(f"\n=== K4 Generator — inkomstår {YEAR} ===")

    personnummer = prompt_personnummer()
    name = prompt_name()

    accounts = list_accounts()
    account_ids = prompt_accounts(accounts)
    chosen_names = [acc_name for acc_id, acc_name, *_ in accounts if acc_id in account_ids]
    print(f"\nValde konton: {', '.join(chosen_names)}\n")

    rows = fetch_pl_by_instrument(account_ids)
    totals = aggregate_to_sek(rows)

    section_a = {k: v for k, v in totals.items() if k not in SECTION_D_INSTRUMENTS}
    section_d = {k: v for k, v in totals.items() if k in SECTION_D_INSTRUMENTS}

    print_preview(section_a, section_d)

    blanketter = build_blanketter(section_a, section_d, personnummer, name)
    info = build_info(personnummer, name)

    blanketter_path = os.path.join(OUTPUT_DIR, "BLANKETTER.SRU")
    info_path = os.path.join(OUTPUT_DIR, "INFO.SRU")

    with open(blanketter_path, "w", encoding="latin-1") as f:
        f.write(blanketter)
    with open(info_path, "w", encoding="latin-1") as f:
        f.write(info)

    print(f"Skapade: {blanketter_path}")
    print(f"Skapade: {info_path}")
    print()
    print("Nästa steg:")
    print("  1. Kontrollera beloppen i previewen ovan")
    print("  2. Verifiera EUR/SEK och DKK/SEK mot Riksbankens årsgenomsnitt")
    print("  3. Logga in på skatteverket.se → Inkomstdeklaration 1")
    print("     → Försäljning värdepapper K4 → Importera → ladda upp BLANKETTER.SRU")


if __name__ == "__main__":
    main()
