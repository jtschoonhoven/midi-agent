"""Migration script to replace repeat column with extend_measures in midi_loops table."""

import sqlite3
from pathlib import Path


def migrate():
    """Replace repeat column with extend_measures column in midi_loops table."""
    # Get path to database
    db_path = Path(__file__).parent.parent.parent / "midi_agent.db"

    if not db_path.exists():
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if extend_measures column already exists
        cursor.execute("PRAGMA table_info(midi_loops)")
        columns = [row[1] for row in cursor.fetchall()]

        if "extend_measures" in columns and "repeat" not in columns:
            print("extend_measures column already exists and repeat is removed. No migration needed.")
            return

        if "extend_measures" in columns:
            print("extend_measures column already exists but repeat still present. Cleaning up...")
            # Just drop repeat column
            cursor.execute("""
                CREATE TABLE midi_loops_new (
                    id VARCHAR(36) PRIMARY KEY,
                    offset INTEGER NOT NULL DEFAULT 0,
                    measures INTEGER NOT NULL,
                    extend_measures INTEGER NOT NULL DEFAULT 0,
                    midi_events JSON NOT NULL,
                    track_id VARCHAR(36) NOT NULL,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL,
                    FOREIGN KEY (track_id) REFERENCES midi_tracks(id)
                )
            """)
            cursor.execute("""
                INSERT INTO midi_loops_new
                (id, offset, measures, extend_measures, midi_events, track_id, created_at, updated_at)
                SELECT id, offset, measures, extend_measures, midi_events, track_id, created_at, updated_at
                FROM midi_loops
            """)
            cursor.execute("DROP TABLE midi_loops")
            cursor.execute("ALTER TABLE midi_loops_new RENAME TO midi_loops")
            conn.commit()
            print("✓ Cleanup successful: repeat column removed")
            return

        print("Migrating repeat column to extend_measures...")

        # Create new table with extend_measures column
        cursor.execute("""
            CREATE TABLE midi_loops_new (
                id VARCHAR(36) PRIMARY KEY,
                offset INTEGER NOT NULL DEFAULT 0,
                measures INTEGER NOT NULL,
                extend_measures INTEGER NOT NULL DEFAULT 0,
                midi_events JSON NOT NULL,
                track_id VARCHAR(36) NOT NULL,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                FOREIGN KEY (track_id) REFERENCES midi_tracks(id)
            )
        """)

        # Copy data, converting repeat to extend_measures
        # extend_measures = measures * (repeat - 1)
        cursor.execute("""
            INSERT INTO midi_loops_new
            (id, offset, measures, extend_measures, midi_events, track_id, created_at, updated_at)
            SELECT
                id,
                offset,
                measures,
                measures * (repeat - 1) as extend_measures,
                midi_events,
                track_id,
                created_at,
                updated_at
            FROM midi_loops
        """)

        # Drop old table and rename new one
        cursor.execute("DROP TABLE midi_loops")
        cursor.execute("ALTER TABLE midi_loops_new RENAME TO midi_loops")

        # Recreate indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_midi_loops_track_id ON midi_loops(track_id)")

        conn.commit()
        print("✓ Migration successful: repeat column replaced with extend_measures")

    except Exception as e:
        conn.rollback()
        print(f"✗ Migration failed: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
