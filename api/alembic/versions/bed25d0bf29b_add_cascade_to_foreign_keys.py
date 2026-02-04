"""add_cascade_to_foreign_keys

Revision ID: bed25d0bf29b
Revises: d1e8089d8f36
Create Date: 2026-02-04

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "bed25d0bf29b"
down_revision: str | Sequence[str] | None = "d1e8089d8f36"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add CASCADE to foreign key constraints."""
    # midi_tracks.song_id -> midi_songs.id
    op.drop_constraint("midi_tracks_song_id_fkey", "midi_tracks", type_="foreignkey")
    op.create_foreign_key(
        "midi_tracks_song_id_fkey",
        "midi_tracks",
        "midi_songs",
        ["song_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # midi_loops.track_id -> midi_tracks.id
    op.drop_constraint("midi_loops_track_id_fkey", "midi_loops", type_="foreignkey")
    op.create_foreign_key(
        "midi_loops_track_id_fkey",
        "midi_loops",
        "midi_tracks",
        ["track_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # chat_messages.loop_id -> midi_loops.id
    op.drop_constraint("chat_messages_loop_id_fkey", "chat_messages", type_="foreignkey")
    op.create_foreign_key(
        "chat_messages_loop_id_fkey",
        "chat_messages",
        "midi_loops",
        ["loop_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    """Remove CASCADE from foreign key constraints."""
    # chat_messages.loop_id -> midi_loops.id
    op.drop_constraint("chat_messages_loop_id_fkey", "chat_messages", type_="foreignkey")
    op.create_foreign_key(
        "chat_messages_loop_id_fkey",
        "chat_messages",
        "midi_loops",
        ["loop_id"],
        ["id"],
    )

    # midi_loops.track_id -> midi_tracks.id
    op.drop_constraint("midi_loops_track_id_fkey", "midi_loops", type_="foreignkey")
    op.create_foreign_key(
        "midi_loops_track_id_fkey",
        "midi_loops",
        "midi_tracks",
        ["track_id"],
        ["id"],
    )

    # midi_tracks.song_id -> midi_songs.id
    op.drop_constraint("midi_tracks_song_id_fkey", "midi_tracks", type_="foreignkey")
    op.create_foreign_key(
        "midi_tracks_song_id_fkey",
        "midi_tracks",
        "midi_songs",
        ["song_id"],
        ["id"],
    )
