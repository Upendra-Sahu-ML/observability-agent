import React, { useState, useEffect } from 'react';
import {
  Container,
  Typography,
  Box,
  Grid,
  Card,
  CardHeader,
  CardContent,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  CircularProgress,
  Alert,
  Chip,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Divider,
  IconButton,
  Tooltip,
  TextField,
  InputAdornment
} from '@mui/material';
import {
  Search as SearchIcon,
  Refresh as RefreshIcon,
  TrendingUp as TrendingUpIcon,
  Memory as MemoryIcon,
  Speed as SpeedIcon,
  Error as ErrorIcon
} from '@mui/icons-material';
import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip as ChartTooltip,
  Legend
} from 'chart.js';
import api from '../api';

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  ChartTooltip,
  Legend
);

export default function Metrics() {
  const [metrics, setMetrics] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [serviceFilter, setServiceFilter] = useState('');
  const [searchTerm, setSearchTerm] = useState('');

  // Fetch metrics data
  const fetchMetrics = async () => {
    setLoading(true);
    try {
      const response = await api.get('/metrics', {
        params: serviceFilter ? { service: serviceFilter } : {}
      });
      setMetrics(response.data);
      setError(null);
    } catch (err) {
      console.error('Error fetching metrics:', err);
      setError(err.message || 'Error fetching metrics');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMetrics();
  }, [serviceFilter]);

  // Handle service filter change
  const handleServiceFilterChange = (event) => {
    setServiceFilter(event.target.value);
  };

  // Handle search
  const handleSearchChange = (event) => {
    setSearchTerm(event.target.value);
  };

  // Group metrics by service
  const metricsByService = metrics.reduce((acc, metric) => {
    if (!acc[metric.service]) {
      acc[metric.service] = [];
    }
    acc[metric.service].push(metric);
    return acc;
  }, {});

  // Filter metrics based on search term
  const filteredMetricsByService = Object.entries(metricsByService)
    .filter(([service]) =>
      serviceFilter ? service === serviceFilter : true
    )
    .filter(([service, serviceMetrics]) =>
      searchTerm ?
        service.toLowerCase().includes(searchTerm.toLowerCase()) ||
        serviceMetrics.some(m => m.name.toLowerCase().includes(searchTerm.toLowerCase()))
        : true
    );

  // Get unique services for filter dropdown
  const services = [...new Set(metrics.map(m => m.service))].sort();

  // Get metric icon based on name
  const getMetricIcon = (metricName) => {
    const name = metricName.toLowerCase();
    if (name.includes('cpu')) return <TrendingUpIcon color="primary" />;
    if (name.includes('memory')) return <MemoryIcon color="secondary" />;
    if (name.includes('rate') && name.includes('error')) return <ErrorIcon color="error" />;
    if (name.includes('rate')) return <SpeedIcon color="success" />;
    return null;
  };

  // Format timestamp
  const formatTimestamp = (timestamp) => {
    return new Date(timestamp).toLocaleString();
  };

  // Generate chart data for a service
  const generateChartData = (serviceMetrics) => {
    // For demo purposes, we'll create some fake historical data
    // In a real app, you would fetch this from an API
    const labels = Array.from({ length: 10 }, (_, i) =>
      new Date(Date.now() - (9 - i) * 3600000).toLocaleTimeString()
    );

    const datasets = serviceMetrics
      .filter(metric => !metric.name.toLowerCase().includes('rate')) // Filter out rate metrics for this demo
      .map((metric, index) => {
        // Generate random historical values
        const data = Array.from({ length: 10 }, () =>
          parseFloat(metric.value) * (0.8 + Math.random() * 0.4)
        );

        // Set the last value to the current value
        data[data.length - 1] = parseFloat(metric.value);

        // Color based on metric type
        let borderColor = '#3f51b5'; // Default blue
        if (metric.name.toLowerCase().includes('cpu')) borderColor = '#f44336'; // Red
        if (metric.name.toLowerCase().includes('memory')) borderColor = '#9c27b0'; // Purple

        return {
          label: metric.name,
          data,
          borderColor,
          backgroundColor: `${borderColor}33`, // Add transparency
          tension: 0.2
        };
      });

    return { labels, datasets };
  };

  return (
    <Container sx={{ mt: 4, mb: 4 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">
          System Metrics
        </Typography>
        <Tooltip title="Refresh metrics">
          <IconButton onClick={fetchMetrics} disabled={loading}>
            <RefreshIcon />
          </IconButton>
        </Tooltip>
      </Box>

      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} md={8}>
          <TextField
            fullWidth
            variant="outlined"
            placeholder="Search metrics..."
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
        <Grid item xs={12} md={4}>
          <FormControl fullWidth variant="outlined">
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
      </Grid>

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
          <CircularProgress />
        </Box>
      ) : error ? (
        <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>
      ) : filteredMetricsByService.length === 0 ? (
        <Alert severity="info">No metrics found matching your criteria</Alert>
      ) : (
        <Grid container spacing={3}>
          {filteredMetricsByService.map(([service, serviceMetrics]) => (
            <Grid item xs={12} key={service}>
              <Card>
                <CardHeader
                  title={`${service} Metrics`}
                  subheader={`Last updated: ${formatTimestamp(serviceMetrics[0].timestamp)}`}
                />
                <Divider />
                <CardContent>
                  <Grid container spacing={3}>
                    <Grid item xs={12} md={6}>
                      <TableContainer component={Paper} variant="outlined">
                        <Table size="small">
                          <TableHead>
                            <TableRow>
                              <TableCell>Metric</TableCell>
                              <TableCell>Value</TableCell>
                              <TableCell>Timestamp</TableCell>
                            </TableRow>
                          </TableHead>
                          <TableBody>
                            {serviceMetrics.map((metric, idx) => (
                              <TableRow key={idx} hover>
                                <TableCell>
                                  <Box sx={{ display: 'flex', alignItems: 'center' }}>
                                    {getMetricIcon(metric.name)}
                                    <Typography sx={{ ml: 1 }}>{metric.name}</Typography>
                                  </Box>
                                </TableCell>
                                <TableCell>
                                  <Chip
                                    label={metric.value}
                                    color={
                                      metric.name.toLowerCase().includes('error') ?
                                        parseFloat(metric.value) > 1 ? 'error' : 'success'
                                        : 'default'
                                    }
                                    variant="outlined"
                                  />
                                </TableCell>
                                <TableCell>{formatTimestamp(metric.timestamp)}</TableCell>
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>
                      </TableContainer>
                    </Grid>
                    <Grid item xs={12} md={6}>
                      <Paper
                        variant="outlined"
                        sx={{ p: 2, height: '100%', minHeight: '250px' }}
                      >
                        <Typography variant="h6" gutterBottom>Trend (Last 10 Hours)</Typography>
                        <Line
                          data={generateChartData(serviceMetrics)}
                          options={{
                            responsive: true,
                            maintainAspectRatio: false,
                            scales: {
                              y: {
                                beginAtZero: true
                              }
                            }
                          }}
                          height={200}
                        />
                      </Paper>
                    </Grid>
                  </Grid>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}
    </Container>
  );
}
