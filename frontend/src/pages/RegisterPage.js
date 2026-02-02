import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Users, Sparkles, Target, Shield, Heart } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useTranslation } from '../context/LanguageContext';
import { CyberCard, CyberButton } from '../components/common/CyberUI';

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
        <h2 className="text-xl sm:text-2xl font-orbitron font-bold text-center mb-6">
          {t('register')} <span className="text-neon-cyan">REALUM</span>
        </h2>
        
        {error && (
          <div className="mb-4 p-3 bg-neon-red/10 border border-neon-red/50 text-neon-red text-sm" data-testid="register-error">
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
                  className={`p-2 sm:p-3 border text-left transition-all ${
                    formData.role === role.value 
                      ? 'border-neon-cyan bg-neon-cyan/10' 
                      : 'border-white/20 hover:border-white/40'
                  }`}
                  data-testid={`role-${role.value}`}
                >
                  <role.icon className={`w-4 h-4 sm:w-5 sm:h-5 mb-1 ${formData.role === role.value ? 'text-neon-cyan' : 'text-white/50'}`} />
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

export default RegisterPage;
