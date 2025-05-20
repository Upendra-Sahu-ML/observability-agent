import React from 'react';
import { Routes, Route } from 'react-router-dom';
import { Box, Toolbar } from '@mui/material';
import Navbar from './components/Navbar';
import Dashboard from './pages/Dashboard';
import Agents from './pages/Agents';
import Metrics from './pages/Metrics';
import Logs from './pages/Logs';
import Deployment from './pages/Deployment';
import RootCause from './pages/RootCause';
import Tracing from './pages/Tracing';
import Notification from './pages/Notification';
import Postmortem from './pages/Postmortem';
import Runbook from './pages/Runbook';
import RunbookManager from './pages/RunbookManager';
import AlertHistory from './pages/AlertHistory';
import KnowledgeBase from './pages/KnowledgeBase';
import K8sCommand from './pages/K8sCommand';

// Drawer width - should match the one in Navbar.js
const drawerWidth = 240;

function App() {
  return (
    <Box sx={{ display: 'flex' }}>
      <Navbar />
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: 3,
          width: { sm: `calc(100% - ${drawerWidth}px)` },
          ml: { sm: `${drawerWidth}px` },
        }}
      >
        <Toolbar /> {/* This empty toolbar creates space below the AppBar */}
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/agents" element={<Agents />} />
          <Route path="/metrics" element={<Metrics />} />
          <Route path="/logs" element={<Logs />} />
          <Route path="/deployment" element={<Deployment />} />
          <Route path="/rootcause" element={<RootCause />} />
          <Route path="/tracing" element={<Tracing />} />
          <Route path="/notification" element={<Notification />} />
          <Route path="/postmortem" element={<Postmortem />} />
          <Route path="/runbook" element={<Runbook />} />
          <Route path="/runbook-manager" element={<RunbookManager />} />
          <Route path="/alerts" element={<AlertHistory />} />
          <Route path="/knowledge-base" element={<KnowledgeBase />} />
          <Route path="/k8s-command" element={<K8sCommand />} />
        </Routes>
      </Box>
    </Box>
  );
}

export default App;
