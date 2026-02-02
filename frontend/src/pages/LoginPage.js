import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useTranslation } from '../../context/LanguageContext';
import { CyberCard, CyberButton } from '../../components/common/CyberUI';

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
        <h2 className="text-xl sm:text-2xl font-orbitron font-bold text-center mb-6">
          {t('login')} <span className="text-neon-cyan">REALUM</span>
        </h2>
        
        {error && (
          <div className="mb-4 p-3 bg-neon-red/10 border border-neon-red/50 text-neon-red text-sm" data-testid="login-error">
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

export default LoginPage;
