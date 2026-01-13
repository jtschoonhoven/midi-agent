import { useMemo } from 'react'
import { ThemeProvider, CssBaseline, useMediaQuery } from '@mui/material'
import ChatInterface from './components/ChatInterface'
import { lightTheme, darkTheme } from './theme'

function App() {
  const prefersDarkMode = useMediaQuery('(prefers-color-scheme: dark)')

  const theme = useMemo(
    () => (prefersDarkMode ? darkTheme : lightTheme),
    [prefersDarkMode]
  )

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <ChatInterface />
    </ThemeProvider>
  )
}

export default App
