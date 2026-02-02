import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Users, Copy, Check, Gift, Trophy, Share2, UserPlus } from 'lucide-react';
import axios from 'axios';
import { API } from '../utils/api';
import { useAuth } from '../context/AuthContext';
import { useTranslation } from '../context/LanguageContext';
import { CyberCard, CyberButton } from '../components/common/CyberUI';

const ReferralPage = () => {
  const { user } = useAuth();
  const t = useTranslation();
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(false);
  const [applyCode, setApplyCode] = useState('');
  const [applying, setApplying] = useState(false);

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      // First get/generate the referral code
      await axios.get(`${API}/referral/code`);
      // Then get stats
      const res = await axios.get(`${API}/referral/stats`);
      setStats(res.data);
    } catch (err) {
      console.error('Error fetching referral stats:', err);
    } finally {
      setLoading(false);
    }
  };

  const copyReferralLink = () => {
    const link = `${window.location.origin}/register?ref=${stats?.referral_code}`;
    navigator.clipboard.writeText(link);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const applyReferralCode = async (e) => {
    e.preventDefault();
    if (!applyCode.trim()) return;
    
    setApplying(true);
    try {
      const res = await axios.post(`${API}/referral/apply?code=${applyCode.trim()}`);
      alert(`Success! You received ${res.data.bonus_received} RLM bonus!`);
      setApplyCode('');
      fetchStats();
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to apply code');
    } finally {
      setApplying(false);
    }
  };

  const shareOnSocial = (platform) => {
    const link = `${window.location.origin}/register?ref=${stats?.referral_code}`;
    const text = `Join REALUM - the educational metaverse! Use my referral code ${stats?.referral_code} and get 50 RLM bonus!`;
    
    const urls = {
      twitter: `https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}&url=${encodeURIComponent(link)}`,
      facebook: `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(link)}&quote=${encodeURIComponent(text)}`,
      whatsapp: `https://wa.me/?text=${encodeURIComponent(text + ' ' + link)}`,
      telegram: `https://t.me/share/url?url=${encodeURIComponent(link)}&text=${encodeURIComponent(text)}`
    };
    
    window.open(urls[platform], '_blank', 'width=600,height=400');
  };

  return (
    <div className="min-h-screen pt-16 sm:pt-20 pb-20 lg:pb-12 px-3 sm:px-4" data-testid="referral-page">
      <div className="max-w-4xl mx-auto">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-6 sm:mb-8">
          <h1 className="text-2xl sm:text-3xl md:text-4xl font-orbitron font-black flex items-center gap-3">
            <Users className="w-8 h-8 sm:w-10 sm:h-10 text-neon-green" />
            Referral <span className="text-neon-green">Program</span>
          </h1>
          <p className="text-white/60 mt-2 text-sm sm:text-base">
            Invite friends and earn 100 RLM when they reach level 2!
          </p>
        </motion.div>

        {loading ? (
          <div className="text-center text-white/50">{t('loading')}</div>
        ) : (
          <>
            {/* How It Works */}
            <CyberCard className="mb-6">
              <h3 className="font-orbitron font-bold mb-4 text-sm sm:text-base">How It Works</h3>
              <div className="grid sm:grid-cols-3 gap-4">
                <div className="text-center p-4 bg-white/5 border border-white/10">
                  <div className="w-12 h-12 mx-auto mb-3 bg-neon-cyan/20 rounded-full flex items-center justify-center">
                    <Share2 className="w-6 h-6 text-neon-cyan" />
                  </div>
                  <h4 className="font-mono font-bold text-sm mb-1">1. Share</h4>
                  <p className="text-xs text-white/60">Share your unique referral link with friends</p>
                </div>
                <div className="text-center p-4 bg-white/5 border border-white/10">
                  <div className="w-12 h-12 mx-auto mb-3 bg-neon-purple/20 rounded-full flex items-center justify-center">
                    <UserPlus className="w-6 h-6 text-neon-purple" />
                  </div>
                  <h4 className="font-mono font-bold text-sm mb-1">2. They Join</h4>
                  <p className="text-xs text-white/60">They get 50 RLM bonus when they sign up</p>
                </div>
                <div className="text-center p-4 bg-white/5 border border-white/10">
                  <div className="w-12 h-12 mx-auto mb-3 bg-neon-green/20 rounded-full flex items-center justify-center">
                    <Gift className="w-6 h-6 text-neon-green" />
                  </div>
                  <h4 className="font-mono font-bold text-sm mb-1">3. You Earn</h4>
                  <p className="text-xs text-white/60">Get 100 RLM when they reach level 2!</p>
                </div>
              </div>
            </CyberCard>

            {/* Your Referral Code */}
            <CyberCard className="mb-6" glow>
              <h3 className="font-orbitron font-bold mb-4 text-sm sm:text-base">Your Referral Code</h3>
              
              {/* Code Display */}
              <div className="flex flex-col sm:flex-row gap-3 mb-4">
                <div className="flex-1 bg-black/50 border border-neon-cyan/50 p-4 flex items-center justify-between">
                  <span className="font-mono text-xl sm:text-2xl text-neon-cyan tracking-widest">
                    {stats?.referral_code || 'Loading...'}
                  </span>
                  <button
                    onClick={copyReferralLink}
                    className="ml-4 p-2 hover:bg-white/10 transition-colors"
                    data-testid="copy-referral-btn"
                  >
                    {copied ? (
                      <Check className="w-5 h-5 text-neon-green" />
                    ) : (
                      <Copy className="w-5 h-5 text-white/50" />
                    )}
                  </button>
                </div>
              </div>

              {/* Share Buttons */}
              <div className="flex flex-wrap gap-2">
                <CyberButton onClick={() => shareOnSocial('twitter')} className="text-xs">
                  Twitter
                </CyberButton>
                <CyberButton onClick={() => shareOnSocial('facebook')} variant="ghost" className="text-xs">
                  Facebook
                </CyberButton>
                <CyberButton onClick={() => shareOnSocial('whatsapp')} variant="ghost" className="text-xs">
                  WhatsApp
                </CyberButton>
                <CyberButton onClick={() => shareOnSocial('telegram')} variant="ghost" className="text-xs">
                  Telegram
                </CyberButton>
              </div>
            </CyberCard>

            {/* Stats Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
              <CyberCard className="text-center p-4">
                <div className="text-2xl sm:text-3xl font-orbitron font-bold text-neon-cyan">
                  {stats?.total_invited || 0}
                </div>
                <div className="text-xs text-white/50">Invited</div>
              </CyberCard>
              <CyberCard className="text-center p-4">
                <div className="text-2xl sm:text-3xl font-orbitron font-bold text-neon-green">
                  {stats?.completed || 0}
                </div>
                <div className="text-xs text-white/50">Completed</div>
              </CyberCard>
              <CyberCard className="text-center p-4">
                <div className="text-2xl sm:text-3xl font-orbitron font-bold text-neon-yellow">
                  {stats?.pending || 0}
                </div>
                <div className="text-xs text-white/50">Pending</div>
              </CyberCard>
              <CyberCard className="text-center p-4">
                <div className="text-2xl sm:text-3xl font-orbitron font-bold text-neon-purple">
                  {stats?.total_earned || 0}
                </div>
                <div className="text-xs text-white/50">RLM Earned</div>
              </CyberCard>
            </div>

            {/* Next Milestone */}
            {stats?.next_milestone && (
              <CyberCard className="mb-6">
                <h3 className="font-orbitron font-bold mb-3 flex items-center gap-2 text-sm sm:text-base">
                  <Trophy className="w-5 h-5 text-neon-yellow" />
                  Next Milestone
                </h3>
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-sm text-white/70">
                      {stats.next_milestone.current} / {stats.next_milestone.required} referrals
                    </div>
                    <div className="text-xs text-white/50">
                      Reward: +{stats.next_milestone.bonus_rlm} RLM & {stats.next_milestone.badge} badge
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-2xl font-orbitron text-neon-yellow">
                      {stats.next_milestone.required - stats.next_milestone.current}
                    </div>
                    <div className="text-xs text-white/50">to go</div>
                  </div>
                </div>
                {/* Progress bar */}
                <div className="mt-3 h-2 bg-white/10 overflow-hidden">
                  <div 
                    className="h-full bg-gradient-to-r from-neon-yellow to-neon-orange transition-all"
                    style={{ width: `${(stats.next_milestone.current / stats.next_milestone.required) * 100}%` }}
                  />
                </div>
              </CyberCard>
            )}

            {/* Recent Referrals */}
            {stats?.referrals?.length > 0 && (
              <CyberCard className="mb-6">
                <h3 className="font-orbitron font-bold mb-4 text-sm sm:text-base">Recent Referrals</h3>
                <div className="space-y-2">
                  {stats.referrals.map(ref => (
                    <div 
                      key={ref.id}
                      className="flex items-center justify-between p-3 bg-black/30 border border-white/10"
                    >
                      <div className="flex items-center gap-3">
                        <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                          ref.completed ? 'bg-neon-green/20' : 'bg-neon-yellow/20'
                        }`}>
                          <UserPlus className={`w-4 h-4 ${ref.completed ? 'text-neon-green' : 'text-neon-yellow'}`} />
                        </div>
                        <div>
                          <div className="font-mono text-sm">{ref.referee_name}</div>
                          <div className="text-xs text-white/50">
                            {new Date(ref.created_at).toLocaleDateString()}
                          </div>
                        </div>
                      </div>
                      <div className="text-right">
                        {ref.completed ? (
                          <span className="text-neon-green text-sm">+{ref.reward_given} RLM</span>
                        ) : (
                          <span className="text-neon-yellow text-xs">Pending Lv.2</span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </CyberCard>
            )}

            {/* Apply Referral Code (if user doesn't have one) */}
            {!user?.referred_by && (
              <CyberCard>
                <h3 className="font-orbitron font-bold mb-4 text-sm sm:text-base">Have a Referral Code?</h3>
                <form onSubmit={applyReferralCode} className="flex gap-2">
                  <input
                    type="text"
                    value={applyCode}
                    onChange={(e) => setApplyCode(e.target.value.toUpperCase())}
                    placeholder="Enter code..."
                    maxLength={8}
                    className="flex-1 bg-black/50 border border-white/20 px-4 py-3 text-white font-mono uppercase tracking-widest focus:border-neon-cyan focus:outline-none"
                    data-testid="apply-referral-input"
                  />
                  <CyberButton type="submit" disabled={applying || !applyCode.trim()}>
                    {applying ? '...' : 'Apply'}
                  </CyberButton>
                </form>
                <p className="text-xs text-white/50 mt-2">
                  Apply a friend's code to get 50 RLM bonus!
                </p>
              </CyberCard>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default ReferralPage;
