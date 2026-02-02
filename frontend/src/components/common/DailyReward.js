import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Gift, Flame, X, Coins, Zap, Trophy } from 'lucide-react';
import axios from 'axios';
import { API } from '../../utils/api';
import { useAuth } from '../../context/AuthContext';
import { useConfetti } from '../../context/ConfettiContext';
import { CyberButton } from './CyberUI';

const DailyReward = () => {
  const { refreshUser } = useAuth();
  const { triggerConfetti } = useConfetti();
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [claiming, setClaiming] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [claimResult, setClaimResult] = useState(null);

  const fetchStatus = async () => {
    try {
      const res = await axios.get(`${API}/daily/status`);
      setStatus(res.data);
      // Auto-show modal if reward available
      if (res.data.can_claim) {
        setShowModal(true);
      }
    } catch (err) {
      console.error('Error fetching daily status:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
  }, []);

  const claimReward = async () => {
    setClaiming(true);
    try {
      const res = await axios.post(`${API}/daily/claim`);
      setClaimResult(res.data);
      triggerConfetti();
      refreshUser();
      // Update status
      setStatus(prev => ({ ...prev, can_claim: false, streak: res.data.new_streak }));
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to claim reward');
    } finally {
      setClaiming(false);
    }
  };

  if (loading || !status) return null;

  return (
    <>
      {/* Floating Daily Reward Button */}
      {status.can_claim && (
        <motion.button
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.95 }}
          onClick={() => setShowModal(true)}
          className="fixed bottom-24 lg:bottom-8 right-4 z-40 w-14 h-14 bg-gradient-to-br from-neon-yellow to-neon-orange rounded-full flex items-center justify-center shadow-lg animate-pulse"
          data-testid="daily-reward-btn"
        >
          <Gift className="w-7 h-7 text-black" />
        </motion.button>
      )}

      {/* Streak indicator on navbar (always visible) */}
      {!status.can_claim && status.streak > 0 && (
        <div className="fixed bottom-24 lg:bottom-8 right-4 z-40 bg-black/80 border border-neon-orange/50 px-3 py-2 flex items-center gap-2">
          <Flame className="w-4 h-4 text-neon-orange" />
          <span className="text-sm font-mono text-neon-orange">{status.streak}</span>
        </div>
      )}

      {/* Daily Reward Modal */}
      <AnimatePresence>
        {showModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4"
            onClick={() => !claiming && setShowModal(false)}
          >
            <motion.div
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.8, opacity: 0 }}
              onClick={(e) => e.stopPropagation()}
              className="bg-black border border-neon-cyan w-full max-w-sm relative overflow-hidden"
            >
              {/* Header Glow */}
              <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-neon-yellow via-neon-orange to-neon-yellow" />
              
              {/* Close Button */}
              <button
                onClick={() => setShowModal(false)}
                className="absolute top-3 right-3 text-white/50 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>

              <div className="p-6">
                {!claimResult ? (
                  <>
                    {/* Pre-claim view */}
                    <div className="text-center mb-6">
                      <motion.div
                        animate={{ rotate: [0, 10, -10, 0], scale: [1, 1.1, 1] }}
                        transition={{ repeat: Infinity, duration: 2 }}
                        className="w-20 h-20 mx-auto mb-4 bg-gradient-to-br from-neon-yellow to-neon-orange rounded-full flex items-center justify-center"
                      >
                        <Gift className="w-10 h-10 text-black" />
                      </motion.div>
                      <h3 className="font-orbitron font-bold text-xl mb-2">Daily Reward</h3>
                      <p className="text-white/60 text-sm">
                        {status.can_claim 
                          ? "Your daily reward is ready!" 
                          : "Come back tomorrow for your next reward"}
                      </p>
                    </div>

                    {/* Streak Display */}
                    <div className="flex items-center justify-center gap-4 mb-6">
                      <div className="text-center">
                        <div className="flex items-center gap-1 text-neon-orange mb-1">
                          <Flame className="w-5 h-5" />
                          <span className="font-orbitron text-2xl font-bold">{status.streak}</span>
                        </div>
                        <span className="text-xs text-white/50">Day Streak</span>
                      </div>
                      {status.streak_bonus > 0 && (
                        <div className="text-center">
                          <div className="text-neon-green font-orbitron text-2xl font-bold">
                            +{status.streak_bonus}%
                          </div>
                          <span className="text-xs text-white/50">Bonus</span>
                        </div>
                      )}
                    </div>

                    {/* Reward Preview */}
                    {status.can_claim && (
                      <div className="bg-white/5 border border-white/10 p-4 mb-6">
                        <div className="text-xs text-white/50 mb-2 text-center">Today's Reward</div>
                        <div className="flex items-center justify-center gap-6">
                          <div className="flex items-center gap-2">
                            <Coins className="w-5 h-5 text-neon-cyan" />
                            <span className="font-mono text-lg text-neon-cyan">+{status.next_reward.rlm} RLM</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <Zap className="w-5 h-5 text-neon-purple" />
                            <span className="font-mono text-lg text-neon-purple">+{status.next_reward.xp} XP</span>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Next Milestone */}
                    {status.next_milestone && (
                      <div className="text-center mb-6">
                        <div className="text-xs text-white/50 mb-1">Next Milestone</div>
                        <div className="flex items-center justify-center gap-2">
                          <Trophy className="w-4 h-4 text-neon-yellow" />
                          <span className="text-sm">
                            Day {status.next_milestone.days}: +{status.next_milestone.rewards.bonus_rlm} RLM bonus
                          </span>
                        </div>
                      </div>
                    )}

                    {/* Claim Button */}
                    {status.can_claim ? (
                      <CyberButton
                        onClick={claimReward}
                        disabled={claiming}
                        className="w-full"
                        data-testid="claim-daily-btn"
                      >
                        {claiming ? 'Claiming...' : 'Claim Reward'}
                      </CyberButton>
                    ) : (
                      <div className="text-center text-white/50 text-sm">
                        Already claimed today. See you tomorrow!
                      </div>
                    )}
                  </>
                ) : (
                  <>
                    {/* Post-claim view */}
                    <div className="text-center">
                      <motion.div
                        initial={{ scale: 0 }}
                        animate={{ scale: 1, rotate: 360 }}
                        transition={{ type: "spring", duration: 0.5 }}
                        className="w-20 h-20 mx-auto mb-4 bg-gradient-to-br from-neon-green to-neon-cyan rounded-full flex items-center justify-center"
                      >
                        <span className="text-3xl">🎉</span>
                      </motion.div>
                      <h3 className="font-orbitron font-bold text-xl mb-2 text-neon-green">Claimed!</h3>
                      
                      <div className="bg-white/5 border border-white/10 p-4 my-4">
                        <div className="flex items-center justify-center gap-6 mb-2">
                          <div className="flex items-center gap-2">
                            <Coins className="w-5 h-5 text-neon-cyan" />
                            <span className="font-mono text-xl text-neon-cyan">+{claimResult.rlm_earned} RLM</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <Zap className="w-5 h-5 text-neon-purple" />
                            <span className="font-mono text-xl text-neon-purple">+{claimResult.xp_earned} XP</span>
                          </div>
                        </div>
                        <div className="flex items-center justify-center gap-2 text-neon-orange">
                          <Flame className="w-4 h-4" />
                          <span className="text-sm">{claimResult.new_streak} day streak!</span>
                        </div>
                      </div>

                      {/* Milestones reached */}
                      {claimResult.milestones_reached?.length > 0 && (
                        <div className="bg-neon-yellow/10 border border-neon-yellow/30 p-3 mb-4">
                          <div className="text-xs text-neon-yellow mb-2">🏆 Milestone Reached!</div>
                          {claimResult.milestones_reached.map((m, i) => (
                            <div key={i} className="text-sm text-white">
                              {m.badge && <span className="text-neon-yellow">Badge: {m.badge}</span>}
                              {m.bonus_rlm && <span> +{m.bonus_rlm} RLM</span>}
                            </div>
                          ))}
                        </div>
                      )}

                      <CyberButton
                        onClick={() => setShowModal(false)}
                        variant="ghost"
                        className="w-full"
                      >
                        Continue
                      </CyberButton>
                    </div>
                  </>
                )}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
};

export default DailyReward;
