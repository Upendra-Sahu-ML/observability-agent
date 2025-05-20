import React, { useState, useEffect } from 'react';
import {
  Container,
  Typography,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  Chip,
  Box,
  Tab,
  Tabs,
  TextField,
  InputAdornment,
  CircularProgress,
  Alert,
  Button,
  IconButton,
  Tooltip,
  Card,
  CardContent,
  Grid
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import RefreshIcon from '@mui/icons-material/Refresh';
import VisibilityIcon from '@mui/icons-material/Visibility';
import api from '../api';

// TabPanel component for tab content
function TabPanel(props) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`alert-tabpanel-${index}`}
      aria-labelledby={`alert-tab-${index}`}
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

export default function AlertHistory() {
  const [value, setValue] = useState(0);
  const [alerts, setAlerts] = useState([]);
  const [activeAlerts, setActiveAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [selectedAlert, setSelectedAlert] = useState(null);

  // Fetch alerts on component mount
  useEffect(() => {
    fetchAlerts();
  }, []);

  // Function to fetch alerts from the API
  const fetchAlerts = async () => {
    setLoading(true);
    try {
      // Fetch historical alerts
      const historicalResponse = await api.get('/alerts/history');
      setAlerts(historicalResponse.data);
      
      // Fetch active alerts
      const activeResponse = await api.get('/alerts/active');
      setActiveAlerts(activeResponse.data);
    } catch (err) {
      console.error('Error fetching alerts:', err);
      setError(err.message || 'Failed to fetch alerts');
    } finally {
      setLoading(false);
    }
  };

  // Handle tab change
  const handleTabChange = (event, newValue) => {
    setValue(newValue);
  };

  // Handle page change
  const handleChangePage = (event, newPage) => {
    setPage(newPage);
  };

  // Handle rows per page change
  const handleChangeRowsPerPage = (event) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  // Handle search
  const handleSearch = (event) => {
    setSearchTerm(event.target.value);
    setPage(0);
  };

  // Handle refresh
  const handleRefresh = () => {
    fetchAlerts();
  };

  // Handle alert selection
  const handleAlertSelect = (alert) => {
    setSelectedAlert(alert);
  };

  // Filter alerts based on search term
  const filteredHistoricalAlerts = alerts.filter(alert => 
    alert.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
    alert.labels.alertname.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (alert.labels.service && alert.labels.service.toLowerCase().includes(searchTerm.toLowerCase())) ||
    (alert.labels.severity && alert.labels.severity.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  const filteredActiveAlerts = activeAlerts.filter(alert => 
    alert.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
    alert.labels.alertname.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (alert.labels.service && alert.labels.service.toLowerCase().includes(searchTerm.toLowerCase())) ||
    (alert.labels.severity && alert.labels.severity.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  // Get severity color
  const getSeverityColor = (severity) => {
    switch (severity?.toLowerCase()) {
      case 'critical':
        return 'error';
      case 'warning':
        return 'warning';
      case 'info':
        return 'info';
      default:
        return 'default';
    }
  };

  // Get status color
  const getStatusColor = (status) => {
    switch (status?.toLowerCase()) {
      case 'resolved':
        return 'success';
      case 'in_progress':
        return 'warning';
      case 'acknowledged':
        return 'info';
      case 'open':
        return 'error';
      default:
        return 'default';
    }
  };

  // Render alert details
  const renderAlertDetails = () => {
    if (!selectedAlert) return null;

    return (
      <Card sx={{ mt: 2 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Alert Details
          </Typography>
          <Grid container spacing={2}>
            <Grid item xs={12} md={6}>
              <Typography variant="subtitle2">Alert ID</Typography>
              <Typography variant="body2" gutterBottom>{selectedAlert.id}</Typography>
              
              <Typography variant="subtitle2">Alert Name</Typography>
              <Typography variant="body2" gutterBottom>{selectedAlert.labels.alertname}</Typography>
              
              <Typography variant="subtitle2">Service</Typography>
              <Typography variant="body2" gutterBottom>{selectedAlert.labels.service || 'N/A'}</Typography>
              
              <Typography variant="subtitle2">Severity</Typography>
              <Chip 
                label={selectedAlert.labels.severity || 'Unknown'} 
                color={getSeverityColor(selectedAlert.labels.severity)}
                size="small"
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <Typography variant="subtitle2">Status</Typography>
              <Chip 
                label={selectedAlert.status || 'Open'} 
                color={getStatusColor(selectedAlert.status)}
                size="small"
              />
              
              <Typography variant="subtitle2" sx={{ mt: 1 }}>Start Time</Typography>
              <Typography variant="body2" gutterBottom>
                {new Date(selectedAlert.startsAt).toLocaleString()}
              </Typography>
              
              {selectedAlert.endsAt && (
                <>
                  <Typography variant="subtitle2">End Time</Typography>
                  <Typography variant="body2" gutterBottom>
                    {new Date(selectedAlert.endsAt).toLocaleString()}
                  </Typography>
                </>
              )}
            </Grid>
            <Grid item xs={12}>
              <Typography variant="subtitle2">Description</Typography>
              <Typography variant="body2" gutterBottom>
                {selectedAlert.annotations?.description || 'No description available'}
              </Typography>
              
              {selectedAlert.annotations?.value && (
                <>
                  <Typography variant="subtitle2">Value</Typography>
                  <Typography variant="body2" gutterBottom>
                    {selectedAlert.annotations.value}
                  </Typography>
                </>
              )}
              
              {selectedAlert.annotations?.threshold && (
                <>
                  <Typography variant="subtitle2">Threshold</Typography>
                  <Typography variant="body2" gutterBottom>
                    {selectedAlert.annotations.threshold}
                  </Typography>
                </>
              )}
            </Grid>
          </Grid>
        </CardContent>
      </Card>
    );
  };

  return (
    <Container sx={{ mt: 4, mb: 4 }}>
      <Typography variant="h4" gutterBottom>
        Alert History
      </Typography>
      
      <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <TextField
          placeholder="Search alerts..."
          variant="outlined"
          size="small"
          value={searchTerm}
          onChange={handleSearch}
          sx={{ width: '300px' }}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon />
              </InputAdornment>
            ),
          }}
        />
        <Button
          variant="outlined"
          startIcon={<RefreshIcon />}
          onClick={handleRefresh}
          disabled={loading}
        >
          Refresh
        </Button>
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
            <Tabs value={value} onChange={handleTabChange} aria-label="alert tabs">
              <Tab label={`Active Alerts (${activeAlerts.length})`} id="alert-tab-0" />
              <Tab label={`Historical Alerts (${alerts.length})`} id="alert-tab-1" />
            </Tabs>
          </Box>
          
          <TabPanel value={value} index={0}>
            {filteredActiveAlerts.length === 0 ? (
              <Alert severity="info">No active alerts found</Alert>
            ) : (
              <TableContainer component={Paper}>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>Alert ID</TableCell>
                      <TableCell>Alert Name</TableCell>
                      <TableCell>Service</TableCell>
                      <TableCell>Severity</TableCell>
                      <TableCell>Status</TableCell>
                      <TableCell>Start Time</TableCell>
                      <TableCell>Actions</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {filteredActiveAlerts
                      .slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage)
                      .map((alert) => (
                        <TableRow key={alert.id} hover>
                          <TableCell>{alert.id}</TableCell>
                          <TableCell>{alert.labels.alertname}</TableCell>
                          <TableCell>{alert.labels.service || 'N/A'}</TableCell>
                          <TableCell>
                            <Chip 
                              label={alert.labels.severity || 'Unknown'} 
                              color={getSeverityColor(alert.labels.severity)}
                              size="small"
                            />
                          </TableCell>
                          <TableCell>
                            <Chip 
                              label={alert.status || 'Open'} 
                              color={getStatusColor(alert.status)}
                              size="small"
                            />
                          </TableCell>
                          <TableCell>{new Date(alert.startsAt).toLocaleString()}</TableCell>
                          <TableCell>
                            <Tooltip title="View Details">
                              <IconButton size="small" onClick={() => handleAlertSelect(alert)}>
                                <VisibilityIcon fontSize="small" />
                              </IconButton>
                            </Tooltip>
                          </TableCell>
                        </TableRow>
                      ))}
                  </TableBody>
                </Table>
                <TablePagination
                  rowsPerPageOptions={[5, 10, 25]}
                  component="div"
                  count={filteredActiveAlerts.length}
                  rowsPerPage={rowsPerPage}
                  page={page}
                  onPageChange={handleChangePage}
                  onRowsPerPageChange={handleChangeRowsPerPage}
                />
              </TableContainer>
            )}
          </TabPanel>
          
          <TabPanel value={value} index={1}>
            {filteredHistoricalAlerts.length === 0 ? (
              <Alert severity="info">No historical alerts found</Alert>
            ) : (
              <TableContainer component={Paper}>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>Alert ID</TableCell>
                      <TableCell>Alert Name</TableCell>
                      <TableCell>Service</TableCell>
                      <TableCell>Severity</TableCell>
                      <TableCell>Status</TableCell>
                      <TableCell>Start Time</TableCell>
                      <TableCell>End Time</TableCell>
                      <TableCell>Actions</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {filteredHistoricalAlerts
                      .slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage)
                      .map((alert) => (
                        <TableRow key={alert.id} hover>
                          <TableCell>{alert.id}</TableCell>
                          <TableCell>{alert.labels.alertname}</TableCell>
                          <TableCell>{alert.labels.service || 'N/A'}</TableCell>
                          <TableCell>
                            <Chip 
                              label={alert.labels.severity || 'Unknown'} 
                              color={getSeverityColor(alert.labels.severity)}
                              size="small"
                            />
                          </TableCell>
                          <TableCell>
                            <Chip 
                              label={alert.status || 'Resolved'} 
                              color={getStatusColor(alert.status)}
                              size="small"
                            />
                          </TableCell>
                          <TableCell>{new Date(alert.startsAt).toLocaleString()}</TableCell>
                          <TableCell>
                            {alert.endsAt ? new Date(alert.endsAt).toLocaleString() : 'N/A'}
                          </TableCell>
                          <TableCell>
                            <Tooltip title="View Details">
                              <IconButton size="small" onClick={() => handleAlertSelect(alert)}>
                                <VisibilityIcon fontSize="small" />
                              </IconButton>
                            </Tooltip>
                          </TableCell>
                        </TableRow>
                      ))}
                  </TableBody>
                </Table>
                <TablePagination
                  rowsPerPageOptions={[5, 10, 25]}
                  component="div"
                  count={filteredHistoricalAlerts.length}
                  rowsPerPage={rowsPerPage}
                  page={page}
                  onPageChange={handleChangePage}
                  onRowsPerPageChange={handleChangeRowsPerPage}
                />
              </TableContainer>
            )}
          </TabPanel>
          
          {selectedAlert && renderAlertDetails()}
        </>
      )}
    </Container>
  );
}
