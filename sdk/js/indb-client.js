
/**
 * INDB Client (JavaScript / ES Module)
 * 
 * Simple wrapper around fetch for INDB API.
 */
export class INDBClient {
    constructor(baseUrl, token = null) {
        this.baseUrl = baseUrl.replace(/\/$/, "");
        this.token = token;
    }

    async _request(method, endpoint, body = null, params = null) {
        const headers = {
            "Content-Type": "application/json"
        };
        if (this.token) {
            headers["Authorization"] = `Bearer ${this.token}`;
        }

        let url = `${this.baseUrl}${endpoint}`;
        if (params) {
            const qs = new URLSearchParams(params).toString();
            url += `?${qs}`;
        }

        const options = {
            method,
            headers,
        };

        if (body) {
            options.body = JSON.stringify(body);
        }

        const response = await fetch(url, options);
        if (!response.ok) {
            throw new Error(`API Error ${response.status}: ${await response.text()}`);
        }

        return await response.json();
    }

    /**
     * Create a new event
     * @param {string[]} rawData 
     * @param {string} location 
     * @param {object} metadata 
     */
    async createEvent(rawData, location, metadata = {}) {
        return this._request("POST", "/api/v2/events", {
            raw_data_anchor: rawData,
            location,
            metadata
        });
    }

    /**
     * Interpret context
     * @param {object} context 
     */
    async interpret(context) {
        return this._request("POST", "/api/v2/interpret", { context });
    }

    /**
     * List events
     * @param {number} limit 
     * @param {number} offset 
     */
    async listEvents(limit = 10, offset = 0) {
        return this._request("GET", "/api/v2/events", null, { limit, offset });
    }
}
