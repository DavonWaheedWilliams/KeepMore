"""SQLite persistence. One database file per workspace; never stores bank credentials."""
from __future__ import annotations
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
from typing import Iterator

SCHEMA = """
CREATE TABLE IF NOT EXISTS transactions (
 id INTEGER PRIMARY KEY AUTOINCREMENT, occurred_on TEXT NOT NULL, merchant TEXT NOT NULL,
 category TEXT NOT NULL, amount_cents INTEGER NOT NULL, source TEXT NOT NULL DEFAULT 'manual',
 note TEXT NOT NULL DEFAULT '', batch_id TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_transactions_date ON transactions(occurred_on);
CREATE TABLE IF NOT EXISTS recurring (
 id INTEGER PRIMARY KEY AUTOINCREMENT, merchant TEXT NOT NULL, category TEXT NOT NULL,
 amount_cents INTEGER NOT NULL, cycle TEXT NOT NULL, next_due TEXT NOT NULL,
 usage TEXT NOT NULL DEFAULT 'Not rated', status TEXT NOT NULL DEFAULT 'active',
 note TEXT NOT NULL DEFAULT '', origin TEXT NOT NULL DEFAULT 'manual', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS actions (
 id INTEGER PRIMARY KEY AUTOINCREMENT, recurring_id INTEGER, title TEXT NOT NULL, kind TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'planned', before_cents INTEGER NOT NULL DEFAULT 0,
 after_cents INTEGER NOT NULL DEFAULT 0, cycle TEXT NOT NULL DEFAULT 'Monthly',
 completed_at TEXT, notes TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS budgets (category TEXT PRIMARY KEY, limit_cents INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS goals (
 id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, target_cents INTEGER NOT NULL,
 saved_cents INTEGER NOT NULL DEFAULT 0, target_date TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS imports (sha256 TEXT PRIMARY KEY, name TEXT NOT NULL, row_count INTEGER NOT NULL, imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS interest (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT NOT NULL UNIQUE, plan TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
"""

def path_for(mode: str, data_dir: str = "data") -> Path:
    if mode not in {"demo","personal"}:
        raise ValueError("Unknown workspace")
    p=Path(data_dir).expanduser().resolve()
    p.mkdir(parents=True,exist_ok=True)
    return p / f"keepmore_{mode}.sqlite3"

@contextmanager
def db(path: Path | str) -> Iterator[sqlite3.Connection]:
    conn=sqlite3.connect(str(path), timeout=20)
    conn.row_factory=sqlite3.Row
    conn.execute("PRAGMA busy_timeout=20000")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(SCHEMA)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def rows(conn,sql: str, params: tuple=()) -> list[dict]:
    return [dict(r) for r in conn.execute(sql,params).fetchall()]

def get_setting(conn,key: str, fallback: str="") -> str:
    r=conn.execute("SELECT value FROM settings WHERE key=?",(key,)).fetchone()
    return r["value"] if r else fallback

def setting(conn,key: str,value: str):
    conn.execute("INSERT INTO settings(key,value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(key,str(value)))

def add_transaction(conn, on: str, merchant: str, category: str, amount_cents: int, note: str="", source: str="manual",batch: str | None=None):
    if not merchant.strip() or not amount_cents:
        raise ValueError("Merchant and nonzero amount required")
    conn.execute("INSERT INTO transactions(occurred_on,merchant,category,amount_cents,note,source,batch_id) VALUES(?,?,?,?,?,?,?)",(on,merchant.strip()[:160],category,amount_cents,note[:500],source,batch))

def add_recurring(conn,merchant,category,amount_cents,cycle,next_due,usage="Not rated",note="",origin="manual"):
    if not merchant.strip() or amount_cents<=0:
        raise ValueError("A name and positive amount are required")
    conn.execute("INSERT INTO recurring(merchant,category,amount_cents,cycle,next_due,usage,note,origin) VALUES(?,?,?,?,?,?,?,?)",(merchant.strip()[:160],category,amount_cents,cycle,next_due,usage,note[:500],origin))

def add_goal(conn,title,target_cents,saved_cents,target_date):
    if not title.strip() or target_cents<=0 or saved_cents<0:
        raise ValueError("Invalid goal")
    conn.execute("INSERT INTO goals(title,target_cents,saved_cents,target_date) VALUES(?,?,?,?)",(title.strip()[:90],target_cents,saved_cents,target_date))

def actions_savings(actions: list[dict]) -> int:
    from keepmore.engine import CYCLES
    return sum(max(0,int(a["before_cents"])-int(a["after_cents"]))*CYCLES.get(a["cycle"],12) for a in actions if a["status"]=="completed")

def export_database(conn) -> dict[str,list[dict]]:
    return {table:rows(conn,f"SELECT * FROM {table}") for table in ["transactions","recurring","actions","budgets","goals","settings"]}

def clear_workspace(conn):
    for table in ["transactions","recurring","actions","budgets","goals","settings","imports","interest"]:
        conn.execute(f"DELETE FROM {table}")
