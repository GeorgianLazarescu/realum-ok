import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import "@/App.css";
import "@/index.css";
import { BrowserRouter, Routes, Route, Navigate, Link, useNavigate, useLocation } from "react-router-dom";
import axios from "axios";
import { motion, AnimatePresence } from "framer-motion";
import { 
  Home, User, Briefcase, Vote, Wallet, Trophy, Map, LogOut, 
  Menu, X, ChevronRight, Zap, Star, Shield, Coins, TrendingUp,
  Users, Building2, Globe, ArrowRight, Play, Check, Clock, Award
} from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// ==================== AUTH CONTEXT ====================
const AuthContext = createContext(null);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within AuthProvider");
  return context;
};

const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem("token"));
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const initAuth = async () => {
      if (token) {
        try {
          const res = await axios.get(`${API}/auth/me`, {
            headers: { Authorization: `Bearer ${token}` }
          });
          setUser(res.data);
        } catch (e) {
          localStorage.removeItem("token");
          setToken(null);
        }
      }
      setLoading(false);
    };
    initAuth();
  }, [token]);

  const login = async (email, password) => {
    const res = await axios.post(`${API}/auth/login`, { email, password });
    localStorage.setItem("token", res.data.access_token);
    setToken(res.data.access_token);
    setUser(res.data.user);
    return res.data;
  };

  const register = async (email, password, username, role) => {
    const res = await axios.post(`${API}/auth/register`, { email, password, username, role });
    localStorage.setItem("token", res.data.access_token);
    setToken(res.data.access_token);
    setUser(res.data.user);
    return res.data;
  };

  const logout = () => {
    localStorage.removeItem("token");
    setToken(null);
    setUser(null);
  };

  const refreshUser = async () => {
    if (token) {
      const res = await axios.get(`${API}/auth/me`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setUser(res.data);
    }
  };

  return (
    <AuthContext.Provider value={{ user, token, loading, login, register, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
};

// ==================== WEB3 CONTEXT ====================
const Web3Context = createContext(null);

export const useWeb3 = () => {
  const context = useContext(Web3Context);
  if (!context) throw new Error("useWeb3 must be used within Web3Provider");
  return context;
};

const Web3Provider = ({ children }) => {
  const [account, setAccount] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState(null);
  const { token, refreshUser } = useAuth();

  const connectWallet = useCallback(async () => {
    try {
      setError(null);
      if (!window.ethereum) {
        throw new Error("MetaMask is not installed. Please install MetaMask to connect your wallet.");
      }

      const accounts = await window.ethereum.request({ method: "eth_requestAccounts" });
      if (accounts.length === 0) throw new Error("No accounts found");

      const walletAddress = accounts[0];
      setAccount(walletAddress);
      setIsConnected(true);

      // Connect to backend
      if (token) {
        await axios.post(`${API}/wallet/connect`, 
          { wallet_address: walletAddress },
          { headers: { Authorization: `Bearer ${token}` } }
        );
        await refreshUser();
      }
    } catch (err) {
      setError(err.message);
      setIsConnected(false);
    }
  }, [token, refreshUser]);

  const disconnectWallet = () => {
    setAccount(null);
    setIsConnected(false);
    setError(null);
  };

  useEffect(() => {
    if (window.ethereum) {
      window.ethereum.on("accountsChanged", (accounts) => {
        if (accounts.length === 0) disconnectWallet();
        else setAccount(accounts[0]);
      });
    }
  }, []);

  return (
    <Web3Context.Provider value={{ account, isConnected, error, connectWallet, disconnectWallet }}>
      {children}
    </Web3Context.Provider>
  );
};

// ==================== COMPONENTS ====================

const CyberButton = ({ children, variant = "primary", className = "", ...props }) => {
  const baseStyles = "relative overflow-hidden px-6 py-3 font-bold uppercase tracking-widest transition-all duration-300 disabled:opacity-50";
  const variants = {
    primary: "bg-neon-cyan text-black hover:shadow-[0_0_30px_rgba(0,240,255,0.5)]",
    secondary: "border border-neon-cyan/50 text-neon-cyan hover:bg-neon-cyan/10",
    danger: "bg-neon-red text-white hover:shadow-[0_0_30px_rgba(255,0,60,0.5)]"
  };
  
  return (
    <button 
      className={`${baseStyles} ${variants[variant]} ${className}`}
      style={{ clipPath: "polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 10px 100%, 0 calc(100% - 10px))" }}
      {...props}
    >
      {children}
    </button>
  );
};

const CyberCard = ({ children, className = "", glow = false, ...props }) => (
  <div 
    className={`relative bg-card border border-border p-6 transition-all duration-300 hover:border-primary/50 ${glow ? "neon-glow" : ""} ${className}`}
    {...props}
  >
    <div className="absolute top-0 left-0 w-4 h-4 border-t-2 border-l-2 border-neon-cyan" />
    <div className="absolute bottom-0 right-0 w-4 h-4 border-b-2 border-r-2 border-neon-cyan" />
    {children}
  </div>
);

const StatBox = ({ icon: Icon, label, value, color = "cyan" }) => {
  const colors = {
    cyan: "text-neon-cyan border-neon-cyan/30",
    red: "text-neon-red border-neon-red/30",
    yellow: "text-neon-yellow border-neon-yellow/30",
    green: "text-neon-green border-neon-green/30",
    purple: "text-neon-purple border-neon-purple/30"
  };
  
  return (
    <div className={`border ${colors[color]} bg-black/50 p-4`}>
      <div className="flex items-center gap-2 mb-2">
        <Icon className={`w-5 h-5 ${colors[color].split(" ")[0]}`} />
        <span className="text-xs uppercase tracking-wider text-muted-foreground">{label}</span>
      </div>
      <div className={`text-2xl font-orbitron font-bold ${colors[color].split(" ")[0]}`}>{value}</div>
    </div>
  );
};

const Badge = ({ name, icon, rarity }) => {
  const rarityColors = {
    common: "border-gray-500 text-gray-400",
    uncommon: "border-neon-green text-neon-green",
    rare: "border-neon-cyan text-neon-cyan",
    legendary: "border-neon-yellow text-neon-yellow"
  };
  
  return (
    <div className={`flex items-center gap-2 px-3 py-2 border ${rarityColors[rarity] || rarityColors.common} bg-black/50`}>
      <span className="text-lg">{icon}</span>
      <span className="text-sm font-mono uppercase">{name}</span>
    </div>
  );
};

const ProgressBar = ({ value, max, label }) => {
  const percentage = Math.min((value / max) * 100, 100);
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs text-muted-foreground">
        <span>{label}</span>
        <span>{value} / {max}</span>
      </div>
      <div className="h-2 bg-muted overflow-hidden">
        <motion.div 
          className="h-full bg-gradient-to-r from-neon-cyan to-neon-purple"
          initial={{ width: 0 }}
          animate={{ width: `${percentage}%` }}
          transition={{ duration: 1, ease: "easeOut" }}
        />
      </div>
    </div>
  );
};

// ==================== NAVIGATION ====================

const Navbar = () => {
  const { user, logout } = useAuth();
  const { isConnected, account, connectWallet } = useWeb3();
  const [mobileOpen, setMobileOpen] = useState(false);
  const location = useLocation();

  const navItems = [
    { path: "/dashboard", icon: Home, label: "Dashboard" },
    { path: "/city", icon: Map, label: "City" },
    { path: "/jobs", icon: Briefcase, label: "Jobs" },
    { path: "/voting", icon: Vote, label: "DAO" },
    { path: "/wallet", icon: Wallet, label: "Wallet" },
    { path: "/leaderboard", icon: Trophy, label: "Ranks" },
    { path: "/profile", icon: User, label: "Profile" },
  ];

  if (!user) return null;

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 glass border-b border-white/10">
      <div className="max-w-7xl mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link to="/dashboard" className="flex items-center gap-2">
            <div className="w-8 h-8 bg-neon-cyan flex items-center justify-center">
              <Globe className="w-5 h-5 text-black" />
            </div>
            <span className="font-orbitron font-bold text-xl tracking-wider neon-text">REALUM</span>
          </Link>

          {/* Desktop Nav */}
          <div className="hidden md:flex items-center gap-1">
            {navItems.map(({ path, icon: Icon, label }) => (
              <Link
                key={path}
                to={path}
                className={`flex items-center gap-2 px-3 py-2 text-sm font-mono uppercase tracking-wider transition-colors ${
                  location.pathname === path 
                    ? "text-neon-cyan bg-neon-cyan/10" 
                    : "text-muted-foreground hover:text-white"
                }`}
              >
                <Icon className="w-4 h-4" />
                {label}
              </Link>
            ))}
          </div>

          {/* Right Side */}
          <div className="flex items-center gap-4">
            {/* Wallet */}
            {isConnected ? (
              <div className="hidden sm:flex items-center gap-2 px-3 py-1 border border-neon-green/50 bg-neon-green/10">
                <div className="w-2 h-2 bg-neon-green rounded-full animate-pulse" />
                <span className="text-xs font-mono text-neon-green">
                  {account?.slice(0, 6)}...{account?.slice(-4)}
                </span>
              </div>
            ) : (
              <button
                onClick={connectWallet}
                className="hidden sm:flex items-center gap-2 px-3 py-1 border border-neon-cyan/50 text-neon-cyan text-xs font-mono uppercase hover:bg-neon-cyan/10 transition-colors"
              >
                Connect Wallet
              </button>
            )}

            {/* User Info */}
            <div className="hidden sm:flex items-center gap-2">
              <div className="text-right">
                <div className="text-sm font-mono">{user.username}</div>
                <div className="text-xs text-neon-cyan">{user.realum_balance?.toFixed(0)} RLM</div>
              </div>
              <div className="w-10 h-10 border-2 border-neon-cyan flex items-center justify-center font-orbitron font-bold text-neon-cyan">
                {user.level}
              </div>
            </div>

            {/* Logout */}
            <button onClick={logout} className="p-2 text-muted-foreground hover:text-neon-red transition-colors">
              <LogOut className="w-5 h-5" />
            </button>

            {/* Mobile Menu Button */}
            <button onClick={() => setMobileOpen(!mobileOpen)} className="md:hidden p-2">
              {mobileOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
          </div>
        </div>

        {/* Mobile Nav */}
        <AnimatePresence>
          {mobileOpen && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="md:hidden border-t border-white/10 overflow-hidden"
            >
              <div className="py-4 space-y-2">
                {navItems.map(({ path, icon: Icon, label }) => (
                  <Link
                    key={path}
                    to={path}
                    onClick={() => setMobileOpen(false)}
                    className={`flex items-center gap-3 px-4 py-3 ${
                      location.pathname === path 
                        ? "text-neon-cyan bg-neon-cyan/10" 
                        : "text-muted-foreground"
                    }`}
                  >
                    <Icon className="w-5 h-5" />
                    {label}
                  </Link>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </nav>
  );
};

// ==================== PAGES ====================

const LandingPage = () => {
  const navigate = useNavigate();
  const { user } = useAuth();

  useEffect(() => {
    if (user) navigate("/dashboard");
  }, [user, navigate]);

  return (
    <div className="min-h-screen bg-background overflow-hidden">
      {/* Hero Section */}
      <section className="relative min-h-screen flex items-center justify-center px-4">
        {/* Background Effects */}
        <div className="absolute inset-0 bg-cyber-grid bg-[length:50px_50px] opacity-30" />
        <div className="absolute inset-0 bg-hero-glow" />
        
        {/* Animated Lines */}
        <div className="absolute top-0 left-1/4 w-px h-full bg-gradient-to-b from-transparent via-neon-cyan/20 to-transparent" />
        <div className="absolute top-0 right-1/4 w-px h-full bg-gradient-to-b from-transparent via-neon-red/20 to-transparent" />

        <div className="relative z-10 max-w-5xl mx-auto text-center">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
          >
            {/* Badge */}
            <div className="inline-flex items-center gap-2 px-4 py-2 border border-neon-cyan/30 bg-neon-cyan/5 mb-8">
              <span className="w-2 h-2 bg-neon-cyan rounded-full animate-pulse" />
              <span className="text-sm font-mono uppercase tracking-wider text-neon-cyan">Web3 Simulation Platform</span>
            </div>

            {/* Title */}
            <h1 className="text-5xl md:text-8xl font-orbitron font-black mb-6 tracking-tighter">
              <span className="text-white">WELCOME TO</span>
              <br />
              <span className="neon-text">REALUM</span>
            </h1>

            {/* Subtitle */}
            <p className="text-xl md:text-2xl text-muted-foreground max-w-2xl mx-auto mb-12 font-rajdhani">
              Experience a fully functional digital society. Work, vote, invest, and build 
              your legacy in the most advanced socio-economic simulation.
            </p>

            {/* CTAs */}
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <CyberButton onClick={() => navigate("/register")} data-testid="hero-cta-register">
                <span className="flex items-center gap-2">
                  Enter REALUM <ArrowRight className="w-5 h-5" />
                </span>
              </CyberButton>
              <CyberButton variant="secondary" onClick={() => navigate("/login")} data-testid="hero-cta-login">
                Connect
              </CyberButton>
            </div>
          </motion.div>

          {/* Stats */}
          <motion.div
            initial={{ opacity: 0, y: 50 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.3 }}
            className="mt-20 grid grid-cols-2 md:grid-cols-4 gap-4"
          >
            {[
              { label: "Total Supply", value: "1B RLM" },
              { label: "Active Citizens", value: "10K+" },
              { label: "Jobs Available", value: "500+" },
              { label: "DAO Proposals", value: "150+" },
            ].map((stat, i) => (
              <div key={i} className="border border-white/10 bg-black/50 p-4">
                <div className="text-2xl md:text-3xl font-orbitron font-bold text-white">{stat.value}</div>
                <div className="text-xs uppercase tracking-wider text-muted-foreground">{stat.label}</div>
              </div>
            ))}
          </motion.div>
        </div>

        {/* Scroll Indicator */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1 }}
          className="absolute bottom-8 left-1/2 -translate-x-1/2"
        >
          <div className="w-6 h-10 border-2 border-neon-cyan/50 rounded-full flex justify-center pt-2">
            <motion.div
              animate={{ y: [0, 8, 0] }}
              transition={{ duration: 1.5, repeat: Infinity }}
              className="w-1 h-2 bg-neon-cyan rounded-full"
            />
          </div>
        </motion.div>
      </section>

      {/* Features Section */}
      <section className="py-24 px-4 relative">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-4xl md:text-5xl font-orbitron font-black text-center mb-16">
            <span className="text-white">BUILD YOUR</span>{" "}
            <span className="text-neon-red">DIGITAL LEGACY</span>
          </h2>

          <div className="grid md:grid-cols-3 gap-6">
            {[
              { icon: Briefcase, title: "Work & Earn", desc: "Take on jobs across the city, complete tasks, and earn REALUM Coin.", color: "cyan" },
              { icon: Vote, title: "DAO Governance", desc: "Vote on proposals, shape the future, and participate in democracy.", color: "purple" },
              { icon: TrendingUp, title: "Level Up", desc: "Gain XP, unlock badges, and climb the leaderboard rankings.", color: "green" },
              { icon: Building2, title: "Explore City", desc: "Navigate through different zones - Tech, Industrial, Education & more.", color: "yellow" },
              { icon: Wallet, title: "Web3 Wallet", desc: "Connect MetaMask, manage your REALUM Coin balance, and transfer.", color: "red" },
              { icon: Users, title: "Community", desc: "Join a thriving digital society with citizens and entrepreneurs.", color: "orange" },
            ].map((feature, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1 }}
              >
                <CyberCard className="h-full">
                  <feature.icon className={`w-10 h-10 mb-4 text-neon-${feature.color}`} />
                  <h3 className="text-xl font-orbitron font-bold mb-2">{feature.title}</h3>
                  <p className="text-muted-foreground">{feature.desc}</p>
                </CyberCard>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-24 px-4 border-t border-white/10">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-4xl md:text-5xl font-orbitron font-black mb-6">
            READY TO <span className="text-neon-cyan neon-text">ENTER?</span>
          </h2>
          <p className="text-xl text-muted-foreground mb-8">
            Join thousands of citizens building the future of digital society.
          </p>
          <CyberButton onClick={() => navigate("/register")} className="text-lg px-8 py-4">
            Create Your Citizen ID
          </CyberButton>
        </div>
      </section>
    </div>
  );
};

const LoginPage = () => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password);
      navigate("/dashboard");
    } catch (err) {
      setError(err.response?.data?.detail || "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4 bg-background">
      <div className="absolute inset-0 bg-cyber-grid bg-[length:50px_50px] opacity-20" />
      
      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        className="relative z-10 w-full max-w-md"
      >
        <CyberCard glow>
          <div className="text-center mb-8">
            <Link to="/" className="inline-flex items-center gap-2 mb-4">
              <div className="w-8 h-8 bg-neon-cyan flex items-center justify-center">
                <Globe className="w-5 h-5 text-black" />
              </div>
              <span className="font-orbitron font-bold text-xl neon-text">REALUM</span>
            </Link>
            <h1 className="text-2xl font-orbitron font-bold">ACCESS TERMINAL</h1>
            <p className="text-muted-foreground mt-2">Enter your credentials</p>
          </div>

          {error && (
            <div className="mb-4 p-3 border border-neon-red/50 bg-neon-red/10 text-neon-red text-sm">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs uppercase tracking-wider text-muted-foreground mb-2">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full bg-black/50 border border-white/20 px-4 py-3 font-mono text-sm focus:border-neon-cyan focus:outline-none transition-colors"
                placeholder="citizen@realum.io"
                required
                data-testid="login-email"
              />
            </div>
            <div>
              <label className="block text-xs uppercase tracking-wider text-muted-foreground mb-2">Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-black/50 border border-white/20 px-4 py-3 font-mono text-sm focus:border-neon-cyan focus:outline-none transition-colors"
                placeholder="••••••••"
                required
                data-testid="login-password"
              />
            </div>
            <CyberButton type="submit" disabled={loading} className="w-full" data-testid="login-submit">
              {loading ? "Authenticating..." : "Login"}
            </CyberButton>
          </form>

          <div className="mt-6 text-center text-sm text-muted-foreground">
            No citizen ID?{" "}
            <Link to="/register" className="text-neon-cyan hover:underline">Register here</Link>
          </div>
        </CyberCard>
      </motion.div>
    </div>
  );
};

const RegisterPage = () => {
  const [formData, setFormData] = useState({ email: "", password: "", username: "", role: "citizen" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { register } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await register(formData.email, formData.password, formData.username, formData.role);
      navigate("/dashboard");
    } catch (err) {
      setError(err.response?.data?.detail || "Registration failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-12 bg-background">
      <div className="absolute inset-0 bg-cyber-grid bg-[length:50px_50px] opacity-20" />
      
      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        className="relative z-10 w-full max-w-md"
      >
        <CyberCard glow>
          <div className="text-center mb-8">
            <Link to="/" className="inline-flex items-center gap-2 mb-4">
              <div className="w-8 h-8 bg-neon-cyan flex items-center justify-center">
                <Globe className="w-5 h-5 text-black" />
              </div>
              <span className="font-orbitron font-bold text-xl neon-text">REALUM</span>
            </Link>
            <h1 className="text-2xl font-orbitron font-bold">CREATE CITIZEN ID</h1>
            <p className="text-muted-foreground mt-2">Join the digital society</p>
          </div>

          {error && (
            <div className="mb-4 p-3 border border-neon-red/50 bg-neon-red/10 text-neon-red text-sm">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs uppercase tracking-wider text-muted-foreground mb-2">Username</label>
              <input
                type="text"
                value={formData.username}
                onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                className="w-full bg-black/50 border border-white/20 px-4 py-3 font-mono text-sm focus:border-neon-cyan focus:outline-none transition-colors"
                placeholder="neo_citizen"
                required
                data-testid="register-username"
              />
            </div>
            <div>
              <label className="block text-xs uppercase tracking-wider text-muted-foreground mb-2">Email</label>
              <input
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                className="w-full bg-black/50 border border-white/20 px-4 py-3 font-mono text-sm focus:border-neon-cyan focus:outline-none transition-colors"
                placeholder="citizen@realum.io"
                required
                data-testid="register-email"
              />
            </div>
            <div>
              <label className="block text-xs uppercase tracking-wider text-muted-foreground mb-2">Password</label>
              <input
                type="password"
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                className="w-full bg-black/50 border border-white/20 px-4 py-3 font-mono text-sm focus:border-neon-cyan focus:outline-none transition-colors"
                placeholder="••••••••"
                required
                minLength={6}
                data-testid="register-password"
              />
            </div>
            <div>
              <label className="block text-xs uppercase tracking-wider text-muted-foreground mb-2">Role</label>
              <div className="grid grid-cols-2 gap-2">
                {[
                  { value: "citizen", label: "Citizen", icon: User },
                  { value: "entrepreneur", label: "Entrepreneur", icon: Briefcase }
                ].map(({ value, label, icon: Icon }) => (
                  <button
                    key={value}
                    type="button"
                    onClick={() => setFormData({ ...formData, role: value })}
                    className={`flex items-center justify-center gap-2 p-3 border transition-colors ${
                      formData.role === value 
                        ? "border-neon-cyan bg-neon-cyan/10 text-neon-cyan" 
                        : "border-white/20 text-muted-foreground hover:border-white/40"
                    }`}
                    data-testid={`register-role-${value}`}
                  >
                    <Icon className="w-4 h-4" />
                    <span className="text-sm font-mono uppercase">{label}</span>
                  </button>
                ))}
              </div>
            </div>
            <CyberButton type="submit" disabled={loading} className="w-full" data-testid="register-submit">
              {loading ? "Creating..." : "Create Citizen ID"}
            </CyberButton>
          </form>

          <div className="mt-6 text-center text-sm text-muted-foreground">
            Already a citizen?{" "}
            <Link to="/login" className="text-neon-cyan hover:underline">Login here</Link>
          </div>
        </CyberCard>
      </motion.div>
    </div>
  );
};

const DashboardPage = () => {
  const { user, token, refreshUser } = useAuth();
  const [stats, setStats] = useState(null);
  const [badges, setBadges] = useState([]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [statsRes, badgesRes] = await Promise.all([
          axios.get(`${API}/stats/platform`),
          axios.get(`${API}/badges`)
        ]);
        setStats(statsRes.data);
        setBadges(badgesRes.data.badges);
      } catch (e) {
        console.error(e);
      }
    };
    fetchData();
  }, []);

  const xpForNextLevel = [0, 100, 300, 600, 1000, 1500, 2100, 2800, 3600, 4500, 5500];
  const currentLevelXp = xpForNextLevel[user?.level - 1] || 0;
  const nextLevelXp = xpForNextLevel[user?.level] || xpForNextLevel[xpForNextLevel.length - 1];
  const xpProgress = user?.xp - currentLevelXp;
  const xpNeeded = nextLevelXp - currentLevelXp;

  const userBadges = badges.filter(b => user?.badges?.includes(b.id));

  return (
    <div className="min-h-screen pt-20 pb-12 px-4" data-testid="dashboard-page">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <h1 className="text-3xl md:text-4xl font-orbitron font-black">
            WELCOME, <span className="text-neon-cyan neon-text">{user?.username?.toUpperCase()}</span>
          </h1>
          <p className="text-muted-foreground mt-2">
            {user?.role === "entrepreneur" ? "Entrepreneur" : "Citizen"} of REALUM • Level {user?.level}
          </p>
        </motion.div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <StatBox icon={Coins} label="REALUM Balance" value={user?.realum_balance?.toFixed(0) || 0} color="cyan" />
          <StatBox icon={Zap} label="Total XP" value={user?.xp || 0} color="yellow" />
          <StatBox icon={Star} label="Level" value={user?.level || 1} color="purple" />
          <StatBox icon={Award} label="Badges" value={user?.badges?.length || 0} color="green" />
        </div>

        {/* Progress & Quick Actions */}
        <div className="grid md:grid-cols-2 gap-6 mb-8">
          <CyberCard>
            <h3 className="font-orbitron font-bold text-lg mb-4">LEVEL PROGRESS</h3>
            <div className="flex items-center gap-4 mb-4">
              <div className="w-16 h-16 border-2 border-neon-cyan flex items-center justify-center relative">
                <span className="font-orbitron font-black text-2xl text-neon-cyan">{user?.level}</span>
                <div className="absolute -inset-1 border border-neon-cyan/30" />
              </div>
              <div className="flex-1">
                <ProgressBar value={xpProgress} max={xpNeeded} label={`XP to Level ${(user?.level || 0) + 1}`} />
              </div>
            </div>
            <p className="text-sm text-muted-foreground">
              {xpNeeded - xpProgress} XP needed for next level
            </p>
          </CyberCard>

          <CyberCard>
            <h3 className="font-orbitron font-bold text-lg mb-4">QUICK ACTIONS</h3>
            <div className="grid grid-cols-2 gap-3">
              <Link to="/jobs" className="flex items-center gap-2 p-3 border border-white/20 hover:border-neon-cyan/50 transition-colors group">
                <Briefcase className="w-5 h-5 text-muted-foreground group-hover:text-neon-cyan" />
                <span className="text-sm">Find Jobs</span>
              </Link>
              <Link to="/voting" className="flex items-center gap-2 p-3 border border-white/20 hover:border-neon-purple/50 transition-colors group">
                <Vote className="w-5 h-5 text-muted-foreground group-hover:text-neon-purple" />
                <span className="text-sm">Vote Now</span>
              </Link>
              <Link to="/city" className="flex items-center gap-2 p-3 border border-white/20 hover:border-neon-yellow/50 transition-colors group">
                <Map className="w-5 h-5 text-muted-foreground group-hover:text-neon-yellow" />
                <span className="text-sm">Explore City</span>
              </Link>
              <Link to="/wallet" className="flex items-center gap-2 p-3 border border-white/20 hover:border-neon-green/50 transition-colors group">
                <Wallet className="w-5 h-5 text-muted-foreground group-hover:text-neon-green" />
                <span className="text-sm">My Wallet</span>
              </Link>
            </div>
          </CyberCard>
        </div>

        {/* Badges */}
        <CyberCard className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-orbitron font-bold text-lg">MY BADGES</h3>
            <Link to="/profile" className="text-sm text-neon-cyan hover:underline">View All</Link>
          </div>
          {userBadges.length > 0 ? (
            <div className="flex flex-wrap gap-3">
              {userBadges.map(badge => (
                <Badge key={badge.id} name={badge.name} icon={badge.icon} rarity={badge.rarity} />
              ))}
            </div>
          ) : (
            <p className="text-muted-foreground">Complete activities to earn badges!</p>
          )}
        </CyberCard>

        {/* Platform Stats */}
        {stats && (
          <CyberCard>
            <h3 className="font-orbitron font-bold text-lg mb-4">PLATFORM STATISTICS</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="text-center">
                <div className="text-2xl font-orbitron font-bold text-neon-cyan">{stats.total_users}</div>
                <div className="text-xs text-muted-foreground uppercase">Total Citizens</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-orbitron font-bold text-neon-green">{stats.total_transactions}</div>
                <div className="text-xs text-muted-foreground uppercase">Transactions</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-orbitron font-bold text-neon-purple">{stats.active_proposals}</div>
                <div className="text-xs text-muted-foreground uppercase">Active Proposals</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-orbitron font-bold text-neon-yellow">{stats.jobs_completed}</div>
                <div className="text-xs text-muted-foreground uppercase">Jobs Completed</div>
              </div>
            </div>
          </CyberCard>
        )}
      </div>
    </div>
  );
};

const CityMapPage = () => {
  const [zones, setZones] = useState([]);
  const [selectedZone, setSelectedZone] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    axios.get(`${API}/city/zones`).then(res => setZones(res.data)).catch(console.error);
  }, []);

  const zonePositions = {
    "downtown": { x: 50, y: 25 },
    "tech-district": { x: 78, y: 35 },
    "industrial": { x: 20, y: 55 },
    "residential": { x: 75, y: 70 },
    "education": { x: 25, y: 30 },
    "marketplace": { x: 55, y: 60 },
    "cultural": { x: 40, y: 75 },
    "civic": { x: 60, y: 40 }
  };

  const zoneIcons = {
    "downtown": "🏛️",
    "tech-district": "💻",
    "industrial": "🏭",
    "residential": "🏘️",
    "education": "🎓",
    "marketplace": "🛒",
    "cultural": "🎭",
    "civic": "⚖️"
  };

  return (
    <div className="min-h-screen pt-20 pb-12 px-4" data-testid="city-map-page">
      <div className="max-w-7xl mx-auto">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
          <h1 className="text-3xl md:text-4xl font-orbitron font-black">
            CITY <span className="text-neon-cyan neon-text">MAP</span>
          </h1>
          <p className="text-muted-foreground mt-2">Explore the digital city of REALUM - navigate zones, find jobs, and build your future</p>
        </motion.div>

        <div className="grid lg:grid-cols-3 gap-6">
          {/* Interactive Map */}
          <div className="lg:col-span-2">
            <CyberCard className="relative aspect-[4/3] overflow-hidden">
              {/* Grid Background */}
              <div className="absolute inset-0 bg-cyber-grid bg-[length:30px_30px] opacity-30" />
              
              {/* Radial Glow */}
              <div className="absolute inset-0 bg-hero-glow opacity-50" />
              
              {/* Zone Markers */}
              {zones.map(zone => {
                const pos = zonePositions[zone.id] || { x: 50, y: 50 };
                const icon = zoneIcons[zone.id] || "🏢";
                return (
                  <motion.button
                    key={zone.id}
                    initial={{ scale: 0, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    transition={{ delay: zones.indexOf(zone) * 0.1 }}
                    whileHover={{ scale: 1.15 }}
                    onClick={() => setSelectedZone(zone)}
                    className={`absolute transform -translate-x-1/2 -translate-y-1/2 z-10 ${
                      selectedZone?.id === zone.id ? "z-20" : ""
                    }`}
                    style={{ left: `${pos.x}%`, top: `${pos.y}%` }}
                    data-testid={`zone-${zone.id}`}
                  >
                    <div 
                      className={`w-16 h-16 md:w-20 md:h-20 border-2 flex items-center justify-center transition-all duration-300 ${
                        selectedZone?.id === zone.id 
                          ? "border-white bg-white/20 scale-110" 
                          : "border-opacity-50 hover:border-opacity-100"
                      }`}
                      style={{ 
                        borderColor: zone.color,
                        boxShadow: selectedZone?.id === zone.id 
                          ? `0 0 40px ${zone.color}, inset 0 0 20px ${zone.color}30` 
                          : `0 0 20px ${zone.color}40`
                      }}
                    >
                      <span className="text-2xl md:text-3xl">{icon}</span>
                    </div>
                    <div className="absolute top-full mt-2 left-1/2 -translate-x-1/2 whitespace-nowrap">
                      <span 
                        className="text-xs font-mono uppercase px-2 py-1 bg-black/90 border border-white/20"
                        style={{ color: zone.color }}
                      >
                        {zone.name}
                      </span>
                    </div>
                  </motion.button>
                );
              })}

              {/* Connection Lines SVG */}
              <svg className="absolute inset-0 w-full h-full pointer-events-none">
                <defs>
                  <linearGradient id="lineGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                    <stop offset="0%" stopColor="#00F0FF" stopOpacity="0.1" />
                    <stop offset="50%" stopColor="#00F0FF" stopOpacity="0.4" />
                    <stop offset="100%" stopColor="#00F0FF" stopOpacity="0.1" />
                  </linearGradient>
                </defs>
                {/* Central Hub Connections */}
                <line x1="50%" y1="25%" x2="78%" y2="35%" stroke="url(#lineGradient)" strokeWidth="1" />
                <line x1="50%" y1="25%" x2="25%" y2="30%" stroke="url(#lineGradient)" strokeWidth="1" />
                <line x1="50%" y1="25%" x2="60%" y2="40%" stroke="url(#lineGradient)" strokeWidth="1" />
                <line x1="78%" y1="35%" x2="75%" y2="70%" stroke="url(#lineGradient)" strokeWidth="1" />
                <line x1="20%" y1="55%" x2="40%" y2="75%" stroke="url(#lineGradient)" strokeWidth="1" />
                <line x1="55%" y1="60%" x2="75%" y2="70%" stroke="url(#lineGradient)" strokeWidth="1" />
                <line x1="55%" y1="60%" x2="40%" y2="75%" stroke="url(#lineGradient)" strokeWidth="1" />
                <line x1="60%" y1="40%" x2="55%" y2="60%" stroke="url(#lineGradient)" strokeWidth="1" />
                <line x1="25%" y1="30%" x2="20%" y2="55%" stroke="url(#lineGradient)" strokeWidth="1" />
              </svg>

              {/* Map Legend */}
              <div className="absolute bottom-4 left-4 text-xs font-mono text-muted-foreground bg-black/80 p-2 border border-white/10">
                <div className="flex items-center gap-2 mb-1">
                  <div className="w-2 h-2 bg-neon-cyan rounded-full animate-pulse" />
                  <span>INTERACTIVE ZONES</span>
                </div>
                <span className="text-[10px]">Click a zone to explore</span>
              </div>
            </CyberCard>
          </div>

          {/* Zone Info Panel */}
          <div>
            <CyberCard className="h-full min-h-[400px]">
              {selectedZone ? (
                <motion.div
                  key={selectedZone.id}
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  className="h-full flex flex-col"
                >
                  <div className="flex items-center gap-3 mb-4">
                    <div 
                      className="w-14 h-14 border-2 flex items-center justify-center"
                      style={{ 
                        borderColor: selectedZone.color,
                        boxShadow: `0 0 20px ${selectedZone.color}40`
                      }}
                    >
                      <span className="text-2xl">{zoneIcons[selectedZone.id] || "🏢"}</span>
                    </div>
                    <div>
                      <h3 className="font-orbitron font-bold text-lg" style={{ color: selectedZone.color }}>
                        {selectedZone.name}
                      </h3>
                      <span className="text-xs uppercase tracking-wider text-muted-foreground">{selectedZone.type} zone</span>
                    </div>
                  </div>
                  
                  <p className="text-muted-foreground mb-4 text-sm">{selectedZone.description}</p>
                  
                  <div className="space-y-4 flex-1">
                    <div className="flex justify-between text-sm p-2 border border-white/10 bg-black/30">
                      <span className="text-muted-foreground">Available Jobs</span>
                      <span className="font-mono font-bold" style={{ color: selectedZone.color }}>{selectedZone.jobs_count}</span>
                    </div>
                    
                    <div>
                      <span className="text-xs uppercase tracking-wider text-muted-foreground">Buildings</span>
                      <div className="mt-2 flex flex-wrap gap-2">
                        {selectedZone.buildings?.map((building, i) => (
                          <span key={i} className="px-2 py-1 text-xs font-mono border border-white/20 bg-black/50">
                            {building}
                          </span>
                        ))}
                      </div>
                    </div>

                    {selectedZone.features && selectedZone.features.length > 0 && (
                      <div>
                        <span className="text-xs uppercase tracking-wider text-muted-foreground">Features</span>
                        <div className="mt-2 space-y-1">
                          {selectedZone.features.map((feature, i) => (
                            <div key={i} className="flex items-center gap-2 text-xs">
                              <div className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: selectedZone.color }} />
                              <span className="text-muted-foreground">{feature}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                  
                  <CyberButton 
                    className="w-full mt-4"
                    onClick={() => navigate(`/jobs?zone=${selectedZone.id}`)}
                  >
                    <span className="flex items-center justify-center gap-2">
                      Find Jobs <ChevronRight className="w-4 h-4" />
                    </span>
                  </CyberButton>
                </motion.div>
              ) : (
                <div className="h-full flex flex-col items-center justify-center text-center py-8">
                  <Map className="w-16 h-16 text-muted-foreground mb-4 opacity-50" />
                  <p className="text-muted-foreground font-mono">SELECT A ZONE</p>
                  <p className="text-xs text-muted-foreground mt-2">Click on a zone marker on the map to view details</p>
                </div>
              )}
            </CyberCard>
          </div>
        </div>

        {/* Zone Grid */}
        <div className="mt-8 grid grid-cols-2 md:grid-cols-4 gap-4">
          {zones.map(zone => (
            <motion.button
              key={zone.id}
              whileHover={{ scale: 1.02 }}
              onClick={() => setSelectedZone(zone)}
              className={`p-4 border text-left transition-all ${
                selectedZone?.id === zone.id 
                  ? "border-white/50 bg-white/5" 
                  : "border-white/10 hover:border-white/30"
              }`}
              style={{ borderLeftColor: zone.color, borderLeftWidth: "3px" }}
            >
              <div className="flex items-center gap-3 mb-2">
                <span className="text-xl">{zoneIcons[zone.id] || "🏢"}</span>
                <span className="font-mono uppercase text-sm" style={{ color: zone.color }}>{zone.name}</span>
              </div>
              <div className="flex justify-between text-xs text-muted-foreground">
                <span>{zone.type}</span>
                <span>{zone.jobs_count} jobs</span>
              </div>
            </motion.button>
          ))}
        </div>
      </div>
    </div>
  );
};

const JobsPage = () => {
  const { token, refreshUser } = useAuth();
  const [jobs, setJobs] = useState([]);
  const [activeJobs, setActiveJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(null);

  const fetchJobs = async () => {
    try {
      const [jobsRes, activeRes] = await Promise.all([
        axios.get(`${API}/jobs`, { headers: { Authorization: `Bearer ${token}` } }),
        axios.get(`${API}/jobs/active`, { headers: { Authorization: `Bearer ${token}` } })
      ]);
      setJobs(jobsRes.data);
      setActiveJobs(activeRes.data.jobs || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJobs();
  }, [token]);

  const applyForJob = async (jobId) => {
    setActionLoading(jobId);
    try {
      await axios.post(`${API}/jobs/apply`, { job_id: jobId }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      await fetchJobs();
    } catch (e) {
      alert(e.response?.data?.detail || "Failed to apply");
    } finally {
      setActionLoading(null);
    }
  };

  const completeJob = async (jobId) => {
    setActionLoading(jobId);
    try {
      const res = await axios.post(`${API}/jobs/complete`, { job_id: jobId }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      await fetchJobs();
      await refreshUser();
      alert(`Job completed! Earned ${res.data.reward} RLM and ${res.data.xp_gained} XP`);
    } catch (e) {
      alert(e.response?.data?.detail || "Failed to complete");
    } finally {
      setActionLoading(null);
    }
  };

  const activeJobIds = activeJobs.map(j => j.id);

  const zoneColors = {
    "downtown": "#00F0FF",
    "tech-district": "#FF003C",
    "industrial": "#F9F871",
    "residential": "#00FF88",
    "education": "#9D4EDD",
    "marketplace": "#FF6B35",
    "cultural": "#E040FB",
    "civic": "#40C4FF"
  };

  return (
    <div className="min-h-screen pt-20 pb-12 px-4" data-testid="jobs-page">
      <div className="max-w-7xl mx-auto">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
          <h1 className="text-3xl md:text-4xl font-orbitron font-black">
            JOB <span className="text-neon-cyan neon-text">BOARD</span>
          </h1>
          <p className="text-muted-foreground mt-2">Find work, earn REALUM Coin, gain experience</p>
        </motion.div>

        {/* Active Jobs */}
        {activeJobs.length > 0 && (
          <div className="mb-8">
            <h2 className="font-orbitron font-bold text-lg mb-4 flex items-center gap-2">
              <Clock className="w-5 h-5 text-neon-yellow" />
              ACTIVE JOBS
            </h2>
            <div className="grid md:grid-cols-2 gap-4">
              {activeJobs.map(job => (
                <CyberCard key={job.id} className="border-neon-yellow/30" glow>
                  <div className="flex justify-between items-start mb-4">
                    <div>
                      <h3 className="font-orbitron font-bold">{job.title}</h3>
                      <p className="text-sm text-muted-foreground">{job.company}</p>
                    </div>
                    <span className="px-2 py-1 text-xs font-mono bg-neon-yellow/20 text-neon-yellow border border-neon-yellow/30">
                      IN PROGRESS
                    </span>
                  </div>
                  <p className="text-sm text-muted-foreground mb-4">{job.description}</p>
                  <div className="flex justify-between items-center">
                    <div className="flex gap-4 text-sm">
                      <span className="text-neon-cyan">{job.reward} RLM</span>
                      <span className="text-neon-purple">{job.xp_reward} XP</span>
                    </div>
                    <CyberButton
                      onClick={() => completeJob(job.id)}
                      disabled={actionLoading === job.id}
                      className="text-sm px-4 py-2"
                      data-testid={`complete-job-${job.id}`}
                    >
                      {actionLoading === job.id ? "..." : "Complete"}
                    </CyberButton>
                  </div>
                </CyberCard>
              ))}
            </div>
          </div>
        )}

        {/* Available Jobs */}
        <h2 className="font-orbitron font-bold text-lg mb-4 flex items-center gap-2">
          <Briefcase className="w-5 h-5 text-neon-cyan" />
          AVAILABLE JOBS
        </h2>

        {loading ? (
          <div className="text-center py-12 text-muted-foreground">Loading jobs...</div>
        ) : (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {jobs.filter(j => !activeJobIds.includes(j.id)).map(job => (
              <motion.div
                key={job.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
              >
                <CyberCard className="h-full flex flex-col">
                  <div className="flex justify-between items-start mb-2">
                    <div className="flex items-center gap-2">
                      <div 
                        className="w-3 h-3 rounded-full"
                        style={{ backgroundColor: zoneColors[job.zone] || "#00F0FF" }}
                      />
                      <span className="text-xs uppercase tracking-wider text-muted-foreground">{job.zone}</span>
                    </div>
                    {job.required_level > 1 && (
                      <span className="text-xs font-mono text-neon-purple">LVL {job.required_level}+</span>
                    )}
                  </div>
                  
                  <h3 className="font-orbitron font-bold text-lg mb-1">{job.title}</h3>
                  <p className="text-sm text-muted-foreground mb-2">{job.company}</p>
                  <p className="text-sm text-muted-foreground mb-4 flex-1">{job.description}</p>
                  
                  <div className="flex items-center justify-between pt-4 border-t border-white/10">
                    <div className="flex gap-3 text-sm">
                      <span className="flex items-center gap-1 text-neon-cyan">
                        <Coins className="w-4 h-4" /> {job.reward}
                      </span>
                      <span className="flex items-center gap-1 text-neon-purple">
                        <Zap className="w-4 h-4" /> {job.xp_reward}
                      </span>
                      <span className="flex items-center gap-1 text-muted-foreground">
                        <Clock className="w-4 h-4" /> {job.duration_minutes}m
                      </span>
                    </div>
                  </div>
                  
                  <CyberButton
                    onClick={() => applyForJob(job.id)}
                    disabled={actionLoading === job.id}
                    variant="secondary"
                    className="w-full mt-4 text-sm"
                    data-testid={`apply-job-${job.id}`}
                  >
                    {actionLoading === job.id ? "Applying..." : "Apply"}
                  </CyberButton>
                </CyberCard>
              </motion.div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

const VotingPage = () => {
  const { token, user, refreshUser } = useAuth();
  const [proposals, setProposals] = useState([]);
  const [showCreate, setShowCreate] = useState(false);
  const [newProposal, setNewProposal] = useState({ title: "", description: "" });
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(null);

  const fetchProposals = async () => {
    try {
      const res = await axios.get(`${API}/proposals`);
      setProposals(res.data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProposals();
  }, []);

  const vote = async (proposalId, voteFor) => {
    setActionLoading(`${proposalId}-${voteFor}`);
    try {
      await axios.post(`${API}/proposals/vote`, 
        { proposal_id: proposalId, vote: voteFor },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      await fetchProposals();
      await refreshUser();
    } catch (e) {
      alert(e.response?.data?.detail || "Failed to vote");
    } finally {
      setActionLoading(null);
    }
  };

  const createProposal = async (e) => {
    e.preventDefault();
    setActionLoading("create");
    try {
      await axios.post(`${API}/proposals`, newProposal, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setNewProposal({ title: "", description: "" });
      setShowCreate(false);
      await fetchProposals();
      await refreshUser();
    } catch (e) {
      alert(e.response?.data?.detail || "Failed to create proposal");
    } finally {
      setActionLoading(null);
    }
  };

  return (
    <div className="min-h-screen pt-20 pb-12 px-4" data-testid="voting-page">
      <div className="max-w-4xl mx-auto">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
          <div className="flex justify-between items-start">
            <div>
              <h1 className="text-3xl md:text-4xl font-orbitron font-black">
                DAO <span className="text-neon-purple neon-text-red">GOVERNANCE</span>
              </h1>
              <p className="text-muted-foreground mt-2">Vote on proposals, shape the future of REALUM</p>
            </div>
            {user?.level >= 2 && (
              <CyberButton onClick={() => setShowCreate(!showCreate)} variant="secondary">
                {showCreate ? "Cancel" : "New Proposal"}
              </CyberButton>
            )}
          </div>
        </motion.div>

        {/* Create Proposal Form */}
        <AnimatePresence>
          {showCreate && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="mb-8 overflow-hidden"
            >
              <CyberCard>
                <h3 className="font-orbitron font-bold text-lg mb-4">CREATE PROPOSAL</h3>
                <form onSubmit={createProposal} className="space-y-4">
                  <div>
                    <label className="block text-xs uppercase tracking-wider text-muted-foreground mb-2">Title</label>
                    <input
                      type="text"
                      value={newProposal.title}
                      onChange={(e) => setNewProposal({ ...newProposal, title: e.target.value })}
                      className="w-full bg-black/50 border border-white/20 px-4 py-3 font-mono text-sm focus:border-neon-purple focus:outline-none"
                      placeholder="Proposal title..."
                      required
                      data-testid="proposal-title"
                    />
                  </div>
                  <div>
                    <label className="block text-xs uppercase tracking-wider text-muted-foreground mb-2">Description</label>
                    <textarea
                      value={newProposal.description}
                      onChange={(e) => setNewProposal({ ...newProposal, description: e.target.value })}
                      className="w-full bg-black/50 border border-white/20 px-4 py-3 font-mono text-sm focus:border-neon-purple focus:outline-none h-32 resize-none"
                      placeholder="Describe your proposal..."
                      required
                      data-testid="proposal-description"
                    />
                  </div>
                  <CyberButton type="submit" disabled={actionLoading === "create"} data-testid="submit-proposal">
                    {actionLoading === "create" ? "Creating..." : "Submit Proposal"}
                  </CyberButton>
                </form>
              </CyberCard>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Proposals List */}
        {loading ? (
          <div className="text-center py-12 text-muted-foreground">Loading proposals...</div>
        ) : (
          <div className="space-y-4">
            {proposals.map(proposal => {
              const totalVotes = proposal.votes_for + proposal.votes_against;
              const forPercentage = totalVotes > 0 ? (proposal.votes_for / totalVotes) * 100 : 50;
              const hasVoted = proposal.voters?.includes(user?.id);

              return (
                <motion.div
                  key={proposal.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                >
                  <CyberCard>
                    <div className="flex justify-between items-start mb-4">
                      <div>
                        <h3 className="font-orbitron font-bold text-lg">{proposal.title}</h3>
                        <p className="text-sm text-muted-foreground">
                          Proposed by {proposal.proposer_name} • {proposal.status}
                        </p>
                      </div>
                      <span className={`px-2 py-1 text-xs font-mono border ${
                        proposal.status === "active" 
                          ? "border-neon-green/50 text-neon-green bg-neon-green/10" 
                          : "border-muted-foreground/50 text-muted-foreground"
                      }`}>
                        {proposal.status.toUpperCase()}
                      </span>
                    </div>

                    <p className="text-muted-foreground mb-6">{proposal.description}</p>

                    {/* Vote Progress */}
                    <div className="mb-4">
                      <div className="flex justify-between text-sm mb-2">
                        <span className="text-neon-green">For: {proposal.votes_for}</span>
                        <span className="text-neon-red">Against: {proposal.votes_against}</span>
                      </div>
                      <div className="h-3 bg-muted flex overflow-hidden">
                        <div 
                          className="bg-neon-green transition-all duration-500"
                          style={{ width: `${forPercentage}%` }}
                        />
                        <div 
                          className="bg-neon-red transition-all duration-500"
                          style={{ width: `${100 - forPercentage}%` }}
                        />
                      </div>
                    </div>

                    {/* Vote Buttons */}
                    {proposal.status === "active" && !hasVoted && (
                      <div className="flex gap-3">
                        <CyberButton
                          onClick={() => vote(proposal.id, true)}
                          disabled={actionLoading === `${proposal.id}-true`}
                          className="flex-1"
                          data-testid={`vote-for-${proposal.id}`}
                        >
                          <Check className="w-4 h-4 mr-2" />
                          Vote For
                        </CyberButton>
                        <CyberButton
                          onClick={() => vote(proposal.id, false)}
                          disabled={actionLoading === `${proposal.id}-false`}
                          variant="danger"
                          className="flex-1"
                          data-testid={`vote-against-${proposal.id}`}
                        >
                          <X className="w-4 h-4 mr-2" />
                          Vote Against
                        </CyberButton>
                      </div>
                    )}

                    {hasVoted && (
                      <div className="text-center py-2 text-sm text-muted-foreground border border-white/10">
                        You have already voted on this proposal
                      </div>
                    )}
                  </CyberCard>
                </motion.div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

const WalletPage = () => {
  const { user, token, refreshUser } = useAuth();
  const { isConnected, account, connectWallet, error: web3Error } = useWeb3();
  const [transactions, setTransactions] = useState([]);
  const [showTransfer, setShowTransfer] = useState(false);
  const [transferData, setTransferData] = useState({ to_user_id: "", amount: "" });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const fetchTransactions = async () => {
      try {
        const res = await axios.get(`${API}/wallet/transactions`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        setTransactions(res.data.transactions || []);
      } catch (e) {
        console.error(e);
      }
    };
    fetchTransactions();
  }, [token]);

  const handleTransfer = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await axios.post(`${API}/wallet/transfer`, {
        to_user_id: transferData.to_user_id,
        amount: parseFloat(transferData.amount)
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setTransferData({ to_user_id: "", amount: "" });
      setShowTransfer(false);
      await refreshUser();
      const res = await axios.get(`${API}/wallet/transactions`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setTransactions(res.data.transactions || []);
    } catch (e) {
      alert(e.response?.data?.detail || "Transfer failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen pt-20 pb-12 px-4" data-testid="wallet-page">
      <div className="max-w-4xl mx-auto">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
          <h1 className="text-3xl md:text-4xl font-orbitron font-black">
            MY <span className="text-neon-green neon-text">WALLET</span>
          </h1>
          <p className="text-muted-foreground mt-2">Manage your REALUM Coin and transactions</p>
        </motion.div>

        {/* Balance Card */}
        <CyberCard className="mb-6" glow>
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-6">
            <div>
              <span className="text-xs uppercase tracking-wider text-muted-foreground">Total Balance</span>
              <div className="text-4xl md:text-5xl font-orbitron font-black text-neon-cyan neon-text">
                {user?.realum_balance?.toFixed(2)} <span className="text-xl">RLM</span>
              </div>
            </div>
            <div className="flex gap-3">
              <CyberButton onClick={() => setShowTransfer(!showTransfer)} variant="secondary">
                {showTransfer ? "Cancel" : "Transfer"}
              </CyberButton>
            </div>
          </div>
        </CyberCard>

        {/* Web3 Connection */}
        <CyberCard className="mb-6">
          <h3 className="font-orbitron font-bold text-lg mb-4">WEB3 WALLET</h3>
          {isConnected ? (
            <div className="flex items-center gap-4">
              <div className="w-3 h-3 bg-neon-green rounded-full animate-pulse" />
              <div>
                <p className="text-sm text-muted-foreground">Connected</p>
                <p className="font-mono text-neon-green">{account}</p>
              </div>
            </div>
          ) : (
            <div>
              {web3Error && (
                <div className="mb-4 p-3 border border-neon-red/50 bg-neon-red/10 text-neon-red text-sm">
                  {web3Error}
                </div>
              )}
              <CyberButton onClick={connectWallet} data-testid="connect-wallet-btn">
                Connect MetaMask
              </CyberButton>
            </div>
          )}
        </CyberCard>

        {/* Transfer Form */}
        <AnimatePresence>
          {showTransfer && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="mb-6 overflow-hidden"
            >
              <CyberCard>
                <h3 className="font-orbitron font-bold text-lg mb-4">TRANSFER REALUM</h3>
                <form onSubmit={handleTransfer} className="space-y-4">
                  <div>
                    <label className="block text-xs uppercase tracking-wider text-muted-foreground mb-2">
                      Recipient User ID
                    </label>
                    <input
                      type="text"
                      value={transferData.to_user_id}
                      onChange={(e) => setTransferData({ ...transferData, to_user_id: e.target.value })}
                      className="w-full bg-black/50 border border-white/20 px-4 py-3 font-mono text-sm focus:border-neon-green focus:outline-none"
                      placeholder="Enter user ID..."
                      required
                      data-testid="transfer-recipient"
                    />
                  </div>
                  <div>
                    <label className="block text-xs uppercase tracking-wider text-muted-foreground mb-2">Amount</label>
                    <input
                      type="number"
                      value={transferData.amount}
                      onChange={(e) => setTransferData({ ...transferData, amount: e.target.value })}
                      className="w-full bg-black/50 border border-white/20 px-4 py-3 font-mono text-sm focus:border-neon-green focus:outline-none"
                      placeholder="0.00"
                      min="0.01"
                      step="0.01"
                      max={user?.realum_balance}
                      required
                      data-testid="transfer-amount"
                    />
                  </div>
                  <CyberButton type="submit" disabled={loading} data-testid="transfer-submit">
                    {loading ? "Transferring..." : "Send Transfer"}
                  </CyberButton>
                </form>
              </CyberCard>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Transaction History */}
        <CyberCard>
          <h3 className="font-orbitron font-bold text-lg mb-4">TRANSACTION HISTORY</h3>
          {transactions.length > 0 ? (
            <div className="space-y-3">
              {transactions.map((tx, i) => (
                <div key={i} className="flex items-center justify-between p-3 border border-white/10 bg-black/30">
                  <div className="flex items-center gap-3">
                    <div className={`w-8 h-8 flex items-center justify-center ${
                      tx.to_user_id === user?.id ? "bg-neon-green/20 text-neon-green" : "bg-neon-red/20 text-neon-red"
                    }`}>
                      {tx.to_user_id === user?.id ? "+" : "-"}
                    </div>
                    <div>
                      <p className="text-sm font-mono">
                        {tx.type === "job_reward" ? "Job Reward" : "Transfer"}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {new Date(tx.created_at).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                  <span className={`font-mono font-bold ${
                    tx.to_user_id === user?.id ? "text-neon-green" : "text-neon-red"
                  }`}>
                    {tx.to_user_id === user?.id ? "+" : "-"}{tx.amount} RLM
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-muted-foreground text-center py-8">No transactions yet</p>
          )}
        </CyberCard>
      </div>
    </div>
  );
};

const LeaderboardPage = () => {
  const { user } = useAuth();
  const [leaderboard, setLeaderboard] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    axios.get(`${API}/leaderboard`)
      .then(res => setLeaderboard(res.data))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const getRankStyle = (rank) => {
    if (rank === 1) return "border-neon-yellow text-neon-yellow bg-neon-yellow/10";
    if (rank === 2) return "border-gray-400 text-gray-400 bg-gray-400/10";
    if (rank === 3) return "border-orange-500 text-orange-500 bg-orange-500/10";
    return "border-white/20 text-muted-foreground";
  };

  return (
    <div className="min-h-screen pt-20 pb-12 px-4" data-testid="leaderboard-page">
      <div className="max-w-4xl mx-auto">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
          <h1 className="text-3xl md:text-4xl font-orbitron font-black">
            <span className="text-neon-yellow">LEADERBOARD</span>
          </h1>
          <p className="text-muted-foreground mt-2">Top citizens of REALUM</p>
        </motion.div>

        {loading ? (
          <div className="text-center py-12 text-muted-foreground">Loading rankings...</div>
        ) : (
          <div className="space-y-3">
            {leaderboard.map((entry, i) => (
              <motion.div
                key={entry.user_id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.05 }}
              >
                <CyberCard className={`${entry.user_id === user?.id ? "border-neon-cyan" : ""}`}>
                  <div className="flex items-center gap-4">
                    {/* Rank */}
                    <div className={`w-12 h-12 flex items-center justify-center border-2 font-orbitron font-black text-lg ${getRankStyle(entry.rank)}`}>
                      {entry.rank}
                    </div>

                    {/* User Info */}
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="font-orbitron font-bold">{entry.username}</span>
                        {entry.user_id === user?.id && (
                          <span className="px-2 py-0.5 text-xs font-mono bg-neon-cyan/20 text-neon-cyan border border-neon-cyan/30">
                            YOU
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-4 text-sm text-muted-foreground">
                        <span>Level {entry.level}</span>
                        <span>{entry.badges_count} badges</span>
                      </div>
                    </div>

                    {/* Stats */}
                    <div className="text-right">
                      <div className="font-mono font-bold text-neon-cyan">{entry.xp} XP</div>
                      <div className="text-sm text-muted-foreground">{entry.realum_balance?.toFixed(0)} RLM</div>
                    </div>
                  </div>
                </CyberCard>
              </motion.div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

const ProfilePage = () => {
  const { user } = useAuth();
  const [allBadges, setAllBadges] = useState([]);

  useEffect(() => {
    axios.get(`${API}/badges`)
      .then(res => setAllBadges(res.data.badges))
      .catch(console.error);
  }, []);

  const xpForNextLevel = [0, 100, 300, 600, 1000, 1500, 2100, 2800, 3600, 4500, 5500];

  return (
    <div className="min-h-screen pt-20 pb-12 px-4" data-testid="profile-page">
      <div className="max-w-4xl mx-auto">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
          <h1 className="text-3xl md:text-4xl font-orbitron font-black">
            CITIZEN <span className="text-neon-cyan neon-text">PROFILE</span>
          </h1>
        </motion.div>

        {/* Profile Header */}
        <CyberCard className="mb-6" glow>
          <div className="flex flex-col md:flex-row md:items-center gap-6">
            <div className="w-24 h-24 border-2 border-neon-cyan flex items-center justify-center relative">
              <span className="font-orbitron font-black text-4xl text-neon-cyan">{user?.level}</span>
              <div className="absolute -inset-2 border border-neon-cyan/30" />
            </div>
            <div className="flex-1">
              <h2 className="text-2xl font-orbitron font-bold">{user?.username}</h2>
              <p className="text-muted-foreground">{user?.email}</p>
              <div className="flex items-center gap-4 mt-2">
                <span className="px-3 py-1 text-xs font-mono uppercase border border-neon-purple/50 text-neon-purple bg-neon-purple/10">
                  {user?.role}
                </span>
                <span className="text-sm text-muted-foreground">
                  Member since {new Date(user?.created_at).toLocaleDateString()}
                </span>
              </div>
            </div>
            <div className="text-right">
              <div className="text-3xl font-orbitron font-black text-neon-cyan">{user?.realum_balance?.toFixed(0)}</div>
              <div className="text-sm text-muted-foreground">REALUM Coin</div>
            </div>
          </div>
        </CyberCard>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <StatBox icon={Star} label="Level" value={user?.level || 1} color="purple" />
          <StatBox icon={Zap} label="Total XP" value={user?.xp || 0} color="yellow" />
          <StatBox icon={Award} label="Badges" value={user?.badges?.length || 0} color="green" />
          <StatBox icon={Briefcase} label="Jobs Done" value={user?.completed_jobs?.length || 0} color="cyan" />
        </div>

        {/* Wallet Info */}
        {user?.wallet_address && (
          <CyberCard className="mb-6">
            <h3 className="font-orbitron font-bold text-lg mb-4">CONNECTED WALLET</h3>
            <div className="flex items-center gap-3">
              <div className="w-3 h-3 bg-neon-green rounded-full" />
              <span className="font-mono text-neon-green break-all">{user.wallet_address}</span>
            </div>
          </CyberCard>
        )}

        {/* All Badges */}
        <CyberCard>
          <h3 className="font-orbitron font-bold text-lg mb-4">BADGES COLLECTION</h3>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {allBadges.map(badge => {
              const earned = user?.badges?.includes(badge.id);
              return (
                <div 
                  key={badge.id}
                  className={`p-4 border ${
                    earned 
                      ? "border-neon-cyan/50 bg-neon-cyan/5" 
                      : "border-white/10 bg-black/30 opacity-50"
                  }`}
                >
                  <div className="flex items-center gap-3 mb-2">
                    <span className="text-2xl">{badge.icon}</span>
                    <div>
                      <p className="font-mono font-bold text-sm">{badge.name}</p>
                      <p className="text-xs text-muted-foreground capitalize">{badge.rarity}</p>
                    </div>
                  </div>
                  <p className="text-xs text-muted-foreground">{badge.description}</p>
                  {earned && (
                    <div className="mt-2 flex items-center gap-1 text-xs text-neon-green">
                      <Check className="w-3 h-3" /> Earned
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </CyberCard>
      </div>
    </div>
  );
};

// ==================== PROTECTED ROUTE ====================

const ProtectedRoute = ({ children }) => {
  const { user, loading } = useAuth();
  
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="text-center">
          <div className="w-12 h-12 border-2 border-neon-cyan border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-muted-foreground font-mono">INITIALIZING...</p>
        </div>
      </div>
    );
  }
  
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  
  return children;
};

// ==================== MAIN APP ====================

function AppContent() {
  const { user } = useAuth();
  const location = useLocation();
  const isAuthPage = ["/", "/login", "/register"].includes(location.pathname);

  // Seed data on first load
  useEffect(() => {
    axios.post(`${API}/seed`).catch(() => {});
  }, []);

  return (
    <div className="App scanlines noise">
      {!isAuthPage && <Navbar />}
      <AnimatePresence mode="wait">
        <Routes location={location} key={location.pathname}>
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/dashboard" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
          <Route path="/city" element={<ProtectedRoute><CityMapPage /></ProtectedRoute>} />
          <Route path="/jobs" element={<ProtectedRoute><JobsPage /></ProtectedRoute>} />
          <Route path="/voting" element={<ProtectedRoute><VotingPage /></ProtectedRoute>} />
          <Route path="/wallet" element={<ProtectedRoute><WalletPage /></ProtectedRoute>} />
          <Route path="/leaderboard" element={<ProtectedRoute><LeaderboardPage /></ProtectedRoute>} />
          <Route path="/profile" element={<ProtectedRoute><ProfilePage /></ProtectedRoute>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AnimatePresence>
    </div>
  );
}

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Web3Provider>
          <AppContent />
        </Web3Provider>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
