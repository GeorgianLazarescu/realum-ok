import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { 
  Trophy, Star, Target, Zap, Medal, Crown, 
  CheckCircle, Lock, TrendingUp, Award
} from 'lucide-react';
import axios from 'axios';
import { API } from '../utils/api';
import { useAuth } from '../context/AuthContext';
import { CyberCard, CyberButton } from '../components/common/CyberUI';

const AchievementsPage = () => {
  const { user } = useAuth();
  const [achievements, setAchievements] = useState(null);
  const [progress, setProgress] = useState([]);
  const [leaderboard, setLeaderboard] = useState([]);
  const [tiers, setTiers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [checking, setChecking] = useState(false);
  const [newlyEarned, setNewlyEarned] = useState([]);
  const [activeTab, setActiveTab] = useState('all');

  useEffect(() => {
    Promise.all([
      axios.get(`${API}/achievements/my`),
      axios.get(`${API}/achievements/progress`),
      axios.get(`${API}/achievements/leaderboard?limit=10`),
      axios.get(`${API}/achievements/tiers`)
    ]).then(([achRes, progRes, leadRes, tierRes]) => {
      setAchievements(achRes.data);
      setProgress(progRes.data.progress || []);
      setLeaderboard(leadRes.data.leaderboard || []);
      setTiers(tierRes.data.tiers || []);
    }).catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const checkAchievements = async () => {
    setChecking(true);
    try {
      const res = await axios.post(`${API}/achievements/check`);
      if (res.data.newly_earned?.length > 0) {
        setNewlyEarned(res.data.newly_earned);
        // Refresh achievements
        const achRes = await axios.get(`${API}/achievements/my`);
        setAchievements(achRes.data);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setChecking(false);
    }
  };

  const tierColors = {
    bronze: '#CD7F32',
    silver: '#C0C0C0',
    gold: '#FFD700',
    platinum: '#E5E4E2',
    diamond: '#B9F2FF'
  };

  const tierIcons = {
    bronze: Medal,
    silver: Medal,
    gold: Trophy,
    platinum: Crown,
    diamond: Crown
  };

  const categoryIcons = {
    learning: '📚',
    social: '👥',
    governance: '🗳️',
    economic: '💰',
    contribution: '🛠️',
    engagement: '🔥',
    special: '⭐'
  };

  if (loading) {
    return (
      <div className="min-h-screen pt-20 flex items-center justify-center">
        <div className="text-neon-cyan font-mono">Loading achievements...</div>
      </div>
    );
  }

  const categories = achievements ? [...new Set(achievements.achievements.map(a => a.category))] : [];

  return (
    <div className="min-h-screen pt-16 sm:pt-20 pb-20 lg:pb-12 px-3 sm:px-4" data-testid="achievements-page">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-6">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h1 className="text-2xl sm:text-3xl font-orbitron font-black mb-2">
                <Trophy className="inline w-8 h-8 mr-2 text-neon-yellow" />
                Achievements
              </h1>
              <p className="text-white/60 text-sm">Track your progress and unlock rewards</p>
            </div>
            <CyberButton onClick={checkAchievements} disabled={checking} variant="success">
              {checking ? 'Checking...' : 'Check Progress'}
            </CyberButton>
          </div>
        </motion.div>

        {/* Newly Earned Banner */}
        {newlyEarned.length > 0 && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="mb-6 p-4 bg-gradient-to-r from-neon-yellow/20 to-neon-green/20 border border-neon-yellow"
          >
            <h3 className="font-orbitron font-bold text-neon-yellow mb-2 flex items-center gap-2">
              <Star className="w-5 h-5" /> New Achievements Unlocked!
            </h3>
            <div className="flex flex-wrap gap-2">
              {newlyEarned.map((a, i) => (
                <span key={i} className="px-3 py-1 bg-black/50 border border-neon-yellow text-sm">
                  {a.name} <span className="text-neon-green">+{a.xp_reward} XP</span>
                </span>
              ))}
            </div>
          </motion.div>
        )}

        {/* Stats Overview */}
        {achievements && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
            <CyberCard className="text-center p-4">
              <Trophy className="w-6 h-6 mx-auto mb-2 text-neon-yellow" />
              <div className="text-2xl font-orbitron font-bold text-neon-yellow">
                {achievements.earned_count}
              </div>
              <div className="text-xs text-white/50">Earned</div>
            </CyberCard>
            <CyberCard className="text-center p-4">
              <Target className="w-6 h-6 mx-auto mb-2 text-neon-cyan" />
              <div className="text-2xl font-orbitron font-bold text-neon-cyan">
                {achievements.total_count}
              </div>
              <div className="text-xs text-white/50">Total</div>
            </CyberCard>
            <CyberCard className="text-center p-4">
              <Zap className="w-6 h-6 mx-auto mb-2 text-neon-purple" />
              <div className="text-2xl font-orbitron font-bold text-neon-purple">
                {achievements.total_xp_from_achievements}
              </div>
              <div className="text-xs text-white/50">XP Earned</div>
            </CyberCard>
            <CyberCard className="text-center p-4">
              <TrendingUp className="w-6 h-6 mx-auto mb-2 text-neon-green" />
              <div className="text-2xl font-orbitron font-bold text-neon-green">
                {achievements.completion_percentage}%
              </div>
              <div className="text-xs text-white/50">Complete</div>
            </CyberCard>
          </div>
        )}

        <div className="grid lg:grid-cols-3 gap-6">
          {/* Main Content */}
          <div className="lg:col-span-2 space-y-6">
            {/* Category Tabs */}
            <div className="flex flex-wrap gap-2">
              <button
                onClick={() => setActiveTab('all')}
                className={`px-3 py-2 text-xs font-mono uppercase border transition-colors ${
                  activeTab === 'all' ? 'border-neon-cyan bg-neon-cyan/10 text-neon-cyan' : 'border-white/20 text-white/60'
                }`}
              >
                All
              </button>
              {categories.map(cat => (
                <button
                  key={cat}
                  onClick={() => setActiveTab(cat)}
                  className={`px-3 py-2 text-xs font-mono uppercase border transition-colors flex items-center gap-1 ${
                    activeTab === cat ? 'border-neon-cyan bg-neon-cyan/10 text-neon-cyan' : 'border-white/20 text-white/60'
                  }`}
                >
                  <span>{categoryIcons[cat] || '🏆'}</span>
                  {cat}
                </button>
              ))}
            </div>

            {/* Achievements Grid */}
            <div className="grid sm:grid-cols-2 gap-3">
              {achievements?.achievements
                .filter(a => activeTab === 'all' || a.category === activeTab)
                .map((ach, i) => {
                  const TierIcon = tierIcons[ach.tier] || Medal;
                  return (
                    <motion.div
                      key={ach.key}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: i * 0.05 }}
                    >
                      <CyberCard 
                        className={`p-4 ${ach.earned ? 'border-neon-green/50' : 'opacity-60'}`}
                      >
                        <div className="flex items-start gap-3">
                          <div 
                            className={`w-12 h-12 flex items-center justify-center border ${
                              ach.earned ? 'bg-black/50' : 'bg-black/30'
                            }`}
                            style={{ borderColor: tierColors[ach.tier] }}
                          >
                            {ach.earned ? (
                              <TierIcon className="w-6 h-6" style={{ color: tierColors[ach.tier] }} />
                            ) : (
                              <Lock className="w-5 h-5 text-white/30" />
                            )}
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                              <h4 className="font-mono text-sm font-bold truncate">{ach.name}</h4>
                              {ach.earned && <CheckCircle className="w-4 h-4 text-neon-green flex-shrink-0" />}
                            </div>
                            <p className="text-xs text-white/50 line-clamp-2">{ach.description}</p>
                            <div className="flex items-center gap-2 mt-2">
                              <span 
                                className="text-[10px] uppercase px-2 py-0.5 border"
                                style={{ borderColor: tierColors[ach.tier], color: tierColors[ach.tier] }}
                              >
                                {ach.tier}
                              </span>
                              <span className="text-xs text-neon-purple">+{ach.xp_reward} XP</span>
                            </div>
                          </div>
                        </div>
                      </CyberCard>
                    </motion.div>
                  );
                })}
            </div>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Progress Tracker */}
            <CyberCard className="p-4">
              <h3 className="font-orbitron font-bold mb-4 flex items-center gap-2">
                <Target className="w-5 h-5 text-neon-cyan" />
                Almost There
              </h3>
              <div className="space-y-3">
                {progress.slice(0, 5).map((p, i) => (
                  <div key={i} className="p-3 bg-black/30 border border-white/10">
                    <div className="flex justify-between text-sm mb-2">
                      <span className="font-mono truncate">{p.name}</span>
                      <span className="text-neon-cyan text-xs">{p.current}/{p.target}</span>
                    </div>
                    <div className="h-2 bg-black/50 overflow-hidden">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${p.percentage}%` }}
                        className="h-full bg-gradient-to-r from-neon-cyan to-neon-purple"
                      />
                    </div>
                  </div>
                ))}
                {progress.length === 0 && (
                  <p className="text-white/50 text-sm text-center py-4">No achievements in progress</p>
                )}
              </div>
            </CyberCard>

            {/* Leaderboard */}
            <CyberCard className="p-4">
              <h3 className="font-orbitron font-bold mb-4 flex items-center gap-2">
                <Award className="w-5 h-5 text-neon-yellow" />
                Top Achievers
              </h3>
              <div className="space-y-2">
                {leaderboard.slice(0, 5).map((entry, i) => (
                  <div 
                    key={i} 
                    className={`p-2 flex items-center gap-3 ${
                      entry.user_id === user?.id ? 'bg-neon-cyan/10 border border-neon-cyan/30' : 'bg-black/30'
                    }`}
                  >
                    <span className={`w-6 text-center font-orbitron font-bold ${
                      i === 0 ? 'text-neon-yellow' : i === 1 ? 'text-gray-300' : i === 2 ? 'text-orange-400' : 'text-white/50'
                    }`}>
                      {entry.rank}
                    </span>
                    <div className="flex-1 min-w-0">
                      <span className="text-sm truncate block">{entry.username}</span>
                      <span className="text-xs text-white/50">Lv.{entry.level}</span>
                    </div>
                    <span className="text-neon-yellow font-mono text-sm">
                      {entry.achievements}
                    </span>
                  </div>
                ))}
              </div>
            </CyberCard>

            {/* Tier Legend */}
            <CyberCard className="p-4">
              <h3 className="font-orbitron font-bold mb-3 text-sm">Achievement Tiers</h3>
              <div className="space-y-2">
                {tiers.map(tier => (
                  <div key={tier.key} className="flex items-center gap-2 text-sm">
                    <div 
                      className="w-3 h-3 rounded-full"
                      style={{ backgroundColor: tier.color }}
                    />
                    <span className="capitalize">{tier.name}</span>
                    <span className="text-white/40 text-xs ml-auto">+{tier.min_xp} XP</span>
                  </div>
                ))}
              </div>
            </CyberCard>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AchievementsPage;
