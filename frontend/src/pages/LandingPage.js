import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ChevronRight, Sparkles, Target, Shield, Heart } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useTranslation } from '../context/LanguageContext';
import { CyberButton } from '../components/common/CyberUI';
import LanguageSelector from '../components/common/LanguageSelector';

const LandingPage = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const t = useTranslation();
  
  useEffect(() => {
    if (user) navigate('/dashboard');
  }, [user, navigate]);
  
  return (
    <div className="min-h-screen relative overflow-hidden">
      <div className="absolute inset-0 bg-cyber-grid bg-[length:50px_50px] opacity-20 animate-pulse" />
      <div className="absolute inset-0 bg-hero-glow" />
      
      <div className="relative z-10 min-h-screen flex flex-col items-center justify-center px-4 text-center">
        <motion.div
          initial={{ opacity: 0, y: 50 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
        >
          <h1 className="text-4xl sm:text-5xl md:text-7xl lg:text-8xl font-orbitron font-black mb-4">
            <span className="text-white">REAL</span>
            <span className="text-neon-cyan neon-text">UM</span>
          </h1>
          
          <p className="text-lg sm:text-xl md:text-2xl font-mono text-neon-purple mb-2">{t('tagline')}</p>
          <p className="text-white/60 max-w-xl mx-auto mb-8 text-sm sm:text-base px-4">{t('subtitle')}</p>
          
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <CyberButton onClick={() => navigate('/register')} data-testid="enter-realum-btn">
              {t('enterRealum')} <ChevronRight className="inline w-4 h-4 ml-2" />
            </CyberButton>
            <CyberButton variant="ghost" onClick={() => navigate('/login')} data-testid="login-btn">
              {t('login')}
            </CyberButton>
          </div>
          
          <div className="mt-12 sm:mt-16 grid grid-cols-2 md:grid-cols-4 gap-4 sm:gap-6 max-w-2xl mx-auto px-4">
            {[
              { icon: Sparkles, label: t('creator'), color: '#E040FB' },
              { icon: Target, label: t('contributor'), color: '#00FF88' },
              { icon: Shield, label: t('evaluator'), color: '#40C4FF' },
              { icon: Heart, label: t('partner'), color: '#FF6B35' }
            ].map((role, i) => (
              <motion.div
                key={role.label}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.5 + i * 0.1 }}
                className="p-3 sm:p-4 border border-white/10 bg-black/30 hover:border-white/30 transition-colors"
              >
                <role.icon className="w-6 h-6 sm:w-8 sm:h-8 mx-auto mb-2" style={{ color: role.color }} />
                <span className="text-xs font-mono text-white/70">{role.label}</span>
              </motion.div>
            ))}
          </div>
        </motion.div>
        
        <div className="absolute top-4 right-4">
          <LanguageSelector />
        </div>
      </div>
    </div>
  );
};

export default LandingPage;
