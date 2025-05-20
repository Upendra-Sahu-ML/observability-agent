import React, { useState, useEffect, useRef } from 'react';
import {
  Container,
  Typography,
  Box,
  Paper,
  TextField,
  Button,
  IconButton,
  Divider,
  CircularProgress,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  ListItemSecondaryAction,
  Snackbar,
  Menu,
  MenuItem,
  Tooltip,
  Chip
} from '@mui/material';
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  PlayArrow as PlayArrowIcon,
  Save as SaveIcon,
  Folder as FolderIcon,
  Download as DownloadIcon,
  MoreVert as MoreVertIcon,
  ContentCopy as ContentCopyIcon,
  Info as InfoIcon,
  Refresh as RefreshIcon
} from '@mui/icons-material';
import api from '../api';

// Create a separate API instance for the K8s command backend
const k8sApi = api.create({
  baseURL: process.env.NODE_ENV === 'production' ? '/k8s-api' : 'http://localhost:5002/api'
});

export default function K8sCommand() {
  // State for notebook
  const [notebook, setNotebook] = useState({
    name: 'Untitled Notebook',
    description: '',
    cells: [{ type: 'command', content: '', executedCommand: '', timestamp: new Date() }]
  });

  // State for UI
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [saveDialogOpen, setSaveDialogOpen] = useState(false);
  const [loadDialogOpen, setLoadDialogOpen] = useState(false);
  const [notebooks, setNotebooks] = useState([]);
  const [notification, setNotification] = useState({ open: false, message: '', severity: 'info' });
  const [exportDialogOpen, setExportDialogOpen] = useState(false);
  const [exportService, setExportService] = useState('');
  const [contextDialogOpen, setContextDialogOpen] = useState(false);

  // Session context state
  const [sessionId, setSessionId] = useState(null);
  const [contextData, setContextData] = useState(null);

  // Ref for auto-scrolling
  const bottomRef = useRef(null);

  // Menu state
  const [menuAnchorEl, setMenuAnchorEl] = useState(null);
  const [selectedCellIndex, setSelectedCellIndex] = useState(null);

  // Load notebooks on component mount
  useEffect(() => {
    fetchNotebooks();
  }, []);

  // Auto-scroll to bottom when cells are added
  useEffect(() => {
    if (bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [notebook.cells.length]);

  // Fetch all notebooks
  const fetchNotebooks = async () => {
    try {
      const response = await k8sApi.get('/notebooks');
      setNotebooks(response.data);
    } catch (err) {
      console.error('Error fetching notebooks:', err);
      setNotification({
        open: true,
        message: `Error fetching notebooks: ${err.message}`,
        severity: 'error'
      });
    }
  };

  // Handle cell content change
  const handleCellChange = (index, content) => {
    const updatedCells = [...notebook.cells];
    updatedCells[index] = { ...updatedCells[index], content };
    setNotebook({ ...notebook, cells: updatedCells });
  };

  // Add a new cell
  const addCell = (index) => {
    const newCells = [...notebook.cells];
    newCells.splice(index + 1, 0, { type: 'command', content: '', executedCommand: '', timestamp: new Date() });
    setNotebook({ ...notebook, cells: newCells });
  };

  // Delete a cell
  const deleteCell = (index) => {
    if (notebook.cells.length === 1) {
      // Don't delete the last cell, just clear it
      handleCellChange(index, '');
      return;
    }

    const newCells = [...notebook.cells];
    newCells.splice(index, 1);
    setNotebook({ ...notebook, cells: newCells });
  };

  // Execute a cell
  const executeCell = async (index) => {
    try {
      setLoading(true);
      setError(null);

      const cell = notebook.cells[index];

      // Convert natural language to K8s command with session context
      const convertResponse = await k8sApi.post('/convert', {
        text: cell.content,
        sessionId: sessionId
      });

      const command = convertResponse.data.command;

      // Update session ID if it's new
      if (!sessionId && convertResponse.data.sessionId) {
        setSessionId(convertResponse.data.sessionId);
      }

      // Execute the command with session context
      const executeResponse = await k8sApi.post('/execute', {
        command,
        sessionId: convertResponse.data.sessionId || sessionId
      });

      // Update session ID if needed
      if (executeResponse.data.sessionId && (!sessionId || sessionId !== executeResponse.data.sessionId)) {
        setSessionId(executeResponse.data.sessionId);
      }

      // Update the cell with the result
      const updatedCells = [...notebook.cells];
      updatedCells[index] = { ...updatedCells[index], executedCommand: command };

      // Add a result cell if it doesn't exist
      if (index + 1 >= updatedCells.length || updatedCells[index + 1].type !== 'result') {
        updatedCells.splice(index + 1, 0, {
          type: 'result',
          content: executeResponse.data.success
            ? executeResponse.data.output
            : `Error: ${executeResponse.data.error}`,
          timestamp: new Date()
        });
      } else {
        // Update existing result cell
        updatedCells[index + 1] = {
          ...updatedCells[index + 1],
          content: executeResponse.data.success
            ? executeResponse.data.output
            : `Error: ${executeResponse.data.error}`,
          timestamp: new Date()
        };
      }

      setNotebook({ ...notebook, cells: updatedCells });
    } catch (err) {
      console.error('Error executing cell:', err);
      setError(`Error executing command: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Save notebook
  const saveNotebook = async () => {
    try {
      setLoading(true);

      // Validate and clean up cells before saving
      const cleanedCells = notebook.cells.map(cell => {
        // Ensure content is never empty (MongoDB validation requires this)
        return {
          ...cell,
          content: cell.content || ' ' // Use a space if content is empty
        };
      });

      const notebookToSave = {
        ...notebook,
        cells: cleanedCells
      };

      if (notebook._id) {
        // Update existing notebook
        const response = await k8sApi.put(`/notebooks/${notebook._id}`, notebookToSave);
        setNotebook(response.data);
        setNotification({
          open: true,
          message: 'Notebook updated successfully',
          severity: 'success'
        });
      } else {
        // Create new notebook
        const response = await k8sApi.post('/notebooks', notebookToSave);
        setNotebook(response.data);
        setNotification({
          open: true,
          message: 'Notebook saved successfully',
          severity: 'success'
        });
      }

      // Refresh notebooks list
      fetchNotebooks();
      setSaveDialogOpen(false);
    } catch (err) {
      console.error('Error saving notebook:', err);
      setNotification({
        open: true,
        message: `Error saving notebook: ${err.message}`,
        severity: 'error'
      });
    } finally {
      setLoading(false);
    }
  };

  // Load notebook
  const loadNotebook = async (id) => {
    try {
      setLoading(true);

      const response = await k8sApi.get(`/notebooks/${id}`);
      setNotebook(response.data);

      // Reset session ID to create a new context for the loaded notebook
      setSessionId(null);

      setLoadDialogOpen(false);
      setNotification({
        open: true,
        message: 'Notebook loaded successfully with fresh context',
        severity: 'success'
      });
    } catch (err) {
      console.error('Error loading notebook:', err);
      setNotification({
        open: true,
        message: `Error loading notebook: ${err.message}`,
        severity: 'error'
      });
    } finally {
      setLoading(false);
    }
  };

  // Export notebook as runbook
  const exportAsRunbook = async () => {
    try {
      setLoading(true);

      if (!notebook._id) {
        // Save notebook first if it's not saved
        const response = await k8sApi.post('/notebooks', notebook);
        setNotebook(response.data);
      }

      // Export as runbook
      await k8sApi.post(`/notebooks/${notebook._id}/export`, {
        service: exportService
      });

      setExportDialogOpen(false);
      setNotification({
        open: true,
        message: 'Notebook exported as runbook successfully',
        severity: 'success'
      });
    } catch (err) {
      console.error('Error exporting notebook:', err);
      setNotification({
        open: true,
        message: `Error exporting notebook: ${err.message}`,
        severity: 'error'
      });
    } finally {
      setLoading(false);
    }
  };

  // Create a new notebook
  const createNewNotebook = () => {
    // Reset notebook
    setNotebook({
      name: 'Untitled Notebook',
      description: '',
      cells: [{ type: 'command', content: '', executedCommand: '', timestamp: new Date() }]
    });

    // Reset session ID to create a new context
    setSessionId(null);

    setNotification({
      open: true,
      message: 'Created new notebook with fresh context',
      severity: 'info'
    });
  };

  // Open cell menu
  const openCellMenu = (event, index) => {
    setMenuAnchorEl(event.currentTarget);
    setSelectedCellIndex(index);
  };

  // Close cell menu
  const closeCellMenu = () => {
    setMenuAnchorEl(null);
    setSelectedCellIndex(null);
  };

  // Copy cell content to clipboard
  const copyCellContent = () => {
    if (selectedCellIndex !== null) {
      navigator.clipboard.writeText(notebook.cells[selectedCellIndex].content);
      setNotification({
        open: true,
        message: 'Cell content copied to clipboard',
        severity: 'success'
      });
    }
    closeCellMenu();
  };

  // Fetch context data
  const fetchContextData = async () => {
    if (!sessionId) {
      setNotification({
        open: true,
        message: 'No active context. Run a command first to establish context.',
        severity: 'info'
      });
      return;
    }

    try {
      setLoading(true);
      const response = await k8sApi.get(`/context/${sessionId}`);
      setContextData(response.data.context);
      setContextDialogOpen(true);
    } catch (err) {
      console.error('Error fetching context:', err);
      setNotification({
        open: true,
        message: `Error fetching context: ${err.message}`,
        severity: 'error'
      });
    } finally {
      setLoading(false);
    }
  };

  // Reset context
  const resetContext = () => {
    setSessionId(null);
    setContextData(null);
    setContextDialogOpen(false);
    setNotification({
      open: true,
      message: 'Context has been reset',
      severity: 'success'
    });
  };

  return (
    <Container sx={{ mt: 4, mb: 8 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          <Typography variant="h4">
            {notebook.name}
          </Typography>

          {sessionId && (
            <Tooltip title="Context is active - commands will maintain context between executions">
              <Box
                sx={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  ml: 2,
                  bgcolor: 'success.light',
                  color: 'success.contrastText',
                  px: 1,
                  py: 0.5,
                  borderRadius: 1,
                  fontSize: '0.75rem',
                  cursor: 'pointer'
                }}
                onClick={fetchContextData}
              >
                Context Active
              </Box>
            </Tooltip>
          )}
        </Box>

        <Box>
          {sessionId && (
            <>
              <Tooltip title="View Current Context">
                <IconButton onClick={fetchContextData} color="info">
                  <InfoIcon />
                </IconButton>
              </Tooltip>

              <Tooltip title="Reset Context">
                <IconButton onClick={resetContext} color="warning">
                  <RefreshIcon />
                </IconButton>
              </Tooltip>
            </>
          )}

          <Tooltip title="New Notebook">
            <IconButton onClick={createNewNotebook} color="primary">
              <AddIcon />
            </IconButton>
          </Tooltip>

          <Tooltip title="Save Notebook">
            <IconButton onClick={() => setSaveDialogOpen(true)} color="primary">
              <SaveIcon />
            </IconButton>
          </Tooltip>

          <Tooltip title="Load Notebook">
            <IconButton onClick={() => setLoadDialogOpen(true)} color="primary">
              <FolderIcon />
            </IconButton>
          </Tooltip>

          <Tooltip title="Export as Runbook">
            <IconButton onClick={() => setExportDialogOpen(true)} color="primary">
              <DownloadIcon />
            </IconButton>
          </Tooltip>
        </Box>
      </Box>

      {notebook.description && (
        <Typography variant="body1" sx={{ mb: 2 }}>
          {notebook.description}
        </Typography>
      )}

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {/* Notebook cells */}
      <Box sx={{ mb: 4 }}>
        {notebook.cells.map((cell, index) => (
          <Paper
            key={index}
            elevation={1}
            sx={{
              mb: 2,
              p: 2,
              backgroundColor: cell.type === 'result' ? '#f5f5f5' : 'white',
              borderLeft: cell.type === 'result' ? '4px solid #2196f3' : 'none'
            }}
          >
            {cell.type === 'command' ? (
              <>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <Typography variant="caption" sx={{ mr: 1 }}>
                    In [{index + 1}]:
                  </Typography>

                  <Box sx={{ flexGrow: 1 }} />

                  <IconButton
                    size="small"
                    onClick={(e) => openCellMenu(e, index)}
                  >
                    <MoreVertIcon fontSize="small" />
                  </IconButton>

                  <IconButton
                    size="small"
                    onClick={() => executeCell(index)}
                    disabled={loading || !cell.content.trim()}
                    color="primary"
                  >
                    {loading ? <CircularProgress size={20} /> : <PlayArrowIcon fontSize="small" />}
                  </IconButton>

                  <IconButton
                    size="small"
                    onClick={() => addCell(index)}
                  >
                    <AddIcon fontSize="small" />
                  </IconButton>

                  <IconButton
                    size="small"
                    onClick={() => deleteCell(index)}
                  >
                    <DeleteIcon fontSize="small" />
                  </IconButton>
                </Box>

                <TextField
                  fullWidth
                  multiline
                  variant="outlined"
                  placeholder="Enter Kubernetes command in natural language..."
                  value={cell.content}
                  onChange={(e) => handleCellChange(index, e.target.value)}
                  sx={{ mb: 1 }}
                />

                {cell.executedCommand && (
                  <Box sx={{ mt: 1 }}>
                    <Typography variant="caption" color="text.secondary">
                      Executed command:
                    </Typography>
                    <Paper variant="outlined" sx={{ p: 1, backgroundColor: '#f8f9fa' }}>
                      <code>{cell.executedCommand}</code>
                    </Paper>
                  </Box>
                )}
              </>
            ) : (
              <>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <Typography variant="caption" sx={{ mr: 1 }}>
                    Out [{index}]:
                  </Typography>

                  <Box sx={{ flexGrow: 1 }} />

                  <IconButton
                    size="small"
                    onClick={(e) => openCellMenu(e, index)}
                  >
                    <MoreVertIcon fontSize="small" />
                  </IconButton>

                  <IconButton
                    size="small"
                    onClick={() => deleteCell(index)}
                  >
                    <DeleteIcon fontSize="small" />
                  </IconButton>
                </Box>

                <Paper
                  variant="outlined"
                  sx={{
                    p: 1,
                    backgroundColor: '#f8f9fa',
                    maxHeight: '300px',
                    overflow: 'auto',
                    whiteSpace: 'pre-wrap',
                    fontFamily: 'monospace'
                  }}
                >
                  {cell.content}
                </Paper>
              </>
            )}
          </Paper>
        ))}

        <div ref={bottomRef} />

        <Button
          startIcon={<AddIcon />}
          onClick={() => addCell(notebook.cells.length - 1)}
          sx={{ mt: 2 }}
        >
          Add Cell
        </Button>
      </Box>

      {/* Cell Menu */}
      <Menu
        anchorEl={menuAnchorEl}
        open={Boolean(menuAnchorEl)}
        onClose={closeCellMenu}
      >
        <MenuItem onClick={copyCellContent}>
          <ContentCopyIcon fontSize="small" sx={{ mr: 1 }} />
          Copy Content
        </MenuItem>
      </Menu>

      {/* Save Dialog */}
      <Dialog open={saveDialogOpen} onClose={() => setSaveDialogOpen(false)}>
        <DialogTitle>Save Notebook</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Notebook Name"
            fullWidth
            value={notebook.name}
            onChange={(e) => setNotebook({ ...notebook, name: e.target.value })}
          />
          <TextField
            margin="dense"
            label="Description"
            fullWidth
            multiline
            rows={3}
            value={notebook.description}
            onChange={(e) => setNotebook({ ...notebook, description: e.target.value })}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSaveDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={saveNotebook}
            variant="contained"
            color="primary"
            disabled={loading || !notebook.name.trim()}
          >
            {loading ? <CircularProgress size={24} /> : 'Save'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Load Dialog */}
      <Dialog
        open={loadDialogOpen}
        onClose={() => setLoadDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>Load Notebook</DialogTitle>
        <DialogContent>
          {notebooks.length === 0 ? (
            <Alert severity="info">No saved notebooks found</Alert>
          ) : (
            <List>
              {notebooks.map((nb) => (
                <ListItem
                  key={nb._id}
                  disablePadding
                >
                  <ListItemButton
                    onClick={() => loadNotebook(nb._id)}
                  >
                    <ListItemText
                      primary={nb.name}
                      secondary={`${nb.description || 'No description'} • Last updated: ${new Date(nb.updatedAt).toLocaleString()}`}
                    />
                  </ListItemButton>
                  <ListItemSecondaryAction>
                    <Typography variant="caption">
                      {nb.cells.length} cells
                    </Typography>
                  </ListItemSecondaryAction>
                </ListItem>
              ))}
            </List>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setLoadDialogOpen(false)}>Cancel</Button>
        </DialogActions>
      </Dialog>

      {/* Export Dialog */}
      <Dialog open={exportDialogOpen} onClose={() => setExportDialogOpen(false)}>
        <DialogTitle>Export as Runbook</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Service Name (optional)"
            fullWidth
            value={exportService}
            onChange={(e) => setExportService(e.target.value)}
            helperText="Specify a service name for this runbook"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setExportDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={exportAsRunbook}
            variant="contained"
            color="primary"
            disabled={loading}
          >
            {loading ? <CircularProgress size={24} /> : 'Export'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Context Dialog */}
      <Dialog
        open={contextDialogOpen}
        onClose={() => setContextDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          Command Context
          <IconButton
            aria-label="close"
            onClick={() => setContextDialogOpen(false)}
            sx={{
              position: 'absolute',
              right: 8,
              top: 8,
            }}
          >
            <DeleteIcon />
          </IconButton>
        </DialogTitle>
        <DialogContent>
          {contextData ? (
            <Box>
              <DialogContentText>
                This is the current context that will be used for command execution. The system will use this information to maintain context between commands.
              </DialogContentText>

              <Box sx={{ mt: 2 }}>
                <Typography variant="subtitle1" fontWeight="bold">Last Command:</Typography>
                {contextData.lastCommand ? (
                  <Paper variant="outlined" sx={{ p: 1, bgcolor: '#f8f9fa', fontFamily: 'monospace', mb: 2 }}>
                    {contextData.lastCommand}
                  </Paper>
                ) : (
                  <Typography variant="body2" color="text.secondary">No previous command</Typography>
                )}

                <Typography variant="subtitle1" fontWeight="bold">Current Namespace:</Typography>
                {contextData.lastNamespace ? (
                  <Chip label={contextData.lastNamespace} color="primary" sx={{ mb: 2 }} />
                ) : (
                  <Typography variant="body2" color="text.secondary">No namespace set (will search across all namespaces)</Typography>
                )}

                {contextData.lastPods && contextData.lastPods.length > 0 && (
                  <Box sx={{ mb: 2 }}>
                    <Typography variant="subtitle1" fontWeight="bold">Recent Pods:</Typography>
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                      {contextData.lastPods.map((pod, index) => (
                        <Chip
                          key={index}
                          label={pod.name}
                          color={pod.status === 'Running' ? 'success' : 'warning'}
                          variant="outlined"
                        />
                      ))}
                    </Box>
                  </Box>
                )}

                {contextData.lastServices && contextData.lastServices.length > 0 && (
                  <Box sx={{ mb: 2 }}>
                    <Typography variant="subtitle1" fontWeight="bold">Recent Services:</Typography>
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                      {contextData.lastServices.map((svc, index) => (
                        <Chip
                          key={index}
                          label={svc.name}
                          color="info"
                          variant="outlined"
                        />
                      ))}
                    </Box>
                  </Box>
                )}

                {contextData.lastDeployments && contextData.lastDeployments.length > 0 && (
                  <Box sx={{ mb: 2 }}>
                    <Typography variant="subtitle1" fontWeight="bold">Recent Deployments:</Typography>
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                      {contextData.lastDeployments.map((deploy, index) => (
                        <Chip
                          key={index}
                          label={deploy.name}
                          color="secondary"
                          variant="outlined"
                        />
                      ))}
                    </Box>
                  </Box>
                )}
              </Box>
            </Box>
          ) : (
            <CircularProgress />
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={resetContext} color="warning">Reset Context</Button>
          <Button onClick={() => setContextDialogOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>

      {/* Notification Snackbar */}
      <Snackbar
        open={notification.open}
        autoHideDuration={6000}
        onClose={() => setNotification({ ...notification, open: false })}
      >
        <Alert
          onClose={() => setNotification({ ...notification, open: false })}
          severity={notification.severity}
        >
          {notification.message}
        </Alert>
      </Snackbar>
    </Container>
  );
}
