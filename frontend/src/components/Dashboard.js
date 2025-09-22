import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
  Box,
  Card,
  CardContent,
  Grid,
  Typography,
  Paper,
  Button,
  Chip,
  Avatar,
  List,
  ListItem,
  ListItemAvatar,
  ListItemText,
  Divider,
  LinearProgress,
} from '@mui/material';
import {
  People as PeopleIcon,
  Groups as GroupsIcon,
  Inventory as InventoryIcon,
  TrendingUp as TrendingUpIcon,
  Add as AddIcon,
  Assessment as AssessmentIcon,
  Notifications as NotificationsIcon,
} from '@mui/icons-material';

const Dashboard = () => {
  const [stats, setStats] = useState({
    totalPlayers: 0,
    totalGuilds: 0,
    totalLoadouts: 0,
    activePlayers: 0
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboardStats();
  }, []);

  const fetchDashboardStats = async () => {
    try {
      // This will connect to your Django API
      const response = await axios.get('/api/dashboard/stats/');
      setStats(response.data);
    } catch (error) {
      console.error('Error fetching dashboard stats:', error);
      // Fallback data for development
      setStats({
        totalPlayers: 42,
        totalGuilds: 3,
        totalLoadouts: 156,
        activePlayers: 28
      });
    } finally {
      setLoading(false);
    }
  };

  const StatCard = ({ title, value, icon, color, trend }) => (
    <Card>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
          <Avatar sx={{ bgcolor: color, mr: 2 }}>
            {icon}
          </Avatar>
          <Box>
            <Typography color="textSecondary" gutterBottom variant="h6">
              {title}
            </Typography>
            <Typography variant="h4" component="div">
              {value}
            </Typography>
          </Box>
        </Box>
        {trend && (
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <TrendingUpIcon sx={{ color: 'success.main', mr: 1 }} />
            <Typography variant="body2" color="success.main">
              {trend}
            </Typography>
          </Box>
        )}
      </CardContent>
    </Card>
  );

  if (loading) {
    return (
      <Box>
        <Typography variant="h4" gutterBottom>
          Loading Dashboard...
        </Typography>
        <LinearProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Dashboard
      </Typography>
      
      <Grid container spacing={3}>
        {/* Stats Cards */}
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Total Players"
            value={stats.totalPlayers}
            icon={<PeopleIcon />}
            color="primary.main"
            trend="+25% Last 30 days"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Total Guilds"
            value={stats.totalGuilds}
            icon={<GroupsIcon />}
            color="secondary.main"
            trend="+5% Last 30 days"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Total Loadouts"
            value={stats.totalLoadouts}
            icon={<InventoryIcon />}
            color="success.main"
            trend="+35% Last 30 days"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Active Players"
            value={stats.activePlayers}
            icon={<TrendingUpIcon />}
            color="warning.main"
            trend="+15% Last 30 days"
          />
        </Grid>

        {/* Quick Actions */}
        <Grid item xs={12} md={8}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Quick Actions
              </Typography>
              <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
                <Button
                  variant="contained"
                  startIcon={<AddIcon />}
                  sx={{ mb: 1 }}
                >
                  Add New Player
                </Button>
                <Button
                  variant="outlined"
                  startIcon={<InventoryIcon />}
                  sx={{ mb: 1 }}
                >
                  Create Loadout
                </Button>
                <Button
                  variant="outlined"
                  startIcon={<GroupsIcon />}
                  sx={{ mb: 1 }}
                >
                  Manage Guild
                </Button>
                <Button
                  variant="outlined"
                  startIcon={<AssessmentIcon />}
                  sx={{ mb: 1 }}
                >
                  View Reports
                </Button>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Recent Activity */}
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Recent Activity
              </Typography>
              <List>
                <ListItem>
                  <ListItemAvatar>
                    <Avatar sx={{ bgcolor: 'primary.main' }}>
                      <PeopleIcon />
                    </Avatar>
                  </ListItemAvatar>
                  <ListItemText
                    primary="New player joined"
                    secondary="PlayerOne joined Warborne Elite"
                  />
                </ListItem>
                <Divider />
                <ListItem>
                  <ListItemAvatar>
                    <Avatar sx={{ bgcolor: 'success.main' }}>
                      <InventoryIcon />
                    </Avatar>
                  </ListItemAvatar>
                  <ListItemText
                    primary="Loadout created"
                    secondary="Tank Build by PlayerTwo"
                  />
                </ListItem>
                <Divider />
                <ListItem>
                  <ListItemAvatar>
                    <Avatar sx={{ bgcolor: 'warning.main' }}>
                      <NotificationsIcon />
                    </Avatar>
                  </ListItemAvatar>
                  <ListItemText
                    primary="Guild event"
                    secondary="Raid scheduled for tomorrow"
                  />
                </ListItem>
              </List>
            </CardContent>
          </Card>
        </Grid>

        {/* System Status */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                System Status
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={12} sm={4}>
                  <Box sx={{ textAlign: 'center' }}>
                    <Chip label="Online" color="success" />
                    <Typography variant="body2" color="textSecondary">
                      Discord Bot
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={12} sm={4}>
                  <Box sx={{ textAlign: 'center' }}>
                    <Chip label="Online" color="success" />
                    <Typography variant="body2" color="textSecondary">
                      Database
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={12} sm={4}>
                  <Box sx={{ textAlign: 'center' }}>
                    <Chip label="Online" color="success" />
                    <Typography variant="body2" color="textSecondary">
                      API Services
                    </Typography>
                  </Box>
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default Dashboard;
