import axios from 'axios';

export const API = process.env.REACT_APP_BACKEND_URL + '/api';

// Configure axios defaults
export const setupAxios = (token) => {
  if (token) {
    axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
  } else {
    delete axios.defaults.headers.common['Authorization'];
  }
};

export default axios;
