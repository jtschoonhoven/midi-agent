"""Migration script to add color column to midi_tracks table."""

import sqlite3
from pathlib import Path

from api.tracks.track_constants import DEFAULT_TRACK_COLOR


def migrate():
    """Add color column to midi_tracks table with default value."""
    # Get path to database
    db_path = Path(__file__).parent.parent.parent / "midi_agent.db"

    if not db_path.exists():
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if column already exists
        cursor.execute("PRAGMA table_info(midi_tracks)")
        columns = [row[1] for row in cursor.fetchall()]

        if "color" in columns:
            print("Color column already exists. No migration needed.")
            return

        # Add color column with default value
        print("Adding color column to midi_tracks table...")
        cursor.execute(f"""
            ALTER TABLE midi_tracks
            ADD COLUMN color VARCHAR(50) NOT NULL DEFAULT '{DEFAULT_TRACK_COLOR}'
        """)

        conn.commit()
        print("✓ Migration successful: color column added")

    except Exception as e:
        conn.rollback()
        print(f"✗ Migration failed: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
