import aiosqlite
from datetime import datetime
from typing import Optional


async def init_db(db_path: str = "database.db") -> None:
    """
    Initializes the database and creates the necessary tables if they don't exist.
    """
    async with aiosqlite.connect(db_path) as db:
        # Create users table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                join_date TEXT NOT NULL
            )
        """)

        # Create subscriptions table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                plan_name TEXT NOT NULL,
                end_date TEXT NOT NULL,
                FOREIGN KEY (telegram_id) REFERENCES users (telegram_id)
            )
        """)

        # Create payments table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                date TEXT NOT NULL,
                FOREIGN KEY (telegram_id) REFERENCES users (telegram_id)
            )
        """)
        await db.commit()
    print(f"Database initialized at {db_path}")


async def add_user(db_path: str, telegram_id: int) -> None:
    """
    Adds a new user to the database.
    """
    join_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    async with aiosqlite.connect(db_path) as db:
        try:
            await db.execute(
                "INSERT INTO users (telegram_id, join_date) VALUES (?, ?)",
                (telegram_id, join_date),
            )
            await db.commit()
            print(f"User {telegram_id} added.")
        except aiosqlite.IntegrityError:
            print(f"User {telegram_id} already exists.")


async def add_payment(db_path: str, telegram_id: int, amount: float) -> None:
    """
    Records a new payment.
    """
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "INSERT INTO payments (telegram_id, amount, date) VALUES (?, ?, ?)",
            (telegram_id, amount, date),
        )
        await db.commit()
        print(f"Payment of {amount} recorded for user {telegram_id}.")


async def add_subscription(db_path: str, telegram_id: int, plan_name: str, end_date: str) -> None:
    """
    Adds or updates a subscription record in the database.
    """
    async with aiosqlite.connect(db_path) as db:
        # Check if user already has this specific plan to update it, otherwise insert new
        async with db.execute(
            "SELECT id FROM subscriptions WHERE telegram_id = ? AND plan_name = ?", 
            (telegram_id, plan_name)
        ) as cursor:
            row = await cursor.fetchone()

        if row:
            await db.execute(
                "UPDATE subscriptions SET end_date = ? WHERE id = ?",
                (end_date, row[0])
            )
        else:
            await db.execute(
                "INSERT INTO subscriptions (telegram_id, plan_name, end_date) VALUES (?, ?, ?)",
                (telegram_id, plan_name, end_date)
            )
        
        await db.commit()
        print(f"Subscription '{plan_name}' for {telegram_id} set until {end_date}.")


async def get_statistics(db_path: str) -> tuple[int, float]:
    """
    Returns the total number of users and the total revenue from payments.
    """
    async with aiosqlite.connect(db_path) as db:
        # Get user count
        async with db.execute("SELECT COUNT(*) FROM users") as cursor:
            user_count = (await cursor.fetchone())[0]

        # Get total revenue
        async with db.execute("SELECT COALESCE(SUM(amount), 0) FROM payments") as cursor:
            total_revenue = (await cursor.fetchone())[0]

        return user_count, float(total_revenue)


async def get_all_users(db_path: str) -> list[int]:
    """
    Returns a list of all telegram_id from the users table.
    """
    async with aiosqlite.connect(db_path) as db:
        async with db.execute("SELECT telegram_id FROM users") as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]


if __name__ == "__main__":
    import asyncio

    async def main():
        db_name = "test_bot.db"
        # Initialize
        await init_db(db_name)

        # Test adding user
        await add_user(db_name, 123456789)

        # Test adding payment
        await add_payment(db_name, 123456789, 500.0)

        # Test issuing subscription (e.g., "Premium" for 30 days)
        await add_subscription(db_name, 123456789, "Premium", 30)

    asyncio.run(main())