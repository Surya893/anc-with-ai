/**
 * REST API Client
 * Handles all HTTP requests to the backend
 */

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';

class APIClient {
    constructor(baseURL) {
        this.baseURL = baseURL;
        this.apiKey = localStorage.getItem('api_key') || '';
    }

    /**
     * Set API key for authentication
     */
    setApiKey(key) {
        this.apiKey = key;
        localStorage.setItem('api_key', key);
    }

    /**
     * Make HTTP request
     */
    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;

        const headers = {
            'Content-Type': 'application/json',
            ...options.headers
        };

        if (this.apiKey) {
            headers['X-API-Key'] = this.apiKey;
        }

        const config = {
            ...options,
            headers
        };

        try {
            const response = await fetch(url, config);

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Request failed');
            }

            return await response.json();
        } catch (error) {
            console.error(`API Error: ${error.message}`);
            throw error;
        }
    }

    /**
     * Health check
     */
    async healthCheck() {
        return this.request('/health');
    }

    /**
     * Process audio file
     */
    async processAudio(data) {
        return this.request('/api/audio/process', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    /**
     * Classify noise type
     */
    async classifyNoise(data) {
        return this.request('/api/audio/classify', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    /**
     * Detect emergency sounds
     */
    async detectEmergency(data) {
        return this.request('/api/audio/emergency-detect', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    /**
     * Create audio session
     */
    async createSession(data) {
        return this.request('/api/sessions/', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    /**
     * Get session details
     */
    async getSession(sessionId) {
        return this.request(`/api/sessions/${sessionId}`);
    }

    /**
     * Update session
     */
    async updateSession(sessionId, data) {
        return this.request(`/api/sessions/${sessionId}`, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    }

    /**
     * Get session metrics
     */
    async getSessionMetrics(sessionId) {
        return this.request(`/api/sessions/${sessionId}/metrics`);
    }

    /**
     * Get current user
     */
    async getCurrentUser() {
        return this.request('/api/users/me');
    }
}

// Export singleton instance
const api = new APIClient(API_URL);

// For vanilla JS
if (typeof window !== 'undefined') {
    window.api = api;
}

// For ES modules
export default api;
