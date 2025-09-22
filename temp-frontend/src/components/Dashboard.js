import React, { useState, useEffect } from 'react';
import axios from 'axios';

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

  if (loading) {
    return (
      <div className="card">
        <h2>Loading Dashboard...</h2>
      </div>
    );
  }

  return (
    <div>
      <div className="card">
        <h2>📊 Guild Dashboard</h2>
        <p>Welcome to the Warborne Guild Management System</p>
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <h3>👥 Total Players</h3>
          <div className="stat-number">{stats.totalPlayers}</div>
        </div>
        <div className="stat-card">
          <h3>🏰 Total Guilds</h3>
          <div className="stat-number">{stats.totalGuilds}</div>
        </div>
        <div className="stat-card">
          <h3>⚔️ Total Loadouts</h3>
          <div className="stat-number">{stats.totalLoadouts}</div>
        </div>
        <div className="stat-card">
          <h3>🟢 Active Players</h3>
          <div className="stat-number">{stats.activePlayers}</div>
        </div>
      </div>

      <div className="card">
        <h3>🚀 Quick Actions</h3>
        <div className="quick-actions">
          <button className="btn">Add New Player</button>
          <button className="btn">Create Loadout</button>
          <button className="btn">Manage Guild</button>
          <button className="btn">View Reports</button>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
