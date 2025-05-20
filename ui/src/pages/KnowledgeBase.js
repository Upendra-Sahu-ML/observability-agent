import React, { useState, useEffect } from 'react';
import {
  Container,
  Typography,
  Paper,
  TextField,
  Button,
  Grid,
  Box,
  Card,
  CardContent,
  CardHeader,
  Divider,
  List,
  ListItem,
  ListItemText,
  CircularProgress,
  Alert,
  Chip,
  InputAdornment,
  IconButton,
  Tabs,
  Tab,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Tooltip
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import ReactMarkdown from 'react-markdown';
import api from '../api';

// TabPanel component for tab content
function TabPanel(props) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`knowledge-tabpanel-${index}`}
      aria-labelledby={`knowledge-tab-${index}`}
      {...other}
    >
      {value === index && (
        <Box sx={{ p: 3 }}>
          {children}
        </Box>
      )}
    </div>
  );
}

export default function KnowledgeBase() {
  const [value, setValue] = useState(0);
  const [incidents, setIncidents] = useState([]);
  const [postmortems, setPostmortems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedIncident, setSelectedIncident] = useState(null);
  const [selectedPostmortem, setSelectedPostmortem] = useState(null);

  // Fetch knowledge base data on component mount
  useEffect(() => {
    fetchKnowledgeBase();
  }, []);

  // Function to fetch knowledge base data from the API
  const fetchKnowledgeBase = async () => {
    setLoading(true);
    try {
      // Fetch incidents
      const incidentsResponse = await api.get('/knowledge/incidents');
      setIncidents(incidentsResponse.data);

      // Fetch postmortems
      const postmortemsResponse = await api.get('/knowledge/postmortems');
      setPostmortems(postmortemsResponse.data);
    } catch (err) {
      console.error('Error fetching knowledge base data:', err);
      setError(err.message || 'Failed to fetch knowledge base data');
    } finally {
      setLoading(false);
    }
  };

  // Handle tab change
  const handleTabChange = (event, newValue) => {
    setValue(newValue);
  };

  // Handle search
  const handleSearch = (event) => {
    setSearchTerm(event.target.value);
  };

  // Handle incident selection
  const handleIncidentSelect = (incident) => {
    setSelectedIncident(incident);
  };

  // Handle postmortem selection
  const handlePostmortemSelect = (postmortem) => {
    setSelectedPostmortem(postmortem);
  };

  // Copy text to clipboard
  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
  };

  // Filter incidents based on search term
  const filteredIncidents = incidents.filter(incident =>
    incident.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
    incident.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
    incident.root_cause.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (incident.service && incident.service.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  // Filter postmortems based on search term
  const filteredPostmortems = postmortems.filter(postmortem =>
    postmortem.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
    postmortem.summary.toLowerCase().includes(searchTerm.toLowerCase()) ||
    postmortem.root_cause.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (postmortem.service && postmortem.service.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  return (
    <Container sx={{ mt: 4, mb: 4 }}>
      <Typography variant="h4" gutterBottom>
        Knowledge Base
      </Typography>

      <Box sx={{ mb: 3 }}>
        <TextField
          placeholder="Search knowledge base..."
          variant="outlined"
          size="small"
          fullWidth
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
        <>
          <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
            <Tabs value={value} onChange={handleTabChange} aria-label="knowledge base tabs">
              <Tab label={`Incidents (${incidents.length})`} id="knowledge-tab-0" />
              <Tab label={`Postmortems (${postmortems.length})`} id="knowledge-tab-1" />
            </Tabs>
          </Box>

          <TabPanel value={value} index={0}>
            <Grid container spacing={3}>
              {/* Incidents List */}
              <Grid item xs={12} md={4}>
                <Paper elevation={2} sx={{ height: '100%' }}>
                  <Box sx={{ p: 2 }}>
                    <Typography variant="h6" gutterBottom>
                      Incident Records
                    </Typography>
                  </Box>
                  <Divider />

                  {filteredIncidents.length === 0 ? (
                    <Box sx={{ p: 2 }}>
                      <Alert severity="info">No incidents found</Alert>
                    </Box>
                  ) : (
                    <List sx={{ maxHeight: '600px', overflow: 'auto' }}>
                      {filteredIncidents.map((incident) => (
                        <React.Fragment key={incident.alert_id}>
                          <ListItem
                            sx={{
                              cursor: 'pointer',
                              bgcolor: selectedIncident && selectedIncident.alert_id === incident.alert_id ? 'action.selected' : 'inherit'
                            }}
                            onClick={() => handleIncidentSelect(incident)}
                          >
                            <ListItemText
                              primary={incident.title}
                              secondary={`Service: ${incident.service || 'N/A'} | ${new Date(incident.timestamp).toLocaleString()}`}
                            />
                          </ListItem>
                          <Divider />
                        </React.Fragment>
                      ))}
                    </List>
                  )}
                </Paper>
              </Grid>

              {/* Incident Details */}
              <Grid item xs={12} md={8}>
                {selectedIncident ? (
                  <Card>
                    <CardHeader
                      title={selectedIncident.title}
                      subheader={`Alert ID: ${selectedIncident.alert_id} | ${new Date(selectedIncident.timestamp).toLocaleString()}`}
                      action={
                        <Tooltip title="Copy incident details">
                          <IconButton onClick={() => copyToClipboard(JSON.stringify(selectedIncident, null, 2))}>
                            <ContentCopyIcon />
                          </IconButton>
                        </Tooltip>
                      }
                    />
                    <Divider />
                    <CardContent>
                      <Accordion defaultExpanded>
                        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                          <Typography variant="h6">Description</Typography>
                        </AccordionSummary>
                        <AccordionDetails>
                          <Typography variant="body1">{selectedIncident.description}</Typography>
                        </AccordionDetails>
                      </Accordion>

                      <Accordion defaultExpanded>
                        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                          <Typography variant="h6">Root Cause</Typography>
                        </AccordionSummary>
                        <AccordionDetails>
                          <Typography variant="body1">{selectedIncident.root_cause}</Typography>
                        </AccordionDetails>
                      </Accordion>

                      <Accordion defaultExpanded>
                        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                          <Typography variant="h6">Resolution</Typography>
                        </AccordionSummary>
                        <AccordionDetails>
                          <Typography variant="body1">{selectedIncident.resolution || 'No resolution information available'}</Typography>
                        </AccordionDetails>
                      </Accordion>

                      {selectedIncident.metadata && Object.keys(selectedIncident.metadata).length > 0 && (
                        <Accordion>
                          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                            <Typography variant="h6">Additional Metadata</Typography>
                          </AccordionSummary>
                          <AccordionDetails>
                            <Grid container spacing={2}>
                              {Object.entries(selectedIncident.metadata).map(([key, value]) => (
                                <Grid item xs={12} sm={6} key={key}>
                                  <Typography variant="subtitle2">{key}</Typography>
                                  <Typography variant="body2">{value}</Typography>
                                </Grid>
                              ))}
                            </Grid>
                          </AccordionDetails>
                        </Accordion>
                      )}
                    </CardContent>
                  </Card>
                ) : (
                  <Paper sx={{ p: 3, height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <Typography variant="body1" color="text.secondary">
                      Select an incident to view details
                    </Typography>
                  </Paper>
                )}
              </Grid>
            </Grid>
          </TabPanel>

          <TabPanel value={value} index={1}>
            <Grid container spacing={3}>
              {/* Postmortems List */}
              <Grid item xs={12} md={4}>
                <Paper elevation={2} sx={{ height: '100%' }}>
                  <Box sx={{ p: 2 }}>
                    <Typography variant="h6" gutterBottom>
                      Postmortem Documents
                    </Typography>
                  </Box>
                  <Divider />

                  {filteredPostmortems.length === 0 ? (
                    <Box sx={{ p: 2 }}>
                      <Alert severity="info">No postmortems found</Alert>
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

                      <Box sx={{ mt: 3 }}>
                        <ReactMarkdown>
                          {selectedPostmortem.content || selectedPostmortem.summary}
                        </ReactMarkdown>
                      </Box>
                    </CardContent>
                  </Card>
                ) : (
                  <Paper sx={{ p: 3, height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <Typography variant="body1" color="text.secondary">
                      Select a postmortem to view details
                    </Typography>
                  </Paper>
                )}
              </Grid>
            </Grid>
          </TabPanel>
        </>
      )}
    </Container>
  );
}
