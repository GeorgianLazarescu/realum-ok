import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import axios from 'axios';
import { 
  Target, Clock, CheckCircle, AlertCircle, Bell, Zap,
  ChevronRight, X, Gift, TrendingUp
} from 'lucide-react';
import { CyberCard, CyberButton } from './common/CyberUI';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

// Objectives Panel Component
export const ObjectivesPanel = () => {
  const [objectives, setObjectives] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadObjectives();
  }, []);

  const loadObjectives = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API}/api/events/objectives`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setObjectives(response.data.objectives || []);
    } catch (error) {
      console.error('Error loading objectives:', error);
    }
    setLoading(false);
  };

  const completedCount = objectives.filter(o => o.completed).length;
  const totalCount = objectives.length;

  return (
    <CyberCard className="p-4 bg-black/50">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-orbitron text-lg text-neon-cyan flex items-center gap-2">
          <Target className="w-5 h-5" />
          Objectives
        </h3>
        <span className="text-sm text-white/60">
          {completedCount}/{totalCount}
        </span>
      </div>

      {loading ? (
        <div className="animate-pulse space-y-2">
          {[1, 2, 3].map(i => (
            <div key={i} className="h-12 bg-white/5 rounded" />
          ))}
        </div>
      ) : (
        <div className="space-y-2">
          {objectives.slice(0, 5).map(objective => (
            <motion.div
              key={objective.id}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              className={`flex items-center gap-3 p-3 rounded-lg transition-colors ${
                objective.completed 
                  ? 'bg-green-500/10 border border-green-500/30' 
                  : 'bg-white/5 hover:bg-white/10'
              }`}
            >
              {objective.completed ? (
                <CheckCircle className="w-5 h-5 text-green-500 flex-shrink-0" />
              ) : (
                <div className={`w-5 h-5 rounded-full border-2 flex-shrink-0 ${
                  objective.priority === 'high' ? 'border-red-500' :
                  objective.priority === 'medium' ? 'border-yellow-500' : 'border-white/30'
                }`} />
              )}
              <div className="flex-1 min-w-0">
                <p className={`text-sm truncate ${objective.completed ? 'text-white/60 line-through' : 'text-white'}`}>
                  {objective.title}
                </p>
                <p className="text-xs text-white/40 truncate">{objective.description}</p>
              </div>
              <span className="text-xs text-yellow-500 flex-shrink-0">
                +{objective.reward_rlm} RLM
              </span>
            </motion.div>
          ))}
        </div>
      )}
    </CyberCard>
  );
};

// Mini-Tasks Panel Component
export const MiniTasksPanel = () => {
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadTasks();
  }, []);

  const loadTasks = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API}/api/events/tasks`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setTasks(response.data.tasks || []);
    } catch (error) {
      console.error('Error loading tasks:', error);
    }
    setLoading(false);
  };

  const acceptTask = async (taskId) => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.post(`${API}/api/events/tasks/${taskId}/accept`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success('Task accepted!', {
        description: `Complete within ${response.data.deadline_mins} minutes`
      });
      loadTasks();
    } catch (error) {
      toast.error('Failed to accept task');
    }
  };

  const completeTask = async (taskId) => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.post(`${API}/api/events/tasks/${taskId}/complete`, { task_id: taskId }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success('Task completed!', {
        description: `You earned ${response.data.reward_rlm} RLM ${response.data.on_time ? '(on time!)' : ''}`
      });
      loadTasks();
    } catch (error) {
      toast.error('Failed to complete task');
    }
  };

  const taskTypeColors = {
    job: '#FF003C',
    decision: '#9D4EDD',
    action: '#00FF88',
    social: '#40C4FF',
    learning: '#FFD700'
  };

  return (
    <CyberCard className="p-4 bg-black/50">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-orbitron text-lg text-neon-cyan flex items-center gap-2">
          <Zap className="w-5 h-5" />
          Mini-Tasks
        </h3>
      </div>

      {loading ? (
        <div className="animate-pulse space-y-2">
          {[1, 2, 3].map(i => (
            <div key={i} className="h-20 bg-white/5 rounded" />
          ))}
        </div>
      ) : (
        <div className="space-y-3">
          {tasks.map(task => (
            <motion.div
              key={task.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="bg-white/5 rounded-lg p-3 border border-white/10"
            >
              <div className="flex items-start justify-between mb-2">
                <div>
                  <span 
                    className="text-xs px-2 py-0.5 rounded-full mr-2"
                    style={{ backgroundColor: `${taskTypeColors[task.type]}20`, color: taskTypeColors[task.type] }}
                  >
                    {task.type}
                  </span>
                  <span className="text-sm font-bold text-white">{task.name}</span>
                </div>
                <span className="text-xs text-yellow-500 font-bold">+{task.reward_rlm} RLM</span>
              </div>
              <p className="text-xs text-white/60 mb-2">{task.description}</p>
              <div className="flex items-center justify-between">
                <span className="text-xs text-white/40 flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  {task.time_limit_mins} min
                </span>
                {task.status === 'pending' ? (
                  <button
                    onClick={() => acceptTask(task.id)}
                    className="text-xs px-3 py-1 bg-neon-cyan/20 text-neon-cyan border border-neon-cyan/50 rounded hover:bg-neon-cyan/30 transition-colors"
                  >
                    Accept
                  </button>
                ) : task.status === 'accepted' ? (
                  <button
                    onClick={() => completeTask(task.id)}
                    className="text-xs px-3 py-1 bg-green-500/20 text-green-500 border border-green-500/50 rounded hover:bg-green-500/30 transition-colors"
                  >
                    Complete
                  </button>
                ) : (
                  <span className="text-xs text-green-500">✓ Done</span>
                )}
              </div>
            </motion.div>
          ))}
        </div>
      )}
    </CyberCard>
  );
};

// Random Events Panel Component
export const RandomEventsPanel = () => {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadEvents();
  }, []);

  const loadEvents = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API}/api/events/active`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setEvents(response.data.events || []);
    } catch (error) {
      console.error('Error loading events:', error);
    }
    setLoading(false);
  };

  const generateEvent = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.post(`${API}/api/events/generate`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success(`New Event: ${response.data.event.name}`, {
        description: response.data.event.description
      });
      loadEvents();
    } catch (error) {
      toast.error('Failed to generate event');
    }
  };

  const respondToEvent = async (eventId, accepted) => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.post(`${API}/api/events/${eventId}/respond`, {
        event_id: eventId,
        accepted
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success(response.data.message);
      loadEvents();
    } catch (error) {
      toast.error('Failed to respond to event');
    }
  };

  const eventTypeIcons = {
    illness: '🤒',
    opportunity: '🌟',
    expense: '💸',
    social: '👥',
    discovery: '🔍',
    challenge: '⚔️'
  };

  const severityColors = {
    minor: 'text-green-400',
    moderate: 'text-yellow-400',
    major: 'text-orange-400',
    critical: 'text-red-400'
  };

  return (
    <CyberCard className="p-4 bg-black/50">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-orbitron text-lg text-neon-cyan flex items-center gap-2">
          <Gift className="w-5 h-5" />
          Life Events
        </h3>
        <button
          onClick={generateEvent}
          className="text-xs px-3 py-1 bg-purple-500/20 text-purple-400 border border-purple-500/50 rounded hover:bg-purple-500/30 transition-colors"
        >
          🎲 New Event
        </button>
      </div>

      {loading ? (
        <div className="animate-pulse h-24 bg-white/5 rounded" />
      ) : events.length === 0 ? (
        <div className="text-center py-6 text-white/40">
          <p>No active events</p>
          <p className="text-xs mt-1">Click "New Event" to generate one!</p>
        </div>
      ) : (
        <div className="space-y-3">
          {events.slice(0, 3).map(event => (
            <motion.div
              key={event.id}
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="bg-white/5 rounded-lg p-3 border border-white/10"
            >
              <div className="flex items-start gap-3">
                <span className="text-2xl">{eventTypeIcons[event.type] || '❓'}</span>
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-sm font-bold text-white">{event.name}</span>
                    <span className={`text-xs ${severityColors[event.severity]}`}>
                      {event.severity}
                    </span>
                  </div>
                  <p className="text-xs text-white/60 mb-2">{event.description}</p>
                  
                  {event.type === 'opportunity' && (
                    <div className="flex gap-2">
                      <button
                        onClick={() => respondToEvent(event.id, true)}
                        className="text-xs px-3 py-1 bg-green-500/20 text-green-400 rounded hover:bg-green-500/30"
                      >
                        Accept (+{event.reward_rlm} RLM)
                      </button>
                      <button
                        onClick={() => respondToEvent(event.id, false)}
                        className="text-xs px-3 py-1 bg-red-500/20 text-red-400 rounded hover:bg-red-500/30"
                      >
                        Decline
                      </button>
                    </div>
                  )}
                  
                  {event.type === 'expense' && (
                    <button
                      onClick={() => respondToEvent(event.id, true)}
                      className="text-xs px-3 py-1 bg-yellow-500/20 text-yellow-400 rounded hover:bg-yellow-500/30"
                    >
                      Pay ({event.cost_rlm} RLM)
                    </button>
                  )}
                  
                  {event.type === 'illness' && (
                    <button
                      onClick={() => respondToEvent(event.id, true)}
                      className="text-xs px-3 py-1 bg-blue-500/20 text-blue-400 rounded hover:bg-blue-500/30"
                    >
                      Rest & Recover
                    </button>
                  )}
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      )}
    </CyberCard>
  );
};

// Notifications Dropdown Component
export const NotificationsDropdown = ({ onClose }) => {
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadNotifications();
  }, []);

  const loadNotifications = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API}/api/events/notifications`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setNotifications(response.data.notifications || []);
    } catch (error) {
      console.error('Error loading notifications:', error);
    }
    setLoading(false);
  };

  const markAsRead = async (id) => {
    try {
      const token = localStorage.getItem('token');
      await axios.post(`${API}/api/events/notifications/${id}/read`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      loadNotifications();
    } catch (error) {
      console.error('Error marking notification as read:', error);
    }
  };

  const markAllRead = async () => {
    try {
      const token = localStorage.getItem('token');
      await axios.post(`${API}/api/events/notifications/read-all`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      loadNotifications();
    } catch (error) {
      console.error('Error marking all as read:', error);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="absolute right-0 top-full mt-2 w-80 z-50"
    >
      <CyberCard className="p-0 bg-black/95 border-neon-cyan/50 max-h-96 overflow-hidden">
        <div className="flex items-center justify-between p-3 border-b border-white/10">
          <h4 className="font-orbitron text-sm text-neon-cyan">Notifications</h4>
          <div className="flex gap-2">
            <button
              onClick={markAllRead}
              className="text-xs text-white/50 hover:text-white"
            >
              Mark all read
            </button>
            <button onClick={onClose} className="text-white/50 hover:text-white">
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
        
        <div className="overflow-y-auto max-h-72">
          {loading ? (
            <div className="p-4 text-center text-white/40">Loading...</div>
          ) : notifications.length === 0 ? (
            <div className="p-4 text-center text-white/40">No notifications</div>
          ) : (
            notifications.map(notif => (
              <div
                key={notif.id}
                onClick={() => markAsRead(notif.id)}
                className={`p-3 border-b border-white/5 cursor-pointer hover:bg-white/5 transition-colors ${
                  !notif.read ? 'bg-neon-cyan/5' : ''
                }`}
              >
                <div className="flex items-start gap-2">
                  {!notif.read && (
                    <div className="w-2 h-2 rounded-full bg-neon-cyan mt-1.5 flex-shrink-0" />
                  )}
                  <div className="flex-1">
                    <p className="text-sm text-white">{notif.title}</p>
                    <p className="text-xs text-white/50 mt-1">{notif.message}</p>
                    <p className="text-xs text-white/30 mt-1">
                      {new Date(notif.created_at).toLocaleTimeString()}
                    </p>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </CyberCard>
    </motion.div>
  );
};

// World Time Display Component
export const WorldTimeDisplay = () => {
  const [worldTime, setWorldTime] = useState(null);

  useEffect(() => {
    const fetchWorldTime = async () => {
      try {
        const response = await axios.get(`${API}/api/events/world/time`);
        setWorldTime(response.data);
      } catch (error) {
        console.error('Error fetching world time:', error);
      }
    };

    fetchWorldTime();
    const interval = setInterval(fetchWorldTime, 60000); // Update every minute
    return () => clearInterval(interval);
  }, []);

  if (!worldTime) return null;

  const periodEmoji = {
    morning: '🌅',
    afternoon: '☀️',
    evening: '🌆',
    night: '🌙'
  };

  return (
    <div className="flex items-center gap-2 text-sm">
      <span>{periodEmoji[worldTime.period]}</span>
      <span className="text-white/60">{worldTime.description}</span>
    </div>
  );
};

// Seasonal Events Banner Component
export const SeasonalEventsBanner = () => {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchEvents = async () => {
      try {
        const response = await axios.get(`${API}/api/events/calendar/active`);
        setEvents(response.data.active_events || []);
      } catch (error) {
        console.error('Error fetching events:', error);
      }
      setLoading(false);
    };
    fetchEvents();
  }, []);

  if (loading || events.length === 0) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      className="mb-6"
    >
      <CyberCard className="p-4 bg-gradient-to-r from-purple-900/50 to-pink-900/50 border-purple-500/30">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-purple-500/20 rounded-lg flex items-center justify-center">
              <span className="text-2xl">🎉</span>
            </div>
            <div>
              <h3 className="font-orbitron text-lg text-purple-300 font-bold">
                {events[0].name}
              </h3>
              <p className="text-sm text-white/60">{events[0].description}</p>
            </div>
          </div>
          <div className="text-right">
            {events[0].bonus_rlm > 0 && (
              <p className="text-yellow-400 font-bold">+{events[0].bonus_rlm} RLM Bonus</p>
            )}
            {events[0].bonus_xp > 1 && (
              <p className="text-green-400 text-sm">{events[0].bonus_xp}x XP Multiplier</p>
            )}
            {events[0].days_remaining !== undefined && (
              <p className="text-white/40 text-xs mt-1">{events[0].days_remaining} days remaining</p>
            )}
          </div>
        </div>
      </CyberCard>
    </motion.div>
  );
};

export default { ObjectivesPanel, MiniTasksPanel, RandomEventsPanel, NotificationsDropdown, WorldTimeDisplay, SeasonalEventsBanner };
