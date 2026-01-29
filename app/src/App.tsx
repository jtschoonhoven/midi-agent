import { useMemo, useState, useEffect } from "react";
import { ThemeProvider as MuiThemeProvider, CssBaseline, useMediaQuery } from "@mui/material";
import { DndProvider } from "react-dnd";
import { HTML5Backend } from "react-dnd-html5-backend";
import ChatInterface from "./components/ChatInterface";
import ApiKeyModal from "./components/ApiKeyModal";
import { lightTheme, darkTheme } from "./theme";
import { PlaybackProvider } from "./contexts/PlaybackContext";
import { ThemeProvider, useThemeMode } from "./contexts/ThemeContext";
import { hasStoredApiKey, storeApiKey } from "./lib/auth";

function AppContent() {
  const { themeMode } = useThemeMode();
  const prefersDarkMode = useMediaQuery("(prefers-color-scheme: dark)");
  const [showApiKeyModal, setShowApiKeyModal] = useState(false);

  useEffect(() => {
    // Check if API key is stored on mount
    if (!hasStoredApiKey()) {
      setShowApiKeyModal(true);
    }
  }, []);

  const handleApiKeySubmit = (apiKey: string) => {
    storeApiKey(apiKey);
    setShowApiKeyModal(false);
  };

  const theme = useMemo(() => {
    // If user has selected a theme, use it
    if (themeMode === "light") return lightTheme;
    if (themeMode === "dark") return darkTheme;
    // Otherwise use system default
    return prefersDarkMode ? darkTheme : lightTheme;
  }, [themeMode, prefersDarkMode]);

  return (
    <MuiThemeProvider theme={theme}>
      <CssBaseline />
      <ApiKeyModal open={showApiKeyModal} onSubmit={handleApiKeySubmit} />
      {!showApiKeyModal && (
        <DndProvider backend={HTML5Backend}>
          <PlaybackProvider>
            <ChatInterface />
          </PlaybackProvider>
        </DndProvider>
      )}
    </MuiThemeProvider>
  );
}

function App() {
  return (
    <ThemeProvider>
      <AppContent />
    </ThemeProvider>
  );
}

export default App;
