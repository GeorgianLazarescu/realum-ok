import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Sword, Crown, Star, Gift, Lock, Check, Zap, Trophy,
  Loader2, ChevronRight, Clock, Sparkles
} from 'lucide-react';
import axios from 'axios';
import { API } from '../utils/api';
import { useAuth } from '../context/AuthContext';
import { CyberCard, CyberButton } from '../components/common/CyberUI';
import { toast } from 'sonner';

const BattlePassPage = () => {
  const { user, refreshUser } = useAuth();
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  
  const [passInfo, setPassInfo] = useState(null);
  const [myProgress, setMyProgress] = useState(null);
  const [weeklyChallenges, setWeeklyChallenges] = useState([]);
  const [leaderboard, setLeaderboard] = useState([]);
  
  const [activeTab, setActiveTab] = useState('rewards'); // rewards, challenges, leaderboard
  const [showPurchaseModal, setShowPurchaseModal] = useState(false);

  useEffect(() => {
    fetchAllData();
  }, []);

  const fetchAllData = async () => {
    try {
      const [infoRes, progressRes, weeklyRes, leaderRes] = await Promise.all([
        axios.get(`${API}/battlepass/info`),
        axios.get(`${API}/battlepass/my-progress`),
        axios.get(`${API}/battlepass/weekly-challenges`),
        axios.get(`${API}/battlepass/leaderboard`)
      ]);
      
      setPassInfo(infoRes.data);
      setMyProgress(progressRes.data);
      setWeeklyChallenges(weeklyRes.data.challenges || []);
      setLeaderboard(leaderRes.data.leaderboard || []);
    } catch (error) {
      console.error('Failed to load battle pass:', error);
    }
    setLoading(false);
  };

  const handlePurchase = async () => {
    setProcessing(true);
    try {
      const res = await axios.post(`${API}/battlepass/purchase`, { use_rlm: true });
      toast.success(res.data.message);
      setShowPurchaseModal(false);
      fetchAllData();
      refreshUser();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to purchase');
    }
    setProcessing(false);
  };

  const handleClaimReward = async (level, track) => {
    setProcessing(true);
    try {
      const res = await axios.post(`${API}/battlepass/claim/${level}?track=${track}`);
      toast.success(`Recompensă revendicată! ${res.data.rlm_added ? `+${res.data.rlm_added} RLM` : ''}`);
      fetchAllData();
      refreshUser();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to claim');
    }
    setProcessing(false);
  };

  const handleClaimChallenge = async (challengeId) => {
    setProcessing(true);
    try {
      const res = await axios.post(`${API}/battlepass/weekly-challenges/${challengeId}/claim`);
      toast.success(res.data.message);
      fetchAllData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to claim');
    }
    setProcessing(false);
  };

  if (loading) {
    return (
      <div className="min-h-screen pt-20 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-neon-cyan" />
      </div>
    );
  }

  return (
    <div className="min-h-screen pt-16 sm:pt-20 pb-20 lg:pb-12 px-3 sm:px-4" data-testid="battlepass-page">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-6">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <h1 className="text-2xl sm:text-3xl font-orbitron font-black flex items-center gap-3">
                <Sword className="w-8 h-8 text-neon-purple" />
                <span>Battle Pass - <span className="text-neon-cyan">{passInfo?.name || 'Season 1'}</span></span>
              </h1>
              <p className="text-white/60 text-sm mt-1">
                {passInfo?.days_remaining} zile rămase în sezon
              </p>
            </div>
            {!myProgress?.is_premium && (
              <CyberButton variant="primary" onClick={() => setShowPurchaseModal(true)}>
                <Crown className="w-4 h-4 mr-2" /> Cumpără Premium ({passInfo?.pass_cost} RLM)
              </CyberButton>
            )}
          </div>
        </motion.div>

        {/* Progress Bar */}
        <CyberCard className="p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <div className="text-3xl font-orbitron text-neon-cyan">
                Level {myProgress?.level || 1}
              </div>
              <div className="text-sm text-white/50">
                {myProgress?.xp || 0} / {passInfo?.xp_per_level || 1000} XP
              </div>
            </div>
            <div className="text-right">
              {myProgress?.is_premium ? (
                <span className="px-4 py-2 bg-neon-yellow/20 border border-neon-yellow text-neon-yellow font-orbitron">
                  <Crown className="w-4 h-4 inline mr-2" /> PREMIUM
                </span>
              ) : (
                <span className="px-4 py-2 bg-white/10 border border-white/20 text-white/60">
                  FREE
                </span>
              )}
            </div>
          </div>
          
          <div className="relative h-4 bg-black/50 border border-white/20">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${myProgress?.level_progress?.percentage || 0}%` }}
              transition={{ duration: 1, ease: "easeOut" }}
              className="absolute inset-y-0 left-0 bg-gradient-to-r from-neon-purple to-neon-cyan"
            />
            <div className="absolute inset-0 flex items-center justify-center text-xs font-mono">
              {myProgress?.level_progress?.percentage || 0}%
            </div>
          </div>
          
          {/* Quick Stats */}
          <div className="grid grid-cols-3 gap-4 mt-4">
            <div className="text-center">
              <div className="text-xl font-orbitron text-neon-green">{myProgress?.claimed_free_count || 0}</div>
              <div className="text-xs text-white/50">Free Claims</div>
            </div>
            <div className="text-center">
              <div className="text-xl font-orbitron text-neon-yellow">{myProgress?.claimed_premium_count || 0}</div>
              <div className="text-xs text-white/50">Premium Claims</div>
            </div>
            <div className="text-center">
              <div className="text-xl font-orbitron text-neon-purple">{passInfo?.max_level || 50}</div>
              <div className="text-xs text-white/50">Max Level</div>
            </div>
          </div>
        </CyberCard>

        {/* Tabs */}
        <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
          {[
            { id: 'rewards', label: 'Recompense', icon: Gift },
            { id: 'challenges', label: 'Provocări', icon: Zap },
            { id: 'leaderboard', label: 'Clasament', icon: Trophy }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-2 font-mono text-sm whitespace-nowrap flex items-center gap-2 transition-all ${
                activeTab === tab.id 
                  ? 'bg-neon-purple/20 border border-neon-purple text-neon-purple' 
                  : 'border border-white/20 text-white/60 hover:border-white/40'
              }`}
            >
              <tab.icon className="w-4 h-4" /> {tab.label}
            </button>
          ))}
        </div>

        {/* Rewards Tab */}
        {activeTab === 'rewards' && (
          <div className="space-y-2">
            {/* Unclaimed Rewards Alert */}
            {(myProgress?.unclaimed_free?.length > 0 || myProgress?.unclaimed_premium?.length > 0) && (
              <CyberCard className="p-4 mb-4 border-neon-green">
                <div className="flex items-center gap-3">
                  <Sparkles className="w-6 h-6 text-neon-green" />
                  <div>
                    <div className="font-orbitron text-neon-green">Recompense disponibile!</div>
                    <div className="text-sm text-white/60">
                      {myProgress?.unclaimed_free?.length || 0} free + {myProgress?.unclaimed_premium?.length || 0} premium de revendicat
                    </div>
                  </div>
                </div>
              </CyberCard>
            )}
            
            {/* Rewards Grid */}
            <div className="grid grid-cols-5 md:grid-cols-10 gap-2">
              {Array.from({ length: passInfo?.max_level || 50 }, (_, i) => i + 1).map(level => {
                const rewards = myProgress?.all_rewards?.[level] || {};
                const isUnlocked = level <= (myProgress?.level || 1);
                const freeReward = rewards.free;
                const premiumReward = rewards.premium;
                const freeClaimed = myProgress?.claimed_free_count > 0 && 
                  !myProgress?.unclaimed_free?.find(u => u.level === level);
                const premiumClaimed = myProgress?.claimed_premium_count > 0 && 
                  !myProgress?.unclaimed_premium?.find(u => u.level === level);
                const canClaimFree = isUnlocked && freeReward && 
                  myProgress?.unclaimed_free?.find(u => u.level === level);
                const canClaimPremium = isUnlocked && premiumReward && myProgress?.is_premium && 
                  myProgress?.unclaimed_premium?.find(u => u.level === level);
                
                return (
                  <div
                    key={level}
                    className={`relative aspect-square border-2 flex flex-col items-center justify-center p-1 ${
                      isUnlocked 
                        ? 'border-neon-cyan bg-neon-cyan/10' 
                        : 'border-white/20 bg-black/30 opacity-50'
                    } ${level === myProgress?.level ? 'ring-2 ring-neon-yellow' : ''}`}
                  >
                    <div className="text-xs font-orbitron mb-1">{level}</div>
                    
                    {/* Free Track */}
                    <div className={`w-full h-1/3 flex items-center justify-center ${freeReward ? 'bg-neon-green/20' : 'bg-white/5'}`}>
                      {freeReward && (
                        canClaimFree ? (
                          <button
                            onClick={() => handleClaimReward(level, 'free')}
                            disabled={processing}
                            className="text-[8px] text-neon-green hover:scale-110 transition-transform"
                          >
                            <Gift className="w-3 h-3" />
                          </button>
                        ) : freeClaimed ? (
                          <Check className="w-3 h-3 text-neon-green" />
                        ) : (
                          <Star className="w-3 h-3 text-neon-green/50" />
                        )
                      )}
                    </div>
                    
                    {/* Premium Track */}
                    <div className={`w-full h-1/3 flex items-center justify-center ${premiumReward ? 'bg-neon-yellow/20' : 'bg-white/5'}`}>
                      {premiumReward && (
                        !myProgress?.is_premium ? (
                          <Lock className="w-3 h-3 text-white/30" />
                        ) : canClaimPremium ? (
                          <button
                            onClick={() => handleClaimReward(level, 'premium')}
                            disabled={processing}
                            className="text-[8px] text-neon-yellow hover:scale-110 transition-transform"
                          >
                            <Crown className="w-3 h-3" />
                          </button>
                        ) : premiumClaimed ? (
                          <Check className="w-3 h-3 text-neon-yellow" />
                        ) : (
                          <Crown className="w-3 h-3 text-neon-yellow/50" />
                        )
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
            
            {/* Legend */}
            <div className="flex justify-center gap-6 mt-4 text-xs">
              <div className="flex items-center gap-2">
                <div className="w-4 h-4 bg-neon-green/20 border border-neon-green"></div>
                <span className="text-white/60">Free Track</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-4 h-4 bg-neon-yellow/20 border border-neon-yellow"></div>
                <span className="text-white/60">Premium Track</span>
              </div>
              <div className="flex items-center gap-2">
                <Check className="w-4 h-4 text-neon-green" />
                <span className="text-white/60">Revendicat</span>
              </div>
            </div>
          </div>
        )}

        {/* Challenges Tab */}
        {activeTab === 'challenges' && (
          <div className="space-y-4">
            <CyberCard className="p-4">
              <h3 className="font-orbitron text-lg mb-4 flex items-center gap-2">
                <Zap className="w-5 h-5 text-neon-yellow" /> Provocări Săptămânale
              </h3>
              
              {weeklyChallenges.length > 0 ? (
                <div className="space-y-3">
                  {weeklyChallenges.map(challenge => (
                    <div
                      key={challenge.id}
                      className={`p-4 border ${
                        challenge.completed 
                          ? 'border-neon-green bg-neon-green/10' 
                          : 'border-white/20 bg-black/30'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <div>
                          <div className="font-orbitron">{challenge.name}</div>
                          <div className="text-sm text-white/60">{challenge.description}</div>
                        </div>
                        <div className="text-right">
                          <div className="font-mono text-neon-yellow">+{challenge.xp_reward} XP</div>
                        </div>
                      </div>
                      
                      <div className="flex items-center gap-4">
                        <div className="flex-1">
                          <div className="h-2 bg-black/50 border border-white/20">
                            <div
                              className="h-full bg-neon-cyan transition-all"
                              style={{ width: `${Math.min(100, (challenge.progress / challenge.target) * 100)}%` }}
                            />
                          </div>
                          <div className="text-xs text-white/50 mt-1">
                            {challenge.progress} / {challenge.target}
                          </div>
                        </div>
                        
                        {challenge.completed && !challenge.claimed && (
                          <CyberButton
                            variant="primary"
                            size="sm"
                            onClick={() => handleClaimChallenge(challenge.id)}
                            disabled={processing}
                          >
                            Claim
                          </CyberButton>
                        )}
                        {challenge.claimed && (
                          <Check className="w-6 h-6 text-neon-green" />
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-white/50 text-center py-8">Nicio provocare disponibilă</p>
              )}
            </CyberCard>
          </div>
        )}

        {/* Leaderboard Tab */}
        {activeTab === 'leaderboard' && (
          <CyberCard className="p-4">
            <h3 className="font-orbitron text-lg mb-4 flex items-center gap-2">
              <Trophy className="w-5 h-5 text-neon-yellow" /> Top Battle Pass
            </h3>
            
            <div className="space-y-2">
              {leaderboard.map((entry, i) => (
                <div
                  key={entry.username}
                  className={`flex items-center justify-between p-3 ${
                    i < 3 ? 'bg-neon-yellow/10 border border-neon-yellow/30' : 'bg-black/30 border border-white/10'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <span className={`text-2xl font-orbitron ${
                      i === 0 ? 'text-neon-yellow' : i === 1 ? 'text-gray-300' : i === 2 ? 'text-orange-400' : 'text-white/50'
                    }`}>
                      #{entry.rank}
                    </span>
                    <div>
                      <div className="font-mono text-neon-cyan flex items-center gap-2">
                        {entry.username}
                        {entry.is_premium && <Crown className="w-4 h-4 text-neon-yellow" />}
                      </div>
                      <div className="text-xs text-white/40">{entry.xp} XP</div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="font-orbitron text-neon-purple">Level {entry.level}</div>
                  </div>
                </div>
              ))}
            </div>
          </CyberCard>
        )}

        {/* Purchase Modal */}
        <AnimatePresence>
          {showPurchaseModal && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/90 z-50 flex items-center justify-center p-4"
              onClick={() => setShowPurchaseModal(false)}
            >
              <motion.div
                initial={{ scale: 0.9, y: 20 }}
                animate={{ scale: 1, y: 0 }}
                exit={{ scale: 0.9, y: 20 }}
                className="bg-gray-900 border border-neon-yellow p-6 max-w-md w-full"
                onClick={e => e.stopPropagation()}
              >
                <div className="text-center mb-6">
                  <Crown className="w-16 h-16 text-neon-yellow mx-auto mb-4" />
                  <h3 className="font-orbitron text-2xl text-neon-yellow mb-2">Battle Pass Premium</h3>
                  <p className="text-white/60">Deblochează toate recompensele premium!</p>
                </div>
                
                <div className="space-y-3 mb-6">
                  <div className="flex items-center gap-3 text-sm">
                    <Check className="w-5 h-5 text-neon-green" />
                    <span>+{passInfo?.total_premium_rlm || 0} RLM total în recompense</span>
                  </div>
                  <div className="flex items-center gap-3 text-sm">
                    <Check className="w-5 h-5 text-neon-green" />
                    <span>Cosmetice exclusive (avatare, efecte, titluri)</span>
                  </div>
                  <div className="flex items-center gap-3 text-sm">
                    <Check className="w-5 h-5 text-neon-green" />
                    <span>Badge-uri unice de sezon</span>
                  </div>
                  <div className="flex items-center gap-3 text-sm">
                    <Check className="w-5 h-5 text-neon-green" />
                    <span>XP Boost-uri progresive</span>
                  </div>
                </div>
                
                <div className="p-4 bg-neon-yellow/10 border border-neon-yellow/30 text-center mb-6">
                  <div className="text-3xl font-orbitron text-neon-yellow">{passInfo?.pass_cost} RLM</div>
                  <div className="text-sm text-white/50">Balanța ta: {user?.realum_balance?.toFixed(0)} RLM</div>
                </div>
                
                <div className="flex gap-3">
                  <CyberButton variant="outline" className="flex-1" onClick={() => setShowPurchaseModal(false)}>
                    Anulează
                  </CyberButton>
                  <CyberButton
                    variant="primary"
                    className="flex-1"
                    onClick={handlePurchase}
                    disabled={processing || (user?.realum_balance || 0) < (passInfo?.pass_cost || 500)}
                  >
                    {processing ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Cumpără Acum'}
                  </CyberButton>
                </div>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
};

export default BattlePassPage;
