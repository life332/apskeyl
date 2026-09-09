# -*- coding: utf-8 -*-
"""Бібліотека відео + черга задач: SQLite у WAL. Файли власника НЕ копіюємо — тільки
шлях + паспорт + превʼю. Файл зник з диска → картка сіріє, а не зникає мовчки.

Черга (Етап 3): jobs + segments. Commit після КОЖНОГО сегмента — світло/kill → на старті
ядро бачить незавершену задачу і продовжує з наступного сегмента, не з нуля."""
from __future__ import annotations
import json, sqlite3, time
from pathlib import Path

from config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS library(
    id INTEGER PRIMARY KEY,
    path TEXT UNIQUE NOT NULL,
    key TEXT UNIQUE NOT NULL,          -- дедуп: розмір+mtime+sha1 1-го МБ
    info TEXT NOT NULL,                -- json-паспорт із media.probe()
    thumb TEXT,
    hard_t REAL,                       -- найдинамічніший момент (для проби)
    added REAL NOT NULL,
    status TEXT DEFAULT 'new'          -- new | queued | running | done | error | missing
);
CREATE TABLE IF NOT EXISTS jobs(
    id INTEGER PRIMARY KEY,
    item_id INTEGER,
    src TEXT NOT NULL,
    recipe TEXT NOT NULL,              -- json: target, model, codec
    state TEXT NOT NULL DEFAULT 'QUEUED',
    reason TEXT DEFAULT '',            -- чому PAUSED / FAILED / що робимо зараз
    seg_total INTEGER DEFAULT 0,
    seg_done INTEGER DEFAULT 0,
    frames_total INTEGER DEFAULT 0,
    frames_done INTEGER DEFAULT 0,
    speed REAL DEFAULT 0,              -- кадр/с за фактом
    eta_s REAL DEFAULT 0,
    out_path TEXT,
    out_size INTEGER DEFAULT 0,
    pid INTEGER DEFAULT 0,
    heartbeat REAL DEFAULT 0,
    created REAL NOT NULL,
    started REAL DEFAULT 0,
    finished REAL DEFAULT 0,
    elapsed_s REAL DEFAULT 0,
    note TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS segments(
    job_id INTEGER NOT NULL,
    idx INTEGER NOT NULL,
    t0 REAL, t1 REAL,
    frames_plan INTEGER DEFAULT 0,
    state TEXT DEFAULT 'todo',         -- todo | done | failed
    frames INTEGER DEFAULT 0,
    ms INTEGER DEFAULT 0,
    path TEXT,
    PRIMARY KEY(job_id, idx)
);
"""

ACTIVE = ("QUEUED", "PREPARING", "PROCESSING", "ENCODING", "VERIFYING", "PAUSED")
RUNNING = ("PREPARING", "PROCESSING", "ENCODING", "VERIFYING")


def cx() -> sqlite3.Connection:
    c = sqlite3.connect(DB_PATH, timeout=15)
    c.execute("PRAGMA journal_mode=WAL")
    c.row_factory = sqlite3.Row
    c.executescript(SCHEMA)
    return c


# ── бібліотека ──────────────────────────────────────────────────────────────────
def add(path: Path, key: str, info: dict, thumb: str, hard_t: float) -> int | None:
    """None = дублікат (той самий файл уже в бібліотеці, хай і під іншим шляхом)."""
    with cx() as c:
        try:
            cur = c.execute(
                "INSERT INTO library(path,key,info,thumb,hard_t,added) VALUES(?,?,?,?,?,?)",
                (str(path), key, json.dumps(info), thumb, hard_t, time.time()))
            return cur.lastrowid
        except sqlite3.IntegrityError:
            return None


def get_by_path(path: Path) -> dict | None:
    with cx() as c:
        r = c.execute("SELECT * FROM library WHERE path=?", (str(path),)).fetchone()
    if r is None:
        return None
    d = dict(r)
    d["info"] = json.loads(d["info"])
    return d


def refresh(path: Path, key: str, info: dict, thumb: str, hard_t: float) -> None:
    """Файл перезаписали під тим самим імʼям → оновлюємо паспорт, а не брешемо
    «уже в бібліотеці» зі старими даними (ревізія 28.08)."""
    with cx() as c:
        c.execute("UPDATE library SET key=?, info=?, thumb=?, hard_t=?, status='new' "
                  "WHERE path=?",
                  (key, json.dumps(info), thumb, hard_t, str(path)))


def known_paths() -> set[str]:
    with cx() as c:
        return {r["path"] for r in c.execute("SELECT path FROM library")}


def _row(r) -> dict:
    d = dict(r)
    d["info"] = json.loads(d["info"])
    d["exists"] = Path(d["path"]).exists()
    return d


def items() -> list[dict]:
    with cx() as c:
        rows = c.execute("SELECT * FROM library ORDER BY added DESC").fetchall()
    return [_row(r) for r in rows]


def get(item_id: int) -> dict | None:
    with cx() as c:
        r = c.execute("SELECT * FROM library WHERE id=?", (item_id,)).fetchone()
    return None if r is None else _row(r)


def remove(item_id: int):
    with cx() as c:
        c.execute("DELETE FROM library WHERE id=?", (item_id,))


# ── черга ───────────────────────────────────────────────────────────────────────
def _jrow(r) -> dict:
    d = dict(r)
    d["recipe"] = json.loads(d["recipe"])
    return d


def job_add(item_id: int, src: Path, recipe: dict) -> int:
    with cx() as c:
        cur = c.execute("INSERT INTO jobs(item_id,src,recipe,created) VALUES(?,?,?,?)",
                        (item_id, str(src), json.dumps(recipe), time.time()))
        c.execute("UPDATE library SET status='queued' WHERE id=?", (item_id,))
        return cur.lastrowid


def job_get(job_id: int) -> dict | None:
    with cx() as c:
        r = c.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    return None if r is None else _jrow(r)


def jobs_list() -> list[dict]:
    with cx() as c:
        rows = c.execute("SELECT * FROM jobs ORDER BY id").fetchall()
    return [_jrow(r) for r in rows]


def job_update(job_id: int, **fields) -> None:
    if not fields:
        return
    cols = ", ".join(f"{k}=?" for k in fields)
    with cx() as c:
        c.execute(f"UPDATE jobs SET {cols} WHERE id=?", (*fields.values(), job_id))


def job_delete(job_id: int) -> None:
    with cx() as c:
        c.execute("DELETE FROM segments WHERE job_id=?", (job_id,))
        c.execute("DELETE FROM jobs WHERE id=?", (job_id,))


def next_queued() -> dict | None:
    with cx() as c:
        r = c.execute("SELECT * FROM jobs WHERE state='QUEUED' ORDER BY id LIMIT 1").fetchone()
    return None if r is None else _jrow(r)


def jobs_active_count() -> int:
    with cx() as c:
        q = ",".join("?" * len(ACTIVE))
        return c.execute(f"SELECT COUNT(*) FROM jobs WHERE state IN ({q})", ACTIVE).fetchone()[0]


def recover_after_restart() -> int:
    """Задачі, що були в роботі, коли процес помер (світло/kill) → назад у чергу.
    Готові сегменти лишаються — продовжимо з наступного."""
    with cx() as c:
        q = ",".join("?" * len(RUNNING))
        cur = c.execute(f"UPDATE jobs SET state='QUEUED', pid=0, "
                        f"reason='продовжено після перезапуску' WHERE state IN ({q})", RUNNING)
        return cur.rowcount


def seg_init(job_id: int, segs: list[tuple[int, float, float, int]]) -> None:
    with cx() as c:
        c.execute("DELETE FROM segments WHERE job_id=?", (job_id,))
        c.executemany("INSERT INTO segments(job_id,idx,t0,t1,frames_plan) VALUES(?,?,?,?,?)",
                      [(job_id, i, t0, t1, n) for (i, t0, t1, n) in segs])


def seg_list(job_id: int) -> list[dict]:
    with cx() as c:
        rows = c.execute("SELECT * FROM segments WHERE job_id=? ORDER BY idx",
                         (job_id,)).fetchall()
    return [dict(r) for r in rows]


def seg_update(job_id: int, idx: int, **fields) -> None:
    cols = ", ".join(f"{k}=?" for k in fields)
    with cx() as c:
        c.execute(f"UPDATE segments SET {cols} WHERE job_id=? AND idx=?",
                  (*fields.values(), job_id, idx))


def library_status(item_id: int, status: str) -> None:
    with cx() as c:
        c.execute("UPDATE library SET status=? WHERE id=?", (status, item_id))
