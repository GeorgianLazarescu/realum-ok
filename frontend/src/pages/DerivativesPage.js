import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { 
  TrendingUp, TrendingDown, Activity, DollarSign, Target,
  Loader2, ArrowUp, ArrowDown, Percent, Clock, X
} from 'lucide-react';
import axios from 'axios';
import { API } from '../utils/api';
import { useAuth } from '../context/AuthContext';
import { CyberCard, CyberButton } from '../components/common/CyberUI';
import { toast } from 'sonner';

const DerivativesPage = () => {
  const { user, refreshUser } = useAuth();
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  
  const [activeTab, setActiveTab] = useState('futures'); // futures, options
  const [futuresPositions, setFuturesPositions] = useState([]);
  const [optionsContracts, setOptionsContracts] = useState([]);
  const [stats, setStats] = useState(null);
  const [companies, setCompanies] = useState([]);
  
  const [showOpenModal, setShowOpenModal] = useState(false);
  const [showOptionsModal, setShowOptionsModal] = useState(false);
  const [selectedCompany, setSelectedCompany] = useState(null);
  const [optionsChain, setOptionsChain] = useState(null);
  
  const [futuresForm, setFuturesForm] = useState({
    company_id: '', position_type: 'long', leverage: 5, margin_amount: 100
  });
  const [optionForm, setOptionForm] = useState({
    option_type: 'call', strike_price: 0, expiration_days: 7, quantity: 1
  });

  useEffect(() => {
    fetchAllData();
  }, []);

  const fetchAllData = async () => {
    try {
      const [posRes, optRes, statsRes, marketRes] = await Promise.all([
        axios.get(`${API}/derivatives/futures/positions`),
        axios.get(`${API}/derivatives/options/my-contracts`),
        axios.get(`${API}/derivatives/stats`),
        axios.get(`${API}/stocks/market`)
      ]);
      
      setFuturesPositions(posRes.data.positions || []);
      setOptionsContracts(optRes.data.contracts || []);
      setStats(statsRes.data);
      setCompanies(marketRes.data.companies || []);
    } catch (error) {
      console.error('Failed to load derivatives:', error);
    }
    setLoading(false);
  };

  const handleOpenFutures = async () => {
    if (!futuresForm.company_id) {
      toast.error('Selectează o companie');
      return;
    }
    setProcessing(true);
    
    try {
      const res = await axios.post(`${API}/derivatives/futures/open`, futuresForm);
      toast.success(res.data.message);
      setShowOpenModal(false);
      fetchAllData();
      refreshUser();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to open position');
    }
    setProcessing(false);
  };

  const handleCloseFutures = async (positionId) => {
    setProcessing(true);
    try {
      const res = await axios.post(`${API}/derivatives/futures/close`, { position_id: positionId });
      toast.success(`Poziție închisă! P&L: ${res.data.realized_pnl} RLM`);
      fetchAllData();
      refreshUser();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to close position');
    }
    setProcessing(false);
  };

  const loadOptionsChain = async (companyId) => {
    try {
      const res = await axios.get(`${API}/derivatives/options/chain/${companyId}`);
      setOptionsChain(res.data);
      setSelectedCompany(companies.find(c => c.id === companyId));
      setShowOptionsModal(true);
    } catch (error) {
      toast.error('Failed to load options chain');
    }
  };

  const handleBuyOption = async () => {
    if (!selectedCompany) return;
    setProcessing(true);
    
    try {
      const res = await axios.post(`${API}/derivatives/options/buy`, {
        company_id: selectedCompany.id,
        ...optionForm
      });
      toast.success(res.data.message);
      setShowOptionsModal(false);
      fetchAllData();
      refreshUser();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to buy option');
    }
    setProcessing(false);
  };

  const handleExerciseOption = async (contractId) => {
    setProcessing(true);
    try {
      const res = await axios.post(`${API}/derivatives/options/exercise/${contractId}`);
      toast.success(`Opțiune exercitată! Profit: ${res.data.profit} RLM`);
      fetchAllData();
      refreshUser();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to exercise option');
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
    <div className="min-h-screen pt-16 sm:pt-20 pb-20 lg:pb-12 px-3 sm:px-4" data-testid="derivatives-page">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl sm:text-3xl font-orbitron font-black flex items-center gap-3">
              <Activity className="w-8 h-8 text-neon-purple" />
              <span>Derivate <span className="text-neon-cyan">Financiare</span></span>
            </h1>
            <p className="text-white/60 text-sm mt-1">Futures & Options cu leverage</p>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
          <CyberCard className="p-4 text-center">
            <div className="text-xl font-orbitron text-neon-cyan">{futuresPositions.length}</div>
            <div className="text-xs text-white/50">Poziții Futures</div>
          </CyberCard>
          <CyberCard className="p-4 text-center">
            <div className={`text-xl font-orbitron ${(stats?.futures?.total_pnl || 0) >= 0 ? 'text-neon-green' : 'text-neon-red'}`}>
              {stats?.futures?.total_pnl || 0} RLM
            </div>
            <div className="text-xs text-white/50">P&L Futures</div>
          </CyberCard>
          <CyberCard className="p-4 text-center">
            <div className="text-xl font-orbitron text-neon-yellow">{optionsContracts.length}</div>
            <div className="text-xs text-white/50">Contracte Options</div>
          </CyberCard>
          <CyberCard className="p-4 text-center">
            <div className={`text-xl font-orbitron ${(stats?.options?.total_pnl || 0) >= 0 ? 'text-neon-green' : 'text-neon-red'}`}>
              {stats?.options?.total_pnl || 0} RLM
            </div>
            <div className="text-xs text-white/50">P&L Options</div>
          </CyberCard>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6">
          {[
            { id: 'futures', label: 'Futures', icon: TrendingUp },
            { id: 'options', label: 'Options', icon: Target }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-2 font-mono text-sm flex items-center gap-2 transition-all ${
                activeTab === tab.id 
                  ? 'bg-neon-purple/20 border border-neon-purple text-neon-purple' 
                  : 'border border-white/20 text-white/60 hover:border-white/40'
              }`}
            >
              <tab.icon className="w-4 h-4" /> {tab.label}
            </button>
          ))}
        </div>

        {/* Futures Tab */}
        {activeTab === 'futures' && (
          <div>
            <div className="flex justify-between items-center mb-4">
              <h3 className="font-orbitron text-lg">Poziții Deschise</h3>
              <CyberButton variant="primary" onClick={() => setShowOpenModal(true)}>
                <TrendingUp className="w-4 h-4 mr-2" /> Deschide Poziție
              </CyberButton>
            </div>
            
            {futuresPositions.length > 0 ? (
              <div className="space-y-3">
                {futuresPositions.map(pos => (
                  <CyberCard key={pos.id} className={`p-4 ${pos.at_risk ? 'border-neon-red' : ''}`}>
                    <div className="flex flex-wrap items-center justify-between gap-4">
                      <div className="flex items-center gap-4">
                        <div className={`p-2 ${pos.position_type === 'long' ? 'bg-neon-green/20' : 'bg-neon-red/20'}`}>
                          {pos.position_type === 'long' ? 
                            <ArrowUp className="w-6 h-6 text-neon-green" /> : 
                            <ArrowDown className="w-6 h-6 text-neon-red" />
                          }
                        </div>
                        <div>
                          <div className="font-orbitron text-neon-cyan">
                            {companies.find(c => c.id === pos.company_id)?.symbol || pos.company_id}
                          </div>
                          <div className="text-sm text-white/50">
                            {pos.position_type.toUpperCase()} {pos.leverage}x • {pos.position_size.toFixed(2)} shares
                          </div>
                        </div>
                      </div>
                      
                      <div className="grid grid-cols-3 gap-4 text-center">
                        <div>
                          <div className="text-xs text-white/50">Entry</div>
                          <div className="font-mono">{pos.entry_price?.toFixed(2)}</div>
                        </div>
                        <div>
                          <div className="text-xs text-white/50">Current</div>
                          <div className="font-mono">{pos.current_price?.toFixed(2)}</div>
                        </div>
                        <div>
                          <div className="text-xs text-white/50">P&L</div>
                          <div className={`font-mono ${pos.unrealized_pnl >= 0 ? 'text-neon-green' : 'text-neon-red'}`}>
                            {pos.unrealized_pnl?.toFixed(2)} ({pos.pnl_percent}%)
                          </div>
                        </div>
                      </div>
                      
                      <div className="flex items-center gap-2">
                        {pos.at_risk && (
                          <span className="text-xs px-2 py-1 bg-neon-red/20 text-neon-red border border-neon-red">
                            RISC LICHIDARE
                          </span>
                        )}
                        <CyberButton 
                          variant="outline" 
                          size="sm"
                          onClick={() => handleCloseFutures(pos.id)}
                          disabled={processing}
                        >
                          Închide
                        </CyberButton>
                      </div>
                    </div>
                    
                    {/* Margin Bar */}
                    <div className="mt-3">
                      <div className="flex justify-between text-xs mb-1">
                        <span className="text-white/50">Margin: {pos.margin_amount} RLM</span>
                        <span className={pos.margin_ratio < 10 ? 'text-neon-red' : 'text-white/50'}>
                          {pos.margin_ratio}% margin ratio
                        </span>
                      </div>
                      <div className="h-1 bg-black/50 border border-white/20">
                        <div 
                          className={`h-full ${pos.margin_ratio < 10 ? 'bg-neon-red' : 'bg-neon-green'}`}
                          style={{ width: `${Math.min(100, pos.margin_ratio)}%` }}
                        />
                      </div>
                    </div>
                  </CyberCard>
                ))}
              </div>
            ) : (
              <CyberCard className="p-8 text-center">
                <Activity className="w-12 h-12 mx-auto mb-4 text-white/30" />
                <p className="text-white/50">Nicio poziție futures deschisă</p>
              </CyberCard>
            )}
          </div>
        )}

        {/* Options Tab */}
        {activeTab === 'options' && (
          <div>
            <div className="flex justify-between items-center mb-4">
              <h3 className="font-orbitron text-lg">Contractele Mele</h3>
              <div className="flex gap-2">
                <select
                  onChange={(e) => e.target.value && loadOptionsChain(e.target.value)}
                  className="bg-black/50 border border-white/20 px-3 py-2 text-white text-sm"
                  defaultValue=""
                >
                  <option value="">Selectează companie</option>
                  {companies.map(c => (
                    <option key={c.id} value={c.id}>{c.symbol} - {c.name}</option>
                  ))}
                </select>
              </div>
            </div>
            
            {optionsContracts.length > 0 ? (
              <div className="space-y-3">
                {optionsContracts.map(contract => (
                  <CyberCard key={contract.id} className="p-4">
                    <div className="flex flex-wrap items-center justify-between gap-4">
                      <div className="flex items-center gap-4">
                        <div className={`p-2 ${contract.option_type === 'call' ? 'bg-neon-green/20' : 'bg-neon-red/20'}`}>
                          {contract.option_type === 'call' ? 
                            <ArrowUp className="w-6 h-6 text-neon-green" /> : 
                            <ArrowDown className="w-6 h-6 text-neon-red" />
                          }
                        </div>
                        <div>
                          <div className="font-orbitron text-neon-cyan">
                            {companies.find(c => c.id === contract.company_id)?.symbol} {contract.option_type.toUpperCase()}
                          </div>
                          <div className="text-sm text-white/50">
                            Strike: {contract.strike_price} • Qty: {contract.quantity}
                          </div>
                        </div>
                      </div>
                      
                      <div className="grid grid-cols-3 gap-4 text-center">
                        <div>
                          <div className="text-xs text-white/50">Cost</div>
                          <div className="font-mono">{contract.total_cost?.toFixed(2)}</div>
                        </div>
                        <div>
                          <div className="text-xs text-white/50">Valoare</div>
                          <div className="font-mono text-neon-cyan">{contract.intrinsic_value?.toFixed(2)}</div>
                        </div>
                        <div>
                          <div className="text-xs text-white/50">Timp rămas</div>
                          <div className="font-mono">{contract.time_remaining}z</div>
                        </div>
                      </div>
                      
                      <div className="flex items-center gap-2">
                        <div className={`text-sm font-mono ${contract.profit_if_exercised >= 0 ? 'text-neon-green' : 'text-neon-red'}`}>
                          {contract.profit_if_exercised >= 0 ? '+' : ''}{contract.profit_if_exercised?.toFixed(2)}
                        </div>
                        <CyberButton 
                          variant="primary" 
                          size="sm"
                          onClick={() => handleExerciseOption(contract.id)}
                          disabled={processing || contract.intrinsic_value <= 0}
                        >
                          Exercită
                        </CyberButton>
                      </div>
                    </div>
                  </CyberCard>
                ))}
              </div>
            ) : (
              <CyberCard className="p-8 text-center">
                <Target className="w-12 h-12 mx-auto mb-4 text-white/30" />
                <p className="text-white/50">Niciun contract options activ</p>
              </CyberCard>
            )}
          </div>
        )}

        {/* Open Futures Modal */}
        {showOpenModal && (
          <div className="fixed inset-0 bg-black/90 z-50 flex items-center justify-center p-4" onClick={() => setShowOpenModal(false)}>
            <CyberCard className="p-6 max-w-md w-full" onClick={e => e.stopPropagation()}>
              <h3 className="font-orbitron text-xl mb-4">Deschide Poziție Futures</h3>
              
              <div className="space-y-4">
                <div>
                  <label className="text-sm text-white/60 block mb-2">Companie</label>
                  <select
                    value={futuresForm.company_id}
                    onChange={e => setFuturesForm({...futuresForm, company_id: e.target.value})}
                    className="w-full bg-black/50 border border-white/20 p-2 text-white"
                  >
                    <option value="">Selectează...</option>
                    {companies.map(c => (
                      <option key={c.id} value={c.id}>{c.symbol} - {c.current_price} RLM</option>
                    ))}
                  </select>
                </div>
                
                <div>
                  <label className="text-sm text-white/60 block mb-2">Direcție</label>
                  <div className="flex gap-2">
                    <button
                      onClick={() => setFuturesForm({...futuresForm, position_type: 'long'})}
                      className={`flex-1 p-3 border ${futuresForm.position_type === 'long' ? 'border-neon-green bg-neon-green/20 text-neon-green' : 'border-white/20'}`}
                    >
                      <ArrowUp className="w-5 h-5 mx-auto mb-1" />
                      LONG
                    </button>
                    <button
                      onClick={() => setFuturesForm({...futuresForm, position_type: 'short'})}
                      className={`flex-1 p-3 border ${futuresForm.position_type === 'short' ? 'border-neon-red bg-neon-red/20 text-neon-red' : 'border-white/20'}`}
                    >
                      <ArrowDown className="w-5 h-5 mx-auto mb-1" />
                      SHORT
                    </button>
                  </div>
                </div>
                
                <div>
                  <label className="text-sm text-white/60 block mb-2">Leverage</label>
                  <div className="flex gap-2">
                    {[2, 5, 10, 20].map(lev => (
                      <button
                        key={lev}
                        onClick={() => setFuturesForm({...futuresForm, leverage: lev})}
                        className={`flex-1 p-2 border font-mono ${futuresForm.leverage === lev ? 'border-neon-purple bg-neon-purple/20 text-neon-purple' : 'border-white/20'}`}
                      >
                        {lev}x
                      </button>
                    ))}
                  </div>
                </div>
                
                <div>
                  <label className="text-sm text-white/60 block mb-2">Margin (RLM)</label>
                  <input
                    type="number"
                    value={futuresForm.margin_amount}
                    onChange={e => setFuturesForm({...futuresForm, margin_amount: parseFloat(e.target.value) || 0})}
                    min={50}
                    className="w-full bg-black/50 border border-white/20 p-2 text-white"
                  />
                  <div className="text-xs text-white/40 mt-1">
                    Valoare poziție: {(futuresForm.margin_amount * futuresForm.leverage).toFixed(0)} RLM
                  </div>
                </div>
                
                <div className="p-3 bg-neon-yellow/10 border border-neon-yellow/30 text-sm">
                  <span className="text-neon-yellow">⚠️ Atenție:</span> Leverage-ul amplifică atât profiturile cât și pierderile!
                </div>
              </div>
              
              <div className="flex gap-3 mt-6">
                <CyberButton variant="outline" className="flex-1" onClick={() => setShowOpenModal(false)}>
                  Anulează
                </CyberButton>
                <CyberButton variant="primary" className="flex-1" onClick={handleOpenFutures} disabled={processing}>
                  {processing ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Deschide'}
                </CyberButton>
              </div>
            </CyberCard>
          </div>
        )}

        {/* Options Chain Modal */}
        {showOptionsModal && optionsChain && (
          <div className="fixed inset-0 bg-black/90 z-50 flex items-center justify-center p-4" onClick={() => setShowOptionsModal(false)}>
            <CyberCard className="p-6 max-w-2xl w-full max-h-[80vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="font-orbitron text-xl">{selectedCompany?.symbol} Options</h3>
                  <p className="text-sm text-white/50">Preț curent: {optionsChain.current_price} RLM</p>
                </div>
                <button onClick={() => setShowOptionsModal(false)}>
                  <X className="w-6 h-6" />
                </button>
              </div>
              
              {/* Quick Buy Form */}
              <div className="p-4 bg-black/30 border border-white/10 mb-4">
                <div className="grid grid-cols-4 gap-3 mb-3">
                  <div>
                    <label className="text-xs text-white/50">Tip</label>
                    <select
                      value={optionForm.option_type}
                      onChange={e => setOptionForm({...optionForm, option_type: e.target.value})}
                      className="w-full bg-black/50 border border-white/20 p-2 text-sm"
                    >
                      <option value="call">CALL</option>
                      <option value="put">PUT</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-xs text-white/50">Strike</label>
                    <input
                      type="number"
                      value={optionForm.strike_price}
                      onChange={e => setOptionForm({...optionForm, strike_price: parseFloat(e.target.value) || 0})}
                      className="w-full bg-black/50 border border-white/20 p-2 text-sm"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-white/50">Expirare</label>
                    <select
                      value={optionForm.expiration_days}
                      onChange={e => setOptionForm({...optionForm, expiration_days: parseInt(e.target.value)})}
                      className="w-full bg-black/50 border border-white/20 p-2 text-sm"
                    >
                      <option value={1}>1 zi</option>
                      <option value={7}>7 zile</option>
                      <option value={30}>30 zile</option>
                      <option value={90}>90 zile</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-xs text-white/50">Cantitate</label>
                    <input
                      type="number"
                      value={optionForm.quantity}
                      onChange={e => setOptionForm({...optionForm, quantity: parseInt(e.target.value) || 1})}
                      min={1}
                      max={100}
                      className="w-full bg-black/50 border border-white/20 p-2 text-sm"
                    />
                  </div>
                </div>
                <CyberButton variant="primary" className="w-full" onClick={handleBuyOption} disabled={processing}>
                  {processing ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Cumpără Option'}
                </CyberButton>
              </div>
              
              {/* Options Chain Table */}
              <div className="text-xs">
                <div className="grid grid-cols-5 gap-2 p-2 bg-white/5 font-mono text-white/50">
                  <div>Strike</div>
                  <div>Tip</div>
                  <div>Expirare</div>
                  <div>Premium</div>
                  <div>ITM</div>
                </div>
                {optionsChain.options?.slice(0, 20).map((opt, i) => (
                  <div 
                    key={i} 
                    className={`grid grid-cols-5 gap-2 p-2 border-b border-white/5 cursor-pointer hover:bg-white/5 ${opt.in_the_money ? 'bg-neon-green/5' : ''}`}
                    onClick={() => setOptionForm({
                      option_type: opt.option_type,
                      strike_price: opt.strike_price,
                      expiration_days: opt.expiration_days,
                      quantity: 1
                    })}
                  >
                    <div className="font-mono">{opt.strike_price}</div>
                    <div className={opt.option_type === 'call' ? 'text-neon-green' : 'text-neon-red'}>
                      {opt.option_type.toUpperCase()}
                    </div>
                    <div>{opt.expiration_days}z</div>
                    <div className="text-neon-yellow">{opt.premium} RLM</div>
                    <div>{opt.in_the_money ? '✓' : '-'}</div>
                  </div>
                ))}
              </div>
            </CyberCard>
          </div>
        )}
      </div>
    </div>
  );
};

export default DerivativesPage;
