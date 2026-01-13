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
} from "@mui/material";
import MenuIcon from "@mui/icons-material/Menu";
import CloseIcon from "@mui/icons-material/Close";
import AddIcon from "@mui/icons-material/Add";
import { listSongs, createSong, getSong } from "../lib/api";
import type { components } from "../types/api";

type Song = components["schemas"]["SongResponse"];
type SongDetail = components["schemas"]["SongDetailResponse"];
type Track = components["schemas"]["TrackResponse"];
type Loop = components["schemas"]["LoopResponse"];

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

  // Create loop modal state
  const [showCreateLoopModal, setShowCreateLoopModal] = useState(false);
  const [selectedTrackId, setSelectedTrackId] = useState<string | null>(null);

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
            // Auto-select first song
            setSelectedSongId(result.data[0].id);
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
    setSelectedTrackId(trackId);
    setShowCreateLoopModal(true);
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
              songs.map((song) => (
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
                      }}
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

      {/* Create Loop Modal (Placeholder) */}
      <Modal
        open={showCreateLoopModal}
        onClose={() => setShowCreateLoopModal(false)}
        aria-labelledby="create-loop-modal-title"
      >
        <Box
          sx={{
            position: "absolute",
            top: "50%",
            left: "50%",
            transform: "translate(-50%, -50%)",
            width: 600,
            bgcolor: "background.paper",
            boxShadow: 24,
            p: 4,
            borderRadius: 2,
          }}
        >
          <Typography id="create-loop-modal-title" variant="h6" component="h2" gutterBottom>
            Create Loop
          </Typography>
          <Typography sx={{ mb: 3 }}>
            Track ID: {selectedTrackId}
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            (Placeholder modal - loop creation coming soon)
          </Typography>
          <Button
            variant="contained"
            fullWidth
            onClick={() => setShowCreateLoopModal(false)}
          >
            Close
          </Button>
        </Box>
      </Modal>
    </Box>
  );
}
