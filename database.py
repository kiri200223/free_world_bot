import aiosqlite
from datetime import datetime
from typing import List, Tuple
from config import DATABASE_PATH

async def init_db():
    """Создает таблицу для хранения раздач."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS sent_giveaways (
                giveaway_id TEXT PRIMARY KEY,
                title TEXT,
                source TEXT,
                published_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()

async def is_giveaway_sent(giveaway_id: str) -> bool:
    """Проверяет, отправлялась ли уже эта раздача."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("SELECT 1 FROM sent_giveaways WHERE giveaway_id = ?", (giveaway_id,))
        row = await cursor.fetchone()
        return row is not None

async def mark_giveaway_sent(giveaway_id: str, title: str, source: str):
    """Сохраняет раздачу как отправленную."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """INSERT OR IGNORE INTO sent_giveaways 
               (giveaway_id, title, source, published_at, last_checked_at) 
               VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)""",
            (giveaway_id, title, source)
        )
        await db.commit()

async def get_all_stored_giveaways() -> List[Tuple[str, str]]:
    """Возвращает список всех сохраненных раздач (id, source)."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("SELECT giveaway_id, source FROM sent_giveaways")
        return await cursor.fetchall()

async def remove_expired_giveaway(giveaway_id: str):
    """Удаляет неактуальную/закончившуюся раздачу из базы данных."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("DELETE FROM sent_giveaways WHERE giveaway_id = ?", (giveaway_id,))
        await db.commit()

async def clean_old_rss_giveaways(days: int = 7):
    """
    Удаляет RSS раздачи старше N дней, так как большинство RSS акций длятся от 1 до 7 дней.
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM sent_giveaways WHERE source != 'GamerPower' AND published_at <= datetime('now', ?)",
            (f"-{days} days",)
        )
        await db.commit()
        return cursor.rowcount
