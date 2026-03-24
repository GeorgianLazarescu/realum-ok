import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { 
  Landmark, Coins, PiggyBank, Receipt, TrendingUp,
  Users, Award, FileText, Loader2, ChevronRight,
  DollarSign, Percent, Building
} from 'lucide-react';
import axios from 'axios';
import { API } from '../utils/api';
import { useAuth } from '../context/AuthContext';
import { CyberCard, CyberButton } from '../components/common/CyberUI';
import { toast } from 'sonner';

const TreasuryPage = () => {
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [treasuryInfo, setTreasuryInfo] = useState(null);
  const [budget, setBudget] = useState(null);
  const [myTaxes, setMyTaxes] = useState([]);
  const [statistics, setStatistics] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');

  useEffect(() => {
    fetchAllData();
  }, []);

  const fetchAllData = async () => {
    try {
      const [infoRes, budgetRes, statsRes] = await Promise.all([
        axios.get(`${API}/treasury/info`),
        axios.get(`${API}/treasury/budget`),
        axios.get(`${API}/treasury/statistics`)
      ]);
      setTreasuryInfo(infoRes.data);
      setBudget(budgetRes.data);
      setStatistics(statsRes.data);
      
      // Fetch user taxes if logged in
      try {
        const taxRes = await axios.get(`${API}/treasury/my-taxes`);
        setMyTaxes(taxRes.data.taxes || []);
      } catch (e) {}
    } catch (error) {
      console.error('Failed to load treasury data:', error);
    }
    setLoading(false);
  };

  if (loading) {
    return (
      <div className="min-h-screen pt-20 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-neon-cyan" />
      </div>
    );
  }

  return (
    <div className="min-h-screen pt-16 sm:pt-20 pb-20 lg:pb-12 px-3 sm:px-4" data-testid="treasury-page">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-6">
          <h1 className="text-2xl sm:text-3xl font-orbitron font-black flex items-center gap-3">
            <Landmark className="w-8 h-8 text-neon-yellow" />
            <span>Trezoreria <span className="text-neon-cyan">REALUM</span></span>
          </h1>
          <p className="text-white/60 text-sm mt-1">Taxe, bugete și cheltuieli publice</p>
        </motion.div>

        {/* Treasury Balance */}
        <div className="grid md:grid-cols-3 gap-4 mb-6">
          <CyberCard className="p-6 text-center border-neon-yellow/30">
            <PiggyBank className="w-10 h-10 mx-auto mb-2 text-neon-yellow" />
            <div className="text-3xl font-orbitron text-neon-yellow">
              {treasuryInfo?.world_treasury?.balance?.toFixed(0) || 0}
            </div>
            <div className="text-sm text-white/50">RLM în Trezorerie</div>
          </CyberCard>
          
          <CyberCard className="p-6 text-center border-neon-green/30">
            <TrendingUp className="w-10 h-10 mx-auto mb-2 text-neon-green" />
            <div className="text-3xl font-orbitron text-neon-green">
              {treasuryInfo?.world_treasury?.total_collected?.toFixed(0) || 0}
            </div>
            <div className="text-sm text-white/50">Total Colectat</div>
          </CyberCard>
          
          <CyberCard className="p-6 text-center border-neon-purple/30">
            <Receipt className="w-10 h-10 mx-auto mb-2 text-neon-purple" />
            <div className="text-3xl font-orbitron text-neon-purple">
              {treasuryInfo?.world_treasury?.total_spent?.toFixed(0) || 0}
            </div>
            <div className="text-sm text-white/50">Total Cheltuit</div>
          </CyberCard>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
          {[
            { id: 'overview', label: 'Prezentare', icon: Landmark },
            { id: 'taxes', label: 'Taxele Mele', icon: Receipt },
            { id: 'budget', label: 'Buget', icon: PiggyBank }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-2 font-mono text-sm whitespace-nowrap flex items-center gap-2 transition-all ${
                activeTab === tab.id 
                  ? 'bg-neon-yellow/20 border border-neon-yellow text-neon-yellow' 
                  : 'border border-white/20 text-white/60 hover:border-white/40'
              }`}
            >
              <tab.icon className="w-4 h-4" /> {tab.label}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        {activeTab === 'overview' && (
          <div className="grid md:grid-cols-2 gap-6">
            {/* Tax Rates */}
            <CyberCard className="p-4">
              <h3 className="font-orbitron text-lg mb-4 flex items-center gap-2">
                <Percent className="w-5 h-5 text-neon-cyan" /> Rate de Impozitare
              </h3>
              <div className="space-y-3">
                {Object.entries(treasuryInfo?.tax_rates || {}).map(([key, rate]) => (
                  <div key={key} className="flex justify-between items-center p-2 bg-black/30 border border-white/10">
                    <span className="text-white/70 capitalize">{key.replace(/_/g, ' ')}</span>
                    <span className="font-mono text-neon-cyan">{(rate * 100).toFixed(1)}%</span>
                  </div>
                ))}
              </div>
            </CyberCard>

            {/* Budget Categories */}
            <CyberCard className="p-4">
              <h3 className="font-orbitron text-lg mb-4 flex items-center gap-2">
                <Building className="w-5 h-5 text-neon-purple" /> Categorii Buget
              </h3>
              <div className="space-y-3">
                {treasuryInfo?.budget_categories?.map(cat => (
                  <div key={cat.id} className="p-3 bg-black/30 border border-white/10">
                    <div className="font-mono text-neon-cyan">{cat.name}</div>
                    <div className="text-xs text-white/50 mt-1">{cat.description}</div>
                    <div className="text-sm text-neon-green mt-2">
                      Cheltuit: {budget?.spending_by_category?.[cat.id]?.toFixed(0) || 0} RLM
                    </div>
                  </div>
                ))}
              </div>
            </CyberCard>

            {/* Top Taxpayers */}
            <CyberCard className="p-4 md:col-span-2">
              <h3 className="font-orbitron text-lg mb-4 flex items-center gap-2">
                <Award className="w-5 h-5 text-neon-yellow" /> Top Contribuabili
              </h3>
              <div className="grid md:grid-cols-2 lg:grid-cols-5 gap-3">
                {statistics?.top_taxpayers?.slice(0, 5).map((tp, i) => (
                  <div key={i} className="p-3 bg-black/30 border border-white/10 text-center">
                    <div className="text-2xl font-orbitron text-neon-yellow">#{i + 1}</div>
                    <div className="font-mono text-neon-cyan mt-1">{tp.username}</div>
                    <div className="text-sm text-white/50">{tp.total_paid?.toFixed(0)} RLM</div>
                  </div>
                ))}
              </div>
            </CyberCard>
          </div>
        )}

        {activeTab === 'taxes' && (
          <CyberCard className="p-4">
            <h3 className="font-orbitron text-lg mb-4">Istoricul Taxelor Tale</h3>
            {myTaxes.length > 0 ? (
              <div className="space-y-2">
                {myTaxes.map(tax => (
                  <div key={tax.id} className="p-3 bg-black/30 border border-white/10 flex justify-between items-center">
                    <div>
                      <div className="font-mono text-white/70 capitalize">{tax.tax_type?.replace(/_/g, ' ')}</div>
                      <div className="text-xs text-white/40">{tax.description}</div>
                      <div className="text-xs text-white/30">{new Date(tax.collected_at).toLocaleString()}</div>
                    </div>
                    <div className="text-right">
                      <div className="font-orbitron text-neon-red">-{tax.amount?.toFixed(2)} RLM</div>
                      <div className="text-xs text-white/40">din {tax.base_amount?.toFixed(0)} RLM</div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-12 text-white/50">
                <Receipt className="w-12 h-12 mx-auto mb-4 opacity-50" />
                <p>Nu ai plătit taxe încă.</p>
              </div>
            )}
          </CyberCard>
        )}

        {activeTab === 'budget' && (
          <div className="space-y-6">
            <CyberCard className="p-4">
              <h3 className="font-orbitron text-lg mb-4">Buget Public</h3>
              <div className="text-center py-8">
                <div className="text-4xl font-orbitron text-neon-yellow mb-2">
                  {budget?.treasury_balance?.toFixed(0) || 0} RLM
                </div>
                <div className="text-white/50">Disponibil pentru alocare</div>
              </div>
            </CyberCard>

            {/* Recent Spending */}
            <CyberCard className="p-4">
              <h3 className="font-orbitron text-lg mb-4">Cheltuieli Recente</h3>
              {treasuryInfo?.recent_spending?.length > 0 ? (
                <div className="space-y-2">
                  {treasuryInfo.recent_spending.map(spend => (
                    <div key={spend.id} className="p-3 bg-black/30 border border-white/10">
                      <div className="flex justify-between">
                        <span className="text-neon-cyan">{spend.category}</span>
                        <span className="font-mono text-neon-red">-{spend.amount} RLM</span>
                      </div>
                      <div className="text-sm text-white/50 mt-1">{spend.description}</div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-white/50">
                  Nicio cheltuială înregistrată.
                </div>
              )}
            </CyberCard>
          </div>
        )}
      </div>
    </div>
  );
};

export default TreasuryPage;
