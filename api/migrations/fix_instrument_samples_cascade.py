"""Migration script to add CASCADE to instrument_samples foreign key constraint."""

import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from psycopg2 import sql

# Load environment variables from .env file
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)


def migrate():
    """Add CASCADE to instrument_samples foreign key constraint."""
    # Get database URL from environment
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL environment variable not set")
        return

    conn = psycopg2.connect(database_url)
    cursor = conn.cursor()

    try:
        # First, find the existing constraint name
        cursor.execute("""
            SELECT con.conname
            FROM pg_constraint con
            INNER JOIN pg_class rel ON rel.oid = con.conrelid
            WHERE rel.relname = 'instrument_samples'
            AND con.contype = 'f'
            AND con.confrelid = (SELECT oid FROM pg_class WHERE relname = 'instruments');
        """)

        result = cursor.fetchone()
        if not result:
            print("Foreign key constraint not found. It may have already been migrated.")
            return

        constraint_name = result[0]
        print(f"Found existing constraint: {constraint_name}")

        # Drop the existing foreign key constraint
        print("Dropping existing foreign key constraint...")
        cursor.execute(
            sql.SQL("""
            ALTER TABLE instrument_samples
            DROP CONSTRAINT {}
        """).format(sql.Identifier(constraint_name))
        )

        # Add the new foreign key constraint with CASCADE
        print("Adding new foreign key constraint with CASCADE...")
        cursor.execute("""
            ALTER TABLE instrument_samples
            ADD CONSTRAINT instrument_samples_instrument_id_fkey
            FOREIGN KEY (instrument_id)
            REFERENCES instruments(id)
            ON DELETE CASCADE
            ON UPDATE CASCADE
        """)

        conn.commit()
        print("✓ Migration successful: foreign key constraint updated with CASCADE")

    except Exception as e:
        conn.rollback()
        print(f"✗ Migration failed: {e}")
        raise
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    migrate()
