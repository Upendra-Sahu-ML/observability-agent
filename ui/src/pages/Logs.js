import React, { useState, useEffect } from 'react';
import {
  Container,
  Typography,
  Box,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  CircularProgress,
  Alert,
  Chip,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Grid,
  TextField,
  InputAdornment,
  IconButton,
  Tooltip,
  Divider
} from '@mui/material';
import {
  Search as SearchIcon,
  Refresh as RefreshIcon,
  FilterList as FilterListIcon,
  ErrorOutline as ErrorIcon,
  Warning as WarningIcon,
  Info as InfoIcon
} from '@mui/icons-material';
// Date picker removed due to compatibility issues
import api from '../api';

export default function Logs() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [serviceFilter, setServiceFilter] = useState('');
  const [levelFilter, setLevelFilter] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  // Fetch logs with filters
  const fetchLogs = async () => {
    setLoading(true);
    try {
      // Build query parameters
      const params = {};
      if (serviceFilter) params.service = serviceFilter;

      const response = await api.get('/logs', { params });
      setLogs(response.data);
      setError(null);
    } catch (err) {
      console.error('Error fetching logs:', err);
      setError(err.message || 'Error fetching logs');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, [serviceFilter]);

  // Handle service filter change
  const handleServiceFilterChange = (event) => {
    setServiceFilter(event.target.value);
  };

  // Handle level filter change
  const handleLevelFilterChange = (event) => {
    setLevelFilter(event.target.value);
  };

  // Handle search term change
  const handleSearchChange = (event) => {
    setSearchTerm(event.target.value);
  };

  // Filter logs based on level and search term
  const filteredLogs = logs.filter(log => {
    // Apply level filter
    if (levelFilter && log.level !== levelFilter) {
      return false;
    }

    // Apply search filter
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      return (
        log.message.toLowerCase().includes(term) ||
        log.service.toLowerCase().includes(term)
      );
    }

    return true;
  });

  // Get unique services and levels for filters
  const services = [...new Set(logs.map(log => log.service))].sort();
  const levels = [...new Set(logs.map(log => log.level))].sort();

  // Get color for log level
  const getLevelColor = (level) => {
    switch (level.toUpperCase()) {
      case 'ERROR':
        return 'error';
      case 'WARN':
        return 'warning';
      case 'INFO':
        return 'info';
      case 'DEBUG':
        return 'default';
      default:
        return 'default';
    }
  };

  // Get icon for log level
  const getLevelIcon = (level) => {
    switch (level.toUpperCase()) {
      case 'ERROR':
        return <ErrorIcon color="error" />;
      case 'WARN':
        return <WarningIcon color="warning" />;
      case 'INFO':
        return <InfoIcon color="info" />;
      default:
        return null;
    }
  };

  // Format timestamp
  const formatTimestamp = (timestamp) => {
    return new Date(timestamp).toLocaleString();
  };

  return (
    <Container sx={{ mt: 4, mb: 4 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">
          System Logs
        </Typography>
        <Tooltip title="Refresh logs">
          <IconButton onClick={fetchLogs} disabled={loading}>
            <RefreshIcon />
          </IconButton>
        </Tooltip>
      </Box>

      <Paper sx={{ p: 2, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          <FilterListIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
          Filters
        </Typography>
        <Divider sx={{ mb: 2 }} />
        <Grid container spacing={2}>
          <Grid item xs={12} md={4}>
            <FormControl fullWidth variant="outlined" size="small">
              <InputLabel id="service-filter-label">Service</InputLabel>
              <Select
                labelId="service-filter-label"
                value={serviceFilter}
                onChange={handleServiceFilterChange}
                label="Service"
              >
                <MenuItem value="">All Services</MenuItem>
                {services.map(service => (
                  <MenuItem key={service} value={service}>{service}</MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} md={4}>
            <FormControl fullWidth variant="outlined" size="small">
              <InputLabel id="level-filter-label">Log Level</InputLabel>
              <Select
                labelId="level-filter-label"
                value={levelFilter}
                onChange={handleLevelFilterChange}
                label="Log Level"
              >
                <MenuItem value="">All Levels</MenuItem>
                {levels.map(level => (
                  <MenuItem key={level} value={level}>
                    <Box sx={{ display: 'flex', alignItems: 'center' }}>
                      {getLevelIcon(level)}
                      <Typography sx={{ ml: 1 }}>{level}</Typography>
                    </Box>
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} md={4}>
            <TextField
              fullWidth
              variant="outlined"
              size="small"
              placeholder="Search logs..."
              value={searchTerm}
              onChange={handleSearchChange}
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
      </Paper>

        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
            <CircularProgress />
          </Box>
        ) : error ? (
          <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>
        ) : filteredLogs.length === 0 ? (
          <Alert severity="info">No logs found matching your criteria</Alert>
        ) : (
          <TableContainer component={Paper}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Timestamp</TableCell>
                  <TableCell>Level</TableCell>
                  <TableCell>Service</TableCell>
                  <TableCell>Message</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {filteredLogs.map((log, idx) => (
                  <TableRow key={idx} hover>
                    <TableCell>{formatTimestamp(log.timestamp)}</TableCell>
                    <TableCell>
                      <Chip
                        icon={getLevelIcon(log.level)}
                        label={log.level}
                        color={getLevelColor(log.level)}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>
                      <Chip label={log.service} variant="outlined" size="small" />
                    </TableCell>
                    <TableCell sx={{ fontFamily: 'monospace', whiteSpace: 'pre-wrap' }}>
                      {log.message}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </Container>
  );
}
