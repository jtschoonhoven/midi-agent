import { useState, useEffect, useRef } from "react";
import {
  Box,
  Container,
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
} from "@mui/material";
import MenuIcon from "@mui/icons-material/Menu";
import CloseIcon from "@mui/icons-material/Close";
import AddIcon from "@mui/icons-material/Add";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import PauseIcon from "@mui/icons-material/Pause";
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
import { useDrag, useDrop } from "react-dnd";
import { usePlayback } from "../contexts/PlaybackContext";
import type { components } from "../types/api";

type Song = components["schemas"]["SongResponse"];
type SongDetail = components["schemas"]["SongDetailResponse"];
type Track = components["schemas"]["TrackResponse"];
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
}
type ChatMessage = components["schemas"]["ChatMessageResponse"];

export default function ChatInterface() {
  const {
    isPlaying,
    bpm,
    togglePlayPause,
    setBpm: setPlaybackBpm,
    loadSong,
    midiOutputs,
    selectedMidiOutput,
    setSelectedMidiOutput,
    requestMidiAccess,
    hasMidiAccess,
  } = usePlayback();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [songs, setSongs] = useState<Song[]>([]);
  const [isLoadingSongs, setIsLoadingSongs] = useState(true);
  const [showNewSongModal, setShowNewSongModal] = useState(false);
  const [isCreatingSong, setIsCreatingSong] = useState(false);

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
  const [editedTrackChannel, setEditedTrackChannel] = useState(1);
  const [editedTrackInstrument, setEditedTrackInstrument] = useState<"piano" | "bass" | "drum">("piano");
  const [isUpdatingTrack, setIsUpdatingTrack] = useState(false);

  // Track loops that are currently generating MIDI
  const [generatingLoops, setGeneratingLoops] = useState<Set<string>>(new Set());

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
            repeat: loop.repeat,
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

  // Create a new song
  const handleCreateSong = async () => {
    try {
      setIsCreatingSong(true);
      const result = await createSong({
        bpm: 120,
        key: "C",
        time_signature: "4/4",
      });

      if (result.data) {
        // Add the new song to the list
        setSongs([result.data, ...songs]);
        setShowNewSongModal(false);
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

  // Handle song selection from sidebar
  const handleSelectSong = (songId: string) => {
    setSelectedSongId(songId);
    setDrawerOpen(false);
  };

  // Handle create loop
  const handleOpenCreateLoopModal = (trackId: string) => {
    setLoopModalMode("create");
    setSelectedTrackId(trackId);
    setSelectedLoop(null);
    setLoopMeasures(4); // Reset to default
    setLoopPrompt(""); // Reset prompt
    setChatHistory([]);
    setActiveTab(0); // Reset to chat tab
    setShowLoopModal(true);
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
      await new Promise(resolve => setTimeout(resolve, pollInterval));

      try {
        const result = await getLoop(loopId);
        if (result.data && result.data.midi_events.length > 0) {
          // Loop has MIDI events now - it's done generating
          setGeneratingLoops(prev => {
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
    setGeneratingLoops(prev => {
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
          repeat: 1,
        });

        if (!createResult.data) {
          console.error("Failed to create loop:", createResult.error);
          alert("Failed to create loop. Please try again.");
          return;
        }

        const newLoop = createResult.data;

        // Step 2: Reload song to show the new loop card
        if (songDetail && selectedSongId) {
          const result = await getSong(selectedSongId);
          if (result.data) {
            setSongDetail(result.data);
          }
        }

        // Step 3: Close modal immediately
        setShowLoopModal(false);
        setLoopPrompt("");
        setLoopMeasures(4);
        setIsCreatingLoop(false);

        // Step 4: Mark loop as generating and start chat in background
        setGeneratingLoops(prev => new Set(prev).add(newLoop.id));

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
            setGeneratingLoops(prev => {
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

        const chatResult = await appendLoopChat({
          loop_id: selectedLoop.id,
          msg: loopPrompt,
          measures: selectedLoop.measures,
        });

        if (!chatResult.data) {
          console.error("Failed to append chat:", chatResult.error);
          alert("Failed to process prompt. Please try again.");
          return;
        }

        // Reload full loop details with updated chat history
        const loopResult = await getLoop(selectedLoop.id);
        if (loopResult.data) {
          setSelectedLoop(loopResult.data);
          setChatHistory(loopResult.data.chats || []);
        }

        // Update the local song detail
        if (songDetail && selectedSongId) {
          const result = await getSong(selectedSongId);
          if (result.data) {
            setSongDetail(result.data);
          }
        }

        // Clear prompt but keep modal open
        setLoopPrompt("");
      } catch (error) {
        console.error("Failed to append chat:", error);
        alert("Failed to process prompt. Please try again.");
      } finally {
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
      alert("No song selected");
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
  const handleLoopDrop = async (loopId: string, newOffset: number) => {
    try {
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
              disabled={isCreatingSong}
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
        </Toolbar>
      </AppBar>

      {/* Main content area */}
      {isLoadingSongDetail ? (
        <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
          <CircularProgress />
        </Box>
      ) : !songDetail ? (
        <Box sx={{ textAlign: "center", py: 8 }}>
          <Typography variant="h6" color="text.secondary">
            No song selected
          </Typography>
        </Box>
      ) : (
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
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  "&:hover": {
                    borderColor: "primary.main",
                    bgcolor: "action.hover",
                  },
                }}
                onClick={handleCreateTrack}
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
          <Box sx={{ flex: 1, px: { xs: 2, sm: 3, md: 4, lg: 6 }, py: 2, overflowX: "auto", overflowY: "auto" }}>
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
                    {Array.from({ length: totalMeasures }, (_, i) => (
                      <Box
                        key={i}
                        sx={{
                          width: MEASURE_WIDTH,
                          flexShrink: 0,
                          borderRight: 1,
                          borderColor: "divider",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          fontWeight: "bold",
                          color: "text.secondary",
                          fontSize: "0.875rem",
                        }}
                      >
                        {i + 1}
                      </Box>
                    ))}
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
                          const [{ isOver }, drop] = useDrop(() => ({
                            accept: ITEM_TYPE,
                            drop: (item: DragItem) => {
                              handleLoopDrop(item.loopId, measureIndex);
                            },
                            collect: (monitor) => ({
                              isOver: monitor.isOver(),
                            }),
                          }));

                          return (
                            <Box
                              ref={drop}
                              sx={{
                                width: MEASURE_WIDTH,
                                flexShrink: 0,
                                borderRight: 1,
                                borderColor: "divider",
                                bgcolor: isOver
                                  ? "primary.light"
                                  : measureIndex % 4 === 0
                                    ? "action.hover"
                                    : "transparent",
                                transition: "background-color 0.2s",
                              }}
                            />
                          );
                        };

                        return <DropCell key={measureIndex} />;
                      })}

                      {/* Positioned loops - draggable */}
                      {track.loops?.map((loop, index) => {
                        const offset = loop.offset || 0;
                        const width = loop.measures * MEASURE_WIDTH;
                        const left = offset * MEASURE_WIDTH;

                        const DraggableLoop = () => {
                          const [{ isDragging }, drag] = useDrag(() => ({
                            type: ITEM_TYPE,
                            item: {
                              type: ITEM_TYPE,
                              loopId: loop.id,
                              trackId: track.id,
                              currentOffset: offset,
                              measures: loop.measures,
                            } as DragItem,
                            collect: (monitor) => ({
                              isDragging: monitor.isDragging(),
                            }),
                          }));

                          const isGenerating = generatingLoops.has(loop.id);

                          return (
                            <Card
                              ref={isGenerating ? undefined : drag}
                              sx={{
                                position: "absolute",
                                left: `${left}px`,
                                width: `${width}px`,
                                height: 140,
                                cursor: isGenerating ? "default" : isDragging ? "grabbing" : "grab",
                                display: "flex",
                                alignItems: "center",
                                justifyContent: "center",
                                opacity: isDragging ? 0.5 : 1,
                                "&:hover": {
                                  bgcolor: isGenerating ? "inherit" : "action.hover",
                                  boxShadow: isGenerating ? 0 : 2,
                                },
                              }}
                              onClick={isGenerating ? undefined : () => handleOpenEditLoopModal(loop)}
                            >
                              <CardContent sx={{ textAlign: "center", p: 2 }}>
                                {isGenerating ? (
                                  <Stack spacing={2} alignItems="center">
                                    <CircularProgress size={32} />
                                    <Typography variant="caption" color="text.secondary">
                                      Generating...
                                    </Typography>
                                  </Stack>
                                ) : (
                                  <>
                                    <Typography variant="subtitle2" gutterBottom>
                                      Loop {index + 1}
                                    </Typography>
                                    <Typography variant="caption" color="text.secondary">
                                      {loop.measures} measures • {loop.midi_events.length} events
                                    </Typography>
                                  </>
                                )}
                              </CardContent>
                            </Card>
                          );
                        };

                        return <DraggableLoop key={loop.id} />;
                      })}

                      {/* Create loop button at the end of existing loops */}
                      {(() => {
                        // Find the rightmost position
                        let rightmostPosition = 0;
                        track.loops?.forEach((loop) => {
                          const loopEnd = (loop.offset || 0) + loop.measures;
                          if (loopEnd > rightmostPosition) {
                            rightmostPosition = loopEnd;
                          }
                        });

                        return (
                          <Card
                            sx={{
                              position: "absolute",
                              left: `${rightmostPosition * MEASURE_WIDTH}px`,
                              width: MEASURE_WIDTH,
                              height: 140,
                              border: "2px dashed",
                              borderColor: "divider",
                              cursor: "pointer",
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "center",
                              "&:hover": {
                                borderColor: "primary.main",
                                bgcolor: "action.hover",
                              },
                            }}
                            onClick={() => handleOpenCreateLoopModal(track.id)}
                          >
                            <CardContent sx={{ textAlign: "center", p: 1 }}>
                              <Stack alignItems="center" spacing={0.5}>
                                <AddIcon color="action" fontSize="small" />
                                <Typography variant="caption" color="text.secondary">
                                  Loop
                                </Typography>
                              </Stack>
                            </CardContent>
                          </Card>
                        );
                      })()}
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
        onClose={() => songs.length > 0 && setShowNewSongModal(false)}
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
          <Typography id="new-song-modal-description" sx={{ mb: 3 }}>
            {songs.length === 0
              ? "You don't have any songs yet. Create your first song to get started."
              : "Create a new song with default settings (C major, 120 BPM)."}
          </Typography>
          <Stack direction="row" spacing={2}>
            {songs.length > 0 && (
              <Button variant="outlined" fullWidth onClick={() => setShowNewSongModal(false)} disabled={isCreatingSong}>
                Cancel
              </Button>
            )}
            <Button variant="contained" fullWidth onClick={handleCreateSong} disabled={isCreatingSong}>
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
                  disabled={isCreatingLoop}
                />

                <TextField
                  label="Musical Prompt"
                  value={loopPrompt}
                  onChange={(e) => setLoopPrompt(e.target.value)}
                  fullWidth
                  required
                  multiline
                  rows={6}
                  placeholder="Describe what you want to create... (e.g., 'A funky bassline in C minor')"
                  helperText="Enter a description of the loop you want to generate"
                  disabled={isCreatingLoop}
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
                      fullWidth
                      multiline
                      rows={3}
                      placeholder="Continue the conversation..."
                      disabled={isCreatingLoop}
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
              {/* Left side: Delete button (only in edit mode) */}
              {loopModalMode === "edit" ? (
                <Button
                  variant="outlined"
                  color="error"
                  onClick={handleDeleteLoop}
                  disabled={isCreatingLoop || isDeletingLoop}
                >
                  {isDeletingLoop ? <CircularProgress size={24} /> : "Delete"}
                </Button>
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
                    disabled={isCreatingLoop || isDeletingLoop || !loopPrompt.trim()}
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
              disabled={isUpdatingTrack || isDeletingTrack}
              required
            />

            <TextField
              label="MIDI Channel"
              type="number"
              value={editedTrackChannel}
              onChange={(e) => setEditedTrackChannel(parseInt(e.target.value) || 1)}
              fullWidth
              disabled={isUpdatingTrack || isDeletingTrack}
              inputProps={{ min: 1, max: 16, step: 1 }}
              helperText="MIDI channel (1-16)"
              required
            />

            <FormControl fullWidth disabled={isUpdatingTrack || isDeletingTrack}>
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
              disabled={isDeletingTrack || isUpdatingTrack}
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
                disabled={isDeletingTrack || isUpdatingTrack || !editedTrackTitle.trim()}
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
          >
            {isPlaying ? <PauseIcon fontSize="large" /> : <PlayArrowIcon fontSize="large" />}
          </IconButton>
        </Paper>
      </Box>
    </Box>
  );
}
