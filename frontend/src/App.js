import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { Box } from '@mui/material';

// Components
import DashboardLayout from './components/DashboardLayout';
import Dashboard from './components/Dashboard';
import PlayerManagement from './components/PlayerManagement';
import LoadoutManagement from './components/LoadoutManagement';
import GuildManagement from './components/GuildManagement';

// Create Material-UI theme
const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
    background: {
      default: '#f5f5f5',
    },
  },
});

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Router>
        <Box sx={{ display: 'flex' }}>
          <DashboardLayout>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/players" element={<PlayerManagement />} />
              <Route path="/loadouts" element={<LoadoutManagement />} />
              <Route path="/guilds" element={<GuildManagement />} />
            </Routes>
          </DashboardLayout>
        </Box>
      </Router>
    </ThemeProvider>
  );
}

export default App;
