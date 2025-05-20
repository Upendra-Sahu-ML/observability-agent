import React, { useState, useEffect } from 'react';
import {
  Container,
  Typography,
  Card,
  CardContent,
  CardActions,
  Button,
  Grid,
  List,
  ListItem,
  ListItemText,
  ListItemButton,
  Divider,
  CircularProgress,
  Alert,
  Box,
  Paper,
  LinearProgress,
  Chip,
  Stepper,
  Step,
  StepLabel,
  StepContent
} from '@mui/material';
import api from '../api';

export default function Runbook() {
  const [runbooks, setRunbooks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedRunbook, setSelectedRunbook] = useState(null);
  const [executionStatus, setExecutionStatus] = useState({});
  const [executingRunbook, setExecutingRunbook] = useState(null);

  useEffect(() => {
    // Fetch runbooks from the API
    api.get('/runbook')
      .then(res => {
        console.log('Runbooks data:', res.data);
        setRunbooks(res.data);
      })
      .catch(err => {
        console.error('Error fetching runbooks:', err);
        setError(err.message || 'Error fetching runbooks');
      })
      .finally(() => setLoading(false));
  }, []);

  const handleRunbookSelect = (runbook) => {
    setSelectedRunbook(runbook);
  };

  const handleExecuteRunbook = async (runbookId) => {
    try {
      setExecutingRunbook(runbookId);
      setExecutionStatus(prev => ({
        ...prev,
        [runbookId]: { status: 'starting', progress: 0, message: 'Initializing execution...' }
      }));

      // Call the API to execute the runbook
      const response = await api.post(`/runbook/execute`, { runbookId });

      // Update execution status with the execution ID
      const executionId = response.data.executionId;
      setExecutionStatus(prev => ({
        ...prev,
        [runbookId]: {
          status: 'in_progress',
          progress: 10,
          message: 'Execution in progress...',
          executionId
        }
      }));

      // Start polling for status updates
      pollExecutionStatus(runbookId, executionId);
    } catch (err) {
      console.error('Error executing runbook:', err);
      setExecutionStatus(prev => ({
        ...prev,
        [runbookId]: { status: 'error', message: `Error: ${err.message}` }
      }));
    }
  };

  // Function to poll for execution status updates
  const pollExecutionStatus = (runbookId, executionId) => {
    const statusInterval = setInterval(async () => {
      try {
        const statusResponse = await api.get(`/runbook/status/${executionId}`);
        const status = statusResponse.data;

        setExecutionStatus(prev => ({
          ...prev,
          [runbookId]: {
            status: status.status,
            progress: status.progress || 0,
            message: getStatusMessage(status.status),
            steps: status.steps || [],
            executionId
          }
        }));

        // If execution is complete or failed, stop polling
        if (status.status === 'completed' || status.status === 'failed') {
          clearInterval(statusInterval);

          // Clear executing runbook after a delay
          setTimeout(() => {
            if (executingRunbook === runbookId) {
              setExecutingRunbook(null);
            }
          }, 5000);
        }
      } catch (err) {
        console.error('Error polling execution status:', err);
        // Don't stop polling on error, just log it
      }
    }, 3000); // Poll every 3 seconds

    // Store the interval ID to clear it if component unmounts
    return () => clearInterval(statusInterval);
  };

  // Helper function to get status message
  const getStatusMessage = (status) => {
    switch (status) {
      case 'starting':
        return 'Initializing execution...';
      case 'in_progress':
        return 'Execution in progress...';
      case 'completed':
        return 'Execution completed successfully!';
      case 'failed':
        return 'Execution failed. Check logs for details.';
      default:
        return 'Unknown status';
    }
  };

  return (
    <Container sx={{ mt: 4 }}>
      <Typography variant="h4" gutterBottom>
        Runbooks
      </Typography>

      {loading && <CircularProgress />}
      {error && <Alert severity="error">{error}</Alert>}

      {!loading && !error && (
        <Grid container spacing={3}>
          {/* Runbook List */}
          <Grid item xs={12} md={4}>
            <Paper elevation={2} sx={{ p: 2, height: '100%' }}>
              <Typography variant="h6" gutterBottom>
                Available Runbooks
              </Typography>
              {runbooks.length === 0 ? (
                <Alert severity="info">No runbooks available</Alert>
              ) : (
                <List>
                  {runbooks.map((runbook) => (
                    <React.Fragment key={runbook.id}>
                      <ListItem disablePadding>
                        <ListItemButton
                          onClick={() => handleRunbookSelect(runbook)}
                          selected={selectedRunbook && selectedRunbook.id === runbook.id}
                        >
                          <ListItemText
                            primary={runbook.title}
                            secondary={`Service: ${runbook.service}`}
                          />
                          {executionStatus[runbook.id] && (
                            <Chip
                              size="small"
                              label={executionStatus[runbook.id].status}
                              color={
                                executionStatus[runbook.id].status === 'completed' ? 'success' :
                                executionStatus[runbook.id].status === 'failed' ? 'error' :
                                executionStatus[runbook.id].status === 'in_progress' ? 'primary' : 'default'
                              }
                            />
                          )}
                        </ListItemButton>
                      </ListItem>
                      <Divider />
                    </React.Fragment>
                  ))}
                </List>
              )}
            </Paper>
          </Grid>

          {/* Runbook Details */}
          <Grid item xs={12} md={8}>
            {selectedRunbook ? (
              <Card>
                <CardContent>
                  <Typography variant="h5" component="div">
                    {selectedRunbook.title}
                  </Typography>
                  <Typography sx={{ mb: 1.5 }} color="text.secondary">
                    Service: {selectedRunbook.service}
                  </Typography>
                  <Typography variant="body2" sx={{ mb: 2 }}>
                    Last Updated: {new Date(selectedRunbook.updatedAt).toLocaleString()}
                  </Typography>

                  <Typography variant="h6" gutterBottom>
                    Steps:
                  </Typography>
                  <List>
                    {selectedRunbook.steps.map((step, index) => (
                      <ListItem key={index}>
                        <ListItemText primary={`${index + 1}. ${step}`} />
                      </ListItem>
                    ))}
                  </List>
                </CardContent>
                {/* Execution Status */}
                {executionStatus[selectedRunbook.id] && (
                  <Box sx={{ mt: 2, mb: 2, p: 2, bgcolor: 'background.paper', borderRadius: 1 }}>
                    <Typography variant="h6" gutterBottom>
                      Execution Status
                    </Typography>

                    <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                      <Typography variant="body1" sx={{ mr: 2 }}>
                        Status:
                      </Typography>
                      <Chip
                        label={executionStatus[selectedRunbook.id].status}
                        color={
                          executionStatus[selectedRunbook.id].status === 'completed' ? 'success' :
                          executionStatus[selectedRunbook.id].status === 'failed' ? 'error' :
                          executionStatus[selectedRunbook.id].status === 'in_progress' ? 'primary' : 'default'
                        }
                      />
                    </Box>

                    <Typography variant="body2" sx={{ mb: 1 }}>
                      {executionStatus[selectedRunbook.id].message}
                    </Typography>

                    {executionStatus[selectedRunbook.id].progress !== undefined && (
                      <Box sx={{ width: '100%', mb: 2 }}>
                        <LinearProgress
                          variant="determinate"
                          value={executionStatus[selectedRunbook.id].progress}
                        />
                        <Typography variant="caption" align="center" display="block">
                          {executionStatus[selectedRunbook.id].progress}% Complete
                        </Typography>
                      </Box>
                    )}

                    {executionStatus[selectedRunbook.id].steps && executionStatus[selectedRunbook.id].steps.length > 0 && (
                      <Box sx={{ mt: 2 }}>
                        <Typography variant="subtitle1" gutterBottom>
                          Execution Steps:
                        </Typography>
                        <Stepper orientation="vertical">
                          {executionStatus[selectedRunbook.id].steps.map((step, index) => (
                            <Step key={index} completed={step.status === 'completed'} active={step.status === 'in_progress'}>
                              <StepLabel>{step.description}</StepLabel>
                              <StepContent>
                                {step.outcome && (
                                  <Typography variant="body2" color="text.secondary">
                                    {step.outcome}
                                  </Typography>
                                )}
                              </StepContent>
                            </Step>
                          ))}
                        </Stepper>
                      </Box>
                    )}
                  </Box>
                )}

                <CardActions>
                  <Button
                    size="small"
                    variant="contained"
                    color="primary"
                    onClick={() => handleExecuteRunbook(selectedRunbook.id)}
                    disabled={executingRunbook === selectedRunbook.id}
                  >
                    {executingRunbook === selectedRunbook.id ? 'Executing...' : 'Execute Runbook'}
                  </Button>
                </CardActions>
              </Card>
            ) : (
              <Box sx={{
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                height: '100%',
                p: 4,
                bgcolor: 'background.paper',
                borderRadius: 1
              }}>
                <Typography variant="body1" color="text.secondary">
                  Select a runbook to view details
                </Typography>
              </Box>
            )}
          </Grid>
        </Grid>
      )}
    </Container>
  );
}
