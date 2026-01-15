import { useMemo } from "react";
import { ThemeProvider, CssBaseline, useMediaQuery } from "@mui/material";
import ChatInterface from "./components/ChatInterface";
import { lightTheme, darkTheme } from "./theme";
import { PlaybackProvider } from "./contexts/PlaybackContext";

function App() {
  const prefersDarkMode = useMediaQuery("(prefers-color-scheme: dark)");

  const theme = useMemo(() => (prefersDarkMode ? darkTheme : lightTheme), [prefersDarkMode]);

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <PlaybackProvider>
        <ChatInterface />
      </PlaybackProvider>
    </ThemeProvider>
  );
}

export default App;
