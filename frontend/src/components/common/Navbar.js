import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import { 
  Home, Briefcase, Wallet, Vote, Trophy, User, LogOut, Menu, X, 
  GraduationCap, Layers, ShoppingBag, Play, Users, Search, Award
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { useWeb3 } from '../../context/Web3Context';
import { useTranslation } from '../../context/LanguageContext';
import LanguageSelector from './LanguageSelector';

const Navbar = () => {
  const { user, logout } = useAuth();
  const { isConnected, formatAddress, account } = useWeb3();
  const t = useTranslation();
  const [menuOpen, setMenuOpen] = useState(false);
  const location = useLocation();
  
  const navItems = [
    { path: '/dashboard', icon: Home, label: t('dashboard') },
    { path: '/metaverse', icon: Layers, label: t('metaverse') },
    { path: '/jobs', icon: Briefcase, label: t('jobs') },
    { path: '/courses', icon: GraduationCap, label: t('courses') },
    { path: '/voting', icon: Vote, label: t('voting') },
    { path: '/wallet', icon: Wallet, label: t('wallet') },
    { path: '/social', icon: Users, label: 'Social' },
    { path: '/achievements', icon: Award, label: 'Achievements' }
  ];
  
  const mobileNavItems = [
    { path: '/dashboard', icon: Home, label: 'Home' },
    { path: '/search', icon: Search, label: 'Search' },
    { path: '/social', icon: Users, label: 'Social' },
    { path: '/achievements', icon: Award, label: 'Awards' },
    { path: '/profile', icon: User, label: t('profile') }
  ];
  
  return (
    <>
      <nav className="fixed top-0 left-0 right-0 z-50 bg-black/90 backdrop-blur-xl border-b border-white/10 safe-area-inset">
        <div className="max-w-7xl mx-auto px-3 sm:px-4">
          <div className="flex items-center justify-between h-14 sm:h-16">
            <Link to="/dashboard" className="flex items-center gap-2">
              <div className="w-8 h-8 sm:w-9 sm:h-9 bg-gradient-to-br from-neon-cyan to-neon-purple flex items-center justify-center flex-shrink-0">
                <span className="text-black font-black text-sm">R</span>
              </div>
              <span className="font-orbitron font-bold text-base sm:text-lg hidden xs:block">REALUM</span>
            </Link>
            
            <div className="hidden lg:flex items-center gap-1">
              {navItems.map(item => (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`px-3 py-2 text-sm transition-colors flex items-center gap-2 ${
                    location.pathname === item.path 
                      ? 'text-neon-cyan' 
                      : 'text-white/70 hover:text-neon-cyan'
                  }`}
                >
                  <item.icon className="w-4 h-4" />
                  <span>{item.label}</span>
                </Link>
              ))}
            </div>
            
            <div className="flex items-center gap-2 sm:gap-4">
              <LanguageSelector />
              
              {user && (
                <div className="hidden md:flex items-center gap-3 sm:gap-4">
                  {/* Web3 Wallet Status */}
                  {isConnected && (
                    <Link 
                      to="/wallet"
                      className="px-2 py-1 bg-neon-green/10 border border-neon-green/30 text-neon-green text-xs font-mono flex items-center gap-1 hover:bg-neon-green/20"
                    >
                      <div className="w-1.5 h-1.5 bg-neon-green rounded-full" />
                      {formatAddress(account)}
                    </Link>
                  )}
                  <div className="text-right">
                    <div className="text-sm font-mono text-neon-cyan">{user.realum_balance?.toFixed(0)} RLM</div>
                    <div className="text-xs text-white/50">Lv.{user.level}</div>
                  </div>
                  <Link to="/profile" className="w-9 h-9 sm:w-10 sm:h-10 border border-neon-cyan/50 flex items-center justify-center hover:bg-neon-cyan/10">
                    <User className="w-4 h-4 sm:w-5 sm:h-5 text-neon-cyan" />
                  </Link>
                  <button onClick={logout} className="text-white/50 hover:text-neon-red p-2" data-testid="logout-btn">
                    <LogOut className="w-4 h-4 sm:w-5 sm:h-5" />
                  </button>
                </div>
              )}
              
              <button 
                onClick={() => setMenuOpen(!menuOpen)} 
                className="lg:hidden p-2 -mr-2"
                aria-label="Toggle menu"
                data-testid="mobile-menu-toggle"
              >
                {menuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
              </button>
            </div>
          </div>
        </div>
        
        <AnimatePresence>
          {menuOpen && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="lg:hidden bg-black/98 border-t border-white/10 max-h-[70vh] overflow-y-auto"
            >
              {user && (
                <div className="px-4 py-3 border-b border-white/10 flex items-center justify-between">
                  <div>
                    <div className="font-mono text-neon-cyan">{user.username}</div>
                    <div className="text-xs text-white/50">Level {user.level} • {user.realum_balance?.toFixed(0)} RLM</div>
                  </div>
                  <div className="flex items-center gap-2">
                    {user.badges?.slice(0, 3).map((b, i) => (
                      <span key={i} className="text-lg">🏆</span>
                    ))}
                  </div>
                </div>
              )}
              
              <div className="py-2">
                {navItems.map(item => (
                  <Link
                    key={item.path}
                    to={item.path}
                    onClick={() => setMenuOpen(false)}
                    className={`flex items-center gap-3 px-4 py-3.5 transition-colors ${
                      location.pathname === item.path
                        ? 'text-neon-cyan bg-neon-cyan/10'
                        : 'text-white/70 hover:text-neon-cyan hover:bg-white/5'
                    }`}
                  >
                    <item.icon className="w-5 h-5" />
                    <span className="font-medium">{item.label}</span>
                  </Link>
                ))}
              </div>
              
              {user && (
                <div className="border-t border-white/10 py-2">
                  <Link 
                    to="/simulation" 
                    onClick={() => setMenuOpen(false)} 
                    className="flex items-center gap-3 px-4 py-3.5 text-white/70 hover:text-neon-cyan hover:bg-white/5"
                  >
                    <Play className="w-5 h-5" />
                    <span>Token Simulation</span>
                  </Link>
                  <button 
                    onClick={() => { logout(); setMenuOpen(false); }} 
                    className="w-full flex items-center gap-3 px-4 py-3.5 text-neon-red hover:bg-white/5"
                  >
                    <LogOut className="w-5 h-5" />
                    <span>{t('logout')}</span>
                  </button>
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </nav>
      
      {user && (
        <nav className="fixed bottom-0 left-0 right-0 z-50 lg:hidden bg-black/95 backdrop-blur-xl border-t border-white/10 safe-area-inset">
          <div className="flex items-center justify-around h-16">
            {mobileNavItems.map(item => (
              <Link
                key={item.path}
                to={item.path}
                className={`flex flex-col items-center justify-center flex-1 h-full py-2 transition-colors ${
                  location.pathname === item.path
                    ? 'text-neon-cyan'
                    : 'text-white/50'
                }`}
              >
                <item.icon className={`w-5 h-5 mb-1 ${location.pathname === item.path ? 'scale-110' : ''}`} />
                <span className="text-[10px] font-medium">{item.label}</span>
              </Link>
            ))}
          </div>
        </nav>
      )}
    </>
  );
};

export default Navbar;
