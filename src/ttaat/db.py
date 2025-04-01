import os
import sqlite3
from pathlib import Path
import platformdirs
from .version import TTAAT_DB_VERSION


def ensure_db_path():
    """Ensure the database directory exists and return the database file path."""
    app_dir = platformdirs.user_data_dir("ttaat")
    os.makedirs(app_dir, exist_ok=True)
    return os.path.join(app_dir, "ttaat.db")


def dbconnect():
    """Open a connection to the SQLite database in WAL mode."""
    db_path = ensure_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def initialize_db():
    """Initialize the database with the schema if it doesn't exist yet."""
    conn = dbconnect()
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ttaat_db_version'")
    if not cursor.fetchone():
        cursor.execute("CREATE TABLE ttaat_db_version (version INTEGER NOT NULL)")
        cursor.execute("INSERT INTO ttaat_db_version (version) VALUES (?)", (TTAAT_DB_VERSION,))
        
        create_schema_v0(cursor)
        
        conn.commit()
    else:
        cursor.execute("SELECT version FROM ttaat_db_version")
        db_version = cursor.fetchone()[0]
        
        if db_version < TTAAT_DB_VERSION:
            migrate_db(conn, db_version)
    
    conn.close()


def create_schema_v0(cursor):
    """Create the initial database schema (version 0)."""
    cursor.execute('''
    CREATE TABLE rounds (
       id INTEGER PRIMARY KEY AUTOINCREMENT,
       category TEXT NOT NULL,
       question TEXT NOT NULL,
       trivia_1 TEXT NOT NULL,
       trivia_2 TEXT NOT NULL,
       trivia_3 TEXT NOT NULL,
       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    cursor.execute('''
    CREATE TABLE guesses (
       id INTEGER PRIMARY KEY AUTOINCREMENT,
       round_id INTEGER NOT NULL,
       guess_index INTEGER NOT NULL,
       submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
       FOREIGN KEY (round_id) REFERENCES rounds(id)
    )
    ''')

    cursor.execute('''
    CREATE TABLE twists (
       id INTEGER PRIMARY KEY AUTOINCREMENT,
       round_id INTEGER NOT NULL,
       twist_index INTEGER NOT NULL,
       explanation_1 TEXT NOT NULL,
       explanation_2 TEXT NOT NULL,
       explanation_3 TEXT NOT NULL,
       revealed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
       FOREIGN KEY (round_id) REFERENCES rounds(id)
    )
    ''')


def migrate_db(conn, current_version):
    """Migrate the database to the current version."""
    cursor = conn.cursor()
    
    # if current_version < 1:
    #     migrate_to_v1(cursor)
    #     current_version = 1
    
    cursor.execute("UPDATE ttaat_db_version SET version = ?", (TTAAT_DB_VERSION,))
    conn.commit()


def get_score():
    """Get the current score (player vs. game master)."""
    conn = dbconnect()
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT COUNT(*) FROM guesses 
    JOIN twists ON guesses.round_id = twists.round_id 
    WHERE guesses.guess_index = twists.twist_index
    ''')
    player_score = cursor.fetchone()[0]
    
    cursor.execute('''
    SELECT COUNT(*) FROM guesses 
    JOIN twists ON guesses.round_id = twists.round_id 
    WHERE guesses.guess_index != twists.twist_index
    ''')
    gm_score = cursor.fetchone()[0]
    
    conn.close()
    return player_score, gm_score


def get_total_rounds():
    """Get the total number of completed rounds."""
    conn = dbconnect()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM rounds")
    total_rounds = cursor.fetchone()[0]
    
    conn.close()
    return total_rounds


def create_round(category, question, trivia_1, trivia_2, trivia_3):
    """Create a new round with the given details."""
    conn = dbconnect()
    cursor = conn.cursor()
    
    cursor.execute('''
    INSERT INTO rounds (category, question, trivia_1, trivia_2, trivia_3)
    VALUES (?, ?, ?, ?, ?)
    ''', (category, question, trivia_1, trivia_2, trivia_3))
    
    round_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return round_id


def submit_guess(round_id, guess_index):
    """Submit a player's guess for a round."""
    conn = dbconnect()
    cursor = conn.cursor()
    
    cursor.execute('''
    INSERT INTO guesses (round_id, guess_index)
    VALUES (?, ?)
    ''', (round_id, guess_index))
    
    conn.commit()
    conn.close()


def reveal_twist(round_id, twist_index, explanation_1, explanation_2, explanation_3):
    """Reveal the twist for a round with explanations."""
    conn = dbconnect()
    cursor = conn.cursor()
    
    cursor.execute('''
    INSERT INTO twists (round_id, twist_index, explanation_1, explanation_2, explanation_3)
    VALUES (?, ?, ?, ?, ?)
    ''', (round_id, twist_index, explanation_1, explanation_2, explanation_3))
    
    conn.commit()
    conn.close()


def get_last_round():
    """Get the details of the last round."""
    conn = dbconnect()
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT * FROM rounds ORDER BY id DESC LIMIT 1
    ''')
    round_data = cursor.fetchone()
    
    conn.close()
    return dict(round_data) if round_data else None


def get_round(round_id):
    """Get the details of a specific round."""
    conn = dbconnect()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM rounds WHERE id = ?', (round_id,))
    round_data = cursor.fetchone()
    
    conn.close()
    return dict(round_data) if round_data else None