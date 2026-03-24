import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { 
  Crown, Star, Zap, Gift, Check, X, Sparkles,
  Loader2, Clock, Award, Shield, Rocket
} from 'lucide-react';
import axios from 'axios';
import { API } from '../utils/api';
import { useAuth } from '../context/AuthContext';
import { CyberCard, CyberButton } from '../components/common/CyberUI';
import { toast } from 'sonner';

const PremiumPage = () => {
  const { user, refreshUser } = useAuth();
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  
  const [tiers, setTiers] = useState({});
  const [status, setStatus] = useState(null);
  const [exclusiveItems, setExclusiveItems] = useState([]);
  const [selectedDuration, setSelectedDuration] = useState('monthly');

  useEffect(() => {
    fetchAllData();
  }, []);

  const fetchAllData = async () => {
    try {
      const tiersRes = await axios.get(`${API}/premium/tiers`);
      setTiers(tiersRes.data.tiers || {});
      setExclusiveItems(tiersRes.data.exclusive_items || []);
      
      try {
        const statusRes = await axios.get(`${API}/premium/status`);
        setStatus(statusRes.data);
      } catch (e) {}
    } catch (error) {
      console.error('Failed to load premium data:', error);
    }
    setLoading(false);
  };

  const handleSubscribe = async (tier) => {
    setProcessing(true);
    try {
      const res = await axios.post(`${API}/premium/subscribe`, {
        tier: tier,
        duration: selectedDuration
      });
      toast.success(res.data.message);
      fetchAllData();
      refreshUser();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to subscribe');
    }
    setProcessing(false);
  };

  const handleClaimDaily = async () => {
    try {
      const res = await axios.post(`${API}/premium/claim-daily`);
      toast.success(res.data.message);
      refreshUser();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to claim bonus');
    }
  };

  const tierOrder = ['silver', 'gold', 'platinum'];
  const tierIcons = { silver: Star, gold: Crown, platinum: Sparkles };
  
  const benefitLabels = {
    interest_bonus: 'Bonus Dobândă',
    fee_reduction: 'Reducere Comisioane',
    tax_reduction: 'Reducere Taxe',
    daily_bonus: 'Bonus Zilnic (RLM)',
    xp_multiplier: 'Multiplicator XP',
    priority_support: 'Suport Prioritar',
    custom_profile: 'Profil Personalizat',
    early_access: 'Acces Anticipat',
    vip_events: 'Evenimente VIP'
  };

  if (loading) {
    return (
      <div className="min-h-screen pt-20 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-neon-cyan" />
      </div>
    );
  }

  return (
    <div className="min-h-screen pt-16 sm:pt-20 pb-20 lg:pb-12 px-3 sm:px-4" data-testid="premium-page">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-8 text-center">
          <h1 className="text-3xl sm:text-4xl font-orbitron font-black flex items-center justify-center gap-3">
            <Crown className="w-10 h-10 text-yellow-400" />
            <span>Premium <span className="text-neon-cyan">REALUM</span></span>
          </h1>
          <p className="text-white/60 mt-2">Deblochează beneficii exclusive și accelerează progresul tău!</p>
        </motion.div>

        {/* Current Status */}
        {status?.is_premium && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mb-8">
            <CyberCard className="p-6" style={{ borderColor: status.tier_color }}>
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div className="flex items-center gap-4">
                  <div className="p-3 rounded-full" style={{ backgroundColor: status.tier_color + '30' }}>
                    <Crown className="w-8 h-8" style={{ color: status.tier_color }} />
                  </div>
                  <div>
                    <h3 className="font-orbitron text-xl" style={{ color: status.tier_color }}>
                      {status.tier_name} Member
                    </h3>
                    <div className="text-sm text-white/50 flex items-center gap-2">
                      <Clock className="w-4 h-4" /> {status.days_remaining} zile rămase
                    </div>
                  </div>
                </div>
                <CyberButton variant="primary" onClick={handleClaimDaily}>
                  <Gift className="w-4 h-4 mr-2" /> Revendică Bonus Zilnic
                </CyberButton>
              </div>
            </CyberCard>
          </motion.div>
        )}

        {/* Duration Toggle */}
        <div className="flex justify-center gap-2 mb-8">
          <button
            onClick={() => setSelectedDuration('monthly')}
            className={`px-6 py-2 font-mono text-sm transition-all ${
              selectedDuration === 'monthly' 
                ? 'bg-neon-cyan/20 border border-neon-cyan text-neon-cyan' 
                : 'border border-white/20 text-white/60 hover:border-white/40'
            }`}
          >
            Lunar
          </button>
          <button
            onClick={() => setSelectedDuration('yearly')}
            className={`px-6 py-2 font-mono text-sm transition-all ${
              selectedDuration === 'yearly' 
                ? 'bg-neon-cyan/20 border border-neon-cyan text-neon-cyan' 
                : 'border border-white/20 text-white/60 hover:border-white/40'
            }`}
          >
            Anual <span className="text-neon-green ml-1">-17%</span>
          </button>
        </div>

        {/* Pricing Cards */}
        <div className="grid md:grid-cols-3 gap-6 mb-12">
          {tierOrder.map((tierKey, index) => {
            const tier = tiers[tierKey];
            if (!tier) return null;
            
            const TierIcon = tierIcons[tierKey];
            const price = selectedDuration === 'yearly' ? tier.price_yearly : tier.price_monthly;
            const isCurrentTier = status?.tier === tierKey;
            const isHigherTier = status?.is_premium && tierOrder.indexOf(tierKey) > tierOrder.indexOf(status.tier);
            
            return (
              <motion.div
                key={tierKey}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
              >
                <CyberCard 
                  className={`p-6 h-full flex flex-col ${index === 1 ? 'border-2' : ''}`}
                  style={{ borderColor: tier.color + (index === 1 ? '' : '40') }}
                >
                  {index === 1 && (
                    <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 text-xs font-mono" style={{ backgroundColor: tier.color, color: '#000' }}>
                      POPULAR
                    </div>
                  )}
                  
                  <div className="text-center mb-6">
                    <div className="inline-block p-3 rounded-full mb-3" style={{ backgroundColor: tier.color + '20' }}>
                      <TierIcon className="w-8 h-8" style={{ color: tier.color }} />
                    </div>
                    <h3 className="font-orbitron text-2xl" style={{ color: tier.color }}>{tier.name}</h3>
                    <div className="mt-2">
                      <span className="text-3xl font-orbitron text-white">{price}</span>
                      <span className="text-white/50 ml-1">RLM/{selectedDuration === 'yearly' ? 'an' : 'lună'}</span>
                    </div>
                  </div>
                  
                  <div className="flex-1 space-y-3 mb-6">
                    {Object.entries(tier.benefits).map(([key, value]) => {
                      if (typeof value === 'boolean') {
                        return (
                          <div key={key} className="flex items-center gap-2 text-sm">
                            {value ? (
                              <Check className="w-4 h-4 text-neon-green flex-shrink-0" />
                            ) : (
                              <X className="w-4 h-4 text-white/20 flex-shrink-0" />
                            )}
                            <span className={value ? 'text-white/80' : 'text-white/30'}>
                              {benefitLabels[key] || key}
                            </span>
                          </div>
                        );
                      } else {
                        return (
                          <div key={key} className="flex items-center justify-between text-sm">
                            <span className="text-white/60">{benefitLabels[key] || key}</span>
                            <span className="font-mono" style={{ color: tier.color }}>
                              {key.includes('bonus') || key.includes('multiplier') 
                                ? (key === 'daily_bonus' ? `+${value}` : `${value}x`)
                                : `+${(value * 100).toFixed(0)}%`
                              }
                            </span>
                          </div>
                        );
                      }
                    })}
                  </div>
                  
                  <CyberButton
                    variant={isCurrentTier ? 'outline' : 'primary'}
                    className="w-full"
                    style={!isCurrentTier ? { backgroundColor: tier.color + '20', borderColor: tier.color } : {}}
                    onClick={() => handleSubscribe(tierKey)}
                    disabled={processing || isCurrentTier}
                  >
                    {processing ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : isCurrentTier ? (
                      'Plan Actual'
                    ) : isHigherTier ? (
                      'Upgrade'
                    ) : (
                      'Abonează-te'
                    )}
                  </CyberButton>
                </CyberCard>
              </motion.div>
            );
          })}
        </div>

        {/* Exclusive Items */}
        <CyberCard className="p-6">
          <h3 className="font-orbitron text-xl mb-6 text-center">
            <Sparkles className="w-5 h-5 inline mr-2 text-yellow-400" />
            Items Exclusive Premium
          </h3>
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
            {exclusiveItems.map(item => {
              const tierInfo = tiers[item.tier];
              return (
                <div 
                  key={item.id} 
                  className="p-4 bg-black/30 border border-white/10 text-center"
                  style={{ borderColor: tierInfo?.color + '40' }}
                >
                  <Award className="w-8 h-8 mx-auto mb-2" style={{ color: tierInfo?.color }} />
                  <div className="font-mono text-white/80">{item.name}</div>
                  <div className="text-xs text-white/40 mt-1 capitalize">{item.type}</div>
                  <div className="text-xs mt-2 px-2 py-1 inline-block" style={{ backgroundColor: tierInfo?.color + '20', color: tierInfo?.color }}>
                    {tierInfo?.name}+
                  </div>
                </div>
              );
            })}
          </div>
        </CyberCard>

        {/* Benefits Summary */}
        <div className="mt-8 grid md:grid-cols-3 gap-4">
          <CyberCard className="p-4 text-center">
            <Zap className="w-8 h-8 mx-auto mb-2 text-neon-yellow" />
            <h4 className="font-orbitron text-lg mb-1">Progres Rapid</h4>
            <p className="text-sm text-white/50">XP multiplicat și bonusuri zilnice</p>
          </CyberCard>
          <CyberCard className="p-4 text-center">
            <Shield className="w-8 h-8 mx-auto mb-2 text-neon-green" />
            <h4 className="font-orbitron text-lg mb-1">Economii</h4>
            <p className="text-sm text-white/50">Reduceri la taxe și comisioane</p>
          </CyberCard>
          <CyberCard className="p-4 text-center">
            <Rocket className="w-8 h-8 mx-auto mb-2 text-neon-purple" />
            <h4 className="font-orbitron text-lg mb-1">Acces VIP</h4>
            <p className="text-sm text-white/50">Evenimente exclusive și early access</p>
          </CyberCard>
        </div>
      </div>
    </div>
  );
};

export default PremiumPage;
