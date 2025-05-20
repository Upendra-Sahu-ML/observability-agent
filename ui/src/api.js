import axios from 'axios';

// Determine the API URL based on environment
let apiUrl = process.env.REACT_APP_API_URL;

// Always use relative paths in production to work with port forwarding
if (process.env.NODE_ENV === 'production' || !apiUrl) {
  apiUrl = '/api';
} else if (!apiUrl) {
  // This fallback should rarely be used now
  apiUrl = '/api';
}

console.log(`API URL: ${apiUrl}`);

// Axios instance for API calls
const api = axios.create({
  baseURL: apiUrl
});

// Add request interceptor for logging
api.interceptors.request.use(config => {
  console.log(`API Request: ${config.method.toUpperCase()} ${config.url}`);
  return config;
});

// Add response interceptor for logging and error handling
api.interceptors.response.use(
  response => {
    console.log(`API Response: ${response.status} from ${response.config.url}`);
    return response;
  },
  error => {
    console.error('API Error:', error.message);
    if (error.response) {
      console.error(`Status: ${error.response.status}`, error.response.data);
    }
    return Promise.reject(error);
  }
);

export default api;
