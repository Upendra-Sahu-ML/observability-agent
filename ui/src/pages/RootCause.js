import React, { useState, useEffect } from 'react';
import {
  Container,
  Typography,
  Card,
  CardContent,
  Grid,
  CircularProgress,
  Alert,
  Chip,
  Box,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  InputAdornment
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import api from '../api';

export default function RootCause() {
  const [rootCauses, setRootCauses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    // Fetch root cause analysis data from the API
    api.get('/rootcause')
      .then(res => {
        console.log('Root cause data:', res.data);
        setRootCauses(res.data);
      })
      .catch(err => {
        console.error('Error fetching root cause data:', err);
        setError(err.message || 'Error fetching root cause analysis data');
      })
      .finally(() => setLoading(false));
  }, []);

  // Filter root causes based on search term
  const filteredRootCauses = rootCauses.filter(rc =>
    rc.service.toLowerCase().includes(searchTerm.toLowerCase()) ||
    rc.cause.toLowerCase().includes(searchTerm.toLowerCase()) ||
    rc.alertId.toLowerCase().includes(searchTerm.toLowerCase())
  );

  // Function to get color based on confidence level
  const getConfidenceColor = (confidence) => {
    if (confidence >= 0.9) return 'success';
    if (confidence >= 0.7) return 'info';
    if (confidence >= 0.5) return 'warning';
    return 'error';
  };

  return (
    <Container sx={{ mt: 4 }}>
      <Typography variant="h4" gutterBottom>
        Root Cause Analysis
      </Typography>

      {loading && <CircularProgress />}
      {error && <Alert severity="error">{error}</Alert>}

      {!loading && !error && (
        <>
          <Box sx={{ mb: 3 }}>
            <TextField
              fullWidth
              variant="outlined"
              placeholder="Search by service, cause, or alert ID"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon />
                  </InputAdornment>
                ),
              }}
            />
          </Box>

          {filteredRootCauses.length === 0 ? (
            <Alert severity="info">No root cause analysis results found</Alert>
          ) : (
            <TableContainer component={Paper}>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Alert ID</TableCell>
                    <TableCell>Service</TableCell>
                    <TableCell>Root Cause</TableCell>
                    <TableCell>Confidence</TableCell>
                    <TableCell>Timestamp</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {filteredRootCauses.map((rc) => (
                    <TableRow key={rc.id} hover>
                      <TableCell>{rc.alertId}</TableCell>
                      <TableCell>{rc.service}</TableCell>
                      <TableCell>{rc.cause}</TableCell>
                      <TableCell>
                        <Chip
                          label={`${Math.round(rc.confidence * 100)}%`}
                          color={getConfidenceColor(rc.confidence)}
                          size="small"
                        />
                      </TableCell>
                      <TableCell>{new Date(rc.timestamp).toLocaleString()}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}

          {filteredRootCauses.length > 0 && (
            <Grid container spacing={3} sx={{ mt: 3 }}>
              {filteredRootCauses.map((rc) => (
                <Grid item xs={12} key={rc.id}>
                  <Card>
                    <CardContent>
                      <Typography variant="h6" gutterBottom>
                        {rc.service} - {rc.cause}
                      </Typography>
                      <Typography variant="body2" color="text.secondary" gutterBottom>
                        Alert ID: {rc.alertId} | Confidence: {Math.round(rc.confidence * 100)}% |
                        {new Date(rc.timestamp).toLocaleString()}
                      </Typography>
                      <Typography variant="body1" sx={{ mt: 2 }}>
                        {rc.details}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>
          )}
        </>
      )}
    </Container>
  );
}
