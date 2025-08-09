# database.py
import sqlite3
import datetime
import os

# On Replit, we save the database file directly in our project folder.
DB_PATH = "contribution_points.db"


def initialize_database():
    """Initializes the database and creates the tables if they don't exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # This table stores every single point transaction.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS points_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            guild_id INTEGER NOT NULL,
            points INTEGER NOT NULL,
            reason TEXT,
            timestamp DATETIME NOT NULL
        )
    """)

    # --- NEW TABLE ---
    # This table logs when an Elder uses their one-time Protégé ability.
    # The elder_id is UNIQUE to ensure it can only be done once.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS protege_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            elder_id INTEGER NOT NULL UNIQUE,
            protege_id INTEGER NOT NULL,
            guild_id INTEGER NOT NULL,
            timestamp DATETIME NOT NULL
        )
    """)

    conn.commit()
    conn.close()
    print("Database initialized successfully.")


def add_points(user_id: int, guild_id: int, points: int, reason: str):
    """Adds a new point transaction for a user."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    timestamp = datetime.datetime.utcnow()

    cursor.execute(
        """
        INSERT INTO points_log (user_id, guild_id, points, reason, timestamp)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, guild_id, points, reason, timestamp))

    conn.commit()
    conn.close()


def get_leaderboard(guild_id: int, time_delta: datetime.timedelta = None):
    """
    Fetches the leaderboard data.
    - Aggregates points for each user.
    - Can be filtered by a time_delta (e.g., last 7 days).
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    query = """
        SELECT user_id, SUM(points) as total_points
        FROM points_log
        WHERE guild_id = ?
    """
    params = [guild_id]

    if time_delta:
        start_date = datetime.datetime.utcnow() - time_delta
        query += " AND timestamp >= ?"
        params.append(start_date)

    query += """
        GROUP BY user_id
        ORDER BY total_points DESC
        LIMIT 20
    """

    cursor.execute(query, tuple(params))
    leaderboard_data = cursor.fetchall()

    conn.close()
    return leaderboard_data


def get_user_points(user_id: int, guild_id: int):
    """Fetches the total points for a single user."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT SUM(points)
        FROM points_log
        WHERE user_id = ? AND guild_id = ?
    """, (user_id, guild_id))

    # fetchone() will return a tuple like (500,) or (None,) if no records exist
    result = cursor.fetchone()

    conn.close()

    # If the result is None or the first item is None, the user has 0 points.
    if result is None or result[0] is None:
        return 0
    else:
        return result[0]

# --- NEW FUNCTIONS ---

def log_protege(elder_id: int, protege_id: int, guild_id: int):
    """Logs the proclamation of a protégé by an elder."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    timestamp = datetime.datetime.utcnow()
    cursor.execute(
        """
        INSERT INTO protege_log (elder_id, protege_id, guild_id, timestamp)
        VALUES (?, ?, ?, ?)
    """, (elder_id, protege_id, guild_id, timestamp))
    conn.commit()
    conn.close()

def has_proclaimed_protege(elder_id: int, guild_id: int) -> bool:
    """Checks if an elder has already proclaimed a protégé."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT 1 FROM protege_log WHERE elder_id = ? AND guild_id = ?
        """, (elder_id, guild_id)
    )
    result = cursor.fetchone()
    conn.close()
    return result is not None