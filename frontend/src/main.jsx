import React from 'react'
import ReactDOM from 'react-dom/client'
import { ThemeProvider, createTheme, CssBaseline } from '@mui/material'
import App from './App'

const theme = createTheme({
  palette: {
    primary: {
      main: '#4a7c59',
      light: '#7aad8a',
      dark: '#2f5c3d',
      contrastText: '#fff',
    },
    secondary: {
      main: '#b5663a',
      light: '#d4886a',
      dark: '#8a4220',
      contrastText: '#fff',
    },
    background: {
      default: '#f4efe6',
      paper: '#fdfaf4',
    },
    text: {
      primary: '#2d2416',
      secondary: '#6b5f4e',
    },
    success: {
      main: '#5a7a52',
    },
    divider: '#ddd5c4',
  },
  typography: {
    fontFamily: '"Lato", "Helvetica Neue", Arial, sans-serif',
    h1: { fontFamily: '"Playfair Display", Georgia, serif' },
    h2: { fontFamily: '"Playfair Display", Georgia, serif' },
    h3: { fontFamily: '"Playfair Display", Georgia, serif' },
    h4: { fontFamily: '"Playfair Display", Georgia, serif' },
    h5: { fontFamily: '"Playfair Display", Georgia, serif' },
    h6: { fontFamily: '"Playfair Display", Georgia, serif' },
  },
  shape: {
    borderRadius: 10,
  },
  components: {
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: 'none',
        },
        elevation3: {
          boxShadow: '0 2px 12px rgba(74, 60, 30, 0.10)',
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          textTransform: 'none',
          fontWeight: 700,
          letterSpacing: '0.02em',
        },
        containedPrimary: {
          background: 'linear-gradient(135deg, #5a8a6a 0%, #4a7c59 100%)',
          '&:hover': {
            background: 'linear-gradient(135deg, #4a7c59 0%, #2f5c3d 100%)',
          },
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          borderRadius: 6,
        },
      },
    },
    MuiLinearProgress: {
      styleOverrides: {
        root: {
          borderRadius: 4,
          backgroundColor: '#d8e8dc',
        },
      },
    },
  },
})

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <App />
    </ThemeProvider>
  </React.StrictMode>
)
