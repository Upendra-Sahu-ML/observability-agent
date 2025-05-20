import React, { useState, useEffect } from 'react';
import { Container, Typography, List, ListItem, CircularProgress, Alert } from '@mui/material';
import api from '../api';

export default function Agents() {
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.get('/agents')
      .then(res => setAgents(res.data))
      .catch(err => setError(err.message || 'Error fetching agents'))
      .finally(() => setLoading(false));
  }, []);

  return (
    <Container sx={{ mt: 4 }}>
      <Typography variant="h4" gutterBottom>Agents</Typography>
      {loading && <CircularProgress />}
      {error && <Alert severity="error">{error}</Alert>}
      <List>
        {agents.map(agent => (
          <ListItem key={agent.id}>{agent.name}</ListItem>
        ))}
      </List>
    </Container>
  );
}
