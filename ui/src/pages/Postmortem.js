import React, { useState, useEffect } from 'react';
import {
  Container,
  Typography,
  Box,
  Paper,
  Grid,
  List,
  ListItem,
  ListItemText,
  Divider,
  Card,
  CardHeader,
  CardContent,
  Chip,
  IconButton,
  Tooltip,
  TextField,
  InputAdornment,
  CircularProgress,
  Alert
} from '@mui/material';
import { Search as SearchIcon, ContentCopy as ContentCopyIcon } from '@mui/icons-material';
import api from '../api';

export default function Postmortem() {
  const [postmortems, setPostmortems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedPostmortem, setSelectedPostmortem] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    // Fetch postmortem data from the API
    const fetchPostmortems = async () => {
      try {
        const response = await api.get('/postmortem');
        setPostmortems(response.data);
      } catch (err) {
        console.error('Error fetching postmortem data:', err);
        setError(err.message || 'Failed to fetch postmortem data');
      } finally {
        setLoading(false);
      }
    };

    fetchPostmortems();
  }, []);

  // Handle postmortem selection
  const handlePostmortemSelect = (postmortem) => {
    setSelectedPostmortem(postmortem);
  };

  // Handle search
  const handleSearch = (event) => {
    setSearchTerm(event.target.value);
  };

  // Filter postmortems based on search term
  const filteredPostmortems = postmortems.filter(postmortem =>
    postmortem.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (postmortem.summary && postmortem.summary.toLowerCase().includes(searchTerm.toLowerCase())) ||
    (postmortem.service && postmortem.service.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  // Copy content to clipboard
  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
  };

  return (
    <Container sx={{ mt: 4 }}>
      <Typography variant="h4" gutterBottom>
        Postmortem Reports
      </Typography>

      <Box sx={{ mb: 3 }}>
        <TextField
          fullWidth
          variant="outlined"
          placeholder="Search postmortems..."
          value={searchTerm}
          onChange={handleSearch}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon />
              </InputAdornment>
            ),
          }}
        />
      </Box>

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
          <CircularProgress />
        </Box>
      ) : error ? (
        <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>
      ) : (
        <Grid container spacing={3}>
          {/* Postmortems List */}
          <Grid item xs={12} md={4}>
            <Paper elevation={2} sx={{ height: '100%' }}>
              <Box sx={{ p: 2 }}>
                <Typography variant="h6" gutterBottom>
                  Postmortem Reports
                </Typography>
              </Box>
              <Divider />

              {filteredPostmortems.length === 0 ? (
                <Box sx={{ p: 2 }}>
                  <Alert severity="info">No postmortem reports found</Alert>
                </Box>
              ) : (
                <List sx={{ maxHeight: '600px', overflow: 'auto' }}>
                  {filteredPostmortems.map((postmortem) => (
                    <React.Fragment key={postmortem.id}>
                      <ListItem
                        sx={{
                          cursor: 'pointer',
                          bgcolor: selectedPostmortem && selectedPostmortem.id === postmortem.id ? 'action.selected' : 'inherit'
                        }}
                        onClick={() => handlePostmortemSelect(postmortem)}
                      >
                        <ListItemText
                          primary={postmortem.title}
                          secondary={`Status: ${postmortem.status} | ${new Date(postmortem.createdAt).toLocaleString()}`}
                        />
                      </ListItem>
                      <Divider />
                    </React.Fragment>
                  ))}
                </List>
              )}
            </Paper>
          </Grid>

          {/* Postmortem Details */}
          <Grid item xs={12} md={8}>
            {selectedPostmortem ? (
              <Card>
                <CardHeader
                  title={selectedPostmortem.title}
                  subheader={`ID: ${selectedPostmortem.id} | Created: ${new Date(selectedPostmortem.createdAt).toLocaleString()}`}
                  action={
                    <Tooltip title="Copy postmortem">
                      <IconButton onClick={() => copyToClipboard(JSON.stringify(selectedPostmortem, null, 2))}>
                        <ContentCopyIcon />
                      </IconButton>
                    </Tooltip>
                  }
                />
                <Divider />
                <CardContent>
                  <Box sx={{ mb: 2 }}>
                    <Chip
                      label={selectedPostmortem.status}
                      color={selectedPostmortem.status === 'completed' ? 'success' : 'warning'}
                      sx={{ mr: 1 }}
                    />
                    {selectedPostmortem.service && (
                      <Chip
                        label={selectedPostmortem.service}
                        color="primary"
                        variant="outlined"
                      />
                    )}
                  </Box>

                  <Typography variant="h6" gutterBottom>Summary</Typography>
                  <Typography paragraph>{selectedPostmortem.summary}</Typography>

                  {selectedPostmortem.impact && (
                    <>
                      <Typography variant="h6" gutterBottom>Impact</Typography>
                      <Typography paragraph>{selectedPostmortem.impact}</Typography>
                    </>
                  )}

                  {selectedPostmortem.rootCause && (
                    <>
                      <Typography variant="h6" gutterBottom>Root Cause</Typography>
                      <Typography paragraph>{selectedPostmortem.rootCause}</Typography>
                    </>
                  )}

                  {selectedPostmortem.resolution && (
                    <>
                      <Typography variant="h6" gutterBottom>Resolution</Typography>
                      <Typography paragraph>{selectedPostmortem.resolution}</Typography>
                    </>
                  )}

                  {selectedPostmortem.actionItems && selectedPostmortem.actionItems.length > 0 && (
                    <>
                      <Typography variant="h6" gutterBottom>Action Items</Typography>
                      <List>
                        {selectedPostmortem.actionItems.map((item, index) => (
                          <ListItem key={index}>
                            <ListItemText primary={item} />
                          </ListItem>
                        ))}
                      </List>
                    </>
                  )}
                </CardContent>
              </Card>
            ) : (
              <Paper sx={{ p: 3, height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Typography variant="body1" color="textSecondary">
                  Select a postmortem report to view details
                </Typography>
              </Paper>
            )}
          </Grid>
        </Grid>
      )}
    </Container>
  );
}
