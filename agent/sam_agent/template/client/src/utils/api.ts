// client/src/utils/api.ts
const API_BASE = '/api';

export const api = {
  healthcheck: async () => {
    const response = await fetch(`${API_BASE}/healthcheck`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
  },
};