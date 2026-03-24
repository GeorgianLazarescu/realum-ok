import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Building2, Factory, Rocket, TrendingUp, Users, DollarSign,
  Plus, Loader2, ChevronRight, Award, BarChart3, Briefcase
} from 'lucide-react';
import axios from 'axios';
import { API } from '../utils/api';
import { useAuth } from '../context/AuthContext';
import { CyberCard, CyberButton } from '../components/common/CyberUI';
import { toast } from 'sonner';

const CompaniesPage = () => {
  const { user, refreshUser } = useAuth();
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [activeTab, setActiveTab] = useState('my-company');
  
  const [sectors, setSectors] = useState([]);
  const [myCompany, setMyCompany] = useState(null);
  const [publicCompanies, setPublicCompanies] = useState([]);
  const [leaderboard, setLeaderboard] = useState([]);
  
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showIPOModal, setShowIPOModal] = useState(false);
  
  const [createForm, setCreateForm] = useState({
    name: '', symbol: '', sector: 'technology', description: '', logo_color: '#00F0FF'
  });
  const [ipoForm, setIpoForm] = useState({
    total_shares: 100000, initial_price: 10, public_percentage: 30, dividend_rate: 0.02
  });

  useEffect(() => {
    fetchAllData();
  }, []);

  const fetchAllData = async () => {
    try {
      const [sectorsRes, publicRes, leaderRes] = await Promise.all([
        axios.get(`${API}/companies/sectors`),
        axios.get(`${API}/companies/public`),
        axios.get(`${API}/companies/leaderboard`)
      ]);
      setSectors(sectorsRes.data.sectors || []);
      setPublicCompanies(publicRes.data.companies || []);
      setLeaderboard(leaderRes.data.leaderboard || []);
      
      try {
        const myRes = await axios.get(`${API}/companies/my-company`);
        setMyCompany(myRes.data);
      } catch (e) {}
    } catch (error) {
      console.error('Failed to load companies:', error);
    }
    setLoading(false);
  };

  const handleCreateCompany = async () => {
    setProcessing(true);
    try {
      const res = await axios.post(`${API}/companies/create`, createForm);
      toast.success(res.data.message);
      setShowCreateModal(false);
      fetchAllData();
      refreshUser();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create company');
    }
    setProcessing(false);
  };

  const handleIPO = async () => {
    setProcessing(true);
    try {
      const res = await axios.post(`${API}/companies/ipo`, ipoForm);
      toast.success(res.data.message);
      setShowIPOModal(false);
      fetchAllData();
      refreshUser();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to launch IPO');
    }
    setProcessing(false);
  };

  const handlePayDividend = async () => {
    if (!myCompany?.company?.id) return;
    setProcessing(true);
    try {
      const res = await axios.post(`${API}/companies/${myCompany.company.id}/dividend`);
      toast.success(res.data.message);
      fetchAllData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to pay dividends');
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
    <div className="min-h-screen pt-16 sm:pt-20 pb-20 lg:pb-12 px-3 sm:px-4" data-testid="companies-page">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-6">
          <h1 className="text-2xl sm:text-3xl font-orbitron font-black flex items-center gap-3">
            <Factory className="w-8 h-8 text-neon-purple" />
            <span>Companii <span className="text-neon-cyan">REALUM</span></span>
          </h1>
          <p className="text-white/60 text-sm mt-1">Creează și administrează propria ta companie</p>
        </motion.div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
          {[
            { id: 'my-company', label: 'Compania Mea', icon: Building2 },
            { id: 'public', label: 'Companii Publice', icon: TrendingUp },
            { id: 'leaderboard', label: 'Clasament', icon: Award }
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

        {/* Tab Content */}
        {activeTab === 'my-company' && (
          <div>
            {myCompany?.has_company ? (
              <div className="space-y-6">
                {/* Company Overview */}
                <CyberCard className="p-6" style={{ borderColor: myCompany.company.logo_color + '40' }}>
                  <div className="flex flex-wrap items-start justify-between gap-4 mb-4">
                    <div>
                      <h2 className="text-2xl font-orbitron" style={{ color: myCompany.company.logo_color }}>
                        {myCompany.company.name}
                      </h2>
                      <div className="text-lg font-mono text-white/60">{myCompany.company.symbol}</div>
                      <div className="text-sm text-white/50 mt-1">{myCompany.company.sector_name}</div>
                    </div>
                    <div className={`px-3 py-1 text-sm ${myCompany.company.is_public ? 'bg-neon-green/20 text-neon-green border border-neon-green' : 'bg-white/10 text-white/60 border border-white/20'}`}>
                      {myCompany.company.is_public ? 'PUBLIC' : 'PRIVAT'}
                    </div>
                  </div>
                  
                  <p className="text-white/70 mb-4">{myCompany.company.description}</p>
                  
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="p-3 bg-black/30 border border-white/10 text-center">
                      <div className="text-xl font-orbitron text-neon-cyan">{myCompany.company.treasury?.toFixed(0)}</div>
                      <div className="text-xs text-white/50">Trezorerie (RLM)</div>
                    </div>
                    {myCompany.company.is_public && (
                      <>
                        <div className="p-3 bg-black/30 border border-white/10 text-center">
                          <div className="text-xl font-orbitron text-neon-green">{myCompany.company.current_price?.toFixed(2)}</div>
                          <div className="text-xs text-white/50">Preț/Acțiune</div>
                        </div>
                        <div className="p-3 bg-black/30 border border-white/10 text-center">
                          <div className="text-xl font-orbitron text-neon-yellow">{(myCompany.company.market_cap / 1000000).toFixed(2)}M</div>
                          <div className="text-xs text-white/50">Market Cap</div>
                        </div>
                        <div className="p-3 bg-black/30 border border-white/10 text-center">
                          <div className="text-xl font-orbitron text-neon-purple">{(myCompany.company.dividend_rate * 100).toFixed(1)}%</div>
                          <div className="text-xs text-white/50">Dividend</div>
                        </div>
                      </>
                    )}
                    {!myCompany.company.is_public && (
                      <>
                        <div className="p-3 bg-black/30 border border-white/10 text-center">
                          <div className="text-xl font-orbitron text-neon-green">{myCompany.company.total_investment?.toFixed(0)}</div>
                          <div className="text-xs text-white/50">Investiții</div>
                        </div>
                        <div className="p-3 bg-black/30 border border-white/10 text-center">
                          <div className="text-xl font-orbitron text-neon-yellow">{myCompany.investors?.length || 0}</div>
                          <div className="text-xs text-white/50">Investitori</div>
                        </div>
                      </>
                    )}
                  </div>
                  
                  <div className="flex gap-3 mt-6">
                    {!myCompany.company.is_public && (
                      <CyberButton variant="primary" onClick={() => setShowIPOModal(true)}>
                        <Rocket className="w-4 h-4 mr-2" /> Lansează IPO
                      </CyberButton>
                    )}
                    {myCompany.company.is_public && (
                      <CyberButton variant="outline" onClick={handlePayDividend} disabled={processing}>
                        <DollarSign className="w-4 h-4 mr-2" /> Plătește Dividende
                      </CyberButton>
                    )}
                  </div>
                </CyberCard>

                {/* Shareholders or Investors */}
                {myCompany.shareholders?.length > 0 && (
                  <CyberCard className="p-4">
                    <h3 className="font-orbitron text-lg mb-4">Acționari</h3>
                    <div className="space-y-2">
                      {myCompany.shareholders.map((sh, i) => (
                        <div key={i} className="flex justify-between p-2 bg-black/30 border border-white/10">
                          <span className="text-neon-cyan">{sh.username}</span>
                          <span className="font-mono">{sh.shares.toLocaleString()} ({sh.percentage}%)</span>
                        </div>
                      ))}
                    </div>
                  </CyberCard>
                )}
              </div>
            ) : (
              <CyberCard className="p-8 text-center">
                <Factory className="w-16 h-16 mx-auto mb-4 text-neon-purple/50" />
                <h3 className="font-orbitron text-xl mb-2">Nu ai o companie</h3>
                <p className="text-white/50 mb-6">Creează propria ta companie și devino antreprenor!</p>
                
                {myCompany?.can_create ? (
                  <CyberButton variant="primary" onClick={() => setShowCreateModal(true)}>
                    <Plus className="w-4 h-4 mr-2" /> Creează Companie ({myCompany.creation_cost} RLM)
                  </CyberButton>
                ) : (
                  <p className="text-neon-red">Ai nevoie de {5000} RLM pentru a crea o companie</p>
                )}
              </CyberCard>
            )}
          </div>
        )}

        {activeTab === 'public' && (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {publicCompanies.map(company => (
              <CyberCard key={company.id} className="p-4">
                <div className="flex justify-between items-start mb-3">
                  <div>
                    <h4 className="font-orbitron text-neon-cyan">{company.symbol}</h4>
                    <div className="text-sm text-white/60">{company.name}</div>
                  </div>
                  <div className="text-right">
                    <div className="font-mono text-neon-green">{company.current_price?.toFixed(2)}</div>
                    <div className="text-xs text-white/40">RLM</div>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div className="text-white/50">Market Cap:</div>
                  <div className="text-right font-mono">{(company.market_cap / 1000000).toFixed(2)}M</div>
                  <div className="text-white/50">Dividend:</div>
                  <div className="text-right font-mono">{(company.dividend_rate * 100).toFixed(1)}%</div>
                </div>
              </CyberCard>
            ))}
            {publicCompanies.length === 0 && (
              <div className="col-span-full text-center py-12 text-white/50">
                Nicio companie publică încă.
              </div>
            )}
          </div>
        )}

        {activeTab === 'leaderboard' && (
          <CyberCard className="p-4">
            <h3 className="font-orbitron text-lg mb-4">Top Companii după Market Cap</h3>
            <div className="space-y-3">
              {leaderboard.map((company, i) => (
                <div key={i} className="flex items-center justify-between p-3 bg-black/30 border border-white/10">
                  <div className="flex items-center gap-3">
                    <span className="text-2xl font-orbitron text-neon-yellow">#{i + 1}</span>
                    <div>
                      <div className="font-mono text-neon-cyan">{company.symbol}</div>
                      <div className="text-sm text-white/50">{company.name}</div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="font-mono text-neon-green">{(company.market_cap / 1000000).toFixed(2)}M RLM</div>
                    <div className="text-xs text-white/40">by {company.owner_username}</div>
                  </div>
                </div>
              ))}
              {leaderboard.length === 0 && (
                <div className="text-center py-8 text-white/50">
                  Nicio companie în clasament.
                </div>
              )}
            </div>
          </CyberCard>
        )}

        {/* Create Company Modal */}
        <AnimatePresence>
          {showCreateModal && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4"
              onClick={() => setShowCreateModal(false)}
            >
              <motion.div
                initial={{ scale: 0.9 }}
                animate={{ scale: 1 }}
                exit={{ scale: 0.9 }}
                className="bg-gray-900 border border-neon-purple p-6 max-w-md w-full max-h-[90vh] overflow-y-auto"
                onClick={e => e.stopPropagation()}
              >
                <h3 className="font-orbitron text-xl mb-4">Creează Companie</h3>
                
                <div className="space-y-4">
                  <div>
                    <label className="text-sm text-white/60 block mb-1">Nume Companie</label>
                    <input
                      type="text"
                      value={createForm.name}
                      onChange={e => setCreateForm({...createForm, name: e.target.value})}
                      className="w-full bg-black/50 border border-white/20 p-2 text-white"
                      placeholder="Tech Innovations Inc"
                    />
                  </div>
                  <div>
                    <label className="text-sm text-white/60 block mb-1">Simbol (2-5 caractere)</label>
                    <input
                      type="text"
                      value={createForm.symbol}
                      onChange={e => setCreateForm({...createForm, symbol: e.target.value.toUpperCase()})}
                      className="w-full bg-black/50 border border-white/20 p-2 text-white"
                      placeholder="TECH"
                      maxLength={5}
                    />
                  </div>
                  <div>
                    <label className="text-sm text-white/60 block mb-1">Sector</label>
                    <select
                      value={createForm.sector}
                      onChange={e => setCreateForm({...createForm, sector: e.target.value})}
                      className="w-full bg-black/50 border border-white/20 p-2 text-white"
                    >
                      {sectors.map(s => (
                        <option key={s.id} value={s.id}>{s.name}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="text-sm text-white/60 block mb-1">Descriere</label>
                    <textarea
                      value={createForm.description}
                      onChange={e => setCreateForm({...createForm, description: e.target.value})}
                      className="w-full bg-black/50 border border-white/20 p-2 text-white h-20"
                      placeholder="Descrie activitatea companiei..."
                    />
                  </div>
                  <div>
                    <label className="text-sm text-white/60 block mb-1">Culoare Logo</label>
                    <input
                      type="color"
                      value={createForm.logo_color}
                      onChange={e => setCreateForm({...createForm, logo_color: e.target.value})}
                      className="w-full h-10 bg-black/50 border border-white/20"
                    />
                  </div>
                </div>
                
                <div className="flex gap-3 mt-6">
                  <CyberButton variant="outline" className="flex-1" onClick={() => setShowCreateModal(false)}>
                    Anulează
                  </CyberButton>
                  <CyberButton 
                    variant="primary" 
                    className="flex-1" 
                    onClick={handleCreateCompany}
                    disabled={processing || !createForm.name || !createForm.symbol || !createForm.description}
                  >
                    {processing ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Creează (5000 RLM)'}
                  </CyberButton>
                </div>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* IPO Modal */}
        <AnimatePresence>
          {showIPOModal && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4"
              onClick={() => setShowIPOModal(false)}
            >
              <motion.div
                initial={{ scale: 0.9 }}
                animate={{ scale: 1 }}
                exit={{ scale: 0.9 }}
                className="bg-gray-900 border border-neon-green p-6 max-w-md w-full"
                onClick={e => e.stopPropagation()}
              >
                <h3 className="font-orbitron text-xl mb-4 flex items-center gap-2">
                  <Rocket className="w-5 h-5 text-neon-green" /> Lansează IPO
                </h3>
                
                <div className="space-y-4">
                  <div>
                    <label className="text-sm text-white/60 block mb-1">Total Acțiuni</label>
                    <input
                      type="number"
                      value={ipoForm.total_shares}
                      onChange={e => setIpoForm({...ipoForm, total_shares: parseInt(e.target.value)})}
                      className="w-full bg-black/50 border border-white/20 p-2 text-white"
                      min={100000}
                      max={10000000}
                    />
                  </div>
                  <div>
                    <label className="text-sm text-white/60 block mb-1">Preț Inițial (RLM)</label>
                    <input
                      type="number"
                      value={ipoForm.initial_price}
                      onChange={e => setIpoForm({...ipoForm, initial_price: parseFloat(e.target.value)})}
                      className="w-full bg-black/50 border border-white/20 p-2 text-white"
                      min={1}
                      max={1000}
                      step={0.1}
                    />
                  </div>
                  <div>
                    <label className="text-sm text-white/60 block mb-1">% Acțiuni Publice</label>
                    <input
                      type="number"
                      value={ipoForm.public_percentage}
                      onChange={e => setIpoForm({...ipoForm, public_percentage: parseInt(e.target.value)})}
                      className="w-full bg-black/50 border border-white/20 p-2 text-white"
                      min={10}
                      max={90}
                    />
                  </div>
                  <div>
                    <label className="text-sm text-white/60 block mb-1">Rata Dividend (%)</label>
                    <input
                      type="number"
                      value={ipoForm.dividend_rate * 100}
                      onChange={e => setIpoForm({...ipoForm, dividend_rate: parseFloat(e.target.value) / 100})}
                      className="w-full bg-black/50 border border-white/20 p-2 text-white"
                      min={0}
                      max={10}
                      step={0.5}
                    />
                  </div>
                  
                  <div className="p-3 bg-black/30 border border-white/10">
                    <div className="text-sm text-white/60">Market Cap estimat:</div>
                    <div className="font-orbitron text-xl text-neon-green">
                      {((ipoForm.total_shares * ipoForm.initial_price) / 1000000).toFixed(2)}M RLM
                    </div>
                  </div>
                </div>
                
                <div className="flex gap-3 mt-6">
                  <CyberButton variant="outline" className="flex-1" onClick={() => setShowIPOModal(false)}>
                    Anulează
                  </CyberButton>
                  <CyberButton 
                    variant="primary" 
                    className="flex-1" 
                    onClick={handleIPO}
                    disabled={processing}
                  >
                    {processing ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Lansează IPO (10000 RLM)'}
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

export default CompaniesPage;
