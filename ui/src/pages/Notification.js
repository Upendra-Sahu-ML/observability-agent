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
  TextField,
  InputAdornment,
  CircularProgress,
  Alert,
  Chip,
  IconButton,
  Tooltip,
  Card,
  CardHeader,
  CardContent,
  Grid,
  Divider,
  MenuItem,
  Select,
  FormControl,
  InputLabel
} from '@mui/material';
import { Search as SearchIcon, Refresh as RefreshIcon } from '@mui/icons-material';
import api from '../api';

export default function Notification() {
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [channelFilter, setChannelFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [selectedNotification, setSelectedNotification] = useState(null);

  // Fetch notifications from the API
  const fetchNotifications = async () => {
    setLoading(true);
    try {
      const response = await api.get('/notification');
      setNotifications(response.data);
      setError(null);
    } catch (err) {
      console.error('Error fetching notification data:', err);
      setError(err.message || 'Failed to fetch notification data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchNotifications();
  }, []);

  // Handle search
  const handleSearch = (event) => {
    setSearchTerm(event.target.value);
  };

  // Handle channel filter change
  const handleChannelFilterChange = (event) => {
    setChannelFilter(event.target.value);
  };

  // Handle status filter change
  const handleStatusFilterChange = (event) => {
    setStatusFilter(event.target.value);
  };

  // Handle notification selection
  const handleNotificationSelect = (notification) => {
    setSelectedNotification(notification);
  };

  // Filter notifications based on search term and filters
  const filteredNotifications = notifications.filter(notification => {
    const matchesSearch =
      notification.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      notification.message.toLowerCase().includes(searchTerm.toLowerCase()) ||
      notification.recipient.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (notification.alertId && notification.alertId.toLowerCase().includes(searchTerm.toLowerCase()));

    const matchesChannel = !channelFilter || notification.channel === channelFilter;
    const matchesStatus = !statusFilter || notification.status === statusFilter;

    return matchesSearch && matchesChannel && matchesStatus;
  });

  // Get unique channels and statuses for filtering
  const channels = [...new Set(notifications.map(n => n.channel))].sort();
  const statuses = [...new Set(notifications.map(n => n.status))].sort();

  // Get status color
  const getStatusColor = (status) => {
    switch (status.toLowerCase()) {
      case 'sent':
        return 'success';
      case 'pending':
        return 'warning';
      case 'failed':
        return 'error';
      default:
        return 'default';
    }
  };

  // Get channel icon/color
  const getChannelChip = (channel) => {
    switch (channel.toLowerCase()) {
      case 'slack':
        return <Chip label="Slack" size="small" color="primary" />;
      case 'email':
        return <Chip label="Email" size="small" color="secondary" />;
      case 'sms':
        return <Chip label="SMS" size="small" color="info" />;
      case 'pagerduty':
        return <Chip label="PagerDuty" size="small" color="warning" />;
      default:
        return <Chip label={channel} size="small" />;
    }
  };

  return (
    <Container sx={{ mt: 4 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">
          Notification Events
        </Typography>
        <Tooltip title="Refresh notifications">
          <IconButton onClick={fetchNotifications} disabled={loading}>
            <RefreshIcon />
          </IconButton>
        </Tooltip>
      </Box>

      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} md={6}>
          <TextField
            fullWidth
            variant="outlined"
            placeholder="Search notifications..."
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
        <Grid item xs={12} md={3}>
          <FormControl fullWidth variant="outlined">
            <InputLabel id="channel-filter-label">Channel</InputLabel>
            <Select
              labelId="channel-filter-label"
              value={channelFilter}
              onChange={handleChannelFilterChange}
              label="Channel"
            >
              <MenuItem value="">All Channels</MenuItem>
              {channels.map(channel => (
                <MenuItem key={channel} value={channel}>{channel}</MenuItem>
              ))}
            </Select>
          </FormControl>
        </Grid>
        <Grid item xs={12} md={3}>
          <FormControl fullWidth variant="outlined">
            <InputLabel id="status-filter-label">Status</InputLabel>
            <Select
              labelId="status-filter-label"
              value={statusFilter}
              onChange={handleStatusFilterChange}
              label="Status"
            >
              <MenuItem value="">All Statuses</MenuItem>
              {statuses.map(status => (
                <MenuItem key={status} value={status}>{status}</MenuItem>
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
      ) : (
        <Grid container spacing={3}>
          {/* Notifications Table */}
          <Grid item xs={12} md={selectedNotification ? 8 : 12}>
            {filteredNotifications.length === 0 ? (
              <Alert severity="info">No notifications found matching your criteria</Alert>
            ) : (
              <TableContainer component={Paper}>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>ID</TableCell>
                      <TableCell>Alert ID</TableCell>
                      <TableCell>Channel</TableCell>
                      <TableCell>Recipient</TableCell>
                      <TableCell>Status</TableCell>
                      <TableCell>Timestamp</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {filteredNotifications.map((notification) => (
                      <TableRow
                        key={notification.id}
                        hover
                        onClick={() => handleNotificationSelect(notification)}
                        sx={{
                          cursor: 'pointer',
                          bgcolor: selectedNotification && selectedNotification.id === notification.id ? 'action.selected' : 'inherit'
                        }}
                      >
                        <TableCell>{notification.id}</TableCell>
                        <TableCell>{notification.alertId || '-'}</TableCell>
                        <TableCell>{getChannelChip(notification.channel)}</TableCell>
                        <TableCell>{notification.recipient}</TableCell>
                        <TableCell>
                          <Chip
                            label={notification.status}
                            size="small"
                            color={getStatusColor(notification.status)}
                          />
                        </TableCell>
                        <TableCell>{new Date(notification.timestamp).toLocaleString()}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            )}
          </Grid>

          {/* Notification Details */}
          {selectedNotification && (
            <Grid item xs={12} md={4}>
              <Card>
                <CardHeader
                  title="Notification Details"
                  subheader={`ID: ${selectedNotification.id}`}
                />
                <Divider />
                <CardContent>
                  <Typography variant="subtitle1" gutterBottom>Message</Typography>
                  <Paper variant="outlined" sx={{ p: 2, mb: 2, bgcolor: 'background.default' }}>
                    <Typography variant="body2">{selectedNotification.message}</Typography>
                  </Paper>

                  <Grid container spacing={2}>
                    <Grid item xs={6}>
                      <Typography variant="subtitle2">Channel</Typography>
                      <Typography variant="body2">{selectedNotification.channel}</Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="subtitle2">Recipient</Typography>
                      <Typography variant="body2">{selectedNotification.recipient}</Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="subtitle2">Status</Typography>
                      <Chip
                        label={selectedNotification.status}
                        size="small"
                        color={getStatusColor(selectedNotification.status)}
                      />
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="subtitle2">Timestamp</Typography>
                      <Typography variant="body2">
                        {new Date(selectedNotification.timestamp).toLocaleString()}
                      </Typography>
                    </Grid>
                    {selectedNotification.alertId && (
                      <Grid item xs={12}>
                        <Typography variant="subtitle2">Alert ID</Typography>
                        <Typography variant="body2">{selectedNotification.alertId}</Typography>
                      </Grid>
                    )}
                  </Grid>
                </CardContent>
              </Card>
            </Grid>
          )}
        </Grid>
      )}
    </Container>
  );
}
