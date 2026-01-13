import { useState, useEffect } from "react";
import {
  Box,
  Container,
  Card,
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
} from "@mui/material";
import MenuIcon from "@mui/icons-material/Menu";
import CloseIcon from "@mui/icons-material/Close";
import { listSongs, createSong } from "../lib/api";
import type { components } from "../types/api";

type Song = components["schemas"]["SongResponse"];

export default function ChatInterface() {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [songs, setSongs] = useState<Song[]>([]);
  const [isLoadingSongs, setIsLoadingSongs] = useState(true);
  const [showNewSongModal, setShowNewSongModal] = useState(false);
  const [isCreatingSong, setIsCreatingSong] = useState(false);

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
                  <ListItemButton onClick={toggleDrawer(false)}>
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
            MIDI Agent
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
        {/* 2-column layout */}
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: {
              xs: "1fr 2fr", // Small screens: 1/3 + 2/3
              md: "1fr 5fr", // Medium+ screens: 1/6 + 5/6
            },
            gap: 2,
            height: "100%",
          }}
        >
          {/* Left column */}
          <Box>
            <Card
              sx={{
                height: "100px",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                p: 2,
              }}
            >
              <Typography variant="body2" color="text.secondary">
                Left Column Card
              </Typography>
            </Card>
          </Box>

          {/* Right column */}
          <Box>
            <Card
              sx={{
                height: "100px",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                p: 2,
              }}
            >
              <Typography variant="body2" color="text.secondary">
                Right Column Card
              </Typography>
            </Card>
          </Box>
        </Box>
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
    </Box>
  );
}
