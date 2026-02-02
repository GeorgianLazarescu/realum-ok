import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Trophy, Medal } from 'lucide-react';
import axios from 'axios';
import { API } from '../../utils/api';
import { useAuth } from '../../context/AuthContext';
import { useTranslation } from '../../context/LanguageContext';
import { CyberCard } from '../../components/common/CyberUI';

const LeaderboardPage = () => {
  const { user } = useAuth();
  const t = useTranslation();
  const [leaderboard, setLeaderboard] = useState([]);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    axios.get(`${API}/leaderboard`).then(res => setLeaderboard(res.data.leaderboard || [])).catch(console.error).finally(() => setLoading(false));
  }, []);
  
  const roleColors = {
    creator: '#E040FB', contributor: '#00FF88', evaluator: '#40C4FF', partner: '#FF6B35', citizen: '#00F0FF'
  };
  
  const getRankIcon = (rank) => {
    if (rank === 1) return <Medal className="w-5 h-5 sm:w-6 sm:h-6 text-yellow-400" />;
    if (rank === 2) return <Medal className="w-5 h-5 sm:w-6 sm:h-6 text-gray-300" />;
    if (rank === 3) return <Medal className="w-5 h-5 sm:w-6 sm:h-6 text-amber-600" />;
    return <span className="text-sm sm:text-base font-mono text-white/50">#{rank}</span>;
  };
  
  return (
    <div className="min-h-screen pt-16 sm:pt-20 pb-20 lg:pb-12 px-3 sm:px-4" data-testid="leaderboard-page">
      <div className="max-w-4xl mx-auto">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-6 sm:mb-8">
          <h1 className="text-2xl sm:text-3xl md:text-4xl font-orbitron font-black flex items-center gap-3">
            <Trophy className="w-8 h-8 sm:w-10 sm:h-10 text-neon-yellow" />
            {t('leaderboard')}
          </h1>
          <p className="text-white/60 mt-2 text-sm sm:text-base">Top contributors in REALUM</p>
        </motion.div>
        
        {loading ? (
          <div className="text-center text-white/50">{t('loading')}</div>
        ) : (
          <div className="space-y-2 sm:space-y-3">
            {leaderboard.map((entry, index) => (
              <CyberCard 
                key={entry.id}
                className={`p-3 sm:p-4 ${entry.id === user?.id ? 'border-neon-cyan' : ''}`}
              >
                <div className="flex items-center gap-3 sm:gap-4">
                  {/* Rank */}
                  <div className="w-8 sm:w-10 flex items-center justify-center">
                    {getRankIcon(entry.rank)}
                  </div>
                  
                  {/* User Info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className={`font-mono font-bold text-sm sm:text-base truncate ${entry.id === user?.id ? 'text-neon-cyan' : ''}`}>
                        {entry.username}
                      </span>
                      <span 
                        className="px-1.5 py-0.5 text-[10px] border uppercase hidden sm:inline"
                        style={{ borderColor: roleColors[entry.role], color: roleColors[entry.role] }}
                      >
                        {entry.role}
                      </span>
                    </div>
                    <div className="text-xs text-white/50">
                      Level {entry.level} • {entry.badges_count} badges
                    </div>
                  </div>
                  
                  {/* Stats */}
                  <div className="text-right">
                    <div className="font-mono text-neon-purple text-sm sm:text-base">{entry.xp} XP</div>
                    <div className="font-mono text-neon-cyan text-xs sm:text-sm">{entry.realum_balance?.toFixed(0)} RLM</div>
                  </div>
                </div>
              </CyberCard>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default LeaderboardPage;
