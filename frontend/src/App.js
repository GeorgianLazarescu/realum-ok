import React, { useState, useEffect, useContext, createContext, useRef, useMemo } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useNavigate, useLocation, Link } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import axios from 'axios';
import Confetti from 'react-confetti';
import {
  Home, Map, Briefcase, Wallet, Vote, Trophy, User, LogOut, Menu, X, ChevronRight, 
  Coins, Star, Zap, Building2, Users, BookOpen, ShoppingBag, Settings, Globe,
  Play, CheckCircle, Award, TrendingUp, Clock, Gift, AlertCircle, Send, Eye,
  GraduationCap, Layers, Target, Shield, Heart, Sparkles, Volume2, VolumeX
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL + '/api';

// ==================== i18n TRANSLATIONS ====================
const translations = {
  en: {
    welcome: "Welcome to REALUM",
    tagline: "Learn, Collaborate, Earn",
    subtitle: "An educational and economic metaverse where your contributions matter",
    enterRealum: "Enter REALUM",
    connectWallet: "Connect Wallet",
    dashboard: "Dashboard",
    cityMap: "City Map",
    metaverse: "3D Metaverse",
    jobs: "Jobs",
    wallet: "Wallet",
    dao: "DAO",
    voting: "Voting",
    leaderboard: "Leaderboard",
    profile: "Profile",
    courses: "Courses",
    marketplace: "Marketplace",
    projects: "Projects",
    simulation: "Simulation",
    login: "Login",
    register: "Register",
    logout: "Logout",
    balance: "Balance",
    level: "Level",
    xp: "XP",
    badges: "Badges",
    apply: "Apply",
    complete: "Complete",
    vote: "Vote",
    voteFor: "Vote For",
    voteAgainst: "Vote Against",
    transfer: "Transfer",
    enroll: "Enroll",
    purchase: "Purchase",
    join: "Join",
    create: "Create",
    submit: "Submit",
    cancel: "Cancel",
    loading: "Loading...",
    noData: "No data available",
    success: "Success!",
    error: "Error",
    creator: "Creator",
    contributor: "Contributor",
    evaluator: "Evaluator",
    partner: "Partner",
    citizen: "Citizen",
    selectRole: "Select your role",
    tokensBurned: "Tokens Burned",
    totalSupply: "Total Supply",
    burnRate: "Burn Rate",
    settings: "Settings",
    language: "Language"
  },
  ro: {
    welcome: "Bun venit în REALUM",
    tagline: "Învață, Colaborează, Câștigă",
    subtitle: "Un metavers educațional și economic unde contribuțiile tale contează",
    enterRealum: "Intră în REALUM",
    connectWallet: "Conectează Portofel",
    dashboard: "Panou",
    cityMap: "Hartă Oraș",
    metaverse: "Metavers 3D",
    jobs: "Joburi",
    wallet: "Portofel",
    dao: "DAO",
    voting: "Votare",
    leaderboard: "Clasament",
    profile: "Profil",
    courses: "Cursuri",
    marketplace: "Piață",
    projects: "Proiecte",
    simulation: "Simulare",
    login: "Autentificare",
    register: "Înregistrare",
    logout: "Deconectare",
    balance: "Sold",
    level: "Nivel",
    xp: "XP",
    badges: "Insigne",
    apply: "Aplică",
    complete: "Finalizează",
    vote: "Votează",
    voteFor: "Votează Pentru",
    voteAgainst: "Votează Împotrivă",
    transfer: "Transfer",
    enroll: "Înscrie-te",
    purchase: "Cumpără",
    join: "Alătură-te",
    create: "Creează",
    submit: "Trimite",
    cancel: "Anulează",
    loading: "Se încarcă...",
    noData: "Nu există date",
    success: "Succes!",
    error: "Eroare",
    creator: "Creator",
    contributor: "Contributor",
    evaluator: "Evaluator",
    partner: "Partener",
    citizen: "Cetățean",
    selectRole: "Selectează rolul tău",
    tokensBurned: "Tokeni Arși",
    totalSupply: "Ofertă Totală",
    burnRate: "Rata de Ardere",
    settings: "Setări",
    language: "Limbă"
  },
  es: {
    welcome: "Bienvenido a REALUM",
    tagline: "Aprende, Colabora, Gana",
    subtitle: "Un metaverso educativo y económico donde tus contribuciones importan",
    enterRealum: "Entrar a REALUM",
    connectWallet: "Conectar Cartera",
    dashboard: "Panel",
    cityMap: "Mapa",
    metaverse: "Metaverso 3D",
    jobs: "Trabajos",
    wallet: "Cartera",
    dao: "DAO",
    voting: "Votación",
    leaderboard: "Clasificación",
    profile: "Perfil",
    courses: "Cursos",
    marketplace: "Mercado",
    projects: "Proyectos",
    simulation: "Simulación",
    login: "Iniciar Sesión",
    register: "Registrarse",
    logout: "Cerrar Sesión",
    balance: "Saldo",
    level: "Nivel",
    xp: "XP",
    badges: "Insignias",
    apply: "Aplicar",
    complete: "Completar",
    vote: "Votar",
    voteFor: "Votar a Favor",
    voteAgainst: "Votar en Contra",
    transfer: "Transferir",
    enroll: "Inscribirse",
    purchase: "Comprar",
    join: "Unirse",
    create: "Crear",
    submit: "Enviar",
    cancel: "Cancelar",
    loading: "Cargando...",
    noData: "Sin datos",
    success: "¡Éxito!",
    error: "Error",
    creator: "Creador",
    contributor: "Contribuidor",
    evaluator: "Evaluador",
    partner: "Socio",
    citizen: "Ciudadano",
    selectRole: "Selecciona tu rol",
    tokensBurned: "Tokens Quemados",
    totalSupply: "Suministro Total",
    burnRate: "Tasa de Quema",
    settings: "Configuración",
    language: "Idioma"
  }
};

// ==================== CONTEXTS ====================
const AuthContext = createContext(null);
const LanguageContext = createContext(null);

const useAuth = () => useContext(AuthContext);
const useLanguage = () => useContext(LanguageContext);

const useTranslation = () => {
  const { language } = useLanguage();
  return (key) => translations[language]?.[key] || translations.en[key] || key;
};

// ==================== AUTH PROVIDER ====================
const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [token, setToken] = useState(localStorage.getItem('token'));

  useEffect(() => {
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      axios.get(`${API}/auth/me`)
        .then(res => setUser(res.data))
        .catch(() => { localStorage.removeItem('token'); setToken(null); })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, [token]);

  const login = async (email, password) => {
    const res = await axios.post(`${API}/auth/login`, { email, password });
    localStorage.setItem('token', res.data.access_token);
    axios.defaults.headers.common['Authorization'] = `Bearer ${res.data.access_token}`;
    setToken(res.data.access_token);
    setUser(res.data.user);
    return res.data;
  };

  const register = async (data) => {
    const res = await axios.post(`${API}/auth/register`, data);
    localStorage.setItem('token', res.data.access_token);
    axios.defaults.headers.common['Authorization'] = `Bearer ${res.data.access_token}`;
    setToken(res.data.access_token);
    setUser(res.data.user);
    return res.data;
  };

  const logout = () => {
    localStorage.removeItem('token');
    delete axios.defaults.headers.common['Authorization'];
    setToken(null);
    setUser(null);
  };

  const refreshUser = async () => {
    if (token) {
      const res = await axios.get(`${API}/auth/me`);
      setUser(res.data);
    }
  };

  return (
    <AuthContext.Provider value={{ user, login, register, logout, loading, refreshUser, token }}>
      {children}
    </AuthContext.Provider>
  );
};

// ==================== LANGUAGE PROVIDER ====================
const LanguageProvider = ({ children }) => {
  const [language, setLanguage] = useState(localStorage.getItem('language') || 'en');

  const changeLanguage = (lang) => {
    localStorage.setItem('language', lang);
    setLanguage(lang);
  };

  return (
    <LanguageContext.Provider value={{ language, changeLanguage }}>
      {children}
    </LanguageContext.Provider>
  );
};

// ==================== UI COMPONENTS ====================
const CyberCard = ({ children, className = "", glow = false, ...props }) => (
  <motion.div
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    className={`relative bg-black/60 backdrop-blur-xl border border-white/10 p-6 overflow-hidden ${glow ? 'shadow-[0_0_30px_rgba(0,240,255,0.15)]' : ''} ${className}`}
    {...props}
  >
    <div className="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-neon-cyan/50 to-transparent" />
    {children}
  </motion.div>
);

const CyberButton = ({ children, variant = "primary", className = "", disabled = false, ...props }) => {
  const variants = {
    primary: "bg-neon-cyan/10 border-neon-cyan text-neon-cyan hover:bg-neon-cyan/20 hover:shadow-[0_0_20px_rgba(0,240,255,0.4)]",
    danger: "bg-neon-red/10 border-neon-red text-neon-red hover:bg-neon-red/20",
    success: "bg-neon-green/10 border-neon-green text-neon-green hover:bg-neon-green/20",
    ghost: "bg-transparent border-white/20 text-white hover:border-white/40"
  };
  
  return (
    <motion.button
      whileHover={{ scale: disabled ? 1 : 1.02 }}
      whileTap={{ scale: disabled ? 1 : 0.98 }}
      disabled={disabled}
      className={`px-6 py-3 border font-mono uppercase tracking-wider text-sm transition-all duration-300 ${variants[variant]} ${disabled ? 'opacity-50 cursor-not-allowed' : ''} ${className}`}
      {...props}
    >
      {children}
    </motion.button>
  );
};

const LanguageSelector = () => {
  const { language, changeLanguage } = useLanguage();
  const [open, setOpen] = useState(false);
  
  const languages = [
    { code: 'en', name: 'English', flag: '🇬🇧' },
    { code: 'ro', name: 'Română', flag: '🇷🇴' },
    { code: 'es', name: 'Español', flag: '🇪🇸' }
  ];
  
  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 px-3 py-2 border border-white/20 hover:border-neon-cyan/50 transition-colors"
      >
        <Globe className="w-4 h-4" />
        <span className="text-sm">{languages.find(l => l.code === language)?.flag}</span>
      </button>
      
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="absolute top-full right-0 mt-2 bg-black/90 border border-white/20 z-50"
          >
            {languages.map(lang => (
              <button
                key={lang.code}
                onClick={() => { changeLanguage(lang.code); setOpen(false); }}
                className={`w-full px-4 py-2 text-left text-sm hover:bg-white/10 flex items-center gap-2 ${language === lang.code ? 'text-neon-cyan' : ''}`}
              >
                <span>{lang.flag}</span>
                <span>{lang.name}</span>
              </button>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

// ==================== CONFETTI HANDLER ====================
const ConfettiContext = createContext(null);
const useConfetti = () => useContext(ConfettiContext);

const ConfettiProvider = ({ children }) => {
  const [showConfetti, setShowConfetti] = useState(false);
  
  const triggerConfetti = () => {
    setShowConfetti(true);
    // Play celebration sound
    try {
      const audio = new Audio('data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2teleT4ZZ5q9z7J+TyQwdqjE0KtzPBklb5+7yqxxORAjbKG+0a51RA0faZ69yK1zQQ4dcJW4xKpxPg8bc5m6xahxPw8Zc5S3w6ZvPBAXdJa5wqVuOxIWdZS4waNtORMUdpO3waJsNxUTdpK2v6FrNhYSd5G1vqBqNRcRd4+0vZ9pNBgQeI6zvJ5oMxkPeI2yvJ1nMhoOeoyxu5xmMRsNeYqwuZtlMBwMeoqwuZpkLx0Leomvt5ljLR4KeYiutphhLB8Jd4atsZZfKiEId4atsJVeKSIHdoSrr5RdKCMGdYOqrpNcJyQFdYKprZJbJiUFdIGprJFaJSYEdICoq5BZJCcDc3+nqo9YIygCc36mqY5XIikBcn2lqI1WISoBcnylp4xVICsBcXukpotUHywAcHqjpYpTHi0Ab3mipIlSHS4AbnihoohRHC8AbnehoogQGy8AbnehoodRGi8AbnehoodQGS8AbnahoodQGC8AbnahoodPFy8AbnahooZPFi8AbnahoYZOFS8AbnWhoYVOFC8AbnWgoYVNEy8AbnWgoIRNEi8AbnWgoIRMES4AbnSfoINMEC4Abg==');
      audio.volume = 0.3;
      audio.play().catch(() => {});
    } catch (e) {}
    setTimeout(() => setShowConfetti(false), 5000);
  };
  
  return (
    <ConfettiContext.Provider value={{ triggerConfetti }}>
      {showConfetti && <Confetti recycle={false} numberOfPieces={200} />}
      {children}
    </ConfettiContext.Provider>
  );
};

// ==================== 2.5D ISOMETRIC MAP COMPONENTS ====================
const IsometricZone = ({ zone, onClick, selected, index }) => {
  const [hovered, setHovered] = useState(false);
  const color = zone.color || '#00F0FF';
  
  const zoneIcons = {
    hub: '🏛️', marketplace: '🛒', learning: '📚', dao: '⚖️',
    'tech-district': '💻', residential: '🏘️', industrial: '🏭', cultural: '🎭'
  };
  
  // Calculate isometric position
  const row = Math.floor(index / 4);
  const col = index % 4;
  const isoX = (col - row) * 120 + 400;
  const isoY = (col + row) * 60 + 100;
  
  return (
    <motion.div
      initial={{ opacity: 0, y: 50 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1 }}
      className="absolute cursor-pointer"
      style={{ left: isoX, top: isoY, zIndex: 100 - row * 10 + col }}
      onClick={onClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      {/* Platform */}
      <motion.div
        animate={{ 
          scale: hovered || selected ? 1.1 : 1,
          y: hovered ? -5 : 0
        }}
        className="relative"
      >
        {/* Base Platform (Isometric Diamond) */}
        <div 
          className="w-32 h-16 relative"
          style={{
            background: `linear-gradient(135deg, ${color}40 0%, ${color}20 50%, ${color}10 100%)`,
            clipPath: 'polygon(50% 0%, 100% 50%, 50% 100%, 0% 50%)',
            boxShadow: selected ? `0 0 30px ${color}` : hovered ? `0 0 20px ${color}60` : 'none'
          }}
        >
          {/* Building Icon */}
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="text-3xl transform -translate-y-2">{zoneIcons[zone.id] || '🏢'}</span>
          </div>
        </div>
        
        {/* Building Structure */}
        <div 
          className="absolute -top-8 left-1/2 -translate-x-1/2 w-12 h-12 flex items-center justify-center"
          style={{
            background: `linear-gradient(to top, ${color}60, ${color}30)`,
            clipPath: 'polygon(20% 100%, 20% 40%, 50% 20%, 80% 40%, 80% 100%)',
            boxShadow: `0 0 15px ${color}40`
          }}
        />
        
        {/* Label */}
        <div 
          className={`absolute -bottom-8 left-1/2 -translate-x-1/2 whitespace-nowrap px-2 py-1 text-xs font-mono transition-all ${
            hovered || selected ? 'bg-black/90' : 'bg-black/60'
          }`}
          style={{ 
            color: color,
            border: `1px solid ${color}40`,
            boxShadow: hovered || selected ? `0 0 10px ${color}40` : 'none'
          }}
        >
          {zone.name}
        </div>
        
        {/* Job Count Badge */}
        <div 
          className="absolute -top-2 -right-2 px-2 py-0.5 text-xs font-mono bg-black border"
          style={{ borderColor: color, color }}
        >
          {zone.jobs_count}
        </div>
      </motion.div>
      
      {/* Hover Info Popup */}
      <AnimatePresence>
        {hovered && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 10 }}
            className="absolute top-full left-1/2 -translate-x-1/2 mt-10 w-56 bg-black/95 border p-3 z-50"
            style={{ borderColor: color }}
          >
            <p className="text-xs text-white/70 mb-2">{zone.description}</p>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="p-1 bg-white/5">
                <div className="text-white/50">Buildings</div>
                <div style={{ color }}>{zone.buildings?.length || 0}</div>
              </div>
              <div className="p-1 bg-white/5">
                <div className="text-white/50">Jobs</div>
                <div style={{ color }}>{zone.jobs_count}</div>
              </div>
            </div>
            {zone.features?.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1">
                {zone.features.slice(0, 3).map((f, i) => (
                  <span key={i} className="text-[9px] px-1 py-0.5 bg-white/5 text-white/60">{f}</span>
                ))}
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

const FloatingProject = ({ project, index }) => {
  const [hovered, setHovered] = useState(false);
  
  const categoryColors = {
    tech: '#FF003C', creative: '#E040FB', education: '#9D4EDD', commerce: '#FF6B35', default: '#00F0FF'
  };
  const color = categoryColors[project.category] || categoryColors.default;
  
  // Random floating position
  const left = 100 + (index % 5) * 180;
  const top = 50 + Math.floor(index / 5) * 100;
  
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0 }}
      animate={{ 
        opacity: 1, 
        scale: 1,
        y: [0, -10, 0]
      }}
      transition={{ 
        delay: 0.5 + index * 0.15,
        y: { duration: 3, repeat: Infinity, ease: "easeInOut" }
      }}
      className="absolute cursor-pointer"
      style={{ left, top }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <div 
        className={`w-12 h-12 rounded-full border-2 flex items-center justify-center transition-all ${
          hovered ? 'scale-125' : ''
        }`}
        style={{ 
          borderColor: color,
          background: `radial-gradient(circle, ${color}30, transparent)`,
          boxShadow: hovered ? `0 0 30px ${color}` : `0 0 15px ${color}40`
        }}
      >
        <span className="text-lg">🔮</span>
      </div>
      
      <AnimatePresence>
        {hovered && (
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            className="absolute top-full left-1/2 -translate-x-1/2 mt-2 w-48 bg-black/95 border p-2 z-50"
            style={{ borderColor: color }}
          >
            <h4 className="font-mono text-xs font-bold" style={{ color }}>{project.title}</h4>
            <p className="text-[10px] text-white/60 mt-1 line-clamp-2">{project.description}</p>
            <div className="mt-2 h-1 bg-white/10">
              <div className="h-full" style={{ width: `${project.progress}%`, backgroundColor: color }} />
            </div>
            <div className="text-[9px] text-white/40 mt-1">{project.progress}% complete</div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

// ==================== NAVBAR ====================
const Navbar = () => {
  const { user, logout } = useAuth();
  const t = useTranslation();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);
  
  const navItems = [
    { path: '/dashboard', icon: Home, label: t('dashboard') },
    { path: '/metaverse', icon: Layers, label: t('metaverse') },
    { path: '/jobs', icon: Briefcase, label: t('jobs') },
    { path: '/courses', icon: GraduationCap, label: t('courses') },
    { path: '/marketplace', icon: ShoppingBag, label: t('marketplace') },
    { path: '/voting', icon: Vote, label: t('voting') },
    { path: '/wallet', icon: Wallet, label: t('wallet') },
    { path: '/leaderboard', icon: Trophy, label: t('leaderboard') }
  ];
  
  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-black/80 backdrop-blur-xl border-b border-white/10">
      <div className="max-w-7xl mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link to="/dashboard" className="flex items-center gap-2">
            <div className="w-8 h-8 bg-gradient-to-br from-neon-cyan to-neon-purple flex items-center justify-center">
              <span className="text-black font-black text-sm">R</span>
            </div>
            <span className="font-orbitron font-bold text-lg hidden sm:block">REALUM</span>
          </Link>
          
          {/* Desktop Nav */}
          <div className="hidden lg:flex items-center gap-1">
            {navItems.map(item => (
              <Link
                key={item.path}
                to={item.path}
                className="px-3 py-2 text-sm text-white/70 hover:text-neon-cyan transition-colors flex items-center gap-2"
              >
                <item.icon className="w-4 h-4" />
                <span>{item.label}</span>
              </Link>
            ))}
          </div>
          
          {/* User Section */}
          <div className="flex items-center gap-4">
            <LanguageSelector />
            
            {user && (
              <div className="hidden md:flex items-center gap-4">
                <div className="text-right">
                  <div className="text-sm font-mono text-neon-cyan">{user.realum_balance?.toFixed(0)} RLM</div>
                  <div className="text-xs text-white/50">Lv.{user.level}</div>
                </div>
                <Link to="/profile" className="w-10 h-10 border border-neon-cyan/50 flex items-center justify-center hover:bg-neon-cyan/10">
                  <User className="w-5 h-5 text-neon-cyan" />
                </Link>
                <button onClick={logout} className="text-white/50 hover:text-neon-red">
                  <LogOut className="w-5 h-5" />
                </button>
              </div>
            )}
            
            {/* Mobile Menu Toggle */}
            <button onClick={() => setMenuOpen(!menuOpen)} className="lg:hidden">
              {menuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
          </div>
        </div>
      </div>
      
      {/* Mobile Menu */}
      <AnimatePresence>
        {menuOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="lg:hidden bg-black/95 border-t border-white/10"
          >
            {navItems.map(item => (
              <Link
                key={item.path}
                to={item.path}
                onClick={() => setMenuOpen(false)}
                className="flex items-center gap-3 px-4 py-3 text-white/70 hover:text-neon-cyan hover:bg-white/5"
              >
                <item.icon className="w-5 h-5" />
                <span>{item.label}</span>
              </Link>
            ))}
            {user && (
              <>
                <Link to="/profile" onClick={() => setMenuOpen(false)} className="flex items-center gap-3 px-4 py-3 text-white/70 hover:text-neon-cyan hover:bg-white/5">
                  <User className="w-5 h-5" />
                  <span>{t('profile')}</span>
                </Link>
                <button onClick={() => { logout(); setMenuOpen(false); }} className="w-full flex items-center gap-3 px-4 py-3 text-neon-red hover:bg-white/5">
                  <LogOut className="w-5 h-5" />
                  <span>{t('logout')}</span>
                </button>
              </>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </nav>
  );
};

// ==================== PROTECTED ROUTE ====================
const ProtectedRoute = ({ children }) => {
  const { user, loading } = useAuth();
  
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-neon-cyan font-mono animate-pulse">LOADING...</div>
      </div>
    );
  }
  
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  
  return <>{children}</>;
};

// ==================== PAGES ====================

// Landing Page
const LandingPage = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const t = useTranslation();
  
  useEffect(() => {
    if (user) navigate('/dashboard');
  }, [user, navigate]);
  
  return (
    <div className="min-h-screen relative overflow-hidden">
      {/* Animated Background */}
      <div className="absolute inset-0 bg-cyber-grid bg-[length:50px_50px] opacity-20 animate-pulse" />
      <div className="absolute inset-0 bg-hero-glow" />
      
      {/* Content */}
      <div className="relative z-10 min-h-screen flex flex-col items-center justify-center px-4 text-center">
        <motion.div
          initial={{ opacity: 0, y: 50 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
        >
          <h1 className="text-5xl md:text-7xl lg:text-8xl font-orbitron font-black mb-4">
            <span className="text-white">REAL</span>
            <span className="text-neon-cyan neon-text">UM</span>
          </h1>
          
          <p className="text-xl md:text-2xl font-mono text-neon-purple mb-2">{t('tagline')}</p>
          <p className="text-white/60 max-w-xl mx-auto mb-8">{t('subtitle')}</p>
          
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <CyberButton onClick={() => navigate('/register')} data-testid="enter-realum-btn">
              {t('enterRealum')} <ChevronRight className="inline w-4 h-4 ml-2" />
            </CyberButton>
            <CyberButton variant="ghost" onClick={() => navigate('/login')}>
              {t('login')}
            </CyberButton>
          </div>
          
          {/* Role Icons */}
          <div className="mt-16 grid grid-cols-2 md:grid-cols-4 gap-6 max-w-2xl mx-auto">
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
                className="p-4 border border-white/10 bg-black/30 hover:border-white/30 transition-colors"
              >
                <role.icon className="w-8 h-8 mx-auto mb-2" style={{ color: role.color }} />
                <span className="text-xs font-mono text-white/70">{role.label}</span>
              </motion.div>
            ))}
          </div>
        </motion.div>
        
        {/* Language Selector */}
        <div className="absolute top-4 right-4">
          <LanguageSelector />
        </div>
      </div>
    </div>
  );
};

// Login Page
const LoginPage = () => {
  const { login } = useAuth();
  const navigate = useNavigate();
  const t = useTranslation();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      await login(email, password);
      navigate('/dashboard');
    } catch (err) {
      setError(err.response?.data?.detail || 'Login failed');
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div className="min-h-screen flex items-center justify-center px-4 bg-cyber-grid bg-[length:30px_30px]">
      <CyberCard className="w-full max-w-md" glow>
        <h2 className="text-2xl font-orbitron font-bold text-center mb-6">
          {t('login')} <span className="text-neon-cyan">REALUM</span>
        </h2>
        
        {error && (
          <div className="mb-4 p-3 bg-neon-red/10 border border-neon-red/50 text-neon-red text-sm">
            {error}
          </div>
        )}
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="text-xs uppercase tracking-wider text-white/50 mb-1 block">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              data-testid="login-email"
              className="w-full bg-black/50 border border-white/20 px-4 py-3 text-white focus:border-neon-cyan focus:outline-none"
            />
          </div>
          
          <div>
            <label className="text-xs uppercase tracking-wider text-white/50 mb-1 block">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              data-testid="login-password"
              className="w-full bg-black/50 border border-white/20 px-4 py-3 text-white focus:border-neon-cyan focus:outline-none"
            />
          </div>
          
          <CyberButton type="submit" className="w-full" disabled={loading} data-testid="login-submit">
            {loading ? t('loading') : t('login')}
          </CyberButton>
        </form>
        
        <p className="text-center text-white/50 text-sm mt-6">
          Don't have an account?{' '}
          <Link to="/register" className="text-neon-cyan hover:underline">{t('register')}</Link>
        </p>
      </CyberCard>
    </div>
  );
};

// Register Page
const RegisterPage = () => {
  const { register } = useAuth();
  const navigate = useNavigate();
  const t = useTranslation();
  const [formData, setFormData] = useState({ username: '', email: '', password: '', role: 'citizen' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  
  const roles = [
    { value: 'citizen', label: t('citizen'), icon: Users, desc: 'General participation' },
    { value: 'creator', label: t('creator'), icon: Sparkles, desc: 'Upload resources & designs' },
    { value: 'contributor', label: t('contributor'), icon: Target, desc: 'Complete tasks & projects' },
    { value: 'evaluator', label: t('evaluator'), icon: Shield, desc: 'Validate & give feedback' },
    { value: 'partner', label: t('partner'), icon: Heart, desc: 'Post missions & pay RLM' }
  ];
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      await register(formData);
      navigate('/dashboard');
    } catch (err) {
      setError(err.response?.data?.detail || 'Registration failed');
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-12 bg-cyber-grid bg-[length:30px_30px]">
      <CyberCard className="w-full max-w-lg" glow>
        <h2 className="text-2xl font-orbitron font-bold text-center mb-6">
          {t('register')} <span className="text-neon-cyan">REALUM</span>
        </h2>
        
        {error && (
          <div className="mb-4 p-3 bg-neon-red/10 border border-neon-red/50 text-neon-red text-sm">
            {error}
          </div>
        )}
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="text-xs uppercase tracking-wider text-white/50 mb-1 block">Username</label>
            <input
              type="text"
              value={formData.username}
              onChange={(e) => setFormData({...formData, username: e.target.value})}
              required
              data-testid="register-username"
              className="w-full bg-black/50 border border-white/20 px-4 py-3 text-white focus:border-neon-cyan focus:outline-none"
            />
          </div>
          
          <div>
            <label className="text-xs uppercase tracking-wider text-white/50 mb-1 block">Email</label>
            <input
              type="email"
              value={formData.email}
              onChange={(e) => setFormData({...formData, email: e.target.value})}
              required
              data-testid="register-email"
              className="w-full bg-black/50 border border-white/20 px-4 py-3 text-white focus:border-neon-cyan focus:outline-none"
            />
          </div>
          
          <div>
            <label className="text-xs uppercase tracking-wider text-white/50 mb-1 block">Password</label>
            <input
              type="password"
              value={formData.password}
              onChange={(e) => setFormData({...formData, password: e.target.value})}
              required
              data-testid="register-password"
              className="w-full bg-black/50 border border-white/20 px-4 py-3 text-white focus:border-neon-cyan focus:outline-none"
            />
          </div>
          
          <div>
            <label className="text-xs uppercase tracking-wider text-white/50 mb-2 block">{t('selectRole')}</label>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {roles.map(role => (
                <button
                  key={role.value}
                  type="button"
                  onClick={() => setFormData({...formData, role: role.value})}
                  className={`p-3 border text-left transition-all ${
                    formData.role === role.value 
                      ? 'border-neon-cyan bg-neon-cyan/10' 
                      : 'border-white/20 hover:border-white/40'
                  }`}
                >
                  <role.icon className={`w-5 h-5 mb-1 ${formData.role === role.value ? 'text-neon-cyan' : 'text-white/50'}`} />
                  <div className="text-xs font-mono">{role.label}</div>
                </button>
              ))}
            </div>
          </div>
          
          <CyberButton type="submit" className="w-full" disabled={loading} data-testid="register-submit">
            {loading ? t('loading') : t('register')}
          </CyberButton>
        </form>
        
        <p className="text-center text-white/50 text-sm mt-6">
          Already have an account?{' '}
          <Link to="/login" className="text-neon-cyan hover:underline">{t('login')}</Link>
        </p>
      </CyberCard>
    </div>
  );
};

// Dashboard Page
const DashboardPage = () => {
  const { user, refreshUser } = useAuth();
  const t = useTranslation();
  const { triggerConfetti } = useConfetti();
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
    { label: t('metaverse'), icon: Layers, path: '/metaverse', color: '#00F0FF' },
    { label: t('voting'), icon: Vote, path: '/voting', color: '#40C4FF' },
    { label: t('projects'), icon: Building2, path: '/projects', color: '#00FF88' }
  ];
  
  return (
    <div className="min-h-screen pt-20 pb-12 px-4" data-testid="dashboard">
      <div className="max-w-7xl mx-auto">
        {/* Welcome Section */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
          <h1 className="text-3xl md:text-4xl font-orbitron font-black mb-2">
            {t('welcome')}, <span className="text-neon-cyan">{user?.username}</span>
          </h1>
          <p className="text-white/60 flex items-center gap-2">
            <span 
              className="px-2 py-1 text-xs border uppercase"
              style={{ borderColor: roleColors[user?.role], color: roleColors[user?.role] }}
            >
              {user?.role}
            </span>
            <span>Member since {new Date(user?.created_at).toLocaleDateString()}</span>
          </p>
        </motion.div>
        
        <div className="grid lg:grid-cols-3 gap-6">
          {/* User Stats */}
          <div className="lg:col-span-2 space-y-6">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <CyberCard className="text-center">
                <Coins className="w-8 h-8 mx-auto mb-2 text-neon-cyan" />
                <div className="text-2xl font-orbitron font-bold text-neon-cyan">{user?.realum_balance?.toFixed(0)}</div>
                <div className="text-xs text-white/50 uppercase">RLM {t('balance')}</div>
              </CyberCard>
              
              <CyberCard className="text-center">
                <Zap className="w-8 h-8 mx-auto mb-2 text-neon-purple" />
                <div className="text-2xl font-orbitron font-bold text-neon-purple">{user?.xp || 0}</div>
                <div className="text-xs text-white/50 uppercase">{t('xp')}</div>
              </CyberCard>
              
              <CyberCard className="text-center">
                <Star className="w-8 h-8 mx-auto mb-2 text-neon-yellow" />
                <div className="text-2xl font-orbitron font-bold text-neon-yellow">{user?.level || 1}</div>
                <div className="text-xs text-white/50 uppercase">{t('level')}</div>
              </CyberCard>
              
              <CyberCard className="text-center">
                <Award className="w-8 h-8 mx-auto mb-2 text-neon-green" />
                <div className="text-2xl font-orbitron font-bold text-neon-green">{user?.badges?.length || 0}</div>
                <div className="text-xs text-white/50 uppercase">{t('badges')}</div>
              </CyberCard>
            </div>
            
            {/* Quick Actions */}
            <CyberCard>
              <h3 className="font-orbitron font-bold mb-4">Quick Actions</h3>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                {quickActions.map(action => (
                  <motion.button
                    key={action.path}
                    whileHover={{ scale: 1.02 }}
                    onClick={() => navigate(action.path)}
                    className="p-4 border border-white/10 hover:border-white/30 transition-all text-left"
                  >
                    <action.icon className="w-6 h-6 mb-2" style={{ color: action.color }} />
                    <span className="text-sm font-mono">{action.label}</span>
                  </motion.button>
                ))}
              </div>
            </CyberCard>
            
            {/* Token Economy */}
            {tokenStats && (
              <CyberCard>
                <h3 className="font-orbitron font-bold mb-4 flex items-center gap-2">
                  <TrendingUp className="w-5 h-5 text-neon-cyan" />
                  Token Economy
                </h3>
                <div className="grid grid-cols-3 gap-4">
                  <div className="p-3 bg-black/30 border border-white/10">
                    <div className="text-xs text-white/50 mb-1">{t('totalSupply')}</div>
                    <div className="font-mono text-neon-cyan">{tokenStats.total_supply?.toFixed(0)} RLM</div>
                  </div>
                  <div className="p-3 bg-black/30 border border-white/10">
                    <div className="text-xs text-white/50 mb-1">{t('tokensBurned')}</div>
                    <div className="font-mono text-neon-red">{tokenStats.total_burned?.toFixed(2)} RLM</div>
                  </div>
                  <div className="p-3 bg-black/30 border border-white/10">
                    <div className="text-xs text-white/50 mb-1">{t('burnRate')}</div>
                    <div className="font-mono text-neon-yellow">{tokenStats.burn_rate}%</div>
                  </div>
                </div>
              </CyberCard>
            )}
          </div>
          
          {/* Sidebar */}
          <div className="space-y-6">
            {/* Platform Stats */}
            {stats && (
              <CyberCard>
                <h3 className="font-orbitron font-bold mb-4">Platform Stats</h3>
                <div className="space-y-3">
                  <div className="flex justify-between text-sm">
                    <span className="text-white/50">Total Users</span>
                    <span className="font-mono text-neon-cyan">{stats.total_users}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-white/50">Jobs Completed</span>
                    <span className="font-mono text-neon-green">{stats.jobs_completed}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-white/50">Active Proposals</span>
                    <span className="font-mono text-neon-purple">{stats.active_proposals}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-white/50">Courses Available</span>
                    <span className="font-mono text-neon-yellow">{stats.courses_available}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-white/50">Active Projects</span>
                    <span className="font-mono text-neon-red">{stats.active_projects}</span>
                  </div>
                </div>
              </CyberCard>
            )}
            
            {/* Badges Preview */}
            <CyberCard>
              <h3 className="font-orbitron font-bold mb-4">Your Badges</h3>
              <div className="flex flex-wrap gap-2">
                {user?.badges?.slice(0, 6).map(badge => (
                  <div key={badge} className="w-10 h-10 bg-neon-cyan/10 border border-neon-cyan/30 flex items-center justify-center">
                    <span className="text-lg">🏆</span>
                  </div>
                ))}
                {user?.badges?.length > 6 && (
                  <Link to="/profile" className="w-10 h-10 bg-white/5 border border-white/20 flex items-center justify-center text-xs text-white/50">
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

// 2.5D Isometric Metaverse Page
const MetaversePage = () => {
  const t = useTranslation();
  const navigate = useNavigate();
  const [zones, setZones] = useState([]);
  const [projects, setProjects] = useState([]);
  const [selectedZone, setSelectedZone] = useState(null);
  
  useEffect(() => {
    axios.get(`${API}/city/zones`).then(res => setZones(res.data)).catch(console.error);
    axios.get(`${API}/projects`).then(res => setProjects(res.data.projects || [])).catch(console.error);
  }, []);
  
  return (
    <div className="min-h-screen pt-16" data-testid="metaverse-page">
      <div className="h-[calc(100vh-64px)] relative overflow-hidden bg-[#0a0a1a]">
        {/* Animated Background Grid */}
        <div className="absolute inset-0 bg-cyber-grid bg-[length:40px_40px] opacity-20" />
        <div className="absolute inset-0 bg-hero-glow opacity-30" />
        
        {/* Floating Stars/Particles */}
        <div className="absolute inset-0 overflow-hidden">
          {[...Array(30)].map((_, i) => (
            <motion.div
              key={i}
              className="absolute w-1 h-1 bg-neon-cyan rounded-full"
              initial={{ 
                x: Math.random() * window.innerWidth, 
                y: Math.random() * window.innerHeight,
                opacity: 0.2 + Math.random() * 0.5
              }}
              animate={{ 
                y: [null, -20, 0],
                opacity: [null, 0.8, 0.2 + Math.random() * 0.5]
              }}
              transition={{ 
                duration: 3 + Math.random() * 3, 
                repeat: Infinity,
                delay: Math.random() * 2
              }}
            />
          ))}
        </div>
        
        {/* Header */}
        <div className="absolute top-4 left-4 right-4 z-20 flex justify-between items-start">
          <div>
            <h1 className="text-2xl md:text-3xl font-orbitron font-black text-white">
              REALUM <span className="text-neon-cyan neon-text">{t('metaverse')}</span>
            </h1>
            <p className="text-sm text-white/60">Explore the city • Click zones to view details</p>
          </div>
          
          {/* Zone Legend */}
          <div className="bg-black/80 border border-white/20 p-3 backdrop-blur hidden md:block">
            <div className="text-xs font-mono text-white/50 mb-2">CITY ZONES</div>
            <div className="grid grid-cols-2 gap-x-4 gap-y-1">
              {zones.map(zone => (
                <button 
                  key={zone.id}
                  className="flex items-center gap-2 text-xs hover:opacity-80 text-left"
                  onClick={() => setSelectedZone(zone)}
                >
                  <div className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: zone.color }} />
                  <span className="text-white/70 truncate">{zone.name}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
        
        {/* Isometric Map Container */}
        <div className="absolute inset-0 pt-20" style={{ perspective: '1000px' }}>
          <div 
            className="relative w-full h-full"
            style={{ transform: 'rotateX(0deg)' }}
          >
            {/* Zone Islands */}
            {zones.map((zone, index) => (
              <IsometricZone
                key={zone.id}
                zone={zone}
                index={index}
                onClick={() => setSelectedZone(zone)}
                selected={selectedZone?.id === zone.id}
              />
            ))}
            
            {/* Floating Projects */}
            {projects.slice(0, 5).map((project, index) => (
              <FloatingProject
                key={project.id}
                project={project}
                index={index}
              />
            ))}
          </div>
        </div>
        
        {/* Selected Zone Panel */}
        <AnimatePresence>
          {selectedZone && (
            <motion.div
              initial={{ opacity: 0, x: 100 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 100 }}
              className="absolute bottom-4 right-4 w-80 bg-black/95 border p-4 z-30"
              style={{ borderColor: selectedZone.color }}
            >
              <div className="flex justify-between items-start mb-3">
                <div>
                  <h3 className="font-orbitron font-bold text-lg" style={{ color: selectedZone.color }}>
                    {selectedZone.name}
                  </h3>
                  <span className="text-xs text-white/50 uppercase">{selectedZone.type} zone</span>
                </div>
                <button onClick={() => setSelectedZone(null)} className="text-white/50 hover:text-white">
                  <X className="w-5 h-5" />
                </button>
              </div>
              
              <p className="text-sm text-white/70 mb-4">{selectedZone.description}</p>
              
              <div className="grid grid-cols-2 gap-2 mb-4">
                <div className="p-2 bg-white/5 border border-white/10">
                  <div className="text-xs text-white/50">Jobs</div>
                  <div className="font-mono text-lg" style={{ color: selectedZone.color }}>{selectedZone.jobs_count}</div>
                </div>
                <div className="p-2 bg-white/5 border border-white/10">
                  <div className="text-xs text-white/50">Buildings</div>
                  <div className="font-mono text-lg" style={{ color: selectedZone.color }}>{selectedZone.buildings?.length || 0}</div>
                </div>
              </div>
              
              {selectedZone.buildings && (
                <div className="mb-4">
                  <div className="text-xs text-white/50 mb-2">Key Locations</div>
                  <div className="flex flex-wrap gap-1">
                    {selectedZone.buildings.slice(0, 4).map((b, i) => (
                      <span key={i} className="text-[10px] px-2 py-1 bg-white/5 border border-white/10">{b}</span>
                    ))}
                  </div>
                </div>
              )}
              
              {selectedZone.features?.length > 0 && (
                <div className="mb-4">
                  <div className="text-xs text-white/50 mb-2">Features</div>
                  <div className="space-y-1">
                    {selectedZone.features.map((f, i) => (
                      <div key={i} className="flex items-center gap-2 text-xs">
                        <div className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: selectedZone.color }} />
                        <span className="text-white/70">{f}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              
              <CyberButton 
                className="w-full"
                onClick={() => navigate(`/jobs?zone=${selectedZone.id}`)}
              >
                Explore Jobs <ChevronRight className="w-4 h-4 inline ml-1" />
              </CyberButton>
            </motion.div>
          )}
        </AnimatePresence>
        
        {/* Bottom Stats Bar */}
        <div className="absolute bottom-4 left-4 flex gap-3">
          <div className="bg-black/80 border border-white/20 px-3 py-2 text-xs">
            <span className="text-white/50">Zones:</span>{' '}
            <span className="text-neon-cyan font-mono">{zones.length}</span>
          </div>
          <div className="bg-black/80 border border-white/20 px-3 py-2 text-xs">
            <span className="text-white/50">Projects:</span>{' '}
            <span className="text-neon-purple font-mono">{projects.length}</span>
          </div>
        </div>
      </div>
    </div>
  );
};

// Jobs Page
const JobsPage = () => {
  const { user, refreshUser } = useAuth();
  const { triggerConfetti } = useConfetti();
  const t = useTranslation();
  const location = useLocation();
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeJobs, setActiveJobs] = useState([]);
  const [filter, setFilter] = useState(new URLSearchParams(location.search).get('zone') || '');
  
  const fetchJobs = async () => {
    try {
      const params = filter ? `?zone=${filter}` : '';
      const [jobsRes, activeRes] = await Promise.all([
        axios.get(`${API}/jobs${params}`),
        axios.get(`${API}/jobs/active`)
      ]);
      setJobs(jobsRes.data);
      setActiveJobs(activeRes.data.active_jobs || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };
  
  useEffect(() => { fetchJobs(); }, [filter]);
  
  const applyForJob = async (jobId) => {
    try {
      await axios.post(`${API}/jobs/${jobId}/apply`);
      fetchJobs();
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to apply');
    }
  };
  
  const completeJob = async (jobId) => {
    try {
      const res = await axios.post(`${API}/jobs/${jobId}/complete`);
      triggerConfetti();
      refreshUser();
      fetchJobs();
      alert(`Completed! +${res.data.reward} RLM, +${res.data.xp_gained} XP`);
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to complete');
    }
  };
  
  const zoneColors = {
    hub: '#FFD700', marketplace: '#FF6B35', learning: '#9D4EDD', dao: '#40C4FF',
    'tech-district': '#FF003C', residential: '#00FF88', industrial: '#F9F871', cultural: '#E040FB'
  };
  
  return (
    <div className="min-h-screen pt-20 pb-12 px-4" data-testid="jobs-page">
      <div className="max-w-6xl mx-auto">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
          <h1 className="text-3xl md:text-4xl font-orbitron font-black">
            {t('jobs')} <span className="text-neon-cyan">BOARD</span>
          </h1>
          <p className="text-white/60 mt-2">Find tasks, earn RLM, level up your skills</p>
        </motion.div>
        
        {/* Active Jobs */}
        {activeJobs.length > 0 && (
          <CyberCard className="mb-6" glow>
            <h3 className="font-orbitron font-bold mb-4 flex items-center gap-2">
              <Clock className="w-5 h-5 text-neon-yellow" />
              Active Jobs
            </h3>
            <div className="space-y-3">
              {activeJobs.map(aj => (
                <div key={aj.id} className="flex items-center justify-between p-3 bg-black/30 border border-neon-yellow/30">
                  <div>
                    <div className="font-mono">{aj.job?.title}</div>
                    <div className="text-xs text-white/50">{aj.job?.company}</div>
                  </div>
                  <CyberButton variant="success" onClick={() => completeJob(aj.job_id)}>
                    {t('complete')}
                  </CyberButton>
                </div>
              ))}
            </div>
          </CyberCard>
        )}
        
        {/* Zone Filter */}
        <div className="flex flex-wrap gap-2 mb-6">
          <button 
            onClick={() => setFilter('')}
            className={`px-3 py-1 text-xs border ${!filter ? 'border-neon-cyan text-neon-cyan' : 'border-white/20 text-white/50'}`}
          >
            All
          </button>
          {Object.entries(zoneColors).map(([zone, color]) => (
            <button
              key={zone}
              onClick={() => setFilter(zone)}
              className="px-3 py-1 text-xs border transition-colors"
              style={{ 
                borderColor: filter === zone ? color : 'rgba(255,255,255,0.2)',
                color: filter === zone ? color : 'rgba(255,255,255,0.5)'
              }}
            >
              {zone.replace('-', ' ')}
            </button>
          ))}
        </div>
        
        {/* Jobs Grid */}
        {loading ? (
          <div className="text-center text-white/50">{t('loading')}</div>
        ) : (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {jobs.map(job => (
              <CyberCard key={job.id}>
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <h4 className="font-mono font-bold">{job.title}</h4>
                    <p className="text-xs text-white/50">{job.company}</p>
                  </div>
                  <span 
                    className="px-2 py-1 text-xs border"
                    style={{ borderColor: zoneColors[job.zone], color: zoneColors[job.zone] }}
                  >
                    {job.zone}
                  </span>
                </div>
                
                <p className="text-sm text-white/70 mb-4 line-clamp-2">{job.description}</p>
                
                <div className="flex flex-wrap gap-2 mb-4">
                  <span className="px-2 py-1 text-xs bg-neon-cyan/10 text-neon-cyan border border-neon-cyan/30">
                    +{job.reward} RLM
                  </span>
                  <span className="px-2 py-1 text-xs bg-neon-purple/10 text-neon-purple border border-neon-purple/30">
                    +{job.xp_reward} XP
                  </span>
                  <span className="px-2 py-1 text-xs bg-white/5 text-white/50 border border-white/10">
                    {job.duration_minutes}m
                  </span>
                </div>
                
                {job.required_role && (
                  <div className="text-xs text-white/40 mb-2">Requires: {job.required_role}</div>
                )}
                
                <CyberButton 
                  className="w-full" 
                  onClick={() => applyForJob(job.id)}
                  disabled={job.required_level > user?.level || (job.required_role && job.required_role !== user?.role)}
                >
                  {job.required_level > user?.level ? `Req. Lv.${job.required_level}` : t('apply')}
                </CyberButton>
              </CyberCard>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

// Courses Page
const CoursesPage = () => {
  const { user, refreshUser } = useAuth();
  const { triggerConfetti } = useConfetti();
  const t = useTranslation();
  const [courses, setCourses] = useState([]);
  const [enrollments, setEnrollments] = useState([]);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    axios.get(`${API}/courses`).then(res => setCourses(res.data.courses || [])).catch(console.error).finally(() => setLoading(false));
  }, []);
  
  const enrollInCourse = async (courseId) => {
    try {
      await axios.post(`${API}/courses/${courseId}/enroll`);
      alert('Enrolled successfully!');
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to enroll');
    }
  };
  
  const categoryColors = {
    basics: '#00F0FF', tech: '#FF003C', civic: '#40C4FF', creative: '#E040FB', economics: '#FFD700'
  };
  
  const difficultyColors = {
    beginner: '#00FF88', intermediate: '#F9F871', advanced: '#FF003C'
  };
  
  return (
    <div className="min-h-screen pt-20 pb-12 px-4" data-testid="courses-page">
      <div className="max-w-6xl mx-auto">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
          <h1 className="text-3xl md:text-4xl font-orbitron font-black">
            LEARNING <span className="text-neon-purple">ZONE</span>
          </h1>
          <p className="text-white/60 mt-2">Master new skills, earn badges and RLM</p>
        </motion.div>
        
        {loading ? (
          <div className="text-center text-white/50">{t('loading')}</div>
        ) : (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {courses.map(course => (
              <CyberCard key={course.id}>
                <div className="flex items-start justify-between mb-3">
                  <span 
                    className="px-2 py-1 text-xs border"
                    style={{ borderColor: categoryColors[course.category], color: categoryColors[course.category] }}
                  >
                    {course.category}
                  </span>
                  <span 
                    className="px-2 py-1 text-xs"
                    style={{ color: difficultyColors[course.difficulty] }}
                  >
                    {course.difficulty}
                  </span>
                </div>
                
                <h4 className="font-orbitron font-bold mb-2">{course.title}</h4>
                <p className="text-sm text-white/70 mb-4 line-clamp-2">{course.description}</p>
                
                <div className="flex items-center gap-4 mb-4 text-xs text-white/50">
                  <span className="flex items-center gap-1">
                    <Clock className="w-3 h-3" /> {course.duration_hours}h
                  </span>
                  <span className="flex items-center gap-1">
                    <BookOpen className="w-3 h-3" /> {course.lessons?.length || 0} lessons
                  </span>
                </div>
                
                <div className="flex gap-2 mb-4">
                  <span className="px-2 py-1 text-xs bg-neon-purple/10 text-neon-purple border border-neon-purple/30">
                    +{course.xp_reward} XP
                  </span>
                  <span className="px-2 py-1 text-xs bg-neon-cyan/10 text-neon-cyan border border-neon-cyan/30">
                    +{course.rlm_reward} RLM
                  </span>
                </div>
                
                {course.skills_gained?.length > 0 && (
                  <div className="flex flex-wrap gap-1 mb-4">
                    {course.skills_gained.map(skill => (
                      <span key={skill} className="text-[10px] px-1 py-0.5 bg-white/5 text-white/50">{skill}</span>
                    ))}
                  </div>
                )}
                
                <CyberButton className="w-full" onClick={() => enrollInCourse(course.id)}>
                  <Play className="w-4 h-4 inline mr-2" /> {t('enroll')}
                </CyberButton>
              </CyberCard>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

// Marketplace Page
const MarketplacePage = () => {
  const { user, refreshUser } = useAuth();
  const t = useTranslation();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    axios.get(`${API}/marketplace`).then(res => setItems(res.data.items || [])).catch(console.error).finally(() => setLoading(false));
  }, []);
  
  const purchaseItem = async (itemId) => {
    if (!window.confirm('Confirm purchase?')) return;
    try {
      const res = await axios.post(`${API}/marketplace/${itemId}/purchase`);
      alert(`Purchased! Paid ${res.data.amount_paid} RLM (${res.data.amount_burned} burned)`);
      refreshUser();
    } catch (err) {
      alert(err.response?.data?.detail || 'Purchase failed');
    }
  };
  
  const categoryIcons = {
    design: Sparkles, code: Target, document: BookOpen, template: Layers, course: GraduationCap, service: Users
  };
  
  return (
    <div className="min-h-screen pt-20 pb-12 px-4" data-testid="marketplace-page">
      <div className="max-w-6xl mx-auto">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
          <h1 className="text-3xl md:text-4xl font-orbitron font-black">
            {t('marketplace')} <span className="text-neon-orange">HUB</span>
          </h1>
          <p className="text-white/60 mt-2">Buy and sell digital resources, designs, and services</p>
        </motion.div>
        
        {loading ? (
          <div className="text-center text-white/50">{t('loading')}</div>
        ) : (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {items.map(item => {
              const Icon = categoryIcons[item.category] || ShoppingBag;
              return (
                <CyberCard key={item.id}>
                  <div className="flex items-start justify-between mb-3">
                    <div className="w-10 h-10 bg-neon-orange/10 border border-neon-orange/30 flex items-center justify-center">
                      <Icon className="w-5 h-5 text-neon-orange" />
                    </div>
                    <span className="text-xs text-white/50">{item.category}</span>
                  </div>
                  
                  <h4 className="font-mono font-bold mb-2">{item.title}</h4>
                  <p className="text-sm text-white/70 mb-4 line-clamp-2">{item.description}</p>
                  
                  <div className="flex items-center justify-between mb-4">
                    <div className="text-xl font-orbitron font-bold text-neon-cyan">{item.price_rlm} RLM</div>
                    <div className="text-xs text-white/50">
                      {item.downloads} downloads • ⭐ {item.rating?.toFixed(1) || 'N/A'}
                    </div>
                  </div>
                  
                  <div className="text-xs text-white/40 mb-4">by {item.seller_name}</div>
                  
                  <CyberButton 
                    className="w-full" 
                    onClick={() => purchaseItem(item.id)}
                    disabled={user?.id === item.seller_id || user?.realum_balance < item.price_rlm}
                  >
                    {user?.realum_balance < item.price_rlm ? 'Insufficient RLM' : t('purchase')}
                  </CyberButton>
                </CyberCard>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

// Voting/DAO Page
const VotingPage = () => {
  const { user } = useAuth();
  const t = useTranslation();
  const [proposals, setProposals] = useState([]);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    axios.get(`${API}/proposals`).then(res => setProposals(res.data)).catch(console.error).finally(() => setLoading(false));
  }, []);
  
  const vote = async (proposalId, voteType) => {
    try {
      await axios.post(`${API}/proposals/${proposalId}/vote`, { vote_type: voteType });
      setProposals(prev => prev.map(p => {
        if (p.id === proposalId) {
          return {
            ...p,
            [voteType === 'for' ? 'votes_for' : 'votes_against']: p[voteType === 'for' ? 'votes_for' : 'votes_against'] + 1,
            voters: [...(p.voters || []), user?.id]
          };
        }
        return p;
      }));
    } catch (err) {
      alert(err.response?.data?.detail || 'Vote failed');
    }
  };
  
  return (
    <div className="min-h-screen pt-20 pb-12 px-4" data-testid="voting-page">
      <div className="max-w-4xl mx-auto">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
          <h1 className="text-3xl md:text-4xl font-orbitron font-black">
            DAO <span className="text-neon-blue">GOVERNANCE</span>
          </h1>
          <p className="text-white/60 mt-2">Shape the future of REALUM with your vote</p>
        </motion.div>
        
        {loading ? (
          <div className="text-center text-white/50">{t('loading')}</div>
        ) : (
          <div className="space-y-6">
            {proposals.map(proposal => {
              const totalVotes = proposal.votes_for + proposal.votes_against;
              const forPercent = totalVotes > 0 ? (proposal.votes_for / totalVotes * 100) : 50;
              const hasVoted = proposal.voters?.includes(user?.id);
              
              return (
                <CyberCard key={proposal.id}>
                  <div className="flex items-start justify-between mb-4">
                    <div>
                      <h4 className="font-orbitron font-bold text-lg">{proposal.title}</h4>
                      <span className="text-xs text-white/50">by {proposal.proposer_name}</span>
                    </div>
                    <span className={`px-2 py-1 text-xs border ${
                      proposal.status === 'active' ? 'border-neon-green text-neon-green' : 'border-white/30 text-white/50'
                    }`}>
                      {proposal.status}
                    </span>
                  </div>
                  
                  <p className="text-white/70 mb-6">{proposal.description}</p>
                  
                  {/* Vote Bar */}
                  <div className="mb-4">
                    <div className="flex justify-between text-xs mb-2">
                      <span className="text-neon-cyan">For: {proposal.votes_for}</span>
                      <span className="text-neon-red">Against: {proposal.votes_against}</span>
                    </div>
                    <div className="h-2 bg-white/10 flex overflow-hidden">
                      <div className="bg-neon-cyan transition-all" style={{ width: `${forPercent}%` }} />
                      <div className="bg-neon-red transition-all" style={{ width: `${100 - forPercent}%` }} />
                    </div>
                  </div>
                  
                  {proposal.status === 'active' && !hasVoted && (
                    <div className="flex gap-3">
                      <CyberButton className="flex-1" onClick={() => vote(proposal.id, 'for')}>
                        {t('voteFor')}
                      </CyberButton>
                      <CyberButton variant="danger" className="flex-1" onClick={() => vote(proposal.id, 'against')}>
                        {t('voteAgainst')}
                      </CyberButton>
                    </div>
                  )}
                  
                  {hasVoted && (
                    <div className="text-center text-neon-green text-sm">
                      <CheckCircle className="w-4 h-4 inline mr-1" /> You have voted
                    </div>
                  )}
                </CyberCard>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

// Wallet Page
const WalletPage = () => {
  const { user, refreshUser } = useAuth();
  const t = useTranslation();
  const [wallet, setWallet] = useState(null);
  const [tokenStats, setTokenStats] = useState(null);
  const [showTransfer, setShowTransfer] = useState(false);
  const [transferData, setTransferData] = useState({ to_user_id: '', amount: '', reason: '' });
  
  useEffect(() => {
    axios.get(`${API}/wallet`).then(res => setWallet(res.data)).catch(console.error);
    axios.get(`${API}/token/stats`).then(res => setTokenStats(res.data)).catch(console.error);
  }, []);
  
  const handleTransfer = async (e) => {
    e.preventDefault();
    try {
      const res = await axios.post(`${API}/wallet/transfer`, {
        ...transferData,
        amount: parseFloat(transferData.amount)
      });
      alert(`Transferred! ${res.data.amount_burned} RLM burned.`);
      setShowTransfer(false);
      refreshUser();
      axios.get(`${API}/wallet`).then(res => setWallet(res.data));
    } catch (err) {
      alert(err.response?.data?.detail || 'Transfer failed');
    }
  };
  
  const connectMetaMask = async () => {
    if (typeof window.ethereum === 'undefined') {
      alert('MetaMask not installed');
      return;
    }
    try {
      const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });
      await axios.post(`${API}/wallet/connect`, { wallet_address: accounts[0] });
      refreshUser();
      alert('Wallet connected!');
    } catch (err) {
      alert('Connection failed');
    }
  };
  
  return (
    <div className="min-h-screen pt-20 pb-12 px-4" data-testid="wallet-page">
      <div className="max-w-4xl mx-auto">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
          <h1 className="text-3xl md:text-4xl font-orbitron font-black">
            {t('wallet')} <span className="text-neon-cyan">HUB</span>
          </h1>
        </motion.div>
        
        <div className="grid md:grid-cols-2 gap-6">
          {/* Balance Card */}
          <CyberCard glow>
            <div className="text-center">
              <Coins className="w-12 h-12 mx-auto mb-4 text-neon-cyan" />
              <div className="text-4xl font-orbitron font-black text-neon-cyan mb-2">
                {user?.realum_balance?.toFixed(2)} RLM
              </div>
              <p className="text-white/50 text-sm">Total Balance</p>
            </div>
            
            <div className="mt-6 flex gap-3">
              <CyberButton className="flex-1" onClick={() => setShowTransfer(true)}>
                <Send className="w-4 h-4 inline mr-2" /> {t('transfer')}
              </CyberButton>
            </div>
          </CyberCard>
          
          {/* Web3 Connection */}
          <CyberCard>
            <h3 className="font-orbitron font-bold mb-4">Web3 Wallet</h3>
            {user?.wallet_address ? (
              <div>
                <div className="text-xs text-white/50 mb-1">Connected Address</div>
                <div className="font-mono text-sm text-neon-green break-all">{user.wallet_address}</div>
              </div>
            ) : (
              <CyberButton onClick={connectMetaMask} className="w-full">
                Connect MetaMask
              </CyberButton>
            )}
            
            {tokenStats && (
              <div className="mt-4 pt-4 border-t border-white/10">
                <div className="text-xs text-white/50 mb-2">Token Economy</div>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-white/60">{t('burnRate')}</span>
                    <span className="text-neon-red">{tokenStats.burn_rate}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-white/60">{t('tokensBurned')}</span>
                    <span className="text-neon-red">{tokenStats.total_burned?.toFixed(2)} RLM</span>
                  </div>
                </div>
              </div>
            )}
          </CyberCard>
        </div>
        
        {/* Transaction History */}
        <CyberCard className="mt-6">
          <h3 className="font-orbitron font-bold mb-4">Transaction History</h3>
          {wallet?.transactions?.length > 0 ? (
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {wallet.transactions.slice().reverse().map(tx => (
                <div key={tx.id} className="flex items-center justify-between p-3 bg-black/30 border border-white/10">
                  <div>
                    <div className="font-mono text-sm">{tx.description}</div>
                    <div className="text-xs text-white/40">{new Date(tx.timestamp).toLocaleString()}</div>
                  </div>
                  <span className={`font-mono font-bold ${tx.type === 'credit' ? 'text-neon-green' : 'text-neon-red'}`}>
                    {tx.type === 'credit' ? '+' : '-'}{tx.amount} RLM
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-white/50 text-center py-8">No transactions yet</p>
          )}
        </CyberCard>
        
        {/* Transfer Modal */}
        <AnimatePresence>
          {showTransfer && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4"
              onClick={() => setShowTransfer(false)}
            >
              <motion.div
                initial={{ scale: 0.9 }}
                animate={{ scale: 1 }}
                exit={{ scale: 0.9 }}
                onClick={e => e.stopPropagation()}
                className="bg-black border border-neon-cyan/50 p-6 w-full max-w-md"
              >
                <h3 className="font-orbitron font-bold mb-4">Transfer RLM</h3>
                <form onSubmit={handleTransfer} className="space-y-4">
                  <div>
                    <label className="text-xs text-white/50 mb-1 block">Recipient User ID</label>
                    <input
                      type="text"
                      value={transferData.to_user_id}
                      onChange={e => setTransferData({...transferData, to_user_id: e.target.value})}
                      required
                      className="w-full bg-black/50 border border-white/20 px-4 py-2 text-white"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-white/50 mb-1 block">Amount (2% burn fee)</label>
                    <input
                      type="number"
                      step="0.01"
                      value={transferData.amount}
                      onChange={e => setTransferData({...transferData, amount: e.target.value})}
                      required
                      className="w-full bg-black/50 border border-white/20 px-4 py-2 text-white"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-white/50 mb-1 block">Reason (optional)</label>
                    <input
                      type="text"
                      value={transferData.reason}
                      onChange={e => setTransferData({...transferData, reason: e.target.value})}
                      className="w-full bg-black/50 border border-white/20 px-4 py-2 text-white"
                    />
                  </div>
                  <div className="flex gap-3">
                    <CyberButton type="submit" className="flex-1">{t('transfer')}</CyberButton>
                    <CyberButton type="button" variant="ghost" onClick={() => setShowTransfer(false)}>{t('cancel')}</CyberButton>
                  </div>
                </form>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
};

// Leaderboard Page
const LeaderboardPage = () => {
  const { user } = useAuth();
  const t = useTranslation();
  const [leaderboard, setLeaderboard] = useState([]);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    axios.get(`${API}/leaderboard`).then(res => setLeaderboard(res.data.leaderboard || [])).catch(console.error).finally(() => setLoading(false));
  }, []);
  
  const roleColors = { creator: '#E040FB', contributor: '#00FF88', evaluator: '#40C4FF', partner: '#FF6B35', citizen: '#00F0FF' };
  
  return (
    <div className="min-h-screen pt-20 pb-12 px-4" data-testid="leaderboard-page">
      <div className="max-w-4xl mx-auto">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
          <h1 className="text-3xl md:text-4xl font-orbitron font-black">
            {t('leaderboard')} <span className="text-neon-yellow">RANKINGS</span>
          </h1>
        </motion.div>
        
        {loading ? (
          <div className="text-center text-white/50">{t('loading')}</div>
        ) : (
          <div className="space-y-3">
            {leaderboard.map((entry, i) => (
              <CyberCard 
                key={entry.id}
                className={entry.id === user?.id ? 'border-neon-cyan' : ''}
              >
                <div className="flex items-center gap-4">
                  <div className={`w-12 h-12 flex items-center justify-center font-orbitron font-black text-xl ${
                    i === 0 ? 'bg-yellow-500/20 text-yellow-400' :
                    i === 1 ? 'bg-gray-400/20 text-gray-300' :
                    i === 2 ? 'bg-orange-600/20 text-orange-400' :
                    'bg-white/5 text-white/50'
                  }`}>
                    #{entry.rank}
                  </div>
                  
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-mono font-bold">{entry.username}</span>
                      {entry.id === user?.id && <span className="text-xs text-neon-cyan">(YOU)</span>}
                      <span 
                        className="text-xs px-1 border"
                        style={{ borderColor: roleColors[entry.role], color: roleColors[entry.role] }}
                      >
                        {entry.role}
                      </span>
                    </div>
                    <div className="text-xs text-white/50">
                      Level {entry.level} • {entry.badges_count} badges
                    </div>
                  </div>
                  
                  <div className="text-right">
                    <div className="font-mono text-neon-purple">{entry.xp} XP</div>
                    <div className="text-xs text-neon-cyan">{entry.realum_balance?.toFixed(0)} RLM</div>
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

// Profile Page
const ProfilePage = () => {
  const { user } = useAuth();
  const t = useTranslation();
  const [badges, setBadges] = useState([]);
  
  useEffect(() => {
    axios.get(`${API}/badges`).then(res => setBadges(res.data.badges || [])).catch(console.error);
  }, []);
  
  const rarityColors = { common: '#9CA3AF', uncommon: '#10B981', rare: '#3B82F6', epic: '#8B5CF6', legendary: '#F59E0B' };
  
  return (
    <div className="min-h-screen pt-20 pb-12 px-4" data-testid="profile-page">
      <div className="max-w-4xl mx-auto">
        <CyberCard glow className="mb-6">
          <div className="flex items-center gap-6">
            <div className="w-20 h-20 bg-neon-cyan/10 border-2 border-neon-cyan flex items-center justify-center">
              <User className="w-10 h-10 text-neon-cyan" />
            </div>
            <div>
              <h1 className="text-2xl font-orbitron font-bold">{user?.username}</h1>
              <p className="text-white/50">{user?.email}</p>
              <p className="text-xs text-white/40 mt-1">Role: {user?.role} • Member since {new Date(user?.created_at).toLocaleDateString()}</p>
            </div>
          </div>
          
          <div className="grid grid-cols-4 gap-4 mt-6">
            <div className="text-center p-3 bg-black/30 border border-white/10">
              <div className="text-2xl font-orbitron font-bold text-neon-cyan">{user?.realum_balance?.toFixed(0)}</div>
              <div className="text-xs text-white/50">RLM</div>
            </div>
            <div className="text-center p-3 bg-black/30 border border-white/10">
              <div className="text-2xl font-orbitron font-bold text-neon-yellow">{user?.level}</div>
              <div className="text-xs text-white/50">{t('level')}</div>
            </div>
            <div className="text-center p-3 bg-black/30 border border-white/10">
              <div className="text-2xl font-orbitron font-bold text-neon-purple">{user?.xp}</div>
              <div className="text-xs text-white/50">{t('xp')}</div>
            </div>
            <div className="text-center p-3 bg-black/30 border border-white/10">
              <div className="text-2xl font-orbitron font-bold text-neon-green">{user?.badges?.length || 0}</div>
              <div className="text-xs text-white/50">{t('badges')}</div>
            </div>
          </div>
        </CyberCard>
        
        {/* Skills */}
        {user?.skills?.length > 0 && (
          <CyberCard className="mb-6">
            <h3 className="font-orbitron font-bold mb-4">Skills</h3>
            <div className="flex flex-wrap gap-2">
              {user.skills.map(skill => (
                <span key={skill} className="px-3 py-1 text-sm bg-neon-purple/10 border border-neon-purple/30 text-neon-purple">
                  {skill}
                </span>
              ))}
            </div>
          </CyberCard>
        )}
        
        {/* Badges Collection */}
        <CyberCard>
          <h3 className="font-orbitron font-bold mb-4">Badges Collection</h3>
          <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 gap-3">
            {badges.map(badge => {
              const earned = user?.badges?.includes(badge.id);
              return (
                <div 
                  key={badge.id}
                  className={`p-3 border text-center transition-all ${
                    earned ? 'bg-white/5 border-white/30' : 'opacity-30 border-white/10'
                  }`}
                  title={badge.description}
                >
                  <div className="text-2xl mb-1">{badge.icon}</div>
                  <div className="text-xs font-mono truncate">{badge.name}</div>
                  <div className="text-[10px]" style={{ color: rarityColors[badge.rarity] }}>{badge.rarity}</div>
                </div>
              );
            })}
          </div>
        </CyberCard>
      </div>
    </div>
  );
};

// Simulation Page (Andreea, Vlad, Sorin)
const SimulationPage = () => {
  const t = useTranslation();
  const [status, setStatus] = useState(null);
  const [stepResult, setStepResult] = useState(null);
  const [loading, setLoading] = useState(false);
  
  const setupSimulation = async () => {
    setLoading(true);
    try {
      const res = await axios.post(`${API}/simulation/setup`);
      setStatus(res.data);
      setStepResult(null);
    } catch (err) {
      alert('Setup failed');
    } finally {
      setLoading(false);
    }
  };
  
  const runStep = async (step) => {
    setLoading(true);
    try {
      const res = await axios.post(`${API}/simulation/step/${step}`);
      setStepResult(res.data);
      // Refresh status
      const statusRes = await axios.get(`${API}/simulation/status`);
      setStatus(statusRes.data);
    } catch (err) {
      alert(err.response?.data?.detail || 'Step failed');
    } finally {
      setLoading(false);
    }
  };
  
  useEffect(() => {
    axios.get(`${API}/simulation/status`).then(res => setStatus(res.data)).catch(() => {});
  }, []);
  
  const roleColors = { creator: '#E040FB', contributor: '#00FF88', evaluator: '#40C4FF' };
  
  return (
    <div className="min-h-screen pt-20 pb-12 px-4" data-testid="simulation-page">
      <div className="max-w-4xl mx-auto">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
          <h1 className="text-3xl md:text-4xl font-orbitron font-black">
            TOKEN <span className="text-neon-cyan">SIMULATION</span>
          </h1>
          <p className="text-white/60 mt-2">Watch RLM tokens flow between Andreea, Vlad, and Sorin</p>
        </motion.div>
        
        {status?.status === 'not_initialized' ? (
          <CyberCard className="text-center py-12">
            <p className="text-white/60 mb-6">Set up the simulation to create 3 demo users</p>
            <CyberButton onClick={setupSimulation} disabled={loading}>
              {loading ? 'Setting up...' : 'Initialize Simulation'}
            </CyberButton>
          </CyberCard>
        ) : (
          <>
            {/* User Cards */}
            <div className="grid md:grid-cols-3 gap-4 mb-8">
              {status?.users && Object.entries(status.users).map(([name, data]) => (
                <CyberCard key={name} className="text-center">
                  <div 
                    className="w-16 h-16 mx-auto mb-3 rounded-full border-2 flex items-center justify-center"
                    style={{ borderColor: roleColors[data.role] || '#00F0FF' }}
                  >
                    <span className="text-2xl">{name === 'andreea' ? '👩‍🎨' : name === 'vlad' ? '👨‍💻' : '👨‍🏫'}</span>
                  </div>
                  <h3 className="font-orbitron font-bold capitalize">{name}</h3>
                  <p className="text-xs uppercase" style={{ color: roleColors[data.role] }}>{data.role}</p>
                  <div className="mt-4 space-y-2">
                    <div className="flex justify-between text-sm">
                      <span className="text-white/50">Balance</span>
                      <span className="text-neon-cyan font-mono">{data.balance?.toFixed(2)} RLM</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-white/50">XP</span>
                      <span className="text-neon-purple font-mono">{data.xp}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-white/50">Transactions</span>
                      <span className="font-mono">{data.transactions}</span>
                    </div>
                  </div>
                </CyberCard>
              ))}
            </div>
            
            {/* Simulation Steps */}
            <CyberCard className="mb-6">
              <h3 className="font-orbitron font-bold mb-4">Simulation Steps</h3>
              <div className="space-y-4">
                <div className="flex items-center gap-4 p-4 bg-black/30 border border-white/10">
                  <div className="w-10 h-10 bg-neon-cyan/10 border border-neon-cyan/30 flex items-center justify-center font-bold">1</div>
                  <div className="flex-1">
                    <div className="font-mono">Vlad purchases Andreea's UI Design</div>
                    <div className="text-xs text-white/50">150 RLM transfer (2% burned)</div>
                  </div>
                  <CyberButton onClick={() => runStep(1)} disabled={loading}>Run</CyberButton>
                </div>
                
                <div className="flex items-center gap-4 p-4 bg-black/30 border border-white/10">
                  <div className="w-10 h-10 bg-neon-green/10 border border-neon-green/30 flex items-center justify-center font-bold">2</div>
                  <div className="flex-1">
                    <div className="font-mono">Vlad completes a task using the design</div>
                    <div className="text-xs text-white/50">Earns 100 RLM + 50 XP</div>
                  </div>
                  <CyberButton variant="success" onClick={() => runStep(2)} disabled={loading}>Run</CyberButton>
                </div>
                
                <div className="flex items-center gap-4 p-4 bg-black/30 border border-white/10">
                  <div className="w-10 h-10 bg-neon-purple/10 border border-neon-purple/30 flex items-center justify-center font-bold">3</div>
                  <div className="flex-1">
                    <div className="font-mono">Sorin validates Vlad's work</div>
                    <div className="text-xs text-white/50">Earns 25 RLM + 15 XP for validation</div>
                  </div>
                  <CyberButton onClick={() => runStep(3)} disabled={loading}>Run</CyberButton>
                </div>
              </div>
            </CyberCard>
            
            {/* Step Result */}
            {stepResult && (
              <CyberCard glow>
                <h3 className="font-orbitron font-bold mb-4 text-neon-green">
                  <CheckCircle className="w-5 h-5 inline mr-2" />
                  Step {stepResult.step} Complete
                </h3>
                <pre className="text-sm text-white/70 overflow-x-auto">
                  {JSON.stringify(stepResult, null, 2)}
                </pre>
              </CyberCard>
            )}
            
            {/* Reset Button */}
            <div className="text-center mt-6">
              <CyberButton variant="ghost" onClick={setupSimulation} disabled={loading}>
                Reset Simulation
              </CyberButton>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

// Projects Page
const ProjectsPage = () => {
  const { user } = useAuth();
  const t = useTranslation();
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    axios.get(`${API}/projects`).then(res => setProjects(res.data.projects || [])).catch(console.error).finally(() => setLoading(false));
  }, []);
  
  const joinProject = async (projectId) => {
    try {
      await axios.post(`${API}/projects/${projectId}/join`);
      alert('Joined project!');
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to join');
    }
  };
  
  const categoryColors = { tech: '#FF003C', creative: '#E040FB', education: '#9D4EDD', commerce: '#FF6B35' };
  
  return (
    <div className="min-h-screen pt-20 pb-12 px-4" data-testid="projects-page">
      <div className="max-w-6xl mx-auto">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
          <h1 className="text-3xl md:text-4xl font-orbitron font-black">
            {t('projects')} <span className="text-neon-green">HUB</span>
          </h1>
          <p className="text-white/60 mt-2">Collaborate on community projects and earn rewards</p>
        </motion.div>
        
        {loading ? (
          <div className="text-center text-white/50">{t('loading')}</div>
        ) : (
          <div className="grid md:grid-cols-2 gap-6">
            {projects.map(project => (
              <CyberCard key={project.id}>
                <div className="flex items-start justify-between mb-3">
                  <span 
                    className="px-2 py-1 text-xs border"
                    style={{ borderColor: categoryColors[project.category], color: categoryColors[project.category] }}
                  >
                    {project.category}
                  </span>
                  <span className={`text-xs ${project.status === 'active' ? 'text-neon-green' : 'text-white/50'}`}>
                    {project.status}
                  </span>
                </div>
                
                <h4 className="font-orbitron font-bold mb-2">{project.title}</h4>
                <p className="text-sm text-white/70 mb-4">{project.description}</p>
                
                <div className="flex items-center gap-4 mb-4 text-xs text-white/50">
                  <span>By {project.creator_name}</span>
                  <span>Budget: {project.budget_rlm} RLM</span>
                  <span>{project.tasks?.length || 0} tasks</span>
                </div>
                
                {/* Progress */}
                <div className="mb-4">
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-white/50">Progress</span>
                    <span className="text-neon-green">{project.progress}%</span>
                  </div>
                  <div className="h-2 bg-white/10">
                    <div 
                      className="h-full bg-neon-green transition-all"
                      style={{ width: `${project.progress}%` }}
                    />
                  </div>
                </div>
                
                <CyberButton className="w-full" onClick={() => joinProject(project.id)}>
                  {t('join')} Project
                </CyberButton>
              </CyberCard>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

// ==================== MAIN APP ====================
function App() {
  return (
    <BrowserRouter>
      <LanguageProvider>
        <AuthProvider>
          <ConfettiProvider>
            <div className="min-h-screen bg-black text-white">
              <Routes>
                <Route path="/" element={<LandingPage />} />
                <Route path="/login" element={<LoginPage />} />
                <Route path="/register" element={<RegisterPage />} />
                <Route path="/dashboard" element={<ProtectedRoute><Navbar /><DashboardPage /></ProtectedRoute>} />
                <Route path="/metaverse" element={<ProtectedRoute><Navbar /><MetaversePage /></ProtectedRoute>} />
                <Route path="/jobs" element={<ProtectedRoute><Navbar /><JobsPage /></ProtectedRoute>} />
                <Route path="/courses" element={<ProtectedRoute><Navbar /><CoursesPage /></ProtectedRoute>} />
                <Route path="/marketplace" element={<ProtectedRoute><Navbar /><MarketplacePage /></ProtectedRoute>} />
                <Route path="/voting" element={<ProtectedRoute><Navbar /><VotingPage /></ProtectedRoute>} />
                <Route path="/wallet" element={<ProtectedRoute><Navbar /><WalletPage /></ProtectedRoute>} />
                <Route path="/leaderboard" element={<ProtectedRoute><Navbar /><LeaderboardPage /></ProtectedRoute>} />
                <Route path="/profile" element={<ProtectedRoute><Navbar /><ProfilePage /></ProtectedRoute>} />
                <Route path="/projects" element={<ProtectedRoute><Navbar /><ProjectsPage /></ProtectedRoute>} />
                <Route path="/simulation" element={<ProtectedRoute><Navbar /><SimulationPage /></ProtectedRoute>} />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </div>
          </ConfettiProvider>
        </AuthProvider>
      </LanguageProvider>
    </BrowserRouter>
  );
}

export default App;
