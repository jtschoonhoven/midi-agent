import { useMemo } from "react";
import { ThemeProvider, CssBaseline, useMediaQuery } from "@mui/material";
import { DndProvider } from "react-dnd";
import { HTML5Backend } from "react-dnd-html5-backend";
import ChatInterface from "./components/ChatInterface";
import { lightTheme, darkTheme } from "./theme";
import { PlaybackProvider } from "./contexts/PlaybackContext";

function App() {
  const prefersDarkMode = useMediaQuery("(prefers-color-scheme: dark)");

  const theme = useMemo(() => (prefersDarkMode ? darkTheme : lightTheme), [prefersDarkMode]);

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <DndProvider backend={HTML5Backend}>
        <PlaybackProvider>
          <ChatInterface />
        </PlaybackProvider>
      </DndProvider>
    </ThemeProvider>
  );
}

export default App;
