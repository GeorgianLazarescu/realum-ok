import axios from 'axios';

export const API = process.env.REACT_APP_BACKEND_URL + '/api';

// Create axios instance with default config
const apiClient = axios.create({
  baseURL: API,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add request interceptor to always attach latest token from localStorage
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Also add interceptor to global axios for backward compatibility with existing code
// This ensures all axios.get/post calls also get the token automatically
axios.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token && !config.headers.Authorization) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Add response interceptor to handle 401 errors
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    // Don't auto-logout on 401 for login/register requests
    if (error.response?.status === 401) {
      const url = error.config?.url || '';
      if (!url.includes('/auth/login') && !url.includes('/auth/register')) {
        console.warn('Authentication error - token may be invalid');
      }
    }
    return Promise.reject(error);
  }
);

// Legacy function for backward compatibility (deprecated)
export const setupAxios = (token) => {
  // No longer needed - interceptor handles this automatically
  // Keeping for backward compatibility with existing code
};

export { apiClient };
export default apiClient;
