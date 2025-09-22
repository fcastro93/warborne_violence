import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import './App.css';

// Components
import Dashboard from './components/Dashboard';
import PlayerManagement from './components/PlayerManagement';
import LoadoutManagement from './components/LoadoutManagement';
import GuildManagement from './components/GuildManagement';

function App() {
  return (
    <Router>
      <div className="App">
        <nav className="navbar">
          <div className="container">
            <div className="nav-brand">
              <h1>⚔️ Warborne Guild Tools</h1>
            </div>
            <div className="nav-links">
              <Link to="/" className="nav-link">Dashboard</Link>
              <Link to="/players" className="nav-link">Players</Link>
              <Link to="/loadouts" className="nav-link">Loadouts</Link>
              <Link to="/guilds" className="nav-link">Guilds</Link>
              <Link to="/admin/" className="nav-link" target="_blank">Admin</Link>
            </div>
          </div>
        </nav>

        <main className="main-content">
          <div className="container">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/players" element={<PlayerManagement />} />
              <Route path="/loadouts" element={<LoadoutManagement />} />
              <Route path="/guilds" element={<GuildManagement />} />
            </Routes>
          </div>
        </main>
      </div>
    </Router>
  );
}

export default App;
