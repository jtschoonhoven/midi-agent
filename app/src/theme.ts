import { createTheme } from "@mui/material/styles";

export const lightTheme = createTheme({
  palette: {
    mode: "light",
    primary: {
      main: "#646cff",
    },
    background: {
      default: "#ffffff",
      paper: "#f8f9fa",
    },
  },
});

export const darkTheme = createTheme({
  palette: {
    mode: "dark",
    primary: {
      main: "#646cff",
    },
    background: {
      default: "#1a1a1a",
      paper: "#242424",
    },
  },
});
