import { useState, useEffect } from "react";
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
} from "@mui/material";
import MenuIcon from "@mui/icons-material/Menu";
import CloseIcon from "@mui/icons-material/Close";
import AddIcon from "@mui/icons-material/Add";
import { listSongs, createSong, getSong, createLoop, appendLoopChat, getLoop, deleteLoop, createTrack } from "../lib/api";
import type { components } from "../types/api";

type Song = components["schemas"]["SongResponse"];
type SongDetail = components["schemas"]["SongDetailResponse"];
type Track = components["schemas"]["TrackResponse"];
type Loop = components["schemas"]["LoopResponse"];
type LoopDetail = components["schemas"]["LoopDetailResponse"];
type ChatMessage = components["schemas"]["ChatMessageResponse"];

export default function ChatInterface() {
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

  // Create a new song
  const handleCreateSong = async () => {
    try {
      setIsCreatingSong(true);
      const result = await createSong({
        bpm: 120,
        key: "C",
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

        // Step 2: Send the initial chat message to start inference
        const chatResult = await appendLoopChat({
          loop_id: newLoop.id,
          msg: loopPrompt,
          measures: loopMeasures,
        });

        if (!chatResult.data) {
          console.error("Failed to start loop inference:", chatResult.error);
          alert("Loop created but failed to process prompt. Please try again.");
          return;
        }

        // Step 3: Update the local song detail with the new loop
        if (songDetail && selectedSongId) {
          // Reload the song details to get the updated loop data
          const result = await getSong(selectedSongId);
          if (result.data) {
            setSongDetail(result.data);
          }
        }

        // Close modal and reset form
        setShowLoopModal(false);
        setLoopPrompt("");
        setLoopMeasures(4);
      } catch (error) {
        console.error("Failed to create loop:", error);
        alert("Failed to create loop. Please try again.");
      } finally {
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

      if (!result.data) {
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

      const result = await createTrack({
        song_id: selectedSongId,
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
            <IconButton
              edge="end"
              onClick={toggleDrawer(false)}
              aria-label="close drawer"
              size="small"
            >
              <CloseIcon />
            </IconButton>
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
                    <ListItemButton
                      selected={selectedSongId === song.id}
                      onClick={() => handleSelectSong(song.id)}
                    >
                      <ListItemText
                        primary={song.title}
                        secondary={`${song.key} • ${song.bpm} BPM`}
                      />
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
          <IconButton
            edge="start"
            color="inherit"
            aria-label="menu"
            onClick={toggleDrawer(true)}
            sx={{ mr: 2 }}
          >
            <MenuIcon />
          </IconButton>
          <Typography variant="h6" component="div">
            {songDetail?.title || "MIDI Agent"}
          </Typography>
        </Toolbar>
      </AppBar>

      {/* Main container with responsive padding */}
      <Container
        maxWidth={false}
        sx={{
          flexGrow: 1,
          px: { xs: 2, sm: 3, md: 4, lg: 6 },
          py: 3,
        }}
      >
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
          <Stack spacing={2}>
            {/* Render each track as a row */}
            {songDetail.tracks.map((track) => (
              <Box
                key={track.id}
                sx={{
                  display: "grid",
                  gridTemplateColumns: {
                    xs: "1fr 2fr",
                    md: "200px 1fr",
                  },
                  gap: 2,
                  alignItems: "start",
                }}
              >
                {/* Left column: Track name */}
                <Card>
                  <CardContent>
                    <Typography variant="h6" gutterBottom>
                      Track {track.midi_channel}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Channel {track.midi_channel}
                    </Typography>
                  </CardContent>
                </Card>

                {/* Right column: Loop cards */}
                <Box sx={{ display: "flex", gap: 2, overflowX: "auto", pb: 1 }}>
                  {/* Loop cards */}
                  {track.loops.map((loop, index) => (
                    <Card
                      key={loop.id}
                      sx={{
                        minWidth: 200,
                        flexShrink: 0,
                        cursor: "pointer",
                        "&:hover": {
                          bgcolor: "action.hover",
                          boxShadow: 2,
                        },
                      }}
                      onClick={() => handleOpenEditLoopModal(loop)}
                    >
                      <CardContent>
                        <Typography variant="subtitle2" gutterBottom>
                          Loop {index + 1}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {loop.measures} measures • {loop.midi_events.length} events
                        </Typography>
                      </CardContent>
                    </Card>
                  ))}

                  {/* Create loop card */}
                  <Card
                    sx={{
                      minWidth: 200,
                      flexShrink: 0,
                      border: "2px dashed",
                      borderColor: "divider",
                      cursor: "pointer",
                      "&:hover": {
                        borderColor: "primary.main",
                        bgcolor: "action.hover",
                      },
                    }}
                    onClick={() => handleOpenCreateLoopModal(track.id)}
                  >
                    <CardContent
                      sx={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        minHeight: 80,
                      }}
                    >
                      <Stack alignItems="center" spacing={1}>
                        <AddIcon color="action" />
                        <Typography variant="body2" color="text.secondary">
                          Create Loop
                        </Typography>
                      </Stack>
                    </CardContent>
                  </Card>
                </Box>
              </Box>
            ))}

            {/* Create Track row */}
            <Box
              sx={{
                display: "grid",
                gridTemplateColumns: {
                  xs: "1fr 2fr",
                  md: "200px 1fr",
                },
                gap: 2,
                alignItems: "start",
              }}
            >
              {/* Left column: Create Track card */}
              <Card
                sx={{
                  border: "2px dashed",
                  borderColor: "divider",
                  cursor: "pointer",
                  "&:hover": {
                    borderColor: "primary.main",
                    bgcolor: "action.hover",
                  },
                }}
                onClick={handleCreateTrack}
              >
                <CardContent
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    minHeight: 80,
                  }}
                >
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

              {/* Right column: Empty space */}
              <Box />
            </Box>
          </Stack>
        )}
      </Container>

      {/* New Song Modal */}
      <Modal
        open={showNewSongModal}
        onClose={() => {}}
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
            Welcome to MIDI Agent
          </Typography>
          <Typography id="new-song-modal-description" sx={{ mb: 3 }}>
            You don't have any songs yet. Create your first song to get started.
          </Typography>
          <Button
            variant="contained"
            fullWidth
            onClick={handleCreateSong}
            disabled={isCreatingSong}
          >
            {isCreatingSong ? <CircularProgress size={24} /> : "New Song"}
          </Button>
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
                                bgcolor: message.role === "user" ? "primary.main" : "grey.100",
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
                    {isCreatingLoop ? <CircularProgress size={24} /> : loopModalMode === "create" ? "Create Loop" : "Send"}
                  </Button>
                )}
              </Stack>
            </Stack>
          </Box>
        </Box>
      </Modal>
    </Box>
  );
}
