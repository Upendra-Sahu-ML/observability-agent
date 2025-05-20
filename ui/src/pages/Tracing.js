import React, { useState, useEffect } from 'react';
import {
  Container,
  Typography,
  Box,
  Paper,
  Grid,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  TextField,
  InputAdornment,
  CircularProgress,
  Alert,
  Chip,
  Divider
} from '@mui/material';
import { Search as SearchIcon, ExpandMore as ExpandMoreIcon } from '@mui/icons-material';
import api from '../api';

export default function Tracing() {
  const [traces, setTraces] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [serviceFilter, setServiceFilter] = useState('');

  useEffect(() => {
    // Fetch tracing data from the API
    const fetchTraces = async () => {
      try {
        const response = await api.get('/tracing');
        setTraces(response.data);
      } catch (err) {
        console.error('Error fetching tracing data:', err);
        setError(err.message || 'Failed to fetch tracing data');
      } finally {
        setLoading(false);
      }
    };

    fetchTraces();
  }, []);

  // Handle search
  const handleSearch = (event) => {
    setSearchTerm(event.target.value);
  };

  // Handle service filter
  const handleServiceFilter = (event) => {
    setServiceFilter(event.target.value);
  };

  // Filter traces based on search term and service filter
  const filteredTraces = traces.filter(trace => {
    const matchesSearch =
      trace.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      trace.operation.toLowerCase().includes(searchTerm.toLowerCase());

    const matchesService =
      !serviceFilter ||
      trace.service.toLowerCase().includes(serviceFilter.toLowerCase()) ||
      trace.spans.some(span => span.service.toLowerCase().includes(serviceFilter.toLowerCase()));

    return matchesSearch && matchesService;
  });

  // Get unique services for filtering
  const services = [...new Set(
    traces.flatMap(trace => [
      trace.service,
      ...trace.spans.map(span => span.service)
    ])
  )].sort();

  // Format duration in milliseconds
  const formatDuration = (ms) => {
    if (ms < 1) {
      return `${(ms * 1000).toFixed(2)}μs`;
    } else if (ms < 1000) {
      return `${ms.toFixed(2)}ms`;
    } else {
      return `${(ms / 1000).toFixed(2)}s`;
    }
  };

  return (
    <Container sx={{ mt: 4 }}>
      <Typography variant="h4" gutterBottom>
        Distributed Tracing
      </Typography>

      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} md={6}>
          <TextField
            fullWidth
            variant="outlined"
            placeholder="Search traces by ID or operation..."
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
        </Grid>
        <Grid item xs={12} md={6}>
          <TextField
            fullWidth
            variant="outlined"
            placeholder="Filter by service..."
            value={serviceFilter}
            onChange={handleServiceFilter}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon />
                </InputAdornment>
              ),
            }}
          />
        </Grid>
      </Grid>

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
          <CircularProgress />
        </Box>
      ) : error ? (
        <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>
      ) : (
        <>
          {services.length > 0 && (
            <Box sx={{ mb: 3, display: 'flex', flexWrap: 'wrap', gap: 1 }}>
              <Typography variant="body2" sx={{ mr: 1 }}>Available services:</Typography>
              {services.map(service => (
                <Chip
                  key={service}
                  label={service}
                  size="small"
                  onClick={() => setServiceFilter(service)}
                  color={serviceFilter === service ? 'primary' : 'default'}
                  sx={{ mr: 1 }}
                />
              ))}
              {serviceFilter && (
                <Chip
                  label="Clear filter"
                  size="small"
                  onClick={() => setServiceFilter('')}
                  variant="outlined"
                />
              )}
            </Box>
          )}

          {filteredTraces.length === 0 ? (
            <Alert severity="info">No traces found matching your criteria</Alert>
          ) : (
            <Paper elevation={2}>
              <TableContainer>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>Trace ID</TableCell>
                      <TableCell>Service</TableCell>
                      <TableCell>Operation</TableCell>
                      <TableCell>Duration</TableCell>
                      <TableCell>Timestamp</TableCell>
                      <TableCell>Spans</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {filteredTraces.map((trace) => (
                      <React.Fragment key={trace.id}>
                        <TableRow hover>
                          <TableCell>{trace.id}</TableCell>
                          <TableCell>
                            <Chip label={trace.service} size="small" />
                          </TableCell>
                          <TableCell>{trace.operation}</TableCell>
                          <TableCell>{formatDuration(trace.duration)}</TableCell>
                          <TableCell>{new Date(trace.timestamp).toLocaleString()}</TableCell>
                          <TableCell>{trace.spans.length}</TableCell>
                        </TableRow>
                        <TableRow>
                          <TableCell colSpan={6} sx={{ p: 0, borderBottom: 'none' }}>
                            <Accordion>
                              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                                <Typography variant="body2">View Spans</Typography>
                              </AccordionSummary>
                              <AccordionDetails>
                                <TableContainer component={Paper} variant="outlined">
                                  <Table size="small">
                                    <TableHead>
                                      <TableRow>
                                        <TableCell>Span ID</TableCell>
                                        <TableCell>Service</TableCell>
                                        <TableCell>Operation</TableCell>
                                        <TableCell>Duration</TableCell>
                                      </TableRow>
                                    </TableHead>
                                    <TableBody>
                                      {trace.spans.map((span) => (
                                        <TableRow key={span.id}>
                                          <TableCell>{span.id}</TableCell>
                                          <TableCell>{span.service}</TableCell>
                                          <TableCell>{span.operation}</TableCell>
                                          <TableCell>{formatDuration(span.duration)}</TableCell>
                                        </TableRow>
                                      ))}
                                    </TableBody>
                                  </Table>
                                </TableContainer>
                              </AccordionDetails>
                            </Accordion>
                          </TableCell>
                        </TableRow>
                        <TableRow>
                          <TableCell colSpan={6} sx={{ p: 0 }}>
                            <Divider />
                          </TableCell>
                        </TableRow>
                      </React.Fragment>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </Paper>
          )}
        </>
      )}
    </Container>
  );
}
