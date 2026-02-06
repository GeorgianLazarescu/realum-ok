import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  TrendingUp, TrendingDown, DollarSign, BarChart3, 
  ArrowUpRight, ArrowDownRight, Briefcase, Activity,
  Loader2, RefreshCw, Search, ChevronRight
} from 'lucide-react';
import axios from 'axios';
import { API } from '../utils/api';
import { useAuth } from '../context/AuthContext';
import { CyberCard, CyberButton } from '../components/common/CyberUI';
import { toast } from 'sonner';

const StocksPage = () => {
  const { user, refreshUser } = useAuth();
  
  const [activeTab, setActiveTab] = useState('market'); // market, portfolio, transactions
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  
  // Data states
  const [marketData, setMarketData] = useState(null);
  const [portfolio, setPortfolio] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [selectedCompany, setSelectedCompany] = useState(null);
  
  // Trading modal
  const [showTradeModal, setShowTradeModal] = useState(false);
  const [tradeType, setTradeType] = useState('buy');
  const [tradeShares, setTradeShares] = useState(1);
  const [searchQuery, setSearchQuery] = useState('');
  
  useEffect(() => {
    fetchAllData();
    // Refresh market data every 30 seconds
    const interval = setInterval(fetchMarketData, 30000);
    return () => clearInterval(interval);
  }, []);
  
  const fetchAllData = async () => {
    await Promise.all([
      fetchMarketData(),
      fetchPortfolio(),
      fetchTransactions()
    ]);
    setLoading(false);
  };
  
  const fetchMarketData = async () => {
    try {
      const res = await axios.get(`${API}/stocks/market`);
      setMarketData(res.data);
    } catch (error) {
      console.error('Failed to load market data:', error);
    }
  };
  
  const fetchPortfolio = async () => {
    try {
      const res = await axios.get(`${API}/stocks/portfolio`);
      setPortfolio(res.data);
    } catch (error) {
      console.error('Failed to load portfolio:', error);
    }
  };
  
  const fetchTransactions = async () => {
    try {
      const res = await axios.get(`${API}/stocks/transactions`);
      setTransactions(res.data.transactions || []);
    } catch (error) {
      console.error('Failed to load transactions:', error);
    }
  };
  
  const fetchCompanyDetails = async (companyId) => {
    try {
      const res = await axios.get(`${API}/stocks/company/${companyId}`);
      setSelectedCompany(res.data);
    } catch (error) {
      toast.error('Failed to load company details');
    }
  };
  
  const handleTrade = async () => {
    if (!selectedCompany || tradeShares < 1) return;
    
    setProcessing(true);
    try {
      const endpoint = tradeType === 'buy' ? '/stocks/buy' : '/stocks/sell';
      const res = await axios.post(`${API}${endpoint}`, {
        company_id: selectedCompany.company.id,
        shares: tradeShares
      });
      toast.success(res.data.message);
      setShowTradeModal(false);
      setTradeShares(1);
      fetchAllData();
      refreshUser();
    } catch (error) {
      toast.error(error.response?.data?.detail || `Failed to ${tradeType} shares`);
    }
    setProcessing(false);
  };
  
  const openTradeModal = (company, type) => {
    fetchCompanyDetails(company.id);
    setTradeType(type);
    setTradeShares(1);
    setShowTradeModal(true);
  };
  
  const filteredCompanies = marketData?.companies?.filter(c => 
    c.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    c.symbol.toLowerCase().includes(searchQuery.toLowerCase())
  ) || [];
  
  const sectorColors = {
    technology: '#00F0FF',
    finance: '#22C55E',
    energy: '#F59E0B',
    real_estate: '#8B5CF6',
    education: '#EC4899',
    research: '#3B82F6',
    media: '#EF4444',
    commerce: '#14B8A6'
  };
  
  if (loading) {
    return (
      <div className="min-h-screen pt-20 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-neon-cyan" />
      </div>
    );
  }
  
  return (
    <div className="min-h-screen pt-16 sm:pt-20 pb-20 lg:pb-12 px-3 sm:px-4" data-testid="stocks-page">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-6">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <h1 className="text-2xl sm:text-3xl font-orbitron font-black flex items-center gap-3">
                <BarChart3 className="w-8 h-8 text-neon-green" />
                <span>Bursă <span className="text-neon-cyan">REALUM</span></span>
              </h1>
              <p className="text-white/60 text-sm mt-1">Tranzacționează acțiuni ale companiilor din metavers</p>
            </div>
            
            {/* Market Status */}
            <div className="flex gap-4 items-center">
              <div className={`px-3 py-1 text-sm flex items-center gap-2 ${marketData?.market_open ? 'bg-neon-green/20 text-neon-green border border-neon-green' : 'bg-red-500/20 text-red-400 border border-red-500'}`}>
                <Activity className="w-4 h-4" />
                {marketData?.market_open ? 'PIAȚĂ DESCHISĂ' : 'PIAȚĂ ÎNCHISĂ'}
              </div>
              <CyberButton variant="outline" size="sm" onClick={fetchAllData}>
                <RefreshCw className="w-4 h-4" />
              </CyberButton>
            </div>
          </div>
        </motion.div>
        
        {/* Market Overview Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
          <CyberCard className="p-4 text-center">
            <div className="text-xs text-white/50 mb-1">Volum Total</div>
            <div className="text-xl font-orbitron text-neon-cyan">
              {marketData?.total_volume?.toLocaleString() || 0}
            </div>
          </CyberCard>
          <CyberCard className="p-4 text-center">
            <div className="text-xs text-white/50 mb-1">Market Cap</div>
            <div className="text-xl font-orbitron text-neon-green">
              {(marketData?.total_market_cap / 1000000)?.toFixed(1) || 0}M
            </div>
          </CyberCard>
          <CyberCard className="p-4 text-center">
            <div className="text-xs text-white/50 mb-1">Portofoliu</div>
            <div className="text-xl font-orbitron text-neon-purple">
              {portfolio?.total_value?.toFixed(0) || 0} RLM
            </div>
          </CyberCard>
          <CyberCard className="p-4 text-center">
            <div className="text-xs text-white/50 mb-1">Profit/Pierdere</div>
            <div className={`text-xl font-orbitron ${(portfolio?.total_gain || 0) >= 0 ? 'text-neon-green' : 'text-neon-red'}`}>
              {(portfolio?.total_gain >= 0 ? '+' : '')}{portfolio?.total_gain?.toFixed(0) || 0}
            </div>
          </CyberCard>
        </div>
        
        {/* Tabs */}
        <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
          {[
            { id: 'market', label: 'Piață', icon: BarChart3 },
            { id: 'portfolio', label: 'Portofoliu', icon: Briefcase },
            { id: 'transactions', label: 'Tranzacții', icon: Activity }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-2 font-mono text-sm whitespace-nowrap flex items-center gap-2 transition-all ${
                activeTab === tab.id 
                  ? 'bg-neon-cyan/20 border border-neon-cyan text-neon-cyan' 
                  : 'border border-white/20 text-white/60 hover:border-white/40'
              }`}
              data-testid={`tab-${tab.id}`}
            >
              <tab.icon className="w-4 h-4" /> {tab.label}
            </button>
          ))}
        </div>
        
        {/* Tab Content */}
        <AnimatePresence mode="wait">
          {/* Market Tab */}
          {activeTab === 'market' && (
            <motion.div
              key="market"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              {/* Search */}
              <div className="mb-4">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/40" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={e => setSearchQuery(e.target.value)}
                    placeholder="Caută companii..."
                    className="w-full bg-black/50 border border-white/20 pl-10 pr-4 py-2 text-white placeholder-white/40"
                  />
                </div>
              </div>
              
              {/* Gainers & Losers */}
              <div className="grid md:grid-cols-2 gap-4 mb-6">
                <CyberCard className="p-4">
                  <h3 className="font-orbitron text-sm text-neon-green mb-3 flex items-center gap-2">
                    <TrendingUp className="w-4 h-4" /> Top Câștigători
                  </h3>
                  <div className="space-y-2">
                    {marketData?.gainers?.map(stock => (
                      <div key={stock.id} className="flex items-center justify-between p-2 bg-black/30 border border-neon-green/20">
                        <div>
                          <span className="font-mono text-neon-cyan">{stock.symbol}</span>
                          <span className="text-xs text-white/50 ml-2">{stock.name}</span>
                        </div>
                        <span className="text-neon-green font-mono flex items-center">
                          <ArrowUpRight className="w-3 h-3" />
                          +{stock.change_percent}%
                        </span>
                      </div>
                    ))}
                  </div>
                </CyberCard>
                
                <CyberCard className="p-4">
                  <h3 className="font-orbitron text-sm text-neon-red mb-3 flex items-center gap-2">
                    <TrendingDown className="w-4 h-4" /> Top Pierzători
                  </h3>
                  <div className="space-y-2">
                    {marketData?.losers?.map(stock => (
                      <div key={stock.id} className="flex items-center justify-between p-2 bg-black/30 border border-neon-red/20">
                        <div>
                          <span className="font-mono text-neon-cyan">{stock.symbol}</span>
                          <span className="text-xs text-white/50 ml-2">{stock.name}</span>
                        </div>
                        <span className="text-neon-red font-mono flex items-center">
                          <ArrowDownRight className="w-3 h-3" />
                          {stock.change_percent}%
                        </span>
                      </div>
                    ))}
                  </div>
                </CyberCard>
              </div>
              
              {/* All Stocks */}
              <CyberCard className="p-4">
                <h3 className="font-orbitron text-sm mb-4">Toate Acțiunile</h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-white/50 text-left border-b border-white/10">
                        <th className="pb-2 font-mono">SIMBOL</th>
                        <th className="pb-2 font-mono hidden md:table-cell">COMPANIE</th>
                        <th className="pb-2 font-mono">PREȚ</th>
                        <th className="pb-2 font-mono">SCHIMBARE</th>
                        <th className="pb-2 font-mono hidden sm:table-cell">VOLUM</th>
                        <th className="pb-2 font-mono">ACȚIUNI</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredCompanies.map(stock => (
                        <tr key={stock.id} className="border-b border-white/5 hover:bg-white/5">
                          <td className="py-3">
                            <div className="flex items-center gap-2">
                              <div 
                                className="w-2 h-2 rounded-full" 
                                style={{ backgroundColor: sectorColors[stock.sector] || '#888' }}
                              />
                              <span className="font-mono text-neon-cyan">{stock.symbol}</span>
                            </div>
                          </td>
                          <td className="py-3 hidden md:table-cell text-white/70">{stock.name}</td>
                          <td className="py-3 font-mono">{stock.current_price?.toFixed(2)} RLM</td>
                          <td className="py-3">
                            <span className={`font-mono flex items-center gap-1 ${stock.change_percent >= 0 ? 'text-neon-green' : 'text-neon-red'}`}>
                              {stock.change_percent >= 0 ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
                              {stock.change_percent >= 0 ? '+' : ''}{stock.change_percent}%
                            </span>
                          </td>
                          <td className="py-3 font-mono text-white/50 hidden sm:table-cell">{stock.volume_today?.toLocaleString()}</td>
                          <td className="py-3">
                            <div className="flex gap-1">
                              <button
                                onClick={() => openTradeModal(stock, 'buy')}
                                className="px-2 py-1 text-xs bg-neon-green/20 text-neon-green border border-neon-green/50 hover:bg-neon-green/30"
                              >
                                Cumpără
                              </button>
                              <button
                                onClick={() => openTradeModal(stock, 'sell')}
                                className="px-2 py-1 text-xs bg-neon-red/20 text-neon-red border border-neon-red/50 hover:bg-neon-red/30"
                              >
                                Vinde
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CyberCard>
            </motion.div>
          )}
          
          {/* Portfolio Tab */}
          {activeTab === 'portfolio' && (
            <motion.div
              key="portfolio"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              {/* Portfolio Summary */}
              <CyberCard className="p-4 mb-6">
                <h3 className="font-orbitron text-sm mb-4">Rezumat Portofoliu</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="p-3 bg-black/30 border border-white/10">
                    <div className="text-xs text-white/50 mb-1">Valoare Totală</div>
                    <div className="font-orbitron text-neon-cyan text-xl">{portfolio?.total_value?.toFixed(2)} RLM</div>
                  </div>
                  <div className="p-3 bg-black/30 border border-white/10">
                    <div className="text-xs text-white/50 mb-1">Cost Total</div>
                    <div className="font-orbitron text-white text-xl">{portfolio?.total_cost?.toFixed(2)} RLM</div>
                  </div>
                  <div className="p-3 bg-black/30 border border-white/10">
                    <div className="text-xs text-white/50 mb-1">Profit/Pierdere</div>
                    <div className={`font-orbitron text-xl ${portfolio?.total_gain >= 0 ? 'text-neon-green' : 'text-neon-red'}`}>
                      {portfolio?.total_gain >= 0 ? '+' : ''}{portfolio?.total_gain?.toFixed(2)} RLM
                    </div>
                  </div>
                  <div className="p-3 bg-black/30 border border-white/10">
                    <div className="text-xs text-white/50 mb-1">Randament</div>
                    <div className={`font-orbitron text-xl ${portfolio?.gain_percent >= 0 ? 'text-neon-green' : 'text-neon-red'}`}>
                      {portfolio?.gain_percent >= 0 ? '+' : ''}{portfolio?.gain_percent}%
                    </div>
                  </div>
                </div>
              </CyberCard>
              
              {/* Holdings */}
              <CyberCard className="p-4">
                <h3 className="font-orbitron text-sm mb-4">Dețineri</h3>
                {portfolio?.holdings?.length > 0 ? (
                  <div className="space-y-3">
                    {portfolio.holdings.map(holding => {
                      const gain = holding.market_value - holding.total_cost;
                      const gainPercent = ((gain / holding.total_cost) * 100).toFixed(2);
                      return (
                        <div key={holding.company_id} className="p-4 bg-black/30 border border-white/10">
                          <div className="flex flex-wrap items-start justify-between gap-4">
                            <div>
                              <div className="font-orbitron text-neon-cyan">{holding.symbol}</div>
                              <div className="text-sm text-white/60">{holding.company_name}</div>
                            </div>
                            <div className="text-right">
                              <div className="font-mono text-lg">{holding.shares} acțiuni</div>
                              <div className="text-sm text-white/50">@ {holding.average_price?.toFixed(2)} RLM avg</div>
                            </div>
                          </div>
                          <div className="mt-3 pt-3 border-t border-white/10 flex flex-wrap justify-between gap-4">
                            <div>
                              <span className="text-xs text-white/50">Valoare: </span>
                              <span className="font-mono">{holding.market_value?.toFixed(2)} RLM</span>
                            </div>
                            <div>
                              <span className="text-xs text-white/50">Preț curent: </span>
                              <span className="font-mono">{holding.current_price?.toFixed(2)} RLM</span>
                            </div>
                            <div className={gain >= 0 ? 'text-neon-green' : 'text-neon-red'}>
                              <span className="text-xs text-white/50">P/L: </span>
                              <span className="font-mono">{gain >= 0 ? '+' : ''}{gain.toFixed(2)} ({gainPercent}%)</span>
                            </div>
                          </div>
                          <div className="mt-3 flex gap-2">
                            <CyberButton 
                              variant="outline" 
                              size="sm"
                              onClick={() => {
                                fetchCompanyDetails(holding.company_id);
                                setTradeType('buy');
                                setTradeShares(1);
                                setShowTradeModal(true);
                              }}
                            >
                              Cumpără Mai Mult
                            </CyberButton>
                            <CyberButton 
                              variant="outline" 
                              size="sm"
                              onClick={() => {
                                fetchCompanyDetails(holding.company_id);
                                setTradeType('sell');
                                setTradeShares(holding.shares);
                                setShowTradeModal(true);
                              }}
                            >
                              Vinde
                            </CyberButton>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div className="text-center py-12 text-white/50">
                    <Briefcase className="w-12 h-12 mx-auto mb-4 opacity-50" />
                    <p>Nu ai nicio acțiune. Începe să investești!</p>
                  </div>
                )}
              </CyberCard>
            </motion.div>
          )}
          
          {/* Transactions Tab */}
          {activeTab === 'transactions' && (
            <motion.div
              key="transactions"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <CyberCard className="p-4">
                <h3 className="font-orbitron text-sm mb-4">Istoric Tranzacții</h3>
                {transactions.length > 0 ? (
                  <div className="space-y-2">
                    {transactions.map(tx => (
                      <div 
                        key={tx.id} 
                        className={`p-3 bg-black/30 border-l-2 ${tx.type === 'buy' ? 'border-neon-green' : 'border-neon-red'}`}
                      >
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <div className="flex items-center gap-3">
                            <span className={`px-2 py-0.5 text-xs ${tx.type === 'buy' ? 'bg-neon-green/20 text-neon-green' : 'bg-neon-red/20 text-neon-red'}`}>
                              {tx.type === 'buy' ? 'CUMPĂRARE' : 'VÂNZARE'}
                            </span>
                            <span className="font-mono text-neon-cyan">{tx.company_symbol}</span>
                            <span className="text-white/60">{tx.shares} acțiuni</span>
                          </div>
                          <div className="text-right">
                            <div className="font-mono">{tx.total?.toFixed(2)} RLM</div>
                            <div className="text-xs text-white/40">@ {tx.price_per_share?.toFixed(2)}/acțiune</div>
                          </div>
                        </div>
                        {tx.profit !== undefined && tx.type === 'sell' && (
                          <div className={`mt-2 text-sm ${tx.profit >= 0 ? 'text-neon-green' : 'text-neon-red'}`}>
                            Profit: {tx.profit >= 0 ? '+' : ''}{tx.profit?.toFixed(2)} RLM
                          </div>
                        )}
                        <div className="mt-1 text-xs text-white/40">
                          {new Date(tx.executed_at).toLocaleString()}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-12 text-white/50">
                    <Activity className="w-12 h-12 mx-auto mb-4 opacity-50" />
                    <p>Nicio tranzacție încă.</p>
                  </div>
                )}
              </CyberCard>
            </motion.div>
          )}
        </AnimatePresence>
        
        {/* Trade Modal */}
        <AnimatePresence>
          {showTradeModal && selectedCompany && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4"
              onClick={() => setShowTradeModal(false)}
            >
              <motion.div
                initial={{ scale: 0.9 }}
                animate={{ scale: 1 }}
                exit={{ scale: 0.9 }}
                className={`bg-gray-900 border p-6 max-w-md w-full ${tradeType === 'buy' ? 'border-neon-green' : 'border-neon-red'}`}
                onClick={e => e.stopPropagation()}
              >
                <h3 className="font-orbitron text-xl mb-4 flex items-center gap-2">
                  {tradeType === 'buy' ? (
                    <TrendingUp className="w-5 h-5 text-neon-green" />
                  ) : (
                    <TrendingDown className="w-5 h-5 text-neon-red" />
                  )}
                  {tradeType === 'buy' ? 'Cumpără' : 'Vinde'} {selectedCompany.company.symbol}
                </h3>
                
                <div className="space-y-4">
                  <div className="p-3 bg-black/30 border border-white/10">
                    <div className="text-sm text-white/60">{selectedCompany.company.name}</div>
                    <div className="flex justify-between items-center mt-2">
                      <span className="text-white/50">Preț curent:</span>
                      <span className="font-orbitron text-xl text-neon-cyan">
                        {selectedCompany.company.current_price?.toFixed(2)} RLM
                      </span>
                    </div>
                    <div className="flex justify-between items-center mt-1">
                      <span className="text-white/50">Schimbare:</span>
                      <span className={`font-mono ${selectedCompany.change_percent >= 0 ? 'text-neon-green' : 'text-neon-red'}`}>
                        {selectedCompany.change_percent >= 0 ? '+' : ''}{selectedCompany.change_percent}%
                      </span>
                    </div>
                  </div>
                  
                  <div>
                    <label className="text-sm text-white/60 block mb-1">Număr Acțiuni</label>
                    <input
                      type="number"
                      min="1"
                      max="10000"
                      value={tradeShares}
                      onChange={e => setTradeShares(Math.max(1, parseInt(e.target.value) || 1))}
                      className="w-full bg-black/50 border border-white/20 p-2 text-white text-center text-xl font-mono"
                    />
                  </div>
                  
                  <div className="p-3 bg-black/30 border border-white/10">
                    <div className="flex justify-between text-sm">
                      <span className="text-white/50">Subtotal:</span>
                      <span className="font-mono">{(selectedCompany.company.current_price * tradeShares).toFixed(2)} RLM</span>
                    </div>
                    <div className="flex justify-between text-sm mt-1">
                      <span className="text-white/50">Comision ({marketData?.trading_fee_percent}%):</span>
                      <span className="font-mono text-white/70">
                        {(selectedCompany.company.current_price * tradeShares * (marketData?.trading_fee_percent || 0.1) / 100).toFixed(2)} RLM
                      </span>
                    </div>
                    <div className="flex justify-between text-lg mt-2 pt-2 border-t border-white/10">
                      <span className="text-white/70">Total:</span>
                      <span className={`font-orbitron ${tradeType === 'buy' ? 'text-neon-red' : 'text-neon-green'}`}>
                        {tradeType === 'buy' 
                          ? (selectedCompany.company.current_price * tradeShares * (1 + (marketData?.trading_fee_percent || 0.1) / 100)).toFixed(2)
                          : (selectedCompany.company.current_price * tradeShares * (1 - (marketData?.trading_fee_percent || 0.1) / 100)).toFixed(2)
                        } RLM
                      </span>
                    </div>
                  </div>
                  
                  <div className="text-xs text-white/40">
                    Balanță disponibilă: <span className="text-neon-cyan">{user?.realum_balance?.toFixed(2)} RLM</span>
                  </div>
                </div>
                
                <div className="flex gap-3 mt-6">
                  <CyberButton variant="outline" className="flex-1" onClick={() => setShowTradeModal(false)}>
                    Anulează
                  </CyberButton>
                  <CyberButton 
                    variant={tradeType === 'buy' ? 'primary' : 'outline'}
                    className={`flex-1 ${tradeType === 'sell' ? '!border-neon-red !text-neon-red hover:!bg-neon-red/20' : ''}`}
                    onClick={handleTrade}
                    disabled={processing}
                  >
                    {processing ? <Loader2 className="w-4 h-4 animate-spin" /> : (tradeType === 'buy' ? 'Cumpără' : 'Vinde')}
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

export default StocksPage;
