import aiosqlite

DB_FILE = "bot_database.db"

async def init_db():
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                user_id INTEGER PRIMARY KEY,
                username TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS groups (
                group_id INTEGER PRIMARY KEY,
                group_name TEXT
            )
        """)
        await db.commit()
        
        cursor = await db.execute("SELECT value FROM settings WHERE key = 'country'")
        if not await cursor.fetchone():
            defaults = [
                ("country", "ET"),
                ("service", "Facebook"),
                ("otp_length", "5"),
                ("otp_type", "new_account"),
                ("number_bot_link", ""),
                ("main_channel_link", ""),
                ("auto_interval", "60")
            ]
            await db.executemany("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", defaults)
            await db.commit()

async def put(key: str, value: str):
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
        await db.commit()

async def all_settings() -> dict:
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute("SELECT key, value FROM settings") as cursor:
            rows = await cursor.fetchall()
            return {row[0]: row[1] for row in rows}

async def is_admin(user_id: int) -> bool:
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute("SELECT 1 FROM admins WHERE user_id = ?", (user_id,)) as cursor:
            if await cursor.fetchone():
                return True
    return False

async def add_admin(user_id: int, username: str = ""):
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("INSERT OR IGNORE INTO admins (user_id, username) VALUES (?, ?)", (user_id, username))
        await db.commit()

async def remove_admin(user_id: int):
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("DELETE FROM admins WHERE user_id = ?", (user_id,))
        await db.commit()

async def list_admins() -> list:
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute("SELECT user_id, username FROM admins") as cursor:
            return await cursor.fetchall()

async def add_group(group_id: int, group_name: str = "Telegram Group") -> bool:
    try:
        async with aiosqlite.connect(DB_FILE) as db:
            await db.execute("INSERT OR REPLACE INTO groups (group_id, group_name) VALUES (?, ?)", (group_id, group_name))
            await db.commit()
        return True
    except Exception:
        return False

async def remove_group(group_id: int):
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("DELETE FROM groups WHERE group_id = ?", (group_id,))
        await db.commit()

async def get_groups() -> list:
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute("SELECT group_id, group_name FROM groups") as cursor:
            rows = await cursor.fetchall()
            return [{"id": r[0], "name": r[1]} for r in rows]

