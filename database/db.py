import json
from pathlib import Path
import aiosqlite

DB_PATH = Path(__file__).resolve().parent.parent / "antihouse.sqlite3"


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        await db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            tg_id INTEGER PRIMARY KEY,
            username TEXT,
            display_name TEXT,
            step INTEGER,
            draft TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tg_id INTEGER NOT NULL UNIQUE,
            answers TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending'
                CHECK(status IN ('pending', 'accepted', 'rejected')),
            reject_reason TEXT,
            invite_link TEXT,
            reviewed_by INTEGER,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            reviewed_at TEXT,
            FOREIGN KEY(tg_id) REFERENCES users(tg_id)
        );

        CREATE TABLE IF NOT EXISTS admin_sessions (
            admin_tg_id INTEGER PRIMARY KEY,
            application_id INTEGER NOT NULL,
            mode TEXT NOT NULL,
            FOREIGN KEY(application_id) REFERENCES applications(id)
        );

        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            application_id INTEGER NOT NULL,
            sender_tg_id INTEGER NOT NULL,
            recipient_tg_id INTEGER NOT NULL,
            text TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(application_id) REFERENCES applications(id)
        );
        """)
        await db.commit()


async def upsert_user(tg_id: int, username: str | None, display_name: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO users (tg_id, username, display_name)
            VALUES (?, ?, ?)
            ON CONFLICT(tg_id) DO UPDATE SET
                username = excluded.username,
                display_name = excluded.display_name
        """, (tg_id, username, display_name))
        await db.commit()


async def get_user(tg_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM users WHERE tg_id = ?", (tg_id,))
        row = await cur.fetchone()
        return dict(row) if row else None


async def update_draft(tg_id: int, step: int | None, draft: dict) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET step = ?, draft = ? WHERE tg_id = ?",
            (step, json.dumps(draft, ensure_ascii=False), tg_id),
        )
        await db.commit()


async def get_application_by_user(tg_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM applications WHERE tg_id = ?", (tg_id,))
        row = await cur.fetchone()
        return dict(row) if row else None


async def get_application(application_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM applications WHERE id = ?", (application_id,))
        row = await cur.fetchone()
        return dict(row) if row else None


async def create_application(tg_id: int, answers: dict) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO applications (tg_id, answers, status) VALUES (?, ?, 'pending')",
            (tg_id, json.dumps(answers, ensure_ascii=False)),
        )
        await db.commit()
        return int(cur.lastrowid)


async def review_application(application_id: int, status: str, admin_id: int,
                             reason: str | None = None, invite_link: str | None = None) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE applications
            SET status = ?, reject_reason = ?, invite_link = ?,
                reviewed_by = ?, reviewed_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (status, reason, invite_link, admin_id, application_id))
        await db.commit()


async def set_admin_session(admin_id: int, application_id: int, mode: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO admin_sessions (admin_tg_id, application_id, mode)
            VALUES (?, ?, ?)
            ON CONFLICT(admin_tg_id) DO UPDATE SET
                application_id = excluded.application_id, mode = excluded.mode
        """, (admin_id, application_id, mode))
        await db.commit()


async def get_admin_session(admin_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM admin_sessions WHERE admin_tg_id = ?", (admin_id,))
        row = await cur.fetchone()
        return dict(row) if row else None


async def clear_admin_session(admin_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM admin_sessions WHERE admin_tg_id = ?", (admin_id,))
        await db.commit()


async def save_message(application_id: int, sender: int, recipient: int, text: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO messages (application_id, sender_tg_id, recipient_tg_id, text)
            VALUES (?, ?, ?, ?)
        """, (application_id, sender, recipient, text))
        await db.commit()
