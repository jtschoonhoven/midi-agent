"""FastAPI routes for MIDI generation."""

import random
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.auth import get_current_user_id
from api.database import get_db
from api.songs import song_models, song_schemas
from api.songs.song_constants import ADJECTIVES, NOUNS
from api.tracks import track_models

router = APIRouter(prefix="/api/midi", tags=["midi"])


# @router.post("/generate", response_model=MidiResponse)
# async def generate_midi(
#     request: GenerateRequest,
#     db: Session = Depends(get_db),
#     user_id: UUID = Depends(get_current_user_id),
# ) -> MidiResponse:
#     """
#     Generate MIDI events from a natural language prompt.

#     Args:
#         request: Generation request with thread_id, constraints, and prompt
#         db: Database session
#         user_id: User ID from Authorization header

#     Returns:
#         MidiResponse with plan and list of MIDI events

#     Raises:
#         HTTPException: If generation fails
#     """
#     try:
#         # Store user message
#         store_user_message(
#             db=db,
#             user_id=user_id,
#             thread_id=request.thread_id,
#             prompt=request.prompt,
#             plan_model=request.plan_model,
#             generate_model=request.generate_model,
#             key=request.key,
#             bpm=request.bpm,
#             time_signature=request.time_signature,
#             measures=request.measures,
#         )

#         # Generate MIDI
#         plan, midi_events = run_generation_pipeline(request)
#         response = MidiResponse(plan=plan, midi=midi_events)

#         # Store assistant response
#         store_assistant_message(
#             db=db,
#             user_id=user_id,
#             thread_id=request.thread_id,
#             content=plan.reasoning,
#             plan_data={
#                 "key": plan.key,
#                 "bpm": plan.bpm,
#                 "time_signature": plan.time_signature,
#                 "measures": plan.measures,
#                 "style": plan.style,
#                 "chord_progression": plan.chord_progression,
#                 "reasoning": plan.reasoning,
#             },
#             midi_events=[
#                 {
#                     "measure": event.measure,
#                     "beat": event.beat,
#                     "beat_div4": event.beat_div4,
#                     "beat_div16": event.beat_div16,
#                     "event": event.event,
#                     "value": event.value,
#                 }
#                 for event in midi_events
#             ],
#         )

#         return response
#     except ValueError as e:
#         raise HTTPException(status_code=400, detail=str(e))
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"MIDI generation failed: {str(e)}")


# @router.post("/restore", response_model=ConversationRestoreResponse)
# async def restore_conversation(
#     request: ConversationRestoreRequest,
#     db: Session = Depends(get_db),
#     user_id: UUID = Depends(get_current_user_id),
# ) -> ConversationRestoreResponse:
#     """
#     Restore a previous conversation by thread_id.

#     Args:
#         request: Restore request with thread_id
#         db: Database session
#         user_id: User ID from Authorization header

#     Returns:
#         ConversationRestoreResponse with full conversation history

#     Raises:
#         HTTPException: If conversation not found or retrieval fails
#     """
#     try:
#         # Retrieve conversation history
#         messages = get_conversation_history(db, user_id, request.thread_id)

#         # Return 404 if no conversation found
#         if not messages:
#             raise HTTPException(status_code=404, detail="Conversation not found")

#         # Convert to response format
#         conversation_messages = [
#             ConversationMessageResponse(
#                 role=msg.role,
#                 content=msg.content,
#                 plan_model=msg.plan_model,
#                 generate_model=msg.generate_model,
#                 key=msg.key,
#                 bpm=msg.bpm,
#                 time_signature=msg.time_signature,
#                 measures=msg.measures,
#                 plan_data=msg.plan_data,
#                 midi_events=msg.midi_events,
#                 created_at=msg.created_at.isoformat(),
#             )
#             for msg in messages
#         ]

#         return ConversationRestoreResponse(
#             user_id=user_id,
#             thread_id=request.thread_id,
#             messages=conversation_messages,
#             message_count=len(conversation_messages),
#         )
#     except HTTPException:
#         raise
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Conversation restoration failed: {str(e)}")


@router.post("/songs/", response_model=song_schemas.SongDetailResponse)
async def create_song(
    request: song_schemas.CreateSongRequest,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
) -> song_schemas.SongDetailResponse:
    """
    Create a new song with three default tracks (piano, bass, drums)."""
    try:
        # Auto-generate title if not provided
        title = request.title
        if not title:
            adjective = random.choice(ADJECTIVES)
            noun = random.choice(NOUNS)
            title = f"{adjective} {noun}"

        # Create the song
        song = song_models.MidiSong(
            user_id=str(user_id),
            title=title,
            bpm=request.bpm,
            key=request.key,
        )
        db.add(song)
        db.flush()  # Flush to get the song ID without committing

        # Create three default tracks: piano, bass, drums
        tracks_config = [
            {"title": "Piano", "midi_channel": 1, "instrument": "piano", "color": "primary"},
            {"title": "Bass", "midi_channel": 2, "instrument": "bass", "color": "secondary"},
            {"title": "Drums", "midi_channel": 10, "instrument": "drum", "color": "warning"},
        ]

        for config in tracks_config:
            track = track_models.MidiTrack(
                song_id=song.id,
                title=config["title"],
                midi_channel=config["midi_channel"],
                instrument=config["instrument"],
                color=config["color"],
            )
            db.add(track)

        db.commit()
        db.refresh(song)

        return song.to_detail_response()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create song: {str(e)}") from e


@router.get("/songs/", response_model=list[song_schemas.SongResponse])
async def list_songs(
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
) -> list[song_schemas.SongResponse]:
    """
    List all songs for the current user.

    Args:
        db: Database session
        user_id: User ID from Authorization header

    Returns:
        List of SongResponse objects

    Raises:
        HTTPException: If retrieval fails
    """
    try:
        songs = (
            db.query(song_models.MidiSong)
            .filter(song_models.MidiSong.user_id == str(user_id))
            .order_by(song_models.MidiSong.created_at.desc())
            .all()
        )

        return [song.to_response() for song in songs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve songs: {str(e)}") from e


@router.get("/songs/{song_id}", response_model=song_schemas.SongDetailResponse)
async def get_song(
    song_id: str,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
) -> song_schemas.SongDetailResponse:
    """
    Get a specific song with all track details and loops.

    Args:
        song_id: Song identifier (path parameter)
        db: Database session
        user_id: User ID from Authorization header

    Returns:
        SongDetailResponse with tracks and loops

    Raises:
        HTTPException: If song not found or access denied
    """
    try:
        song = (
            db.query(song_models.MidiSong)
            .filter(song_models.MidiSong.id == song_id, song_models.MidiSong.user_id == str(user_id))
            .first()
        )

        if not song:
            raise HTTPException(status_code=404, detail="Song not found or access denied")

        return song.to_detail_response()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve song: {str(e)}") from e
