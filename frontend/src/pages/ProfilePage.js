import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { User, Award, Settings } from 'lucide-react';
import axios from 'axios';
import { API } from '../utils/api';
import { useAuth } from '../context/AuthContext';
import { useTranslation } from '../context/LanguageContext';
import { CyberCard, CyberButton } from '../components/common/CyberUI';

const ProfilePage = () => {
  const { user, refreshUser } = useAuth();
  const t = useTranslation();
  const [allBadges, setAllBadges] = useState([]);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    axios.get(`${API}/badges`).then(res => setAllBadges(res.data.badges || [])).catch(console.error).finally(() => setLoading(false));
  }, []);
  
  const roleColors = {
    creator: '#E040FB', contributor: '#00FF88', evaluator: '#40C4FF', partner: '#FF6B35', citizen: '#00F0FF'
  };
  
  const rarityColors = {
    common: '#9CA3AF', uncommon: '#22C55E', rare: '#3B82F6', legendary: '#F59E0B'
  };
  
  const userBadges = user?.badges || [];
  
  return (
    <div className="min-h-screen pt-16 sm:pt-20 pb-20 lg:pb-12 px-3 sm:px-4" data-testid="profile-page">
      <div className="max-w-4xl mx-auto">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-6 sm:mb-8">
          <h1 className="text-2xl sm:text-3xl md:text-4xl font-orbitron font-black flex items-center gap-3">
            <User className="w-8 h-8 sm:w-10 sm:h-10 text-neon-cyan" />
            {t('profile')}
          </h1>
        </motion.div>
        
        {/* User Info Card */}
        <CyberCard className="mb-6" glow>
          <div className="flex flex-col sm:flex-row sm:items-center gap-4">
            <div className="w-16 h-16 sm:w-20 sm:h-20 bg-gradient-to-br from-neon-cyan to-neon-purple flex items-center justify-center text-2xl sm:text-3xl font-black">
              {user?.username?.charAt(0).toUpperCase()}
            </div>
            <div className="flex-1">
              <h2 className="text-xl sm:text-2xl font-orbitron font-bold">{user?.username}</h2>
              <div className="flex flex-wrap items-center gap-2 mt-1">
                <span 
                  className="px-2 py-1 text-xs border uppercase"
                  style={{ borderColor: roleColors[user?.role], color: roleColors[user?.role] }}
                >
                  {user?.role}
                </span>
                <span className="text-xs sm:text-sm text-white/60">{user?.email}</span>
              </div>
              <div className="flex flex-wrap gap-4 mt-3 text-xs sm:text-sm">
                <div>
                  <span className="text-white/50">Level</span>{' '}
                  <span className="font-mono text-neon-yellow">{user?.level}</span>
                </div>
                <div>
                  <span className="text-white/50">XP</span>{' '}
                  <span className="font-mono text-neon-purple">{user?.xp}</span>
                </div>
                <div>
                  <span className="text-white/50">Balance</span>{' '}
                  <span className="font-mono text-neon-cyan">{user?.realum_balance?.toFixed(0)} RLM</span>
                </div>
              </div>
            </div>
          </div>
        </CyberCard>
        
        {/* Skills */}
        {user?.skills?.length > 0 && (
          <CyberCard className="mb-6">
            <h3 className="font-orbitron font-bold mb-4 text-sm sm:text-base">Skills</h3>
            <div className="flex flex-wrap gap-2">
              {user.skills.map(skill => (
                <span key={skill} className="px-3 py-1.5 text-xs bg-neon-cyan/10 text-neon-cyan border border-neon-cyan/30">
                  {skill}
                </span>
              ))}
            </div>
          </CyberCard>
        )}
        
        {/* Badges Collection */}
        <CyberCard>
          <h3 className="font-orbitron font-bold mb-4 flex items-center gap-2 text-sm sm:text-base">
            <Award className="w-5 h-5 text-neon-yellow" />
            Badge Collection ({userBadges.length}/{allBadges.length})
          </h3>
          
          {loading ? (
            <div className="text-center text-white/50">{t('loading')}</div>
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2 sm:gap-3">
              {allBadges.map(badge => {
                const owned = userBadges.includes(badge.id);
                return (
                  <div 
                    key={badge.id}
                    className={`p-3 border text-center transition-all ${
                      owned 
                        ? 'border-neon-cyan/50 bg-neon-cyan/5' 
                        : 'border-white/10 bg-black/30 opacity-50'
                    }`}
                  >
                    <div className="text-2xl sm:text-3xl mb-2">{badge.icon}</div>
                    <div className="text-xs font-mono font-bold truncate">{badge.name}</div>
                    <div className="text-[10px] text-white/50 line-clamp-2 mt-1">{badge.description}</div>
                    <div 
                      className="text-[10px] mt-2 uppercase"
                      style={{ color: rarityColors[badge.rarity] }}
                    >
                      {badge.rarity}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CyberCard>
      </div>
    </div>
  );
};

export default ProfilePage;
