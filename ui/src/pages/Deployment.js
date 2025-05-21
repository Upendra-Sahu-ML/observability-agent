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
  Grid,
  Card,
  CardContent,
  CardHeader,
  Divider,
  TextField,
  InputAdornment,
  IconButton,
  Tooltip,

} from '@mui/material';
import {
  Timeline,
  TimelineItem,
  TimelineSeparator,
  TimelineConnector,
  TimelineContent,
  TimelineDot,
  TimelineOppositeContent
} from '@mui/lab';
import {
  Search as SearchIcon,
  Refresh as RefreshIcon,
  CheckCircle as SuccessIcon,
  Cancel as FailedIcon,
  Pending as PendingIcon,
  Code as CodeIcon,
  CloudUpload as DeployIcon
} from '@mui/icons-material';
import api from '../api';

export default function Deployment() {
  const [deployments, setDeployments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');

  // Fetch deployment data
  const fetchDeployments = async () => {
    setLoading(true);
    try {
      const response = await api.get('/deployment');
      setDeployments(response.data);
      setError(null);
    } catch (err) {
      console.error('Error fetching deployment data:', err);
      setError(err.message || 'Error fetching deployment data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDeployments();
  }, []);

  // Handle search
  const handleSearchChange = (event) => {
    setSearchTerm(event.target.value);
  };

  // Filter deployments based on search term
  const filteredDeployments = deployments.filter(deployment => {
    if (!searchTerm) return true;

    const term = searchTerm.toLowerCase();
    return (
      deployment.id.toLowerCase().includes(term) ||
      deployment.service.toLowerCase().includes(term) ||
      deployment.version.toLowerCase().includes(term) ||
      deployment.status.toLowerCase().includes(term)
    );
  });

  // Sort deployments by timestamp (newest first)
  const sortedDeployments = [...filteredDeployments].sort((a, b) =>
    new Date(b.timestamp) - new Date(a.timestamp)
  );

  // Get status color
  const getStatusColor = (status) => {
    if (!status) return 'default';

    switch (status.toLowerCase()) {
      case 'deployed':
        return 'success';
      case 'failed':
        return 'error';
      case 'pending':
        return 'warning';
      default:
        return 'default';
    }
  };

  // Get status icon
  const getStatusIcon = (status) => {
    if (!status) return null;

    switch (status.toLowerCase()) {
      case 'deployed':
        return <SuccessIcon />;
      case 'failed':
        return <FailedIcon />;
      case 'pending':
        return <PendingIcon />;
      default:
        return null;
    }
  };

  // Format timestamp
  const formatTimestamp = (timestamp) => {
    return new Date(timestamp).toLocaleString();
  };

  // Get deployment statistics
  const getDeploymentStats = () => {
    const total = deployments.length;
    const successful = deployments.filter(d => d.status.toLowerCase() === 'deployed').length;
    const failed = deployments.filter(d => d.status.toLowerCase() === 'failed').length;
    const pending = deployments.filter(d => d.status.toLowerCase() === 'pending').length;

    return { total, successful, failed, pending };
  };

  // Get services with deployment counts
  const getServiceDeployments = () => {
    const serviceMap = {};

    deployments.forEach(deployment => {
      if (!serviceMap[deployment.service]) {
        serviceMap[deployment.service] = {
          total: 0,
          successful: 0,
          failed: 0,
          pending: 0,
          lastDeployment: null
        };
      }

      serviceMap[deployment.service].total++;

      if (deployment.status.toLowerCase() === 'deployed') {
        serviceMap[deployment.service].successful++;
      } else if (deployment.status.toLowerCase() === 'failed') {
        serviceMap[deployment.service].failed++;
      } else if (deployment.status.toLowerCase() === 'pending') {
        serviceMap[deployment.service].pending++;
      }

      // Track the most recent deployment
      if (!serviceMap[deployment.service].lastDeployment ||
          new Date(deployment.timestamp) > new Date(serviceMap[deployment.service].lastDeployment.timestamp)) {
        serviceMap[deployment.service].lastDeployment = deployment;
      }
    });

    return Object.entries(serviceMap).map(([service, stats]) => ({
      service,
      ...stats
    }));
  };

  const stats = getDeploymentStats();
  const serviceDeployments = getServiceDeployments();

  return (
    <Container sx={{ mt: 4, mb: 4 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">
          Deployments
        </Typography>
        <Tooltip title="Refresh deployments">
          <IconButton onClick={fetchDeployments} disabled={loading}>
            <RefreshIcon />
          </IconButton>
        </Tooltip>
      </Box>

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
          <CircularProgress />
        </Box>
      ) : error ? (
        <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>
      ) : (
        <>
          {/* Deployment Statistics */}
          <Grid container spacing={3} sx={{ mb: 3 }}>
            <Grid item xs={12} md={3}>
              <Card>
                <CardContent sx={{ textAlign: 'center' }}>
                  <Typography variant="h6" color="text.secondary" gutterBottom>
                    Total Deployments
                  </Typography>
                  <Typography variant="h3">{stats.total}</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} md={3}>
              <Card>
                <CardContent sx={{ textAlign: 'center' }}>
                  <Typography variant="h6" color="success.main" gutterBottom>
                    Successful
                  </Typography>
                  <Typography variant="h3" color="success.main">{stats.successful}</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} md={3}>
              <Card>
                <CardContent sx={{ textAlign: 'center' }}>
                  <Typography variant="h6" color="error.main" gutterBottom>
                    Failed
                  </Typography>
                  <Typography variant="h3" color="error.main">{stats.failed}</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} md={3}>
              <Card>
                <CardContent sx={{ textAlign: 'center' }}>
                  <Typography variant="h6" color="warning.main" gutterBottom>
                    Pending
                  </Typography>
                  <Typography variant="h3" color="warning.main">{stats.pending}</Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>

          {/* Service Deployment Status */}
          <Card sx={{ mb: 3 }}>
            <CardHeader title="Service Deployment Status" />
            <Divider />
            <CardContent>
              <TableContainer>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Service</TableCell>
                      <TableCell>Last Version</TableCell>
                      <TableCell>Status</TableCell>
                      <TableCell>Last Deployed</TableCell>
                      <TableCell>Total Deployments</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {serviceDeployments.map((service) => (
                      <TableRow key={service.service} hover>
                        <TableCell>
                          <Box sx={{ display: 'flex', alignItems: 'center' }}>
                            <CodeIcon sx={{ mr: 1 }} />
                            <Typography>{service.service}</Typography>
                          </Box>
                        </TableCell>
                        <TableCell>{service.lastDeployment?.version}</TableCell>
                        <TableCell>
                          <Chip
                            icon={getStatusIcon(service.lastDeployment?.status)}
                            label={service.lastDeployment?.status}
                            color={getStatusColor(service.lastDeployment?.status)}
                            size="small"
                          />
                        </TableCell>
                        <TableCell>{formatTimestamp(service.lastDeployment?.timestamp)}</TableCell>
                        <TableCell>
                          <Box sx={{ display: 'flex', gap: 1 }}>
                            <Chip label={`${service.total} total`} size="small" variant="outlined" />
                            {service.failed > 0 && (
                              <Chip label={`${service.failed} failed`} size="small" color="error" variant="outlined" />
                            )}
                          </Box>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>

          {/* Deployment Search */}
          <Box sx={{ mb: 3 }}>
            <TextField
              fullWidth
              variant="outlined"
              placeholder="Search deployments..."
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
          </Box>

          {/* Deployment Timeline */}
          <Card>
            <CardHeader title="Deployment History" />
            <Divider />
            <CardContent>
              {sortedDeployments.length === 0 ? (
                <Alert severity="info">No deployments found matching your criteria</Alert>
              ) : (
                <Timeline position="alternate">
                  {sortedDeployments.map((deployment, index) => (
                    <TimelineItem key={deployment.id}>
                      <TimelineOppositeContent color="text.secondary">
                        {formatTimestamp(deployment.timestamp)}
                      </TimelineOppositeContent>
                      <TimelineSeparator>
                        <TimelineDot
                          color={getStatusColor(deployment.status)}
                          sx={{
                            p: 1,
                            '& .MuiSvgIcon-root': {
                              fontSize: '1rem',
                              color: 'inherit'
                            }
                          }}
                        >
                          <DeployIcon />
                        </TimelineDot>
                        {index < sortedDeployments.length - 1 && <TimelineConnector />}
                      </TimelineSeparator>
                      <TimelineContent>
                        <Paper elevation={3} sx={{ p: 2 }}>
                          <Typography variant="h6" component="span">
                            {deployment.service}
                          </Typography>
                          <Typography>Version: {deployment.version}</Typography>
                          <Box sx={{ mt: 1 }}>
                            <Chip
                              icon={getStatusIcon(deployment.status)}
                              label={deployment.status}
                              color={getStatusColor(deployment.status)}
                              size="small"
                            />
                          </Box>
                        </Paper>
                      </TimelineContent>
                    </TimelineItem>
                  ))}
                </Timeline>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </Container>
  );
}
