import React, { useState, useEffect } from 'react';
import axios from 'axios';

const PlayerManagement = () => {
  const [players, setPlayers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    fetchPlayers();
  }, []);

  const fetchPlayers = async () => {
    try {
      const response = await axios.get('/api/players/');
      setPlayers(response.data);
    } catch (error) {
      console.error('Error fetching players:', error);
      // Fallback data for development
      setPlayers([
        { id: 1, discord_name: 'PlayerOne', game_role: 'Tank', guild: 'Warborne Elite' },
        { id: 2, discord_name: 'PlayerTwo', game_role: 'DPS', guild: 'Warborne Elite' },
        { id: 3, discord_name: 'PlayerThree', game_role: 'Support', guild: 'Warborne Elite' }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const filteredPlayers = players.filter(player =>
    player.discord_name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  if (loading) {
    return (
      <div className="card">
        <h2>Loading Players...</h2>
      </div>
    );
  }

  return (
    <div>
      <div className="card">
        <h2>👥 Player Management</h2>
        <div className="search-bar">
          <input
            type="text"
            placeholder="Search players..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="search-input"
          />
        </div>
      </div>

      <div className="card">
        <h3>Player List ({filteredPlayers.length} players)</h3>
        <div className="table-container">
          <table className="players-table">
            <thead>
              <tr>
                <th>Discord Name</th>
                <th>Game Role</th>
                <th>Guild</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredPlayers.map(player => (
                <tr key={player.id}>
                  <td>{player.discord_name}</td>
                  <td>
                    <span className={`role-badge role-${player.game_role?.toLowerCase()}`}>
                      {player.game_role}
                    </span>
                  </td>
                  <td>{player.guild}</td>
                  <td>
                    <button className="btn btn-small">Edit</button>
                    <button className="btn btn-small btn-danger">Delete</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default PlayerManagement;
