"""Constants for track colors and configuration."""

from api.tracks.track_types import TrackColor

# Track color palette inspired by modern DAWs
# Using semantic color names that can be themed for light/dark mode
TRACK_COLORS: list[TrackColor] = [
    "error",  # Red/Pink
    "warning",  # Orange
    "success",  # Green
    "info",  # Cyan/Blue
    "primary",  # Blue
    "secondary",  # Purple
]

DEFAULT_TRACK_COLOR: TrackColor = "primary"
