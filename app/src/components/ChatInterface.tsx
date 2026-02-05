import { useState, useEffect, useRef } from "react";
import {
  Box,
  Card,
  CardContent,
  AppBar,
  Toolbar,
  Typography,
  IconButton,
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  Divider,
  Modal,
  Button,
  CircularProgress,
  Stack,
  TextField,
  Tabs,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  ToggleButtonGroup,
  ToggleButton,
  useMediaQuery,
  Alert,
  Link,
} from "@mui/material";
import MenuIcon from "@mui/icons-material/Menu";
import CloseIcon from "@mui/icons-material/Close";
import AddIcon from "@mui/icons-material/Add";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import PauseIcon from "@mui/icons-material/Pause";
import SkipPreviousIcon from "@mui/icons-material/SkipPrevious";
import Brightness7Icon from "@mui/icons-material/Brightness7";
import Brightness4Icon from "@mui/icons-material/Brightness4";
import {
  listSongs,
  createSong,
  getSong,
  createLoop,
  appendLoopChat,
  getLoop,
  deleteLoop,
  updateLoop,
  createTrack,
  deleteTrack,
  updateTrack,
} from "../lib/api";
import { hasStoredApiKey, clearApiKey } from "../lib/auth";
import { useDrag, useDrop } from "react-dnd";
import { usePlayback } from "../contexts/PlaybackContext";
import { useThemeMode } from "../contexts/ThemeContext";
import type { components } from "../types/api";
import openApiSchema from "../types/openapi.json";

type Song = components["schemas"]["SongResponse"];
type SongDetail = components["schemas"]["SongDetailResponse"];
type Track = components["schemas"]["TrackResponse"];
type TrackDetail = components["schemas"]["TrackDetailResponse"];
type Loop = components["schemas"]["LoopResponse"];
type LoopDetail = components["schemas"]["LoopDetailResponse"];

// Drag and drop type
const ITEM_TYPE = "LOOP";

interface DragItem {
  type: string;
  loopId: string;
  trackId: string;
  currentOffset: number;
  measures: number;
  dragGrabOffset?: number; // Which measure within the loop was grabbed (0 = first measure)
}
type ChatMessage = components["schemas"]["ChatMessageResponse"];
type CreateSongRequest = components["schemas"]["CreateSongRequest"];

// Extract key enum values from OpenAPI schema
const SONG_KEYS = (openApiSchema as any).components.schemas.CreateSongRequest.properties.key
  .enum as CreateSongRequest["key"][];

interface ChatInterfaceProps {
  onRequestAuth?: () => void;
}

export default function ChatInterface({ onRequestAuth }: ChatInterfaceProps) {
  const {
    isPlaying,
    bpm,
    currentBeat,
    togglePlayPause,
    stop,
    playFromBeat,
    setBpm: setPlaybackBpm,
    loadSong,
    midiOutputs,
    selectedMidiOutput,
    setLoopZone,
    setSelectedMidiOutput,
    requestMidiAccess,
    hasMidiAccess,
  } = usePlayback();
  const { themeMode, setThemeMode } = useThemeMode();
  const prefersDarkMode = useMediaQuery("(prefers-color-scheme: dark)");

  // Determine the actual active theme (user selection or system default)
  const activeTheme = themeMode === null ? (prefersDarkMode ? "dark" : "light") : themeMode;

  // Check if user is in demo mode (not authenticated)
  const isDemo = !hasStoredApiKey();

  const [drawerOpen, setDrawerOpen] = useState(false);
  const [songs, setSongs] = useState<Song[]>([]);
  const [isLoadingSongs, setIsLoadingSongs] = useState(true);
  const [showNewSongModal, setShowNewSongModal] = useState(false);
  const [isCreatingSong, setIsCreatingSong] = useState(false);
  const [newSongKey, setNewSongKey] = useState<CreateSongRequest["key"]>("C");
  const [newSongTimeSignature, setNewSongTimeSignature] = useState<CreateSongRequest["time_signature"]>("4/4");
  const [newSongBpm, setNewSongBpm] = useState(120);

  // Selected song state
  const [selectedSongId, setSelectedSongId] = useState<string | null>(null);
  const [songDetail, setSongDetail] = useState<SongDetail | null>(null);
  const [isLoadingSongDetail, setIsLoadingSongDetail] = useState(false);

  // Loop modal state (for both create and edit)
  const [showLoopModal, setShowLoopModal] = useState(false);
  const [loopModalMode, setLoopModalMode] = useState<"create" | "edit">("create");
  const [selectedTrackId, setSelectedTrackId] = useState<string | null>(null);
  const [selectedLoop, setSelectedLoop] = useState<LoopDetail | null>(null);
  const [loopMeasures, setLoopMeasures] = useState<number>(4);
  const [loopOffset, setLoopOffset] = useState<number>(0);
  const [loopPrompt, setLoopPrompt] = useState<string>("");
  const [isCreatingLoop, setIsCreatingLoop] = useState(false);
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const [isLoadingChat, setIsLoadingChat] = useState(false);
  const [activeTab, setActiveTab] = useState<number>(0);
  const [isDeletingLoop, setIsDeletingLoop] = useState(false);
  const [isCreatingTrack, setIsCreatingTrack] = useState(false);

  // Track modal state
  const [showTrackModal, setShowTrackModal] = useState(false);
  const [selectedTrack, setSelectedTrack] = useState<Track | null>(null);
  const [isDeletingTrack, setIsDeletingTrack] = useState(false);
  const [editedTrackTitle, setEditedTrackTitle] = useState("");

  // Refs
  const loopPromptInputRef = useRef<HTMLInputElement>(null);
  const [editedTrackChannel, setEditedTrackChannel] = useState(1);
  const [editedTrackInstrument, setEditedTrackInstrument] = useState<"piano" | "bass" | "drum">("piano");
  const [isUpdatingTrack, setIsUpdatingTrack] = useState(false);

  // Track loops that are currently generating MIDI
  const [generatingLoops, setGeneratingLoops] = useState<Set<string>>(new Set());

  // Track drag-to-create loop state
  const [isDraggingNewLoop, setIsDraggingNewLoop] = useState(false);
  const [dragStartMeasure, setDragStartMeasure] = useState<number | null>(null);
  const [dragCurrentMeasure, setDragCurrentMeasure] = useState<number | null>(null);
  const [dragTrackId, setDragTrackId] = useState<string | null>(null);

  // Playback loop zone state (for ruler bar loop selection)
  const [loopZoneStart, setLoopZoneStart] = useState<number | null>(null);
  const [loopZoneEnd, setLoopZoneEnd] = useState<number | null>(null);
  const [isDraggingLoopZone, setIsDraggingLoopZone] = useState(false);

  // Track loop resize state
  const [isResizingLoop, setIsResizingLoop] = useState(false);
  const [resizingLoopId, setResizingLoopId] = useState<string | null>(null);
  const [resizeStartExtendMeasures, setResizeStartExtendMeasures] = useState<number>(0);
  const [resizeCurrentExtendMeasures, setResizeCurrentExtendMeasures] = useState<number>(0);

  const toggleDrawer = (open: boolean) => () => {
    setDrawerOpen(open);
  };

  // Load songs on mount
  useEffect(() => {
    const loadSongs = async () => {
      try {
        setIsLoadingSongs(true);
        const result = await listSongs();

        if (result.data) {
          setSongs(result.data);
          // Show modal if no songs exist
          if (result.data.length === 0) {
            setShowNewSongModal(true);
          } else {
            // Auto-select most recent song (by updated_at)
            const sortedSongs = [...result.data].sort(
              (a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
            );
            setSelectedSongId(sortedSongs[0].id);
          }
        } else {
          // Handle error or empty list
          console.error("Failed to load songs:", result.error);
          setShowNewSongModal(true);
        }
      } catch (error) {
        console.error("Failed to load songs:", error);
        setShowNewSongModal(true);
      } finally {
        setIsLoadingSongs(false);
      }
    };

    loadSongs();
  }, []);

  // Load song details when selected
  useEffect(() => {
    const loadSongDetail = async () => {
      if (!selectedSongId) return;

      try {
        setIsLoadingSongDetail(true);
        const result = await getSong(selectedSongId);

        if (result.data) {
          setSongDetail(result.data);
        } else {
          console.error("Failed to load song details:", result.error);
        }
      } catch (error) {
        console.error("Failed to load song details:", error);
      } finally {
        setIsLoadingSongDetail(false);
      }
    };

    loadSongDetail();
  }, [selectedSongId]);

  // Show create song modal when no song is selected
  useEffect(() => {
    if (!isLoadingSongs && !selectedSongId && !songDetail) {
      setShowNewSongModal(true);
    }
  }, [isLoadingSongs, selectedSongId, songDetail]);

  // Load song data into playback context when song details change
  useEffect(() => {
    if (songDetail && songDetail.tracks) {
      loadSong({
        tracks: songDetail.tracks.map((track) => ({
          id: track.id,
          midi_channel: track.midi_channel,
          instrument: track.instrument,
          loops: (track.loops || []).map((loop) => ({
            id: loop.id,
            offset: loop.offset,
            measures: loop.measures,
            extend_measures: loop.extend_measures,
            midi_events: loop.midi_events as any, // API returns MidiEvent[] but typed as { [key: string]: unknown; }[]
            track_id: loop.track_id,
          })),
        })),
        bpm: songDetail.bpm,
        time_signature: songDetail.time_signature,
      });
    } else {
      loadSong(null);
    }
  }, [songDetail, loadSong]);

  // Global mouse up handler for drag-to-create
  useEffect(() => {
    const handleMouseUp = () => {
      if (isDraggingNewLoop) {
        handleDragCreateEnd();
      }
    };

    window.addEventListener("mouseup", handleMouseUp);
    return () => {
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, [isDraggingNewLoop, dragStartMeasure, dragCurrentMeasure, dragTrackId, songDetail]);

  // Global mouse up handler for loop zone drag
  useEffect(() => {
    const handleMouseUp = () => {
      if (isDraggingLoopZone) {
        handleLoopZoneDragEnd();
      }
    };

    window.addEventListener("mouseup", handleMouseUp);
    return () => {
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, [isDraggingLoopZone, loopZoneStart, loopZoneEnd, songDetail]);

  // Global mouse up handler for loop resize
  useEffect(() => {
    const handleMouseUp = () => {
      if (isResizingLoop) {
        handleLoopResizeEnd();
      }
    };

    window.addEventListener("mouseup", handleMouseUp);
    return () => {
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, [
    isResizingLoop,
    resizingLoopId,
    resizeCurrentExtendMeasures,
    resizeStartExtendMeasures,
    songDetail,
    selectedSongId,
  ]);

  // Global keyboard handler for space bar to toggle playback
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Check if space bar was pressed
      if (e.code === "Space" || e.key === " ") {
        // Check if the target is a text input element
        const target = e.target as HTMLElement;
        const isTextInput = target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable;

        // If not in a text input, toggle playback
        if (!isTextInput) {
          e.preventDefault(); // Prevent page scroll
          togglePlayPause();
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [togglePlayPause]);

  // Focus the prompt input when the loop modal opens or when switching to chat tab
  useEffect(() => {
    if (showLoopModal && loopPromptInputRef.current) {
      // Only focus if we're in create mode or on the chat tab in edit mode
      const shouldFocus = loopModalMode === "create" || (loopModalMode === "edit" && activeTab === 0);

      if (shouldFocus) {
        // Use a small timeout to ensure the modal/tab is fully rendered
        setTimeout(() => {
          loopPromptInputRef.current?.focus();
        }, 150);
      }
    }
  }, [showLoopModal, loopModalMode, activeTab]);

  // Create a new song
  const handleCreateSong = async () => {
    try {
      setIsCreatingSong(true);
      const result = await createSong({
        bpm: newSongBpm,
        key: newSongKey,
        time_signature: newSongTimeSignature,
      });

      if (result.data) {
        // Add the new song to the list
        setSongs([result.data, ...songs]);
        setShowNewSongModal(false);
        // Reset form
        setNewSongKey("C");
        setNewSongTimeSignature("4/4");
        setNewSongBpm(120);
        // Select the new song
        setSelectedSongId(result.data.id);
      } else {
        console.error("Failed to create song:", result.error);
        alert("Failed to create song. Please try again.");
      }
    } catch (error) {
      console.error("Failed to create song:", error);
      alert("Failed to create song. Please try again.");
    } finally {
      setIsCreatingSong(false);
    }
  };

  // Handle closing new song modal
  const handleCloseNewSongModal = () => {
    if (songs.length > 0) {
      setShowNewSongModal(false);
      // Reset form
      setNewSongKey("C");
      setNewSongTimeSignature("4/4");
      setNewSongBpm(120);
    }
  };

  // Handle song selection from sidebar
  const handleSelectSong = (songId: string) => {
    setSelectedSongId(songId);
    setDrawerOpen(false);
  };

  // Handle edit loop
  const handleOpenEditLoopModal = async (loop: Loop) => {
    setLoopModalMode("edit");
    setSelectedTrackId(loop.track_id);
    setLoopMeasures(loop.measures);
    setLoopPrompt("");
    setActiveTab(0); // Reset to chat tab
    setShowLoopModal(true);

    // Load full loop details with chat history
    setIsLoadingChat(true);
    try {
      const result = await getLoop(loop.id);
      if (result.data) {
        setSelectedLoop(result.data);
        setChatHistory(result.data.chats || []);
      } else {
        console.error("Failed to load loop details:", result.error);
        setChatHistory([]);
      }
    } catch (error) {
      console.error("Failed to load loop details:", error);
      setChatHistory([]);
    } finally {
      setIsLoadingChat(false);
    }
  };

  // Poll for loop updates
  const pollLoopUpdates = async (loopId: string) => {
    const maxAttempts = 60; // Poll for up to 60 seconds
    const pollInterval = 1000; // 1 second between polls

    for (let attempt = 0; attempt < maxAttempts; attempt++) {
      await new Promise((resolve) => setTimeout(resolve, pollInterval));

      try {
        const result = await getLoop(loopId);
        if (result.data && result.data.midi_events.length > 0) {
          // Loop has MIDI events now - it's done generating
          setGeneratingLoops((prev) => {
            const next = new Set(prev);
            next.delete(loopId);
            return next;
          });

          // Reload song details
          if (selectedSongId) {
            const songResult = await getSong(selectedSongId);
            if (songResult.data) {
              setSongDetail(songResult.data);
            }
          }
          return;
        }
      } catch (error) {
        console.error("Error polling loop:", error);
      }
    }

    // Timeout - remove from generating set
    setGeneratingLoops((prev) => {
      const next = new Set(prev);
      next.delete(loopId);
      return next;
    });
    console.warn(`Loop ${loopId} generation timed out`);
  };

  // Handle loop creation and chat submission
  const handleSubmitLoop = async () => {
    if (!loopPrompt.trim()) {
      alert("Please enter a prompt");
      return;
    }

    if (loopModalMode === "create") {
      if (!selectedTrackId) {
        alert("No track selected");
        return;
      }

      if (loopMeasures < 1 || loopMeasures > 32) {
        alert("Measures must be between 1 and 32");
        return;
      }

      try {
        setIsCreatingLoop(true);

        // Step 1: Create the loop
        const createResult = await createLoop({
          track_id: selectedTrackId,
          measures: loopMeasures,
          extend_measures: 0,
        });

        if (!createResult.data) {
          console.error("Failed to create loop:", createResult.error);
          alert("Failed to create loop. Please try again.");
          return;
        }

        const newLoop = createResult.data;

        // Step 2: Update loop offset if not 0
        if (loopOffset !== 0) {
          await updateLoop(newLoop.id, { offset: loopOffset });
        }

        // Step 3: Reload song to show the new loop card
        if (songDetail && selectedSongId) {
          const result = await getSong(selectedSongId);
          if (result.data) {
            setSongDetail(result.data);
          }
        }

        // Step 4: Close modal immediately
        setShowLoopModal(false);
        setLoopPrompt("");
        setLoopMeasures(4);
        setLoopOffset(0);
        setIsCreatingLoop(false);

        // Step 4: Mark loop as generating and start chat in background
        setGeneratingLoops((prev) => new Set(prev).add(newLoop.id));

        // Start background generation (don't await)
        (async () => {
          try {
            await appendLoopChat({
              loop_id: newLoop.id,
              msg: loopPrompt,
              measures: loopMeasures,
            });

            // Start polling for updates
            await pollLoopUpdates(newLoop.id);
          } catch (error) {
            console.error("Failed to generate loop:", error);
            setGeneratingLoops((prev) => {
              const next = new Set(prev);
              next.delete(newLoop.id);
              return next;
            });
            alert("Failed to process prompt. Please try editing the loop to try again.");
          }
        })();
      } catch (error) {
        console.error("Failed to create loop:", error);
        alert("Failed to create loop. Please try again.");
        setIsCreatingLoop(false);
      }
    } else {
      // Edit mode - append to existing loop
      if (!selectedLoop) {
        alert("No loop selected");
        return;
      }

      try {
        setIsCreatingLoop(true);

        const loopId = selectedLoop.id;
        const prompt = loopPrompt;
        const measures = selectedLoop.measures;

        // Close modal immediately
        setShowLoopModal(false);
        setLoopPrompt("");
        setIsCreatingLoop(false);

        // Mark loop as generating and start chat in background
        setGeneratingLoops((prev) => new Set(prev).add(loopId));

        // Start background generation (don't await)
        (async () => {
          try {
            const chatResult = await appendLoopChat({
              loop_id: loopId,
              msg: prompt,
              measures: measures,
            });

            if (!chatResult.data) {
              console.error("Failed to append chat:", chatResult.error);
              setGeneratingLoops((prev) => {
                const next = new Set(prev);
                next.delete(loopId);
                return next;
              });
              alert("Failed to process prompt. Please try again.");
              return;
            }

            // Start polling for updates
            await pollLoopUpdates(loopId);
          } catch (error) {
            console.error("Failed to append chat:", error);
            setGeneratingLoops((prev) => {
              const next = new Set(prev);
              next.delete(loopId);
              return next;
            });
            alert("Failed to process prompt. Please try again.");
          }
        })();
      } catch (error) {
        console.error("Failed to append chat:", error);
        alert("Failed to process prompt. Please try again.");
        setIsCreatingLoop(false);
      }
    }
  };

  // Handle loop deletion
  const handleDeleteLoop = async () => {
    if (!selectedLoop) {
      alert("No loop selected");
      return;
    }

    if (!confirm("Are you sure you want to delete this loop? This action cannot be undone.")) {
      return;
    }

    try {
      setIsDeletingLoop(true);

      const result = await deleteLoop(selectedLoop.id);

      if (result.error) {
        console.error("Failed to delete loop:", result.error);
        alert("Failed to delete loop. Please try again.");
        return;
      }

      // Update the local song detail to remove the deleted loop
      if (songDetail && selectedSongId) {
        const result = await getSong(selectedSongId);
        if (result.data) {
          setSongDetail(result.data);
        }
      }

      // Close modal
      setShowLoopModal(false);
    } catch (error) {
      console.error("Failed to delete loop:", error);
      alert("Failed to delete loop. Please try again.");
    } finally {
      setIsDeletingLoop(false);
    }
  };

  // Handle track creation
  const handleCreateTrack = async () => {
    if (!selectedSongId) {
      setShowNewSongModal(true);
      return;
    }

    try {
      setIsCreatingTrack(true);

      // Calculate the next track number based on existing tracks
      const trackNumber = (songDetail?.tracks?.length || 0) + 1;
      const trackTitle = `Track ${trackNumber}`;

      const result = await createTrack({
        song_id: selectedSongId,
        title: trackTitle,
      });

      if (!result.data) {
        console.error("Failed to create track:", result.error);
        alert("Failed to create track. Please try again.");
        return;
      }

      // Reload song details to show the new track
      const songResult = await getSong(selectedSongId);
      if (songResult.data) {
        setSongDetail(songResult.data);
      }
    } catch (error) {
      console.error("Failed to create track:", error);
      alert("Failed to create track. Please try again.");
    } finally {
      setIsCreatingTrack(false);
    }
  };

  // Handle opening track modal
  const handleOpenTrackModal = (track: Track) => {
    setSelectedTrack(track);
    setEditedTrackTitle(track.title);
    setEditedTrackChannel(track.midi_channel);
    setEditedTrackInstrument(track.instrument);
    setShowTrackModal(true);
  };

  // Handle track deletion
  const handleDeleteTrack = async () => {
    if (!selectedTrack) {
      alert("No track selected");
      return;
    }

    if (
      !confirm(
        "Are you sure you want to delete this track? This will also delete all loops in this track. This action cannot be undone."
      )
    ) {
      return;
    }

    try {
      setIsDeletingTrack(true);

      const result = await deleteTrack(selectedTrack.id);

      if (result.error) {
        console.error("Failed to delete track:", result.error);
        alert("Failed to delete track. Please try again.");
        return;
      }

      // Reload song details to reflect the deletion
      if (songDetail && selectedSongId) {
        const songResult = await getSong(selectedSongId);
        if (songResult.data) {
          setSongDetail(songResult.data);
        }
      }

      // Close modal
      setShowTrackModal(false);
    } catch (error) {
      console.error("Failed to delete track:", error);
      alert("Failed to delete track. Please try again.");
    } finally {
      setIsDeletingTrack(false);
    }
  };

  // Handle track update
  const handleUpdateTrack = async () => {
    if (!selectedTrack) {
      alert("No track selected");
      return;
    }

    if (!editedTrackTitle.trim()) {
      alert("Track title cannot be empty");
      return;
    }

    if (editedTrackChannel < 1 || editedTrackChannel > 16) {
      alert("MIDI channel must be between 1 and 16");
      return;
    }

    try {
      setIsUpdatingTrack(true);

      const result = await updateTrack(selectedTrack.id, {
        title: editedTrackTitle,
        midi_channel: editedTrackChannel,
        instrument: editedTrackInstrument,
      });

      if (result.error) {
        console.error("Failed to update track:", result.error);
        alert("Failed to update track. Please try again.");
        return;
      }

      // Reload song details to reflect the update
      if (songDetail && selectedSongId) {
        const songResult = await getSong(selectedSongId);
        if (songResult.data) {
          setSongDetail(songResult.data);
        }
      }

      // Close modal
      setShowTrackModal(false);
    } catch (error) {
      console.error("Failed to update track:", error);
      alert("Failed to update track. Please try again.");
    } finally {
      setIsUpdatingTrack(false);
    }
  };

  // Handle loop drop to update offset
  const handleLoopDrop = async (loopId: string, dropMeasure: number, dragItem: DragItem) => {
    // Don't allow drops in demo mode
    if (isDemo) return;

    try {
      // Calculate the actual new offset based on where the loop was grabbed
      const grabOffset = dragItem.dragGrabOffset || 0;
      const newOffset = dropMeasure - grabOffset;

      // Don't allow negative offsets
      if (newOffset < 0) {
        return;
      }

      // Find the track and loop being dragged
      const track = songDetail?.tracks?.find((t) => t.id === dragItem.trackId);
      if (!track) return;

      const draggedLoop = track.loops?.find((l) => l.id === loopId);
      if (!draggedLoop) return;

      // Check for collisions with other loops (exclude the loop being dragged)
      const loopEnd = newOffset + dragItem.measures;
      const hasCollision = track.loops?.some((otherLoop) => {
        // Skip the loop being dragged
        if (otherLoop.id === loopId) return false;

        const otherStart = otherLoop.offset || 0;
        const otherEnd = otherStart + otherLoop.measures;

        // Check if ranges overlap
        return newOffset < otherEnd && loopEnd > otherStart;
      });

      if (hasCollision) {
        return; // Don't allow drop if it would overlap with another loop
      }

      const result = await updateLoop(loopId, { offset: newOffset });

      if (result.error) {
        console.error("Failed to update loop offset:", result.error);
        alert("Failed to move loop. Please try again.");
        return;
      }

      // Reload song details to reflect the update
      if (songDetail && selectedSongId) {
        const songResult = await getSong(selectedSongId);
        if (songResult.data) {
          setSongDetail(songResult.data);
        }
      }
    } catch (error) {
      console.error("Failed to update loop offset:", error);
      alert("Failed to move loop. Please try again.");
    }
  };

  // Handle drag-to-create loop start
  const handleDragCreateStart = (measureIndex: number, trackId: string, track: TrackDetail) => {
    // Don't allow creating loops in demo mode
    if (isDemo) return;

    // Check if there's already a loop at this position
    const hasLoopAtPosition = track.loops?.some((loop) => {
      const loopStart = loop.offset || 0;
      const loopEnd = loopStart + loop.measures;
      return measureIndex >= loopStart && measureIndex < loopEnd;
    });

    if (hasLoopAtPosition) {
      return; // Don't start drag if there's already a loop here
    }

    setIsDraggingNewLoop(true);
    setDragStartMeasure(measureIndex);
    setDragCurrentMeasure(measureIndex);
    setDragTrackId(trackId);
  };

  // Handle drag-to-create loop update
  const handleDragCreateMove = (measureIndex: number) => {
    if (isDraggingNewLoop && dragStartMeasure !== null) {
      setDragCurrentMeasure(measureIndex);
    }
  };

  // Handle drag-to-create loop end
  const handleDragCreateEnd = () => {
    if (isDraggingNewLoop && dragStartMeasure !== null && dragCurrentMeasure !== null && dragTrackId) {
      // Calculate offset and measures
      const startMeasure = Math.min(dragStartMeasure, dragCurrentMeasure);
      const endMeasure = Math.max(dragStartMeasure, dragCurrentMeasure);
      const measures = endMeasure - startMeasure + 1;

      // Open create loop modal with pre-filled values
      setSelectedTrackId(dragTrackId);
      setLoopOffset(startMeasure);
      setLoopMeasures(measures);
      setLoopModalMode("create");
      setLoopPrompt("");
      setShowLoopModal(true);
    }

    // Reset drag state
    setIsDraggingNewLoop(false);
    setDragStartMeasure(null);
    setDragCurrentMeasure(null);
    setDragTrackId(null);
  };

  // Handle loop zone drag start (in ruler bar)
  const handleLoopZoneDragStart = (measureIndex: number) => {
    // If clicking on an existing loop zone, remove it
    if (loopZoneStart !== null && loopZoneEnd !== null) {
      const minZone = Math.min(loopZoneStart, loopZoneEnd);
      const maxZone = Math.max(loopZoneStart, loopZoneEnd);
      if (measureIndex >= minZone && measureIndex <= maxZone) {
        // Clear the loop zone
        setLoopZoneStart(null);
        setLoopZoneEnd(null);
        setLoopZone(null, null);
        return;
      }
    }

    // Start new loop zone drag
    setIsDraggingLoopZone(true);
    setLoopZoneStart(measureIndex);
    setLoopZoneEnd(measureIndex);
  };

  // Handle loop zone drag move (in ruler bar)
  const handleLoopZoneDragMove = (measureIndex: number) => {
    if (isDraggingLoopZone && loopZoneStart !== null) {
      setLoopZoneEnd(measureIndex);
    }
  };

  // Handle loop zone drag end (in ruler bar)
  const handleLoopZoneDragEnd = () => {
    if (isDraggingLoopZone && loopZoneStart !== null && loopZoneEnd !== null && songDetail) {
      // Calculate start and end in beats
      const beatsPerMeasure = parseInt(songDetail.time_signature.split("/")[0]) || 4;
      const startMeasure = Math.min(loopZoneStart, loopZoneEnd);
      const endMeasure = Math.max(loopZoneStart, loopZoneEnd);

      // Convert to beats (add 1 to end measure to include it in the loop)
      const startBeat = startMeasure * beatsPerMeasure;
      const endBeat = (endMeasure + 1) * beatsPerMeasure;

      // Set loop zone in playback context
      setLoopZone(startBeat, endBeat);

      // Update visual state
      setLoopZoneStart(startMeasure);
      setLoopZoneEnd(endMeasure);
    }

    setIsDraggingLoopZone(false);
  };

  // Handle loop resize start
  const handleLoopResizeStart = (e: React.MouseEvent, loop: Loop, _track: TrackDetail) => {
    // Don't allow resizing loops in demo mode
    if (isDemo) return;

    e.stopPropagation(); // Prevent loop card click
    setIsResizingLoop(true);
    setResizingLoopId(loop.id);
    setResizeStartExtendMeasures(loop.extend_measures);
    setResizeCurrentExtendMeasures(loop.extend_measures);
  };

  // Handle loop resize move
  const handleLoopResizeMove = (measureIndex: number, loop: Loop, track: TrackDetail) => {
    if (!isResizingLoop || resizingLoopId !== loop.id) return;

    const loopStart = loop.offset || 0;
    const originalEndMeasure = loopStart + loop.measures - 1;

    // Calculate new extend_measures based on where the resize is
    const newExtendMeasures = measureIndex - originalEndMeasure;

    // Calculate the new total end position
    const newTotalMeasures = loop.measures + newExtendMeasures;
    const newEndMeasure = loopStart + newTotalMeasures;

    // Allow negative extend_measures to truncate the loop
    // Minimum: keep at least 0.25 measures (1 beat in 4/4) to keep the loop visible
    if (newTotalMeasures < 0.25) return;

    // Check for collisions with other loops
    const hasCollision = track.loops?.some((otherLoop) => {
      if (otherLoop.id === loop.id) return false;

      const otherStart = otherLoop.offset || 0;
      const otherEnd = otherStart + otherLoop.measures + otherLoop.extend_measures;

      // Check if the new range would overlap
      // Only check collision if we're extending (positive direction)
      if (newTotalMeasures > 0) {
        return loopStart < otherEnd && newEndMeasure > otherStart;
      }
      return false;
    });

    // Don't update if there would be a collision
    if (hasCollision) return;

    setResizeCurrentExtendMeasures(newExtendMeasures);
  };

  // Handle loop resize end
  const handleLoopResizeEnd = async () => {
    if (!isResizingLoop || !resizingLoopId) return;

    // Only persist if the value changed
    if (resizeCurrentExtendMeasures !== resizeStartExtendMeasures) {
      try {
        const result = await updateLoop(resizingLoopId, {
          extend_measures: resizeCurrentExtendMeasures,
        });

        if (result.error) {
          console.error("Failed to update loop extend_measures:", result.error);
          alert("Failed to resize loop. Please try again.");
        }

        // Reload song details to reflect the update
        if (songDetail && selectedSongId) {
          const songResult = await getSong(selectedSongId);
          if (songResult.data) {
            setSongDetail(songResult.data);
          }
        }
      } catch (error) {
        console.error("Failed to update loop extend_measures:", error);
        alert("Failed to resize loop. Please try again.");
      }
    }

    // Reset resize state
    setIsResizingLoop(false);
    setResizingLoopId(null);
    setResizeStartExtendMeasures(0);
    setResizeCurrentExtendMeasures(0);
  };

  return (
    <Box sx={{ display: "flex", flexDirection: "column", minHeight: "100vh" }}>
      {/* Left Drawer */}
      <Drawer
        anchor="left"
        open={drawerOpen}
        onClose={toggleDrawer(false)}
        sx={{
          zIndex: (theme) => theme.zIndex.appBar + 1,
        }}
      >
        <Box sx={{ width: 280 }} role="presentation">
          {/* Drawer Title */}
          <Box
            sx={{
              p: 2,
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
            }}
          >
            <Typography variant="h6" component="div">
              Songs
            </Typography>
            <IconButton edge="end" onClick={toggleDrawer(false)} aria-label="close drawer" size="small">
              <CloseIcon />
            </IconButton>
          </Box>
          <Divider />

          {/* Create New Song Button */}
          <Box sx={{ p: 2 }}>
            <Button
              variant="contained"
              fullWidth
              startIcon={<AddIcon />}
              onClick={() => {
                setShowNewSongModal(true);
                setDrawerOpen(false);
              }}
              disabled={isCreatingSong || isDemo}
            >
              New Song
            </Button>
          </Box>
          <Divider />

          {/* Song List */}
          <List>
            {isLoadingSongs ? (
              <Box sx={{ display: "flex", justifyContent: "center", p: 3 }}>
                <CircularProgress size={24} />
              </Box>
            ) : songs.length === 0 ? (
              <Box sx={{ p: 2, textAlign: "center" }}>
                <Typography variant="body2" color="text.secondary">
                  No songs yet
                </Typography>
              </Box>
            ) : (
              [...songs]
                .sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())
                .map((song) => (
                  <ListItem key={song.id} disablePadding>
                    <ListItemButton selected={selectedSongId === song.id} onClick={() => handleSelectSong(song.id)}>
                      <ListItemText primary={song.title} secondary={`${song.key} • ${song.bpm} BPM`} />
                    </ListItemButton>
                  </ListItem>
                ))
            )}
          </List>
        </Box>
      </Drawer>

      {/* Full-width navbar */}
      <AppBar position="static" elevation={1}>
        <Toolbar>
          <IconButton edge="start" color="inherit" aria-label="menu" onClick={toggleDrawer(true)} sx={{ mr: 2 }}>
            <MenuIcon />
          </IconButton>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            {songDetail?.title || "MIDI Agent"}
          </Typography>

          {/* MIDI Output Selector */}
          <FormControl variant="standard" sx={{ minWidth: 200 }}>
            <InputLabel id="midi-output-label" sx={{ color: "inherit" }}>
              MIDI Output
            </InputLabel>
            <Select
              labelId="midi-output-label"
              value={selectedMidiOutput.id}
              onChange={(e) => {
                const outputId = e.target.value;
                if (outputId === "request-midi") {
                  requestMidiAccess();
                } else {
                  const output = midiOutputs.find((o) => o.id === outputId);
                  if (output) {
                    setSelectedMidiOutput(output);
                  }
                }
              }}
              sx={{ color: "inherit", "& .MuiSelect-icon": { color: "inherit" } }}
            >
              {midiOutputs.map((output) => (
                <MenuItem key={output.id} value={output.id}>
                  {output.name}
                </MenuItem>
              ))}
              {!hasMidiAccess && <MenuItem value="request-midi">Allow MIDI Access</MenuItem>}
            </Select>
          </FormControl>

          {/* Theme Toggle */}
          <ToggleButtonGroup
            value={activeTheme}
            exclusive
            onChange={(_, newMode) => {
              if (newMode !== null) {
                setThemeMode(newMode as "light" | "dark");
              }
            }}
            size="small"
            sx={{ ml: 2 }}
          >
            <ToggleButton value="light" aria-label="light theme" sx={{ color: "inherit" }}>
              <Brightness7Icon fontSize="small" />
            </ToggleButton>
            <ToggleButton value="dark" aria-label="dark theme" sx={{ color: "inherit" }}>
              <Brightness4Icon fontSize="small" />
            </ToggleButton>
          </ToggleButtonGroup>

          {/* Sign In button when not authenticated */}
          {!hasStoredApiKey() && onRequestAuth && (
            <Button color="inherit" onClick={onRequestAuth} sx={{ ml: 2 }}>
              Sign In
            </Button>
          )}

          {/* Sign Out button when authenticated */}
          {hasStoredApiKey() && (
            <Button
              color="inherit"
              onClick={() => {
                clearApiKey();
                window.location.reload();
              }}
              sx={{ ml: 2 }}
            >
              Sign Out
            </Button>
          )}
        </Toolbar>
      </AppBar>

      {/* Demo Mode Banner */}
      {isDemo && (
        <Alert
          severity="info"
          sx={{
            borderRadius: 0,
            justifyContent: "center",
          }}
        >
          You are in read-only demo mode.{" "}
          <Link component="button" onClick={onRequestAuth} sx={{ fontWeight: "medium", verticalAlign: "baseline" }}>
            Sign in
          </Link>{" "}
          with your Anthropic API key to create and edit songs.
        </Alert>
      )}

      {/* Main content area */}
      {isLoadingSongDetail ? (
        <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
          <CircularProgress />
        </Box>
      ) : !songDetail ? null : (
        <Box sx={{ display: "flex", flexGrow: 1, minHeight: 0 }}>
          {/* Left fixed column: Track labels with full-height background */}
          <Box
            sx={{
              flexShrink: 0,
              bgcolor: "action.hover",
              pr: 2,
              py: 2,
              display: "flex",
              flexDirection: "column",
              minHeight: "100%",
            }}
          >
            <Stack spacing={2} sx={{ pl: 2, pt: 6 }}>
              {/* Track label cards */}
              {songDetail.tracks?.map((track) => (
                <Card
                  key={track.id}
                  sx={{
                    width: 140,
                    height: 140,
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    borderLeft: 4,
                    borderLeftColor: `${track.color}.main`,
                    "&:hover": {
                      bgcolor: "action.hover",
                      boxShadow: 2,
                    },
                  }}
                  onClick={() => handleOpenTrackModal(track)}
                >
                  <CardContent sx={{ textAlign: "center", p: 2 }}>
                    <Typography variant="h6" gutterBottom>
                      {track.title}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Channel {track.midi_channel}
                    </Typography>
                    <Typography variant="caption" color="text.secondary" sx={{ textTransform: "capitalize" }}>
                      {track.instrument}
                    </Typography>
                  </CardContent>
                </Card>
              ))}

              {/* Create Track card */}
              <Card
                sx={{
                  width: 140,
                  height: 140,
                  border: "2px dashed",
                  borderColor: "divider",
                  cursor: isDemo ? "not-allowed" : "pointer",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  opacity: isDemo ? 0.5 : 1,
                  "&:hover": isDemo
                    ? {}
                    : {
                        borderColor: "primary.main",
                        bgcolor: "action.hover",
                      },
                }}
                onClick={isDemo ? undefined : handleCreateTrack}
              >
                <CardContent sx={{ textAlign: "center", p: 2 }}>
                  <Stack alignItems="center" spacing={1}>
                    {isCreatingTrack ? (
                      <CircularProgress size={24} />
                    ) : (
                      <>
                        <AddIcon color="action" />
                        <Typography variant="body2" color="text.secondary">
                          Create Track
                        </Typography>
                      </>
                    )}
                  </Stack>
                </CardContent>
              </Card>
            </Stack>
          </Box>

          {/* Right scrollable area: Sequencer Grid */}
          <Box
            sx={{
              flex: 1,
              px: { xs: 2, sm: 3, md: 4, lg: 6 },
              py: 2,
              overflowX: "auto",
              overflowY: "auto",
              userSelect: isDraggingNewLoop || isDraggingLoopZone || isResizingLoop ? "none" : "auto",
            }}
          >
            {(() => {
              // Calculate total measures needed for the grid
              const MEASURE_WIDTH = 80; // pixels per measure
              let totalMeasures = 8; // Minimum grid size

              songDetail.tracks?.forEach((track) => {
                track.loops?.forEach((loop) => {
                  const loopEnd = (loop.offset || 0) + loop.measures;
                  if (loopEnd > totalMeasures) {
                    totalMeasures = loopEnd;
                  }
                });
              });

              // Add some extra measures for breathing room
              totalMeasures += 4;

              // Calculate current measure from currentBeat and time signature
              const getBeatsPerMeasure = (timeSignature?: string): number => {
                if (!timeSignature) return 4;
                const [numerator] = timeSignature.split("/").map(Number);
                return numerator || 4;
              };

              const beatsPerMeasure = getBeatsPerMeasure(songDetail.time_signature);
              const currentMeasure = currentBeat >= 0 ? Math.floor(currentBeat / beatsPerMeasure) : -1;

              return (
                <Stack spacing={0}>
                  {/* Measure Ruler */}
                  <Box
                    sx={{
                      display: "flex",
                      height: 32,
                      borderBottom: 2,
                      borderColor: "divider",
                      mb: 2,
                    }}
                  >
                    {Array.from({ length: totalMeasures }, (_, i) => {
                      const isCurrentMeasure = i === currentMeasure;

                      // Check if this measure is in the loop zone
                      const isInLoopZone =
                        loopZoneStart !== null &&
                        loopZoneEnd !== null &&
                        i >= Math.min(loopZoneStart, loopZoneEnd) &&
                        i <= Math.max(loopZoneStart, loopZoneEnd);

                      return (
                        <Box
                          key={i}
                          onMouseDown={(e) => {
                            e.preventDefault();
                            handleLoopZoneDragStart(i);
                          }}
                          onMouseEnter={() => {
                            handleLoopZoneDragMove(i);
                          }}
                          onClick={() => {
                            // Only seek playback if not dragging a loop zone
                            if (!isDraggingLoopZone && !isInLoopZone) {
                              const startBeat = i * beatsPerMeasure;
                              playFromBeat(startBeat);
                            }
                          }}
                          sx={{
                            width: MEASURE_WIDTH,
                            flexShrink: 0,
                            borderRight: 1,
                            borderColor: "divider",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            fontWeight: "bold",
                            color: isCurrentMeasure
                              ? "primary.main"
                              : isInLoopZone
                                ? "secondary.main"
                                : "text.secondary",
                            fontSize: "0.875rem",
                            bgcolor: isCurrentMeasure
                              ? "primary.light"
                              : isInLoopZone
                                ? "secondary.light"
                                : "transparent",
                            transition: "background-color 0.1s, color 0.1s",
                            cursor: "pointer",
                            "&:hover": {
                              bgcolor: isCurrentMeasure
                                ? "primary.light"
                                : isInLoopZone
                                  ? "secondary.main"
                                  : "action.hover",
                            },
                          }}
                        >
                          {i + 1}
                        </Box>
                      );
                    })}
                  </Box>

                  {/* Track Grid Rows */}
                  {songDetail.tracks?.map((track) => (
                    <Box
                      key={track.id}
                      sx={{
                        position: "relative",
                        height: 140 + 16, // Card height + spacing
                        display: "flex",
                      }}
                    >
                      {/* Grid background with measure markers - droppable cells */}
                      {Array.from({ length: totalMeasures }, (_, measureIndex) => {
                        const DropCell = () => {
                          const [{ isOver, canDrop }, drop] = useDrop(() => ({
                            accept: ITEM_TYPE,
                            canDrop: (item: DragItem, _monitor) => {
                              // Don't allow drops in demo mode or during playback
                              if (isDemo || isPlaying) return false;

                              // Only allow drops on the same track
                              if (item.trackId !== track.id) return false;

                              // Calculate the actual new offset based on where the loop was grabbed
                              const grabOffset = item.dragGrabOffset || 0;
                              const newOffset = measureIndex - grabOffset;

                              // Don't allow negative offsets
                              if (newOffset < 0) return false;

                              // Check for collisions with other loops (exclude the loop being dragged)
                              const loopEnd = newOffset + item.measures;

                              // Find loops that would collide with the new position
                              const hasCollision = track.loops?.some((otherLoop) => {
                                // Skip the loop being dragged (comparing by ID)
                                if (otherLoop.id === item.loopId) return false;

                                const otherStart = otherLoop.offset || 0;
                                const otherEnd = otherStart + otherLoop.measures;

                                // Check if ranges [newOffset, loopEnd) and [otherStart, otherEnd) overlap
                                return newOffset < otherEnd && loopEnd > otherStart;
                              });

                              return !hasCollision;
                            },
                            drop: (item: DragItem) => {
                              handleLoopDrop(item.loopId, measureIndex, item);
                            },
                            collect: (monitor) => ({
                              isOver: monitor.isOver(),
                              canDrop: monitor.canDrop(),
                            }),
                          }));

                          // Check if this cell is part of the drag selection
                          const isInDragSelection =
                            isDraggingNewLoop &&
                            dragTrackId === track.id &&
                            dragStartMeasure !== null &&
                            dragCurrentMeasure !== null &&
                            measureIndex >= Math.min(dragStartMeasure, dragCurrentMeasure) &&
                            measureIndex <= Math.max(dragStartMeasure, dragCurrentMeasure);

                          // Check if there's a loop at this position
                          const hasLoopAtPosition = track.loops?.some((loop) => {
                            const loopStart = loop.offset || 0;
                            const loopEnd = loopStart + loop.measures;
                            return measureIndex >= loopStart && measureIndex < loopEnd;
                          });

                          // Check if this is the current measure
                          const isCurrentMeasure = measureIndex === currentMeasure;

                          // Find the loop being resized if any
                          const resizingLoop = isResizingLoop
                            ? track.loops?.find((l) => l.id === resizingLoopId)
                            : null;

                          return (
                            <Box
                              ref={drop as any}
                              onMouseDown={(e) => {
                                if (!isPlaying && !isResizingLoop) {
                                  e.preventDefault();
                                  handleDragCreateStart(measureIndex, track.id, track);
                                }
                              }}
                              onMouseEnter={() => {
                                if (!isPlaying) {
                                  if (isResizingLoop && resizingLoop) {
                                    handleLoopResizeMove(measureIndex, resizingLoop, track);
                                  } else {
                                    handleDragCreateMove(measureIndex);
                                  }
                                }
                              }}
                              sx={{
                                width: MEASURE_WIDTH,
                                flexShrink: 0,
                                borderRight: 1,
                                borderColor: "divider",
                                bgcolor: isInDragSelection
                                  ? "primary.main"
                                  : isOver && canDrop
                                    ? "success.light"
                                    : isOver && !canDrop
                                      ? "error.light"
                                      : isCurrentMeasure
                                        ? "primary.light"
                                        : "transparent",
                                transition: "background-color 0.1s",
                                cursor: isPlaying || isDemo ? "default" : hasLoopAtPosition ? "default" : "ew-resize",
                                opacity: isInDragSelection ? 0.6 : 1,
                              }}
                            />
                          );
                        };

                        return <DropCell key={measureIndex} />;
                      })}

                      {/* Positioned loops - draggable */}
                      {track.loops?.map((loop, index) => {
                        const offset = loop.offset || 0;
                        const left = offset * MEASURE_WIDTH;

                        // Calculate width including extend_measures
                        // Use current resize value if this loop is being resized
                        const currentExtendMeasures =
                          isResizingLoop && resizingLoopId === loop.id
                            ? resizeCurrentExtendMeasures
                            : loop.extend_measures;
                        const totalMeasures = loop.measures + currentExtendMeasures;
                        const width = totalMeasures * MEASURE_WIDTH;

                        const DraggableLoop = () => {
                          const [{ isDragging }, drag] = useDrag(() => ({
                            type: ITEM_TYPE,
                            canDrag: () => !isPlaying && !isResizingLoop && !isDemo,
                            item: (monitor) => {
                              // Calculate which measure within the loop was grabbed
                              const initialOffset = monitor.getInitialClientOffset();
                              const initialSourceOffset = monitor.getInitialSourceClientOffset();

                              let dragGrabOffset = 0;
                              if (initialOffset && initialSourceOffset) {
                                // Calculate relative X position within the card
                                const relativeX = initialOffset.x - initialSourceOffset.x;
                                // Convert to measure index (0-based)
                                dragGrabOffset = Math.floor(relativeX / MEASURE_WIDTH);
                                // Clamp to valid range
                                dragGrabOffset = Math.max(0, Math.min(dragGrabOffset, loop.measures - 1));
                              }

                              return {
                                type: ITEM_TYPE,
                                loopId: loop.id,
                                trackId: track.id,
                                currentOffset: offset,
                                measures: loop.measures,
                                dragGrabOffset,
                              } as DragItem;
                            },
                            collect: (monitor) => ({
                              isDragging: monitor.isDragging(),
                            }),
                          }));

                          const isGenerating = generatingLoops.has(loop.id);
                          const isBeingResized = isResizingLoop && resizingLoopId === loop.id;

                          return (
                            <Card
                              ref={isGenerating || isPlaying || isBeingResized || isDemo ? undefined : (drag as any)}
                              sx={{
                                position: "absolute",
                                left: `${left}px`,
                                width: `${width}px`,
                                height: 140,
                                cursor:
                                  isGenerating || isPlaying || isDemo ? "pointer" : isDragging ? "grabbing" : "grab",
                                display: "flex",
                                alignItems: "center",
                                justifyContent: "center",
                                border: 1,
                                borderColor: isBeingResized ? "primary.main" : "divider",
                                borderLeft: 4,
                                borderLeftColor: `${track.color}.main`,
                                pointerEvents: isDragging || isBeingResized ? "none" : "auto",
                                opacity: isDragging ? 0.5 : 1,
                                "&:hover":
                                  isGenerating || isPlaying
                                    ? {}
                                    : {
                                        borderColor: "text.primary",
                                      },
                              }}
                              onClick={isGenerating || isBeingResized ? undefined : () => handleOpenEditLoopModal(loop)}
                            >
                              <CardContent sx={{ textAlign: "center", p: 2, width: "100%", position: "relative" }}>
                                {isGenerating ? (
                                  <Stack spacing={2} alignItems="center">
                                    <CircularProgress size={32} />
                                    <Typography variant="caption" color="text.secondary">
                                      Generating...
                                    </Typography>
                                  </Stack>
                                ) : (
                                  <>
                                    <Typography variant="subtitle2">Loop {index + 1}</Typography>
                                    {currentExtendMeasures !== 0 && (
                                      <Typography variant="caption" color="text.secondary">
                                        {currentExtendMeasures > 0
                                          ? `+${currentExtendMeasures}`
                                          : currentExtendMeasures}{" "}
                                        measures
                                      </Typography>
                                    )}
                                  </>
                                )}
                              </CardContent>

                              {/* Resize handle on right edge */}
                              {!isGenerating && !isPlaying && !isDemo && (
                                <Box
                                  onMouseDown={(e) => handleLoopResizeStart(e, loop, track)}
                                  sx={{
                                    position: "absolute",
                                    right: 0,
                                    top: 0,
                                    bottom: 0,
                                    width: 16,
                                    cursor: "ew-resize",
                                    bgcolor: "transparent",
                                    zIndex: 10,
                                    "&:hover": {
                                      bgcolor: "primary.main",
                                      opacity: 0.3,
                                    },
                                  }}
                                />
                              )}
                            </Card>
                          );
                        };

                        return <DraggableLoop key={loop.id} />;
                      })}
                    </Box>
                  ))}
                </Stack>
              );
            })()}
          </Box>
        </Box>
      )}

      {/* New Song Modal */}
      <Modal
        open={showNewSongModal}
        onClose={handleCloseNewSongModal}
        aria-labelledby="new-song-modal-title"
        aria-describedby="new-song-modal-description"
      >
        <Box
          sx={{
            position: "absolute",
            top: "50%",
            left: "50%",
            transform: "translate(-50%, -50%)",
            width: 400,
            bgcolor: "background.paper",
            boxShadow: 24,
            p: 4,
            borderRadius: 2,
          }}
        >
          <Typography id="new-song-modal-title" variant="h6" component="h2" gutterBottom>
            {songs.length === 0 ? "Welcome to MIDI Agent" : "Create New Song"}
          </Typography>

          <Stack spacing={2} sx={{ mb: 3 }}>
            {/* Key Selection */}
            <FormControl fullWidth size="small">
              <InputLabel id="song-key-label">Key</InputLabel>
              <Select
                labelId="song-key-label"
                id="song-key"
                value={newSongKey}
                label="Key"
                onChange={(e) => setNewSongKey(e.target.value as CreateSongRequest["key"])}
                disabled={isCreatingSong || isDemo}
              >
                {SONG_KEYS.map((key) => (
                  <MenuItem key={key} value={key}>
                    {key}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            {/* Time Signature Selection */}
            <FormControl fullWidth size="small">
              <InputLabel id="song-time-sig-label">Time Signature</InputLabel>
              <Select
                labelId="song-time-sig-label"
                id="song-time-sig"
                value={newSongTimeSignature}
                label="Time Signature"
                onChange={(e) => setNewSongTimeSignature(e.target.value)}
                disabled={isCreatingSong || isDemo}
              >
                <MenuItem value="4/4">4/4</MenuItem>
                <MenuItem value="3/4">3/4</MenuItem>
                <MenuItem value="6/8">6/8</MenuItem>
                <MenuItem value="5/4">5/4</MenuItem>
                <MenuItem value="7/8">7/8</MenuItem>
              </Select>
            </FormControl>

            {/* BPM Input */}
            <TextField
              fullWidth
              size="small"
              label="BPM"
              type="number"
              value={newSongBpm}
              onChange={(e) => setNewSongBpm(parseInt(e.target.value) || 120)}
              inputProps={{ min: 30, max: 300, step: 1 }}
              disabled={isCreatingSong || isDemo}
            />
          </Stack>

          <Stack direction="row" spacing={2}>
            {songs.length > 0 && (
              <Button variant="outlined" fullWidth onClick={handleCloseNewSongModal} disabled={isCreatingSong}>
                Cancel
              </Button>
            )}
            <Button variant="contained" fullWidth onClick={handleCreateSong} disabled={isCreatingSong || isDemo}>
              {isCreatingSong ? <CircularProgress size={24} /> : "Create Song"}
            </Button>
          </Stack>
        </Box>
      </Modal>

      {/* Loop Modal (Create/Edit) */}
      <Modal
        open={showLoopModal}
        onClose={() => !isCreatingLoop && !isDeletingLoop && setShowLoopModal(false)}
        aria-labelledby="loop-modal-title"
      >
        <Box
          sx={{
            position: "absolute",
            top: "50%",
            left: "50%",
            transform: "translate(-50%, -50%)",
            width: { xs: "90%", sm: 700 },
            maxHeight: "90vh",
            bgcolor: "background.paper",
            boxShadow: 24,
            borderRadius: 2,
            display: "flex",
            flexDirection: "column",
          }}
        >
          {/* Header */}
          <Box sx={{ p: 3, pb: 2 }}>
            <Typography id="loop-modal-title" variant="h6" component="h2">
              {loopModalMode === "create" ? "Create Loop" : `Loop ${loopMeasures} measures`}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {loopModalMode === "create"
                ? "Create a new loop with AI-generated MIDI"
                : "View loop details and continue the conversation"}
            </Typography>
          </Box>

          {/* Tabs */}
          {loopModalMode === "edit" && (
            <Box sx={{ borderBottom: 1, borderColor: "divider", px: 3 }}>
              <Tabs value={activeTab} onChange={(_, newValue) => setActiveTab(newValue)}>
                <Tab label="Chat" />
                <Tab label="MIDI Events" />
              </Tabs>
            </Box>
          )}

          {/* Content Area */}
          <Box sx={{ flexGrow: 1, overflow: "auto", p: 3 }}>
            {loopModalMode === "create" ? (
              // Create mode: show measures input and prompt
              <Stack spacing={3}>
                <TextField
                  label="Number of Measures"
                  type="number"
                  value={loopMeasures}
                  onChange={(e) => setLoopMeasures(parseInt(e.target.value) || 1)}
                  fullWidth
                  required
                  inputProps={{ min: 1, max: 32 }}
                  helperText="Enter a value between 1 and 32"
                  disabled={isCreatingLoop || isDemo}
                />

                <TextField
                  label="Musical Prompt"
                  value={loopPrompt}
                  onChange={(e) => setLoopPrompt(e.target.value)}
                  onKeyDown={(e) => {
                    // Check for Command+Enter (Mac) or Ctrl+Enter (Windows/Linux)
                    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
                      e.preventDefault();
                      if (loopPrompt.trim() && !isCreatingLoop && !isDemo) {
                        handleSubmitLoop();
                      }
                    }
                  }}
                  inputRef={loopPromptInputRef}
                  fullWidth
                  required
                  multiline
                  rows={6}
                  placeholder="Describe what you want to create... (e.g., 'A funky bassline in C minor')"
                  helperText="Cmd+Enter to send"
                  disabled={isCreatingLoop || isDemo}
                />
              </Stack>
            ) : (
              // Edit mode: show tabs content
              <>
                {activeTab === 0 && (
                  // Chat tab
                  <Stack spacing={2}>
                    {isLoadingChat ? (
                      <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
                        <CircularProgress />
                      </Box>
                    ) : chatHistory.length === 0 ? (
                      <Typography color="text.secondary" align="center" sx={{ py: 4 }}>
                        No chat history yet
                      </Typography>
                    ) : (
                      <Stack spacing={2} sx={{ mb: 2 }}>
                        {chatHistory.map((message) => (
                          <Box
                            key={message.id}
                            sx={{
                              display: "flex",
                              justifyContent: message.role === "user" ? "flex-end" : "flex-start",
                            }}
                          >
                            <Paper
                              elevation={1}
                              sx={{
                                p: 2,
                                maxWidth: "75%",
                                bgcolor: message.role === "user" ? "primary.main" : "action.hover",
                                color: message.role === "user" ? "primary.contrastText" : "text.primary",
                              }}
                            >
                              <Typography variant="caption" sx={{ opacity: 0.8, display: "block", mb: 0.5 }}>
                                {message.role === "user" ? "You" : "Assistant"}
                              </Typography>
                              <Typography variant="body2">{message.msg}</Typography>
                            </Paper>
                          </Box>
                        ))}
                      </Stack>
                    )}

                    {/* Prompt input for edit mode */}
                    <TextField
                      label="Add message"
                      value={loopPrompt}
                      onChange={(e) => setLoopPrompt(e.target.value)}
                      onKeyDown={(e) => {
                        // Check for Command+Enter (Mac) or Ctrl+Enter (Windows/Linux)
                        if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
                          e.preventDefault();
                          if (loopPrompt.trim() && !isCreatingLoop && !isDemo) {
                            handleSubmitLoop();
                          }
                        }
                      }}
                      inputRef={loopPromptInputRef}
                      fullWidth
                      multiline
                      rows={3}
                      placeholder="Continue the conversation..."
                      helperText="Cmd+Enter to send"
                      disabled={isCreatingLoop || isDemo}
                    />
                  </Stack>
                )}

                {activeTab === 1 && (
                  // MIDI Events tab
                  <TableContainer component={Paper} variant="outlined">
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell>Measure</TableCell>
                          <TableCell>Beat</TableCell>
                          <TableCell>Event</TableCell>
                          <TableCell>Value</TableCell>
                          <TableCell>Chord</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {selectedLoop?.midi_events.length === 0 ? (
                          <TableRow>
                            <TableCell colSpan={5} align="center">
                              <Typography color="text.secondary">No MIDI events</Typography>
                            </TableCell>
                          </TableRow>
                        ) : (
                          selectedLoop?.midi_events.map((event: any, index: number) => (
                            <TableRow key={index}>
                              <TableCell>{event.measure}</TableCell>
                              <TableCell>
                                {event.beat}.{event.beat_div4}.{event.beat_div16}
                              </TableCell>
                              <TableCell>{event.event}</TableCell>
                              <TableCell>{event.value}</TableCell>
                              <TableCell>{event.chord || "-"}</TableCell>
                            </TableRow>
                          ))
                        )}
                      </TableBody>
                    </Table>
                  </TableContainer>
                )}
              </>
            )}
          </Box>

          {/* Footer with buttons */}
          <Box sx={{ p: 3, pt: 2, borderTop: 1, borderColor: "divider" }}>
            <Stack direction="row" spacing={2} justifyContent="space-between" alignItems="center">
              {/* Left side: Delete and Download buttons (only in edit mode) */}
              {loopModalMode === "edit" ? (
                <Stack direction="row" spacing={2}>
                  <Button
                    variant="outlined"
                    color="error"
                    onClick={handleDeleteLoop}
                    disabled={isCreatingLoop || isDeletingLoop || isDemo}
                  >
                    {isDeletingLoop ? <CircularProgress size={24} /> : "Delete"}
                  </Button>
                </Stack>
              ) : (
                <Box /> // Empty spacer in create mode
              )}

              {/* Right side: Close/Cancel and Send/Create buttons */}
              <Stack direction="row" spacing={2}>
                <Button
                  variant="outlined"
                  onClick={() => setShowLoopModal(false)}
                  disabled={isCreatingLoop || isDeletingLoop}
                >
                  {loopModalMode === "edit" ? "Close" : "Cancel"}
                </Button>
                {(loopModalMode === "create" || activeTab === 0) && (
                  <Button
                    variant="contained"
                    onClick={handleSubmitLoop}
                    disabled={isCreatingLoop || isDeletingLoop || !loopPrompt.trim() || isDemo}
                  >
                    {isCreatingLoop ? (
                      <CircularProgress size={24} />
                    ) : loopModalMode === "create" ? (
                      "Create Loop"
                    ) : (
                      "Send"
                    )}
                  </Button>
                )}
              </Stack>
            </Stack>
          </Box>
        </Box>
      </Modal>

      {/* Track Modal */}
      <Modal
        open={showTrackModal}
        onClose={() => !isDeletingTrack && !isUpdatingTrack && setShowTrackModal(false)}
        aria-labelledby="track-modal-title"
      >
        <Box
          sx={{
            position: "absolute",
            top: "50%",
            left: "50%",
            transform: "translate(-50%, -50%)",
            width: { xs: "90%", sm: 600 },
            maxHeight: "90vh",
            bgcolor: "background.paper",
            boxShadow: 24,
            borderRadius: 2,
            p: 4,
          }}
        >
          {/* Header */}
          <Typography id="track-modal-title" variant="h6" component="h2" gutterBottom>
            Edit Track
          </Typography>

          {/* Editable Fields */}
          <Stack spacing={3} sx={{ my: 3 }}>
            <TextField
              label="Track Title"
              value={editedTrackTitle}
              onChange={(e) => setEditedTrackTitle(e.target.value)}
              fullWidth
              disabled={isUpdatingTrack || isDeletingTrack || isDemo}
              required
            />

            <TextField
              label="MIDI Channel"
              type="number"
              value={editedTrackChannel}
              onChange={(e) => setEditedTrackChannel(parseInt(e.target.value) || 1)}
              fullWidth
              disabled={isUpdatingTrack || isDeletingTrack || isDemo}
              inputProps={{ min: 1, max: 16, step: 1 }}
              helperText="MIDI channel (1-16)"
              required
            />

            <FormControl fullWidth disabled={isUpdatingTrack || isDeletingTrack || isDemo}>
              <InputLabel id="instrument-select-label">Instrument</InputLabel>
              <Select
                labelId="instrument-select-label"
                value={editedTrackInstrument}
                label="Instrument"
                onChange={(e) => setEditedTrackInstrument(e.target.value as "piano" | "bass" | "drum")}
              >
                <MenuItem value="piano">Piano</MenuItem>
                <MenuItem value="bass">Bass</MenuItem>
                <MenuItem value="drum">Drum</MenuItem>
              </Select>
            </FormControl>
          </Stack>

          {/* Footer */}
          <Box sx={{ display: "flex", justifyContent: "space-between", pt: 2 }}>
            <Button
              variant="outlined"
              color="error"
              onClick={handleDeleteTrack}
              disabled={isDeletingTrack || isUpdatingTrack || isDemo}
            >
              {isDeletingTrack ? <CircularProgress size={24} /> : "Delete"}
            </Button>
            <Stack direction="row" spacing={2}>
              <Button
                variant="outlined"
                onClick={() => setShowTrackModal(false)}
                disabled={isDeletingTrack || isUpdatingTrack}
              >
                Cancel
              </Button>
              <Button
                variant="contained"
                onClick={handleUpdateTrack}
                disabled={isDeletingTrack || isUpdatingTrack || !editedTrackTitle.trim() || isDemo}
              >
                {isUpdatingTrack ? <CircularProgress size={24} /> : "Save"}
              </Button>
            </Stack>
          </Box>
        </Box>
      </Modal>

      {/* Floating Playback Control Bar */}
      <Box
        sx={{
          position: "fixed",
          bottom: 24,
          left: "50%",
          transform: "translateX(-50%)",
          zIndex: (theme) => theme.zIndex.appBar,
          boxShadow: 4,
        }}
      >
        <Paper
          elevation={8}
          sx={{
            px: 3,
            py: 2,
            borderRadius: 4,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: 2,
            bgcolor: "background.paper",
          }}
        >
          {/* BPM Input */}
          <TextField
            label="BPM"
            type="number"
            value={bpm}
            onChange={(e) => setPlaybackBpm(parseInt(e.target.value) || 120)}
            size="small"
            inputProps={{ min: 30, max: 300, step: 1 }}
            sx={{ width: 100 }}
          />

          {/* Playback Controls */}
          <Box sx={{ display: "flex", gap: 1, alignItems: "center" }}>
            {/* Back to Start Button */}
            <IconButton
              color="primary"
              size="large"
              onClick={stop}
              sx={{
                bgcolor: "action.hover",
                "&:hover": {
                  bgcolor: "action.selected",
                },
              }}
              aria-label="back to start"
            >
              <SkipPreviousIcon fontSize="large" />
            </IconButton>

            {/* Play/Pause Button */}
            <IconButton
              color="primary"
              size="large"
              onClick={togglePlayPause}
              sx={{
                bgcolor: "primary.main",
                color: "primary.contrastText",
                "&:hover": {
                  bgcolor: "primary.dark",
                },
              }}
              aria-label={isPlaying ? "pause" : "play"}
            >
              {isPlaying ? <PauseIcon fontSize="large" /> : <PlayArrowIcon fontSize="large" />}
            </IconButton>
          </Box>
        </Paper>
      </Box>
    </Box>
  );
}
