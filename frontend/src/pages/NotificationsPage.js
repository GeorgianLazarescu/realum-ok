import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Bell, Check, CheckCheck, Trash2, Filter, Settings,
  MessageCircle, Award, Vote, Briefcase, GraduationCap,
  Shield, Megaphone, Info, AlertTriangle, X, RefreshCw
} from 'lucide-react';
import axios from 'axios';
import { API } from '../utils/api';
import { useAuth } from '../context/AuthContext';
import { CyberCard, CyberButton } from '../components/common/CyberUI';

// Category icons mapping
const categoryIcons = {
  general: Info,
  social: MessageCircle,
  governance: Vote,
  rewards: Award,
  jobs: Briefcase,
  courses: GraduationCap,
  announcement: Megaphone,
  security: Shield
};

// Notification type colors
const typeColors = {
  info: '#3B82F6',
  success: '#10B981',
  warning: '#F59E0B',
  error: '#EF4444',
  achievement: '#8B5CF6',
  system: '#6B7280'
};

// Single notification item component
const NotificationItem = ({ notification, onMarkRead, onDelete }) => {
  const Icon = categoryIcons[notification.category] || Info;
  const color = typeColors[notification.notification_type] || typeColors.info;
  
  const formatTimeAgo = (dateStr) => {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    const now = new Date();
    const diff = Math.floor((now - date) / 1000);
    
    if (diff < 60) return 'just now';
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    if (diff < 604800) return `${Math.floor(diff / 86400)}d ago`;
    return date.toLocaleDateString();
  };

  return (
    <motion.div
      layout
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 20 }}
      className={`p-4 border-l-4 transition-colors ${
        notification.is_read 
          ? 'bg-black/20 border-white/20' 
          : 'bg-black/40 border-l-4'
      }`}
      style={{ borderLeftColor: notification.is_read ? undefined : color }}
    >
      <div className="flex items-start gap-3">
        <div 
          className="w-10 h-10 flex items-center justify-center border flex-shrink-0"
          style={{ borderColor: color, backgroundColor: `${color}10` }}
        >
          <Icon className="w-5 h-5" style={{ color }} />
        </div>
        
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h4 className={`font-mono text-sm ${notification.is_read ? 'text-white/70' : 'font-bold'}`}>
              {notification.title}
            </h4>
            {!notification.is_read && (
              <span className="w-2 h-2 rounded-full bg-neon-cyan flex-shrink-0" />
            )}
          </div>
          <p className="text-sm text-white/60 line-clamp-2">{notification.message}</p>
          
          <div className="flex items-center justify-between mt-2">
            <span className="text-xs text-white/40">{formatTimeAgo(notification.created_at)}</span>
            
            <div className="flex items-center gap-2">
              {notification.action_url && (
                <a 
                  href={notification.action_url}
                  className="text-xs text-neon-cyan hover:underline"
                >
                  {notification.action_label || 'View'}
                </a>
              )}
              
              {!notification.is_read && (
                <button
                  onClick={() => onMarkRead(notification.id)}
                  className="p-1 text-white/40 hover:text-neon-green transition-colors"
                  title="Mark as read"
                >
                  <Check className="w-4 h-4" />
                </button>
              )}
              
              <button
                onClick={() => onDelete(notification.id)}
                className="p-1 text-white/40 hover:text-neon-red transition-colors"
                title="Delete"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
};

const NotificationsPage = () => {
  const { user } = useAuth();
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [categories, setCategories] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [showUnreadOnly, setShowUnreadOnly] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [preferences, setPreferences] = useState(null);

  const loadNotifications = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (showUnreadOnly) params.append('unread_only', 'true');
      if (selectedCategory) params.append('category', selectedCategory);
      params.append('limit', '50');

      const res = await axios.get(`${API}/notifications/?${params.toString()}`);
      setNotifications(res.data.notifications || []);
      setUnreadCount(res.data.unread_count || 0);
      setTotal(res.data.total || 0);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [showUnreadOnly, selectedCategory]);

  const loadCategories = async () => {
    try {
      const res = await axios.get(`${API}/notifications/categories`);
      setCategories(res.data.categories || []);
    } catch (err) {
      console.error(err);
    }
  };

  const loadPreferences = async () => {
    try {
      const res = await axios.get(`${API}/notifications/preferences`);
      setPreferences(res.data.preferences || {});
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    loadCategories();
    loadPreferences();
  }, []);

  useEffect(() => {
    loadNotifications();
  }, [loadNotifications]);

  const handleMarkRead = async (notificationId) => {
    try {
      await axios.patch(`${API}/notifications/${notificationId}/read`);
      setNotifications(prev => 
        prev.map(n => n.id === notificationId ? { ...n, is_read: true } : n)
      );
      setUnreadCount(prev => Math.max(0, prev - 1));
    } catch (err) {
      console.error(err);
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await axios.post(`${API}/notifications/mark-all-read`);
      setNotifications(prev => prev.map(n => ({ ...n, is_read: true })));
      setUnreadCount(0);
    } catch (err) {
      console.error(err);
    }
  };

  const handleDelete = async (notificationId) => {
    try {
      await axios.delete(`${API}/notifications/${notificationId}`);
      const deleted = notifications.find(n => n.id === notificationId);
      setNotifications(prev => prev.filter(n => n.id !== notificationId));
      if (deleted && !deleted.is_read) {
        setUnreadCount(prev => Math.max(0, prev - 1));
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleUpdatePreference = async (key, value) => {
    try {
      await axios.put(`${API}/notifications/preferences`, { [key]: value });
      setPreferences(prev => ({ ...prev, [key]: value }));
    } catch (err) {
      console.error(err);
    }
  };

  if (loading && notifications.length === 0) {
    return (
      <div className="min-h-screen pt-20 flex items-center justify-center">
        <div className="text-neon-cyan font-mono">Loading notifications...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen pt-16 sm:pt-20 pb-20 lg:pb-12 px-3 sm:px-4" data-testid="notifications-page">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-6">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h1 className="text-2xl sm:text-3xl font-orbitron font-black mb-2">
                <Bell className="inline w-8 h-8 mr-2 text-neon-cyan" />
                Notifications
                {unreadCount > 0 && (
                  <span className="ml-2 px-2 py-1 bg-neon-cyan/20 border border-neon-cyan text-neon-cyan text-sm">
                    {unreadCount} new
                  </span>
                )}
              </h1>
              <p className="text-white/60 text-sm">Stay updated with your REALUM activity</p>
            </div>
            <div className="flex gap-2">
              <CyberButton onClick={loadNotifications} variant="ghost">
                <RefreshCw className="w-4 h-4" />
              </CyberButton>
              <CyberButton onClick={() => setShowSettings(!showSettings)} variant="ghost">
                <Settings className="w-4 h-4" />
              </CyberButton>
              {unreadCount > 0 && (
                <CyberButton onClick={handleMarkAllRead}>
                  <CheckCheck className="w-4 h-4 mr-2" />
                  Mark All Read
                </CyberButton>
              )}
            </div>
          </div>
        </motion.div>

        {/* Settings Panel */}
        <AnimatePresence>
          {showSettings && preferences && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="overflow-hidden mb-6"
            >
              <CyberCard className="p-4">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-orbitron font-bold">Notification Settings</h3>
                  <button onClick={() => setShowSettings(false)} className="text-white/50 hover:text-white">
                    <X className="w-5 h-5" />
                  </button>
                </div>
                <div className="grid sm:grid-cols-3 gap-4">
                  <label className="flex items-center gap-3 p-3 bg-black/30 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={preferences.in_app_enabled}
                      onChange={(e) => handleUpdatePreference('in_app_enabled', e.target.checked)}
                      className="w-4 h-4 accent-neon-cyan"
                    />
                    <span className="text-sm">In-App Notifications</span>
                  </label>
                  <label className="flex items-center gap-3 p-3 bg-black/30 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={preferences.email_enabled}
                      onChange={(e) => handleUpdatePreference('email_enabled', e.target.checked)}
                      className="w-4 h-4 accent-neon-cyan"
                    />
                    <span className="text-sm">Email Notifications</span>
                  </label>
                  <label className="flex items-center gap-3 p-3 bg-black/30 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={preferences.daily_digest}
                      onChange={(e) => handleUpdatePreference('daily_digest', e.target.checked)}
                      className="w-4 h-4 accent-neon-cyan"
                    />
                    <span className="text-sm">Daily Digest</span>
                  </label>
                </div>
              </CyberCard>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Filters */}
        <div className="flex flex-wrap gap-2 mb-6">
          <button
            onClick={() => setShowUnreadOnly(!showUnreadOnly)}
            className={`px-3 py-2 border text-xs font-mono flex items-center gap-2 transition-colors ${
              showUnreadOnly ? 'border-neon-cyan bg-neon-cyan/10 text-neon-cyan' : 'border-white/20 text-white/60'
            }`}
          >
            <Filter className="w-4 h-4" />
            Unread Only
          </button>
          
          <button
            onClick={() => setSelectedCategory(null)}
            className={`px-3 py-2 border text-xs font-mono transition-colors ${
              !selectedCategory ? 'border-neon-cyan bg-neon-cyan/10 text-neon-cyan' : 'border-white/20 text-white/60'
            }`}
          >
            All
          </button>
          
          {categories.map(cat => {
            const Icon = categoryIcons[cat.key] || Info;
            return (
              <button
                key={cat.key}
                onClick={() => setSelectedCategory(cat.key)}
                className={`px-3 py-2 border text-xs font-mono flex items-center gap-2 transition-colors ${
                  selectedCategory === cat.key ? 'border-neon-cyan bg-neon-cyan/10 text-neon-cyan' : 'border-white/20 text-white/60'
                }`}
              >
                <Icon className="w-3 h-3" />
                {cat.name}
              </button>
            );
          })}
        </div>

        {/* Notifications List */}
        <CyberCard className="overflow-hidden">
          {notifications.length > 0 ? (
            <div className="divide-y divide-white/10">
              <AnimatePresence>
                {notifications.map(notification => (
                  <NotificationItem
                    key={notification.id}
                    notification={notification}
                    onMarkRead={handleMarkRead}
                    onDelete={handleDelete}
                  />
                ))}
              </AnimatePresence>
            </div>
          ) : (
            <div className="p-12 text-center">
              <Bell className="w-16 h-16 mx-auto mb-4 text-white/20" />
              <h3 className="font-orbitron font-bold mb-2">No Notifications</h3>
              <p className="text-white/50 text-sm">
                {showUnreadOnly 
                  ? "You're all caught up! No unread notifications."
                  : "You don't have any notifications yet."}
              </p>
            </div>
          )}
        </CyberCard>

        {/* Stats */}
        <div className="mt-6 grid grid-cols-3 gap-3">
          <CyberCard className="p-3 text-center">
            <div className="text-xl font-orbitron font-bold text-neon-cyan">{total}</div>
            <div className="text-xs text-white/50">Total</div>
          </CyberCard>
          <CyberCard className="p-3 text-center">
            <div className="text-xl font-orbitron font-bold text-neon-yellow">{unreadCount}</div>
            <div className="text-xs text-white/50">Unread</div>
          </CyberCard>
          <CyberCard className="p-3 text-center">
            <div className="text-xl font-orbitron font-bold text-neon-green">{total - unreadCount}</div>
            <div className="text-xs text-white/50">Read</div>
          </CyberCard>
        </div>
      </div>
    </div>
  );
};

export default NotificationsPage;
