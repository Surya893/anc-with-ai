/**
 * WebSocket Client for Real-Time Audio Streaming
 * Uses Socket.IO for bidirectional communication
 */

const WS_URL = process.env.REACT_APP_WS_URL || 'ws://localhost:5000';

class WebSocketClient {
    constructor(url) {
        this.url = url;
        this.socket = null;
        this.sessionId = null;
        this.callbacks = {
            connected: [],
            disconnected: [],
            processed_audio: [],
            metrics_update: [],
            error: []
        };
    }

    /**
     * Connect to WebSocket server
     */
    connect() {
        if (this.socket && this.socket.connected) {
            console.log('Already connected');
            return;
        }

        this.socket = io(this.url, {
            transports: ['websocket', 'polling'],
            reconnection: true,
            reconnectionDelay: 1000,
            reconnectionAttempts: 5
        });

        // Setup event listeners
        this.socket.on('connect', () => {
            console.log('WebSocket connected');
            this._trigger('connected');
        });

        this.socket.on('disconnect', () => {
            console.log('WebSocket disconnected');
            this._trigger('disconnected');
        });

        this.socket.on('processed_audio', (data) => {
            this._trigger('processed_audio', data);
        });

        this.socket.on('metrics_update', (data) => {
            this._trigger('metrics_update', data);
        });

        this.socket.on('error', (error) => {
            console.error('WebSocket error:', error);
            this._trigger('error', error);
        });
    }

    /**
     * Disconnect from server
     */
    disconnect() {
        if (this.socket) {
            this.socket.disconnect();
            this.socket = null;
        }
    }

    /**
     * Join audio processing session
     */
    joinSession(sessionId) {
        this.sessionId = sessionId;
        this.socket.emit('join_session', { session_id: sessionId });
    }

    /**
     * Leave current session
     */
    leaveSession() {
        if (this.sessionId) {
            this.socket.emit('leave_session', { session_id: this.sessionId });
            this.sessionId = null;
        }
    }

    /**
     * Send audio chunk for processing
     */
    sendAudioChunk(audioData, options = {}) {
        if (!this.sessionId) {
            console.error('No active session');
            return;
        }

        this.socket.emit('audio_chunk', {
            session_id: this.sessionId,
            audio_data: audioData,
            sample_rate: options.sample_rate || 48000,
            algorithm: options.algorithm || 'nlms',
            intensity: options.intensity || 1.0,
            chunk_index: options.chunk_index || 0
        });
    }

    /**
     * Request metrics update
     */
    requestMetrics() {
        if (!this.sessionId) {
            console.error('No active session');
            return;
        }

        this.socket.emit('request_metrics', {
            session_id: this.sessionId
        });
    }

    /**
     * Register event callback
     */
    on(event, callback) {
        if (this.callbacks[event]) {
            this.callbacks[event].push(callback);
        }
    }

    /**
     * Unregister event callback
     */
    off(event, callback) {
        if (this.callbacks[event]) {
            this.callbacks[event] = this.callbacks[event].filter(cb => cb !== callback);
        }
    }

    /**
     * Trigger event callbacks
     */
    _trigger(event, data) {
        if (this.callbacks[event]) {
            this.callbacks[event].forEach(callback => callback(data));
        }
    }

    /**
     * Check if connected
     */
    isConnected() {
        return this.socket && this.socket.connected;
    }
}

// Export singleton instance
const wsClient = new WebSocketClient(WS_URL);

// For vanilla JS
if (typeof window !== 'undefined') {
    window.wsClient = wsClient;
}

// For ES modules
export default wsClient;
