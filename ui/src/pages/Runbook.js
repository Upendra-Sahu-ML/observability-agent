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
  Divider,
  CircularProgress,
  Alert,
  Box,
  Paper
} from '@mui/material';
import api from '../api';

export default function Runbook() {
  const [runbooks, setRunbooks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedRunbook, setSelectedRunbook] = useState(null);

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

  const handleExecuteRunbook = (runbookId) => {
    // In a real implementation, this would call an API to execute the runbook
    console.log(`Executing runbook: ${runbookId}`);
    alert(`Runbook ${runbookId} execution started`);
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
                      <ListItem
                        button
                        onClick={() => handleRunbookSelect(runbook)}
                        selected={selectedRunbook && selectedRunbook.id === runbook.id}
                      >
                        <ListItemText
                          primary={runbook.title}
                          secondary={`Service: ${runbook.service}`}
                        />
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
                <CardActions>
                  <Button
                    size="small"
                    variant="contained"
                    color="primary"
                    onClick={() => handleExecuteRunbook(selectedRunbook.id)}
                  >
                    Execute Runbook
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
