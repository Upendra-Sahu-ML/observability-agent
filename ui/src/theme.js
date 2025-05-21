import { createTheme } from '@mui/material/styles';

// Create a theme instance with proper color palette configuration
const theme = createTheme({
  palette: {
    primary: {
      main: '#1976d2',
      light: '#42a5f5',
      dark: '#1565c0',
      contrastText: '#ffffff',
    },
    secondary: {
      main: '#9c27b0',
      light: '#ba68c8',
      dark: '#7b1fa2',
      contrastText: '#ffffff',
    },
    error: {
      main: '#d32f2f',
      light: '#ef5350',
      dark: '#c62828',
      contrastText: '#ffffff',
    },
    warning: {
      main: '#ed6c02',
      light: '#ff9800',
      dark: '#e65100',
      contrastText: '#ffffff',
    },
    info: {
      main: '#0288d1',
      light: '#03a9f4',
      dark: '#01579b',
      contrastText: '#ffffff',
    },
    success: {
      main: '#2e7d32',
      light: '#4caf50',
      dark: '#1b5e20',
      contrastText: '#ffffff',
    },
    default: {
      main: '#9e9e9e',
      light: '#bdbdbd',
      dark: '#757575',
      contrastText: '#ffffff',
    },
    background: {
      default: '#f5f5f5',
      paper: '#ffffff',
    },
    text: {
      primary: 'rgba(0, 0, 0, 0.87)',
      secondary: 'rgba(0, 0, 0, 0.6)',
      disabled: 'rgba(0, 0, 0, 0.38)',
    },
  },
  typography: {
    fontFamily: [
      '-apple-system',
      'BlinkMacSystemFont',
      '"Segoe UI"',
      'Roboto',
      '"Helvetica Neue"',
      'Arial',
      'sans-serif',
      '"Apple Color Emoji"',
      '"Segoe UI Emoji"',
      '"Segoe UI Symbol"',
    ].join(','),
  },
  components: {
    MuiTimelineDot: {
      styleOverrides: {
        root: {
          margin: 0,
          padding: 0,
        },
        filled: {
          boxShadow: '0px 2px 4px rgba(0, 0, 0, 0.1)',
        },
        outlined: {
          boxShadow: 'none',
        },
      },
      variants: [
        {
          props: { color: 'success' },
          style: {
            backgroundColor: '#2e7d32',
            color: '#ffffff',
          },
        },
        {
          props: { color: 'error' },
          style: {
            backgroundColor: '#d32f2f',
            color: '#ffffff',
          },
        },
        {
          props: { color: 'warning' },
          style: {
            backgroundColor: '#ed6c02',
            color: '#ffffff',
          },
        },
        {
          props: { color: 'info' },
          style: {
            backgroundColor: '#0288d1',
            color: '#ffffff',
          },
        },
        {
          props: { color: 'default' },
          style: {
            backgroundColor: '#9e9e9e',
            color: '#ffffff',
          },
        },
      ],
    },
  },
});

export default theme;
