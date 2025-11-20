# Frontend Layer

## Overview

This is the frontend web application for the ANC Platform. It provides a user interface for real-time audio processing and visualization.

## Architecture

```
frontend/
├── public/                 # Static assets
│   ├── index.html
│   ├── favicon.ico
│   └── assets/
├── src/                    # Source code
│   ├── components/        # React components
│   │   ├── AudioPlayer.jsx
│   │   ├── AudioVisualizer.jsx
│   │   ├── ControlPanel.jsx
│   │   └── MetricsDisplay.jsx
│   ├── services/          # API clients
│   │   ├── api.js         # REST API client
│   │   └── websocket.js   # WebSocket client
│   ├── utils/             # Utilities
│   │   └── audio.js
│   ├── App.jsx            # Main app component
│   ├── index.jsx          # Entry point
│   └── styles.css         # Global styles
├── package.json
└── README.md
```

## Technology Stack

- **Framework**: React 18+ (or vanilla HTML/JS)
- **Audio**: Web Audio API
- **Visualization**: Canvas API / D3.js
- **WebSocket**: Socket.IO client
- **HTTP**: Axios
- **Build**: Vite / Webpack

## Features

1. **Real-Time Audio Processing**
   - Microphone input capture
   - WebSocket streaming to backend
   - Real-time ANC processing
   - Playback of processed audio

2. **Audio Visualization**
   - Waveform display
   - Frequency spectrum
   - Before/After comparison

3. **Control Panel**
   - ANC on/off toggle
   - Algorithm selection (NLMS, LMS, RLS)
   - Intensity slider
   - Session management

4. **Metrics Display**
   - Noise reduction (dB)
   - Processing latency
   - Noise classification
   - Emergency alerts

## Environment Variables

Create a `.env` file:

```bash
# Backend API
REACT_APP_API_URL=http://localhost:5000
REACT_APP_WS_URL=ws://localhost:5000

# Environment
REACT_APP_ENV=development
```

## Installation

```bash
# Install dependencies
npm install

# Or with yarn
yarn install
```

## Development

```bash
# Start development server
npm start

# Runs on http://localhost:3000
```

## Build for Production

```bash
# Create production build
npm run build

# Output in ./build or ./dist
```

## API Integration

### REST API Client

```javascript
import api from './services/api';

// Process audio
const result = await api.processAudio({
  audio_data: base64Audio,
  sample_rate: 48000,
  algorithm: 'nlms'
});
```

### WebSocket Client

```javascript
import { socket } from './services/websocket';

// Connect to server
socket.connect();

// Join session
socket.emit('join_session', { session_id });

// Send audio chunk
socket.emit('audio_chunk', {
  session_id,
  audio_data: base64Audio,
  sample_rate: 48000
});

// Receive processed audio
socket.on('processed_audio', (data) => {
  playAudio(data.processed_audio);
});
```

## Key Components

### AudioPlayer
Handles microphone input and audio playback

### AudioVisualizer
Renders waveforms and frequency spectrum

### ControlPanel
UI controls for ANC settings

### MetricsDisplay
Shows real-time metrics and statistics

## Testing

```bash
# Run tests
npm test

# Run with coverage
npm run test:coverage
```

## Browser Support

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+

Requires Web Audio API and WebSocket support.
