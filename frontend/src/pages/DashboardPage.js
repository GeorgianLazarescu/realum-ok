import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { 
  Coins, Zap, Star, Award, Briefcase, GraduationCap, ShoppingBag, 
  Layers, Vote, Building2, TrendingUp, Users
} from 'lucide-react';
import axios from 'axios';
import { API } from '../utils/api';
import { useAuth } from '../context/AuthContext';
import { useTranslation } from '../context/LanguageContext';
import { CyberCard } from '../components/common/CyberUI';
import { ObjectivesPanel, MiniTasksPanel, RandomEventsPanel, WorldTimeDisplay, SeasonalEventsBanner } from '../components/DashboardWidgets';

const DashboardPage = () => {
  const { user } = useAuth();
  const t = useTranslation();
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);
  const [tokenStats, setTokenStats] = useState(null);
  
  useEffect(() => {
    axios.get(`${API}/stats`).then(res => setStats(res.data)).catch(console.error);
    axios.get(`${API}/token/stats`).then(res => setTokenStats(res.data)).catch(console.error);
  }, []);
  
  const roleColors = {
    creator: '#E040FB',
    contributor: '#00FF88',
    evaluator: '#40C4FF',
    partner: '#FF6B35',
    citizen: '#00F0FF'
  };
  
  const quickActions = [
    { label: t('jobs'), icon: Briefcase, path: '/jobs', color: '#FF003C' },
    { label: t('courses'), icon: GraduationCap, path: '/courses', color: '#9D4EDD' },
    { label: t('marketplace'), icon: ShoppingBag, path: '/marketplace', color: '#FF6B35' },
    { label: t('metaverse'), icon: Layers, path: '/metaverse/3d', color: '#00F0FF' },
    { label: t('voting'), icon: Vote, path: '/voting', color: '#40C4FF' },
    { label: 'Referral', icon: Users, path: '/referral', color: '#00FF88' }
  ];
  
  return (
    <div className="min-h-screen pt-16 sm:pt-20 pb-20 lg:pb-12 px-3 sm:px-4" data-testid="dashboard">
      <div className="max-w-7xl mx-auto">
        {/* Welcome Section */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-6 sm:mb-8">
          <div className="flex justify-between items-start">
            <div>
              <h1 className="text-2xl sm:text-3xl md:text-4xl font-orbitron font-black mb-2 leading-tight">
                {t('welcome')}, <span className="text-neon-cyan block sm:inline">{user?.username}</span>
              </h1>
              <div className="flex flex-wrap items-center gap-2 text-sm">
                <span 
                  className="px-2 py-1 text-xs border uppercase"
                  style={{ borderColor: roleColors[user?.role], color: roleColors[user?.role] }}
                  data-testid="user-role"
                >
                  {user?.role}
                </span>
                <span className="text-white/60 text-xs sm:text-sm">Member since {new Date(user?.created_at).toLocaleDateString()}</span>
              </div>
            </div>
            {/* World Time */}
            <div className="hidden md:block">
              <WorldTimeDisplay />
            </div>
          </div>
        </motion.div>
        
        {/* Stats Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 sm:gap-4 mb-6">
          <CyberCard className="text-center p-3 sm:p-6">
            <Coins className="w-6 h-6 sm:w-8 sm:h-8 mx-auto mb-1 sm:mb-2 text-neon-cyan" />
            <div className="text-xl sm:text-2xl font-orbitron font-bold text-neon-cyan" data-testid="balance-display">
              {user?.realum_balance?.toFixed(0)}
            </div>
            <div className="text-[10px] sm:text-xs text-white/50 uppercase">RLM</div>
          </CyberCard>
          
          <CyberCard className="text-center p-3 sm:p-6">
            <Zap className="w-6 h-6 sm:w-8 sm:h-8 mx-auto mb-1 sm:mb-2 text-neon-purple" />
            <div className="text-xl sm:text-2xl font-orbitron font-bold text-neon-purple" data-testid="xp-display">
              {user?.xp || 0}
            </div>
            <div className="text-[10px] sm:text-xs text-white/50 uppercase">{t('xp')}</div>
          </CyberCard>
          
          <CyberCard className="text-center p-3 sm:p-6">
            <Star className="w-6 h-6 sm:w-8 sm:h-8 mx-auto mb-1 sm:mb-2 text-neon-yellow" />
            <div className="text-xl sm:text-2xl font-orbitron font-bold text-neon-yellow" data-testid="level-display">
              {user?.level || 1}
            </div>
            <div className="text-[10px] sm:text-xs text-white/50 uppercase">{t('level')}</div>
          </CyberCard>
          
          <CyberCard className="text-center p-3 sm:p-6">
            <Award className="w-6 h-6 sm:w-8 sm:h-8 mx-auto mb-1 sm:mb-2 text-neon-green" />
            <div className="text-xl sm:text-2xl font-orbitron font-bold text-neon-green" data-testid="badges-count">
              {user?.badges?.length || 0}
            </div>
            <div className="text-[10px] sm:text-xs text-white/50 uppercase">{t('badges')}</div>
          </CyberCard>
        </div>
        
        <div className="grid lg:grid-cols-3 gap-4 sm:gap-6">
          {/* Main Content */}
          <div className="lg:col-span-2 space-y-4 sm:space-y-6">
            {/* Quick Actions */}
            <CyberCard className="p-4 sm:p-6">
              <h3 className="font-orbitron font-bold mb-3 sm:mb-4 text-sm sm:text-base">Quick Actions</h3>
              <div className="grid grid-cols-3 sm:grid-cols-3 md:grid-cols-6 gap-2 sm:gap-3">
                {quickActions.map(action => (
                  <motion.button
                    key={action.path}
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={() => navigate(action.path)}
                    className="p-3 sm:p-4 border border-white/10 hover:border-white/30 active:bg-white/5 transition-all text-center flex flex-col items-center"
                    data-testid={`quick-action-${action.path.slice(1)}`}
                  >
                    <action.icon className="w-5 h-5 sm:w-6 sm:h-6 mb-1 sm:mb-2" style={{ color: action.color }} />
                    <span className="text-[10px] sm:text-xs font-mono">{action.label}</span>
                  </motion.button>
                ))}
              </div>
            </CyberCard>
            
            {/* Token Economy */}
            {tokenStats && (
              <CyberCard className="p-4 sm:p-6">
                <h3 className="font-orbitron font-bold mb-3 sm:mb-4 flex items-center gap-2 text-sm sm:text-base">
                  <TrendingUp className="w-4 h-4 sm:w-5 sm:h-5 text-neon-cyan" />
                  Token Economy
                </h3>
                <div className="grid grid-cols-3 gap-2 sm:gap-4">
                  <div className="p-2 sm:p-3 bg-black/30 border border-white/10">
                    <div className="text-[10px] sm:text-xs text-white/50 mb-1">{t('totalSupply')}</div>
                    <div className="font-mono text-xs sm:text-base text-neon-cyan">{tokenStats.total_supply?.toFixed(0)}</div>
                  </div>
                  <div className="p-2 sm:p-3 bg-black/30 border border-white/10">
                    <div className="text-[10px] sm:text-xs text-white/50 mb-1">{t('tokensBurned')}</div>
                    <div className="font-mono text-xs sm:text-base text-neon-red">{tokenStats.total_burned?.toFixed(1)}</div>
                  </div>
                  <div className="p-2 sm:p-3 bg-black/30 border border-white/10">
                    <div className="text-[10px] sm:text-xs text-white/50 mb-1">{t('burnRate')}</div>
                    <div className="font-mono text-xs sm:text-base text-neon-yellow">{tokenStats.burn_rate}%</div>
                  </div>
                </div>
              </CyberCard>
            )}
          </div>
          
          {/* Sidebar */}
          <div className="space-y-4 sm:space-y-6">
            {/* Objectives Panel */}
            <ObjectivesPanel />
            
            {/* Mini Tasks Panel */}
            <MiniTasksPanel />
            
            {/* Random Events Panel */}
            <RandomEventsPanel />
            
            {/* Platform Stats */}
            {stats && (
              <CyberCard className="p-4 sm:p-6">
                <h3 className="font-orbitron font-bold mb-3 sm:mb-4 text-sm sm:text-base">Platform Stats</h3>
                <div className="grid grid-cols-2 lg:grid-cols-1 gap-2 sm:gap-3">
                  <div className="flex justify-between text-xs sm:text-sm p-2 bg-black/20">
                    <span className="text-white/50">Users</span>
                    <span className="font-mono text-neon-cyan">{stats.total_users}</span>
                  </div>
                  <div className="flex justify-between text-xs sm:text-sm p-2 bg-black/20">
                    <span className="text-white/50">Jobs Done</span>
                    <span className="font-mono text-neon-green">{stats.jobs_completed}</span>
                  </div>
                  <div className="flex justify-between text-xs sm:text-sm p-2 bg-black/20">
                    <span className="text-white/50">Proposals</span>
                    <span className="font-mono text-neon-purple">{stats.active_proposals}</span>
                  </div>
                  <div className="flex justify-between text-xs sm:text-sm p-2 bg-black/20">
                    <span className="text-white/50">Courses</span>
                    <span className="font-mono text-neon-yellow">{stats.courses_available}</span>
                  </div>
                </div>
              </CyberCard>
            )}
            
            {/* Badges Preview */}
            <CyberCard className="p-4 sm:p-6">
              <h3 className="font-orbitron font-bold mb-3 sm:mb-4 text-sm sm:text-base">Your Badges</h3>
              <div className="flex flex-wrap gap-2">
                {user?.badges?.slice(0, 6).map(badge => (
                  <div key={badge} className="w-9 h-9 sm:w-10 sm:h-10 bg-neon-cyan/10 border border-neon-cyan/30 flex items-center justify-center">
                    <span className="text-base sm:text-lg">🏆</span>
                  </div>
                ))}
                {user?.badges?.length > 6 && (
                  <Link to="/profile" className="w-9 h-9 sm:w-10 sm:h-10 bg-white/5 border border-white/20 flex items-center justify-center text-xs text-white/50">
                    +{user.badges.length - 6}
                  </Link>
                )}
              </div>
              <Link to="/profile" className="text-xs text-neon-cyan hover:underline mt-3 block">
                View all badges →
              </Link>
            </CyberCard>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DashboardPage;
