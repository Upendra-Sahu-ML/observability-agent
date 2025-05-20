import React from 'react';
import {
  AppBar,
  Toolbar,
  Typography,
  Drawer,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Box,
  ListItemButton
} from '@mui/material';
import { useLocation, Link as RouterLink } from 'react-router-dom';
import DashboardIcon from '@mui/icons-material/Dashboard';
import NotificationsIcon from '@mui/icons-material/Notifications';
import PeopleIcon from '@mui/icons-material/People';
import BarChartIcon from '@mui/icons-material/BarChart';
import SubjectIcon from '@mui/icons-material/Subject';
import CloudIcon from '@mui/icons-material/Cloud';
import BugReportIcon from '@mui/icons-material/BugReport';
import TimelineIcon from '@mui/icons-material/Timeline';
import EmailIcon from '@mui/icons-material/Email';
import AssignmentIcon from '@mui/icons-material/Assignment';
import MenuBookIcon from '@mui/icons-material/MenuBook';
import LibraryBooksIcon from '@mui/icons-material/LibraryBooks';
import StorageIcon from '@mui/icons-material/Storage';
import CodeIcon from '@mui/icons-material/Code';

const navItems = [
  { label: 'Dashboard', path: '/', icon: <DashboardIcon /> },
  { label: 'Alerts', path: '/alerts', icon: <NotificationsIcon /> },
  { label: 'Agents', path: '/agents', icon: <PeopleIcon /> },
  { label: 'Metrics', path: '/metrics', icon: <BarChartIcon /> },
  { label: 'Logs', path: '/logs', icon: <SubjectIcon /> },
  { label: 'Deployment', path: '/deployment', icon: <CloudIcon /> },
  { label: 'Root Cause', path: '/rootcause', icon: <BugReportIcon /> },
  { label: 'Tracing', path: '/tracing', icon: <TimelineIcon /> },
  { label: 'Notification', path: '/notification', icon: <EmailIcon /> },
  { label: 'Postmortem', path: '/postmortem', icon: <AssignmentIcon /> },
  { label: 'Runbooks', path: '/runbook', icon: <MenuBookIcon /> },
  { label: 'Runbook Manager', path: '/runbook-manager', icon: <LibraryBooksIcon /> },
  { label: 'Knowledge Base', path: '/knowledge-base', icon: <StorageIcon /> },
  { label: 'K8s Commands', path: '/k8s-command', icon: <CodeIcon /> },
];

// Drawer width
const drawerWidth = 240;

export default function Navbar() {
  const location = useLocation();

  return (
    <>
      <AppBar
        position="fixed"
        sx={{
          zIndex: (theme) => theme.zIndex.drawer + 1,
          width: `calc(100% - ${drawerWidth}px)`,
          ml: `${drawerWidth}px`
        }}
      >
        <Toolbar>
          <Typography variant="h6" noWrap component="div">
            Observability Agent
          </Typography>
        </Toolbar>
      </AppBar>
      <Drawer
        variant="permanent"
        sx={{
          width: drawerWidth,
          flexShrink: 0,
          [`& .MuiDrawer-paper`]: {
            width: drawerWidth,
            boxSizing: 'border-box',
            backgroundColor: (theme) => theme.palette.background.default,
          },
        }}
      >
        <Toolbar /> {/* This empty toolbar creates space for the AppBar */}
        <Box sx={{ overflow: 'auto' }}>
          <List>
            {navItems.map((item) => {
              const isSelected = location.pathname === item.path;
              return (
                <ListItem key={item.path} disablePadding>
                  <ListItemButton
                    component={RouterLink}
                    to={item.path}
                    sx={{
                      backgroundColor: isSelected
                        ? (theme) => theme.palette.primary.light
                        : 'transparent',
                      color: isSelected
                        ? (theme) => theme.palette.primary.contrastText
                        : (theme) => theme.palette.text.primary,
                      '&:hover': {
                        backgroundColor: isSelected
                          ? (theme) => theme.palette.primary.main
                          : (theme) => theme.palette.action.hover,
                      },
                    }}
                  >
                    <ListItemIcon sx={{
                      color: isSelected
                        ? (theme) => theme.palette.primary.contrastText
                        : (theme) => theme.palette.text.primary
                    }}>
                      {item.icon}
                    </ListItemIcon>
                    <ListItemText primary={item.label} />
                  </ListItemButton>
                </ListItem>
              );
            })}
          </List>
        </Box>
      </Drawer>
    </>
  );
}
