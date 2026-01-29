const express = require('express');
const sqlite3 = require('sqlite3').verbose();
const bodyParser = require('body-parser');
const path = require('path');

const app = express();
const db = new sqlite3.Database(path.join(__dirname, 'users.db'));

let authenticatedUsers = new Set(); // Temporary in-memory store for authenticated sessions

// Middleware
app.use(bodyParser.json());
app.use(express.static(path.join(__dirname)));

// Create users table if it doesn't exist
db.run(`
  CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL
  )
`);

// Serve login.html for the login route
app.get('/login.html', (req, res) => {
  res.sendFile(path.join(__dirname, 'login.html'));
});

// Authentication check endpoint
app.get('/auth-check', (req, res) => {
  const sessionId = req.headers['authorization'];
  if (authenticatedUsers.has(sessionId)) {
    res.sendStatus(200);
  } else {
    res.sendStatus(401);
  }
});

// Login endpoint
app.post('/login', (req, res) => {
  const { username, password } = req.body;

  if (!username || !password) {
    return res.status(400).json({ success: false, message: 'Missing username or password' });
  }

  db.get('SELECT * FROM users WHERE username = ? AND password = ?', [username, password], (err, row) => {
    if (err) {
      return res.status(500).json({ success: false, message: 'Database error' });
    }

    if (row) {
      const sessionId = `${username}-${Date.now()}`;
      authenticatedUsers.add(sessionId);
      res.json({ success: true, sessionId });
    } else {
      res.status(401).json({ success: false, message: 'Invalid credentials' });
    }
  });
});

// Middleware to protect index.html
app.use('/index.html', (req, res, next) => {
  const sessionId = req.headers['authorization'];
  if (authenticatedUsers.has(sessionId)) {
    next();
  } else {
    res.redirect('/login.html');
  }
});

// Start server
const PORT = 3000;
app.listen(PORT, () => {
  console.log(`Server running on http://localhost:${PORT}`);
});
