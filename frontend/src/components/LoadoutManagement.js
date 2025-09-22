import React, { useState, useEffect } from 'react';
import axios from 'axios';

const LoadoutManagement = () => {
  const [loadouts, setLoadouts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchLoadouts();
  }, []);

  const fetchLoadouts = async () => {
    try {
      const response = await axios.get('/api/loadouts/');
      setLoadouts(response.data);
    } catch (error) {
      console.error('Error fetching loadouts:', error);
      // Fallback data for development
      setLoadouts([
        { id: 1, name: 'Tank Build', player: 'PlayerOne', gear_count: 8 },
        { id: 2, name: 'DPS Build', player: 'PlayerTwo', gear_count: 6 },
        { id: 3, name: 'Support Build', player: 'PlayerThree', gear_count: 7 }
      ]);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="card">
        <h2>Loading Loadouts...</h2>
      </div>
    );
  }

  return (
    <div>
      <div className="card">
        <h2>⚔️ Loadout Management</h2>
        <p>Manage player loadouts and gear configurations</p>
      </div>

      <div className="card">
        <h3>Loadout List ({loadouts.length} loadouts)</h3>
        <div className="loadouts-grid">
          {loadouts.map(loadout => (
            <div key={loadout.id} className="loadout-card">
              <h4>{loadout.name}</h4>
              <p><strong>Player:</strong> {loadout.player}</p>
              <p><strong>Gear Items:</strong> {loadout.gear_count}</p>
              <div className="loadout-actions">
                <button className="btn btn-small">View</button>
                <button className="btn btn-small">Edit</button>
                <button className="btn btn-small btn-danger">Delete</button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default LoadoutManagement;
