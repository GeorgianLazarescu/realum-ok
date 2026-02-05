import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { apiClient } from '../utils/api';

const AuthContext = createContext(null);

export const useAuth = () => useContext(AuthContext);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [token, setToken] = useState(() => localStorage.getItem('token'));
  const initializedRef = useRef(false);

  // Initialize auth state on mount - only runs once
  useEffect(() => {
    if (initializedRef.current) return;
    initializedRef.current = true;

    const initializeAuth = async () => {
      const storedToken = localStorage.getItem('token');
      
      if (!storedToken) {
        setLoading(false);
        return;
      }

      try {
        // Use apiClient which automatically attaches the token from localStorage
        const res = await apiClient.get('/auth/me');
        setUser(res.data);
        setToken(storedToken);
      } catch (error) {
        const status = error?.response?.status;
        console.warn('Auth initialization failed:', status);
        
        // Only clear token if it's actually invalid (401)
        // For rate limits (429) or network errors, keep the token
        if (status === 401) {
          localStorage.removeItem('token');
          setToken(null);
          setUser(null);
        } else if (status === 429) {
          // Rate limited - keep the token, assume user is still valid
          // The user will be validated on the next API call
          console.warn('Rate limited during auth check - keeping session');
          setToken(storedToken);
          // Create a minimal user object to prevent redirect
          // The real user data will be fetched on next successful API call
          setUser({ id: 'pending', email: 'loading...', username: 'loading...' });
        }
        // For network errors, keep the token but don't set user
        // This will show loading state and allow retry
      } finally {
        setLoading(false);
      }
    };

    initializeAuth();
  }, []);

  const login = useCallback(async (email, password) => {
    const res = await apiClient.post('/auth/login', { email, password });
    const { access_token, user: userData } = res.data;
    
    // Store token first, then update state
    localStorage.setItem('token', access_token);
    setToken(access_token);
    setUser(userData);
    
    return res.data;
  }, []);

  const register = useCallback(async (data) => {
    const res = await apiClient.post('/auth/register', data);
    const { access_token, user: userData } = res.data;
    
    // Store token first, then update state
    localStorage.setItem('token', access_token);
    setToken(access_token);
    setUser(userData);
    
    return res.data;
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem('token');
    setToken(null);
    setUser(null);
  }, []);

  const refreshUser = useCallback(async () => {
    const storedToken = localStorage.getItem('token');
    if (!storedToken) return;
    
    try {
      const res = await apiClient.get('/auth/me');
      setUser(res.data);
    } catch (error) {
      console.warn('Failed to refresh user:', error?.response?.status);
      if (error?.response?.status === 401) {
        logout();
      }
    }
  }, [logout]);

  // Check if user is authenticated - also consider token presence for pending auth
  const isAuthenticated = Boolean(token && user);

  return (
    <AuthContext.Provider value={{ 
      user, 
      login, 
      register, 
      logout, 
      loading, 
      refreshUser, 
      token,
      isAuthenticated 
    }}>
      {children}
    </AuthContext.Provider>
  );
};
