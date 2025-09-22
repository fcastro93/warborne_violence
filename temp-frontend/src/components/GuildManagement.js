import React, { useState, useEffect } from 'react';
import axios from 'axios';

const GuildManagement = () => {
  const [guilds, setGuilds] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchGuilds();
  }, []);

  const fetchGuilds = async () => {
    try {
      const response = await axios.get('/api/guilds/');
      setGuilds(response.data);
    } catch (error) {
      console.error('Error fetching guilds:', error);
      // Fallback data for development
      setGuilds([
        { id: 1, name: 'Warborne Elite', member_count: 15, description: 'Elite guild for experienced players' },
        { id: 2, name: 'Warborne Warriors', member_count: 12, description: 'Warrior-focused guild' },
        { id: 3, name: 'Warborne Support', member_count: 8, description: 'Support and healing focused' }
      ]);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="card">
        <h2>Loading Guilds...</h2>
      </div>
    );
  }

  return (
    <div>
      <div className="card">
        <h2>🏰 Guild Management</h2>
        <p>Manage guild information and member statistics</p>
      </div>

      <div className="card">
        <h3>Guild List ({guilds.length} guilds)</h3>
        <div className="guilds-grid">
          {guilds.map(guild => (
            <div key={guild.id} className="guild-card">
              <h4>{guild.name}</h4>
              <p><strong>Members:</strong> {guild.member_count}</p>
              <p><strong>Description:</strong> {guild.description}</p>
              <div className="guild-actions">
                <button className="btn btn-small">View Members</button>
                <button className="btn btn-small">Edit Guild</button>
                <button className="btn btn-small btn-danger">Delete</button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default GuildManagement;
