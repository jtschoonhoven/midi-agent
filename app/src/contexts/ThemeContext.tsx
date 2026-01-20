import { createContext, useContext, useState, useEffect, type ReactNode } from "react";

type ThemeMode = "light" | "dark" | null; // null means use system default

interface ThemeContextType {
  themeMode: ThemeMode;
  setThemeMode: (mode: "light" | "dark") => void;
  clearThemeMode: () => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [themeMode, setThemeModeState] = useState<ThemeMode>(() => {
    // Load from localStorage or default to null (system)
    const stored = localStorage.getItem("themeMode");
    if (stored === "light" || stored === "dark") {
      return stored;
    }
    return null;
  });

  useEffect(() => {
    // Save to localStorage whenever it changes
    if (themeMode === null) {
      localStorage.removeItem("themeMode");
    } else {
      localStorage.setItem("themeMode", themeMode);
    }
  }, [themeMode]);

  const setThemeMode = (mode: "light" | "dark") => {
    setThemeModeState(mode);
  };

  const clearThemeMode = () => {
    setThemeModeState(null);
  };

  return (
    <ThemeContext.Provider value={{ themeMode, setThemeMode, clearThemeMode }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useThemeMode() {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error("useThemeMode must be used within a ThemeProvider");
  }
  return context;
}
