import React, { useState, useEffect } from 'react';
import {
  Container,
  Typography,
  Grid,
  Card,
  CardContent,
  CardHeader,
  CircularProgress,
  Alert,
  Box,
  Paper,
  List,
  ListItem,
  ListItemText,
  Divider,
  Chip
} from '@mui/material';
import {
  CheckCircle as CheckCircleIcon,
  Warning as WarningIcon,
  Error as ErrorIcon,
  Info as InfoIcon
} from '@mui/icons-material';
import api from '../api';

export default function Dashboard() {
  const [agentStatus, setAgentStatus] = useState([]);
  const [metrics, setMetrics] = useState([]);
  const [rootCauses, setRootCauses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    // Create an array of promises for parallel API calls
    const fetchData = async () => {
      try {
        const [agentsRes, metricsRes, rootCauseRes] = await Promise.all([
          api.get('/agents'),
          api.get('/metrics'),
          api.get('/rootcause')
        ]);

        setAgentStatus(agentsRes.data);
        setMetrics(metricsRes.data);
        setRootCauses(rootCauseRes.data);
        setLoading(false);
      } catch (err) {
        console.error('Error fetching dashboard data:', err);
        setError(err.message || 'Error fetching dashboard data');
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  // Group metrics by service
  const metricsByService = metrics.reduce((acc, metric) => {
    if (!acc[metric.service]) {
      acc[metric.service] = [];
    }
    acc[metric.service].push(metric);
    return acc;
  }, {});

  // Get status icon based on agent status
  const getStatusIcon = (status) => {
    switch (status) {
      case 'active':
        return <CheckCircleIcon color="success" />;
      case 'warning':
        return <WarningIcon color="warning" />;
      case 'error':
        return <ErrorIcon color="error" />;
      default:
        return <InfoIcon color="info" />;
    }
  };

  return (
    <Container>
      <Typography variant="h4" gutterBottom>
        Dashboard
      </Typography>

      {loading && <CircularProgress />}
      {error && <Alert severity="error">{error}</Alert>}

      {!loading && !error && (
        <Grid container spacing={3}>
          {/* Agent Status Card */}
          <Grid item xs={12} md={6}>
            <Card>
              <CardHeader title="Agent Status" />
              <CardContent>
                {agentStatus.length === 0 ? (
                  <Alert severity="info">No agent data available</Alert>
                ) : (
                  <List>
                    {agentStatus.map((agent) => (
                      <React.Fragment key={agent.id}>
                        <ListItem>
                          <Box sx={{ mr: 2 }}>
                            {getStatusIcon(agent.status)}
                          </Box>
                          <ListItemText
                            primary={agent.name}
                            secondary={`Last seen: ${new Date(agent.lastSeen).toLocaleString()}`}
                          />
                          <Chip
                            label={agent.status}
                            color={agent.status === 'active' ? 'success' : 'error'}
                            size="small"
                          />
                        </ListItem>
                        <Divider />
                      </React.Fragment>
                    ))}
                  </List>
                )}
              </CardContent>
            </Card>
          </Grid>

          {/* Recent Root Causes Card */}
          <Grid item xs={12} md={6}>
            <Card>
              <CardHeader title="Recent Root Causes" />
              <CardContent>
                {rootCauses.length === 0 ? (
                  <Alert severity="info">No root cause data available</Alert>
                ) : (
                  <List>
                    {rootCauses.slice(0, 5).map((rc) => (
                      <React.Fragment key={rc.id}>
                        <ListItem>
                          <ListItemText
                            primary={`${rc.service} - ${rc.cause}`}
                            secondary={`Alert ID: ${rc.alertId} | ${new Date(rc.timestamp).toLocaleString()}`}
                          />
                          <Chip
                            label={`${Math.round(rc.confidence * 100)}%`}
                            color={rc.confidence > 0.7 ? 'success' : 'warning'}
                            size="small"
                          />
                        </ListItem>
                        <Divider />
                      </React.Fragment>
                    ))}
                  </List>
                )}
              </CardContent>
            </Card>
          </Grid>

          {/* Service Metrics Cards */}
          {Object.entries(metricsByService).map(([service, serviceMetrics]) => (
            <Grid item xs={12} md={6} lg={4} key={service}>
              <Card>
                <CardHeader title={`${service} Metrics`} />
                <CardContent>
                  <List dense>
                    {serviceMetrics.map((metric, index) => (
                      <React.Fragment key={index}>
                        <ListItem>
                          <ListItemText
                            primary={metric.name}
                            secondary={`Value: ${metric.value} | ${new Date(metric.timestamp).toLocaleString()}`}
                          />
                        </ListItem>
                        <Divider />
                      </React.Fragment>
                    ))}
                  </List>
                </CardContent>
              </Card>
            </Grid>
          ))}

          {/* System Overview Card */}
          <Grid item xs={12}>
            <Card>
              <CardHeader title="System Overview" />
              <CardContent>
                <Grid container spacing={2}>
                  <Grid item xs={6} md={3}>
                    <Paper elevation={2} sx={{ p: 2, textAlign: 'center' }}>
                      <Typography variant="h6">{agentStatus.length}</Typography>
                      <Typography variant="body2">Active Agents</Typography>
                    </Paper>
                  </Grid>
                  <Grid item xs={6} md={3}>
                    <Paper elevation={2} sx={{ p: 2, textAlign: 'center' }}>
                      <Typography variant="h6">{rootCauses.length}</Typography>
                      <Typography variant="body2">Root Causes</Typography>
                    </Paper>
                  </Grid>
                  <Grid item xs={6} md={3}>
                    <Paper elevation={2} sx={{ p: 2, textAlign: 'center' }}>
                      <Typography variant="h6">{Object.keys(metricsByService).length}</Typography>
                      <Typography variant="body2">Services</Typography>
                    </Paper>
                  </Grid>
                  <Grid item xs={6} md={3}>
                    <Paper elevation={2} sx={{ p: 2, textAlign: 'center' }}>
                      <Typography variant="h6">{metrics.length}</Typography>
                      <Typography variant="body2">Metrics</Typography>
                    </Paper>
                  </Grid>
                </Grid>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}
    </Container>
  );
}
