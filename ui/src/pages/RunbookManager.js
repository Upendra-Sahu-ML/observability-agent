import React, { useState } from 'react';
import {
  Container,
  Typography,
  Paper,
  TextField,
  Button,
  Grid,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Alert,
  Snackbar,
  CircularProgress,
  Box,
  Divider,
  Card,
  CardContent,
  CardActions
} from '@mui/material';
import SyncIcon from '@mui/icons-material/Sync';
import BookmarkAddIcon from '@mui/icons-material/BookmarkAdd';
import api from '../api';

export default function RunbookManager() {
  // State for GitHub sync
  const [githubRepo, setGithubRepo] = useState('');
  const [githubBranch, setGithubBranch] = useState('main');
  const [githubPath, setGithubPath] = useState('runbooks');
  const [githubToken, setGithubToken] = useState('');
  
  // State for manual runbook addition
  const [runbookName, setRunbookName] = useState('');
  const [runbookService, setRunbookService] = useState('');
  const [runbookContent, setRunbookContent] = useState('');
  
  // UI state
  const [loading, setLoading] = useState(false);
  const [notification, setNotification] = useState({ open: false, message: '', severity: 'info' });
  
  const handleSyncFromGitHub = async () => {
    if (!githubRepo) {
      setNotification({
        open: true,
        message: 'GitHub repository is required',
        severity: 'error'
      });
      return;
    }
    
    setLoading(true);
    try {
      const response = await api.post('/api/runbook/sync', {
        source: 'github',
        repo: githubRepo,
        branch: githubBranch,
        path: githubPath,
        token: githubToken || undefined
      });
      
      setNotification({
        open: true,
        message: `Successfully synced ${response.data.count} runbooks from GitHub`,
        severity: 'success'
      });
    } catch (error) {
      setNotification({
        open: true,
        message: `Error syncing runbooks: ${error.response?.data?.message || error.message}`,
        severity: 'error'
      });
    } finally {
      setLoading(false);
    }
  };
  
  const handleAddRunbook = async () => {
    if (!runbookName || !runbookContent) {
      setNotification({
        open: true,
        message: 'Runbook name and content are required',
        severity: 'error'
      });
      return;
    }
    
    setLoading(true);
    try {
      await api.post('/api/runbook', {
        name: runbookName,
        service: runbookService,
        content: runbookContent
      });
      
      // Clear form
      setRunbookName('');
      setRunbookService('');
      setRunbookContent('');
      
      setNotification({
        open: true,
        message: 'Runbook added successfully',
        severity: 'success'
      });
    } catch (error) {
      setNotification({
        open: true,
        message: `Error adding runbook: ${error.response?.data?.message || error.message}`,
        severity: 'error'
      });
    } finally {
      setLoading(false);
    }
  };
  
  const handleCloseNotification = () => {
    setNotification({ ...notification, open: false });
  };
  
  return (
    <Container sx={{ mt: 4, mb: 4 }}>
      <Typography variant="h4" gutterBottom>
        Runbook Management
      </Typography>
      
      <Grid container spacing={3}>
        {/* GitHub Sync Section */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
                <SyncIcon sx={{ mr: 1 }} /> Sync Runbooks from GitHub
              </Typography>
              
              <TextField
                fullWidth
                label="GitHub Repository (owner/repo)"
                variant="outlined"
                margin="normal"
                value={githubRepo}
                onChange={(e) => setGithubRepo(e.target.value)}
                placeholder="e.g., username/repo"
              />
              
              <TextField
                fullWidth
                label="Branch"
                variant="outlined"
                margin="normal"
                value={githubBranch}
                onChange={(e) => setGithubBranch(e.target.value)}
              />
              
              <TextField
                fullWidth
                label="Path to Runbooks"
                variant="outlined"
                margin="normal"
                value={githubPath}
                onChange={(e) => setGithubPath(e.target.value)}
              />
              
              <TextField
                fullWidth
                label="GitHub Token (optional)"
                variant="outlined"
                margin="normal"
                type="password"
                value={githubToken}
                onChange={(e) => setGithubToken(e.target.value)}
                helperText="Required for private repositories"
              />
            </CardContent>
            <CardActions>
              <Button
                variant="contained"
                color="primary"
                startIcon={<SyncIcon />}
                onClick={handleSyncFromGitHub}
                disabled={loading}
              >
                {loading ? <CircularProgress size={24} /> : 'Sync Runbooks'}
              </Button>
            </CardActions>
          </Card>
        </Grid>
        
        {/* Manual Runbook Addition Section */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
                <BookmarkAddIcon sx={{ mr: 1 }} /> Add New Runbook
              </Typography>
              
              <TextField
                fullWidth
                label="Runbook Name"
                variant="outlined"
                margin="normal"
                value={runbookName}
                onChange={(e) => setRunbookName(e.target.value)}
                placeholder="e.g., HighCpuUsage"
              />
              
              <TextField
                fullWidth
                label="Service (optional)"
                variant="outlined"
                margin="normal"
                value={runbookService}
                onChange={(e) => setRunbookService(e.target.value)}
                placeholder="e.g., payment-service"
              />
              
              <TextField
                fullWidth
                label="Runbook Content (Markdown)"
                variant="outlined"
                margin="normal"
                multiline
                rows={10}
                value={runbookContent}
                onChange={(e) => setRunbookContent(e.target.value)}
                placeholder="# Runbook Title\n\n## Steps\n1. First step\n2. Second step\n3. Third step"
              />
            </CardContent>
            <CardActions>
              <Button
                variant="contained"
                color="primary"
                startIcon={<BookmarkAddIcon />}
                onClick={handleAddRunbook}
                disabled={loading}
              >
                {loading ? <CircularProgress size={24} /> : 'Add Runbook'}
              </Button>
            </CardActions>
          </Card>
        </Grid>
      </Grid>
      
      <Snackbar
        open={notification.open}
        autoHideDuration={6000}
        onClose={handleCloseNotification}
      >
        <Alert onClose={handleCloseNotification} severity={notification.severity}>
          {notification.message}
        </Alert>
      </Snackbar>
    </Container>
  );
}
