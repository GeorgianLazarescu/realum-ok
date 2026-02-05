import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import axios from 'axios';
import { 
  User, Heart, Users, Brain, Scale, Briefcase, Sparkles,
  X, ChevronRight, Save, RefreshCw, Plus, BookOpen,
  Smile, Frown, Zap, Moon, Coffee, AlertTriangle
} from 'lucide-react';
import { CyberCard, CyberButton } from './common/CyberUI';

const API = process.env.REACT_APP_BACKEND_URL;

// Emotion icons mapping
const emotionIcons = {
  happy: Smile,
  sad: Frown,
  excited: Zap,
  stressed: AlertTriangle,
  calm: Moon,
  motivated: Coffee,
  neutral: User,
};

// Life Simulation Panel Component
const LifeSimulationPanel = ({ isOpen, onClose }) => {
  const [activeTab, setActiveTab] = useState('identity');
  const [loading, setLoading] = useState(false);
  const [lifeSummary, setLifeSummary] = useState(null);
  
  // Identity state
  const [identity, setIdentity] = useState({
    display_name: '',
    use_real_name: false,
    biological_sex: 'not_specified',
    gender_identity: 'prefer_not_say',
    avatar_age: 25,
    biography: '',
    pronouns: '',
  });
  
  // Health state
  const [health, setHealth] = useState({
    status: 'healthy',
    energy_level: 100,
    stress_level: 0,
    task_capacity: 100,
  });
  
  // Emotion state
  const [currentEmotion, setCurrentEmotion] = useState({
    state: 'neutral',
    intensity: 50,
    note: '',
  });
  
  // Career state
  const [career, setCareer] = useState({
    field: 'technology',
    title: '',
    experience_years: 0,
    skills: [],
    is_volunteer: false,
  });
  
  // Relationships state
  const [relationships, setRelationships] = useState([]);
  
  // Reputation state
  const [reputation, setReputation] = useState({ score: 0, level: 'Neutral' });
  
  // Journal entries
  const [journalEntries, setJournalEntries] = useState([]);
  const [newJournalEntry, setNewJournalEntry] = useState({ title: '', content: '', mood: 'neutral' });

  const tabs = [
    { id: 'identity', label: 'Identity', icon: User },
    { id: 'health', label: 'Health', icon: Heart },
    { id: 'relationships', label: 'Relations', icon: Users },
    { id: 'emotions', label: 'Emotions', icon: Brain },
    { id: 'ethics', label: 'Ethics', icon: Scale },
    { id: 'career', label: 'Career', icon: Briefcase },
    { id: 'spirituality', label: 'Reflection', icon: Sparkles },
  ];

  // Load life summary
  useEffect(() => {
    if (isOpen) {
      loadLifeSummary();
    }
  }, [isOpen]);

  const loadLifeSummary = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API}/api/life/summary`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setLifeSummary(response.data);
      
      if (response.data.identity) {
        setIdentity(prev => ({ ...prev, ...response.data.identity }));
      }
      if (response.data.health) {
        setHealth(response.data.health);
      }
      if (response.data.current_emotion) {
        setCurrentEmotion(prev => ({ ...prev, ...response.data.current_emotion }));
      }
      if (response.data.career) {
        setCareer(prev => ({ ...prev, ...response.data.career }));
      }
      if (response.data.reputation) {
        setReputation(response.data.reputation);
      }
    } catch (error) {
      console.error('Error loading life summary:', error);
    }
    setLoading(false);
  };

  const saveIdentity = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      await axios.post(`${API}/api/life/avatar/identity`, identity, {
        headers: { Authorization: `Bearer ${token}` }
      });
      loadLifeSummary();
    } catch (error) {
      console.error('Error saving identity:', error);
    }
    setLoading(false);
  };

  const takeRest = async () => {
    try {
      const token = localStorage.getItem('token');
      await axios.post(`${API}/api/life/health/rest`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      loadLifeSummary();
    } catch (error) {
      console.error('Error taking rest:', error);
    }
  };

  const logEmotion = async () => {
    try {
      const token = localStorage.getItem('token');
      await axios.post(`${API}/api/life/emotions/log`, currentEmotion, {
        headers: { Authorization: `Bearer ${token}` }
      });
      loadLifeSummary();
    } catch (error) {
      console.error('Error logging emotion:', error);
    }
  };

  const saveCareer = async () => {
    try {
      const token = localStorage.getItem('token');
      await axios.post(`${API}/api/life/career`, career, {
        headers: { Authorization: `Bearer ${token}` }
      });
      loadLifeSummary();
    } catch (error) {
      console.error('Error saving career:', error);
    }
  };

  const saveJournalEntry = async () => {
    if (!newJournalEntry.title || !newJournalEntry.content) return;
    try {
      const token = localStorage.getItem('token');
      await axios.post(`${API}/api/life/reflection/journal`, newJournalEntry, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setNewJournalEntry({ title: '', content: '', mood: 'neutral' });
      loadJournalEntries();
    } catch (error) {
      console.error('Error saving journal:', error);
    }
  };

  const loadJournalEntries = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API}/api/life/reflection/journal`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setJournalEntries(response.data.entries || []);
    } catch (error) {
      console.error('Error loading journal:', error);
    }
  };

  const resetAvatar = async () => {
    if (!window.confirm('Are you sure? This will reset your entire avatar and start fresh.')) return;
    try {
      const token = localStorage.getItem('token');
      await axios.post(`${API}/api/life/health/reset`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      loadLifeSummary();
    } catch (error) {
      console.error('Error resetting avatar:', error);
    }
  };

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-[100] flex items-center justify-center bg-black/80 backdrop-blur-sm p-4"
        onClick={onClose}
      >
        <motion.div
          initial={{ scale: 0.9, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.9, opacity: 0 }}
          className="w-full max-w-4xl max-h-[90vh] overflow-hidden"
          onClick={e => e.stopPropagation()}
        >
          <CyberCard className="bg-black/95 border-neon-cyan">
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b border-white/10">
              <h2 className="font-orbitron text-xl text-neon-cyan flex items-center gap-2">
                <User className="w-6 h-6" />
                LIFE SIMULATION
              </h2>
              <button
                onClick={onClose}
                className="p-2 hover:bg-white/10 rounded transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Tabs */}
            <div className="flex overflow-x-auto border-b border-white/10">
              {tabs.map(tab => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-2 px-4 py-3 text-sm whitespace-nowrap transition-colors ${
                    activeTab === tab.id
                      ? 'text-neon-cyan border-b-2 border-neon-cyan bg-neon-cyan/10'
                      : 'text-white/60 hover:text-white hover:bg-white/5'
                  }`}
                >
                  <tab.icon className="w-4 h-4" />
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Content */}
            <div className="p-4 overflow-y-auto max-h-[60vh]">
              {loading ? (
                <div className="flex items-center justify-center py-12">
                  <RefreshCw className="w-8 h-8 text-neon-cyan animate-spin" />
                </div>
              ) : (
                <>
                  {/* Identity Tab */}
                  {activeTab === 'identity' && (
                    <div className="space-y-4">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                          <label className="block text-sm text-white/60 mb-1">Display Name</label>
                          <input
                            type="text"
                            value={identity.display_name}
                            onChange={e => setIdentity({...identity, display_name: e.target.value})}
                            className="w-full px-3 py-2 bg-white/5 border border-white/20 rounded text-white focus:border-neon-cyan outline-none"
                            placeholder="Your avatar name"
                          />
                        </div>
                        <div>
                          <label className="block text-sm text-white/60 mb-1">Avatar Age</label>
                          <input
                            type="number"
                            value={identity.avatar_age}
                            onChange={e => setIdentity({...identity, avatar_age: parseInt(e.target.value)})}
                            min={18}
                            max={100}
                            className="w-full px-3 py-2 bg-white/5 border border-white/20 rounded text-white focus:border-neon-cyan outline-none"
                          />
                        </div>
                        <div>
                          <label className="block text-sm text-white/60 mb-1">Biological Sex</label>
                          <select
                            value={identity.biological_sex}
                            onChange={e => setIdentity({...identity, biological_sex: e.target.value})}
                            className="w-full px-3 py-2 bg-white/5 border border-white/20 rounded text-white focus:border-neon-cyan outline-none"
                          >
                            <option value="not_specified">Not Specified</option>
                            <option value="male">Male</option>
                            <option value="female">Female</option>
                            <option value="intersex">Intersex</option>
                          </select>
                        </div>
                        <div>
                          <label className="block text-sm text-white/60 mb-1">Gender Identity</label>
                          <select
                            value={identity.gender_identity}
                            onChange={e => setIdentity({...identity, gender_identity: e.target.value})}
                            className="w-full px-3 py-2 bg-white/5 border border-white/20 rounded text-white focus:border-neon-cyan outline-none"
                          >
                            <option value="prefer_not_say">Prefer Not to Say</option>
                            <option value="male">Male</option>
                            <option value="female">Female</option>
                            <option value="non_binary">Non-Binary</option>
                            <option value="fluid">Gender Fluid</option>
                            <option value="other">Other</option>
                          </select>
                        </div>
                        <div>
                          <label className="block text-sm text-white/60 mb-1">Pronouns</label>
                          <input
                            type="text"
                            value={identity.pronouns}
                            onChange={e => setIdentity({...identity, pronouns: e.target.value})}
                            className="w-full px-3 py-2 bg-white/5 border border-white/20 rounded text-white focus:border-neon-cyan outline-none"
                            placeholder="e.g., he/him, she/her, they/them"
                          />
                        </div>
                        <div className="flex items-center gap-2">
                          <input
                            type="checkbox"
                            checked={identity.use_real_name}
                            onChange={e => setIdentity({...identity, use_real_name: e.target.checked})}
                            className="w-4 h-4"
                          />
                          <label className="text-sm text-white/60">Use real name publicly</label>
                        </div>
                      </div>
                      <div>
                        <label className="block text-sm text-white/60 mb-1">Biography</label>
                        <textarea
                          value={identity.biography}
                          onChange={e => setIdentity({...identity, biography: e.target.value})}
                          rows={3}
                          className="w-full px-3 py-2 bg-white/5 border border-white/20 rounded text-white focus:border-neon-cyan outline-none resize-none"
                          placeholder="Tell your story..."
                        />
                      </div>
                      <CyberButton onClick={saveIdentity} className="w-full">
                        <Save className="w-4 h-4 mr-2" />
                        Save Identity
                      </CyberButton>
                    </div>
                  )}

                  {/* Health Tab */}
                  {activeTab === 'health' && (
                    <div className="space-y-6">
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <div className="bg-white/5 rounded-lg p-4 text-center">
                          <div className="text-2xl font-bold text-green-400">{health.energy_level}%</div>
                          <div className="text-xs text-white/60">Energy</div>
                        </div>
                        <div className="bg-white/5 rounded-lg p-4 text-center">
                          <div className="text-2xl font-bold text-red-400">{health.stress_level}%</div>
                          <div className="text-xs text-white/60">Stress</div>
                        </div>
                        <div className="bg-white/5 rounded-lg p-4 text-center">
                          <div className="text-2xl font-bold text-blue-400">{health.task_capacity}%</div>
                          <div className="text-xs text-white/60">Capacity</div>
                        </div>
                        <div className="bg-white/5 rounded-lg p-4 text-center">
                          <div className={`text-2xl font-bold ${
                            health.status === 'healthy' ? 'text-green-400' :
                            health.status === 'vulnerable' ? 'text-yellow-400' : 'text-red-400'
                          }`}>
                            {health.status?.toUpperCase()}
                          </div>
                          <div className="text-xs text-white/60">Status</div>
                        </div>
                      </div>
                      
                      <div className="flex gap-4">
                        <CyberButton onClick={takeRest} className="flex-1">
                          <Moon className="w-4 h-4 mr-2" />
                          Take Rest
                        </CyberButton>
                        <CyberButton onClick={resetAvatar} className="flex-1 border-red-500 text-red-500 hover:bg-red-500/20">
                          <RefreshCw className="w-4 h-4 mr-2" />
                          Reset Avatar
                        </CyberButton>
                      </div>
                      
                      <p className="text-xs text-white/40 text-center">
                        Taking rest restores energy and reduces stress. Resetting avatar is a symbolic "death" - starting fresh.
                      </p>
                    </div>
                  )}

                  {/* Relationships Tab */}
                  {activeTab === 'relationships' && (
                    <div className="space-y-4">
                      <div className="text-center py-8">
                        <Users className="w-12 h-12 text-white/20 mx-auto mb-4" />
                        <p className="text-white/60 mb-4">
                          {lifeSummary?.relationships_count || 0} active relationships
                        </p>
                        <p className="text-xs text-white/40">
                          Create partnerships, families, friendships, and mentorships with other users.
                        </p>
                      </div>
                      <div className="grid grid-cols-2 gap-4">
                        <div className="bg-white/5 rounded-lg p-4">
                          <h4 className="text-sm font-bold text-neon-cyan mb-2">Marriage/Partnership</h4>
                          <p className="text-xs text-white/60">Digital contract between users</p>
                        </div>
                        <div className="bg-white/5 rounded-lg p-4">
                          <h4 className="text-sm font-bold text-neon-cyan mb-2">Family</h4>
                          <p className="text-xs text-white/60">Virtual family groups</p>
                        </div>
                        <div className="bg-white/5 rounded-lg p-4">
                          <h4 className="text-sm font-bold text-neon-cyan mb-2">Friendship</h4>
                          <p className="text-xs text-white/60">Trust-based connections</p>
                        </div>
                        <div className="bg-white/5 rounded-lg p-4">
                          <h4 className="text-sm font-bold text-neon-cyan mb-2">Mentorship</h4>
                          <p className="text-xs text-white/60">Learning relationships</p>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Emotions Tab */}
                  {activeTab === 'emotions' && (
                    <div className="space-y-4">
                      <div className="bg-white/5 rounded-lg p-4">
                        <h4 className="text-sm font-bold text-white/80 mb-3">Current Emotional State</h4>
                        <div className="grid grid-cols-3 md:grid-cols-6 gap-2">
                          {['happy', 'sad', 'excited', 'stressed', 'calm', 'motivated'].map(emotion => {
                            const Icon = emotionIcons[emotion] || User;
                            return (
                              <button
                                key={emotion}
                                onClick={() => setCurrentEmotion({...currentEmotion, state: emotion})}
                                className={`p-3 rounded-lg text-center transition-colors ${
                                  currentEmotion.state === emotion
                                    ? 'bg-neon-cyan/20 border border-neon-cyan'
                                    : 'bg-white/5 hover:bg-white/10 border border-transparent'
                                }`}
                              >
                                <Icon className="w-6 h-6 mx-auto mb-1" />
                                <span className="text-xs capitalize">{emotion}</span>
                              </button>
                            );
                          })}
                        </div>
                      </div>
                      
                      <div>
                        <label className="block text-sm text-white/60 mb-1">Intensity: {currentEmotion.intensity}%</label>
                        <input
                          type="range"
                          min={0}
                          max={100}
                          value={currentEmotion.intensity}
                          onChange={e => setCurrentEmotion({...currentEmotion, intensity: parseInt(e.target.value)})}
                          className="w-full"
                        />
                      </div>
                      
                      <div>
                        <label className="block text-sm text-white/60 mb-1">Note (optional)</label>
                        <textarea
                          value={currentEmotion.note}
                          onChange={e => setCurrentEmotion({...currentEmotion, note: e.target.value})}
                          rows={2}
                          className="w-full px-3 py-2 bg-white/5 border border-white/20 rounded text-white focus:border-neon-cyan outline-none resize-none"
                          placeholder="What's on your mind?"
                        />
                      </div>
                      
                      <CyberButton onClick={logEmotion} className="w-full">
                        <Brain className="w-4 h-4 mr-2" />
                        Log Emotion
                      </CyberButton>
                    </div>
                  )}

                  {/* Ethics Tab */}
                  {activeTab === 'ethics' && (
                    <div className="space-y-4">
                      <div className="bg-white/5 rounded-lg p-6 text-center">
                        <Scale className="w-12 h-12 text-neon-cyan mx-auto mb-4" />
                        <div className="text-3xl font-bold text-white mb-2">
                          {reputation.score || 0}
                        </div>
                        <div className={`text-lg ${
                          (reputation.score || 0) > 0 ? 'text-green-400' :
                          (reputation.score || 0) < 0 ? 'text-red-400' : 'text-white/60'
                        }`}>
                          {reputation.level || 'Neutral'}
                        </div>
                        <p className="text-xs text-white/40 mt-4">
                          Your moral reputation based on actions in the platform
                        </p>
                      </div>
                      
                      <div className="grid grid-cols-2 gap-4">
                        <div className="bg-green-500/10 border border-green-500/30 rounded-lg p-4">
                          <h4 className="text-sm font-bold text-green-400 mb-2">Good Actions</h4>
                          <p className="text-xs text-white/60">Helping others, completing tasks, mentoring</p>
                        </div>
                        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4">
                          <h4 className="text-sm font-bold text-red-400 mb-2">Bad Actions</h4>
                          <p className="text-xs text-white/60">Rule violations, harm, dishonesty</p>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Career Tab */}
                  {activeTab === 'career' && (
                    <div className="space-y-4">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                          <label className="block text-sm text-white/60 mb-1">Field</label>
                          <select
                            value={career.field}
                            onChange={e => setCareer({...career, field: e.target.value})}
                            className="w-full px-3 py-2 bg-white/5 border border-white/20 rounded text-white focus:border-neon-cyan outline-none"
                          >
                            <option value="education">Education</option>
                            <option value="healthcare">Healthcare</option>
                            <option value="technology">Technology</option>
                            <option value="arts">Arts</option>
                            <option value="business">Business</option>
                            <option value="science">Science</option>
                            <option value="governance">Governance</option>
                            <option value="social_work">Social Work</option>
                            <option value="freelance">Freelance</option>
                            <option value="volunteer">Volunteer</option>
                          </select>
                        </div>
                        <div>
                          <label className="block text-sm text-white/60 mb-1">Title</label>
                          <input
                            type="text"
                            value={career.title}
                            onChange={e => setCareer({...career, title: e.target.value})}
                            className="w-full px-3 py-2 bg-white/5 border border-white/20 rounded text-white focus:border-neon-cyan outline-none"
                            placeholder="e.g., Senior Developer"
                          />
                        </div>
                        <div>
                          <label className="block text-sm text-white/60 mb-1">Experience (years)</label>
                          <input
                            type="number"
                            value={career.experience_years}
                            onChange={e => setCareer({...career, experience_years: parseInt(e.target.value)})}
                            min={0}
                            className="w-full px-3 py-2 bg-white/5 border border-white/20 rounded text-white focus:border-neon-cyan outline-none"
                          />
                        </div>
                        <div className="flex items-center gap-2">
                          <input
                            type="checkbox"
                            checked={career.is_volunteer}
                            onChange={e => setCareer({...career, is_volunteer: e.target.checked})}
                            className="w-4 h-4"
                          />
                          <label className="text-sm text-white/60">Volunteer position (no financial reward)</label>
                        </div>
                      </div>
                      <CyberButton onClick={saveCareer} className="w-full">
                        <Briefcase className="w-4 h-4 mr-2" />
                        Save Career
                      </CyberButton>
                    </div>
                  )}

                  {/* Spirituality Tab */}
                  {activeTab === 'spirituality' && (
                    <div className="space-y-4">
                      <div className="bg-white/5 rounded-lg p-4">
                        <h4 className="text-sm font-bold text-white/80 mb-3">
                          <BookOpen className="w-4 h-4 inline mr-2" />
                          New Journal Entry
                        </h4>
                        <input
                          type="text"
                          value={newJournalEntry.title}
                          onChange={e => setNewJournalEntry({...newJournalEntry, title: e.target.value})}
                          className="w-full px-3 py-2 mb-2 bg-white/5 border border-white/20 rounded text-white focus:border-neon-cyan outline-none"
                          placeholder="Title"
                        />
                        <textarea
                          value={newJournalEntry.content}
                          onChange={e => setNewJournalEntry({...newJournalEntry, content: e.target.value})}
                          rows={4}
                          className="w-full px-3 py-2 bg-white/5 border border-white/20 rounded text-white focus:border-neon-cyan outline-none resize-none"
                          placeholder="Write your thoughts, reflections, or meditation notes..."
                        />
                        <CyberButton onClick={saveJournalEntry} className="w-full mt-2">
                          <Plus className="w-4 h-4 mr-2" />
                          Save Entry
                        </CyberButton>
                      </div>
                      
                      <div>
                        <h4 className="text-sm font-bold text-white/80 mb-3">Meditation Spaces</h4>
                        <div className="grid grid-cols-2 gap-3">
                          {[
                            { name: 'Zen Garden', icon: '🌿', desc: 'Peaceful meditation' },
                            { name: 'Starlight', icon: '✨', desc: 'Cosmic contemplation' },
                            { name: 'Forest', icon: '🌲', desc: 'Nature sanctuary' },
                            { name: 'Temple', icon: '🏛️', desc: 'Silent reflection' },
                          ].map(space => (
                            <div key={space.name} className="bg-white/5 rounded-lg p-3 cursor-pointer hover:bg-white/10 transition-colors">
                              <div className="text-2xl mb-1">{space.icon}</div>
                              <div className="text-sm font-bold">{space.name}</div>
                              <div className="text-xs text-white/40">{space.desc}</div>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>
          </CyberCard>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
};

export default LifeSimulationPanel;
