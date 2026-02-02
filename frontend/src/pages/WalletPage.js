import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Wallet as WalletIcon, Send, ArrowUpRight, ArrowDownRight, Flame } from 'lucide-react';
import axios from 'axios';
import { API } from '../utils/api';
import { useAuth } from '../context/AuthContext';
import { useTranslation } from '../context/LanguageContext';
import { CyberCard, CyberButton } from '../components/common/CyberUI';

const WalletPage = () => {
  const { user, refreshUser } = useAuth();
  const t = useTranslation();
  const [wallet, setWallet] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showTransfer, setShowTransfer] = useState(false);
  const [transfer, setTransfer] = useState({ to_user_id: '', amount: '', reason: '' });
  const [users, setUsers] = useState([]);
  
  useEffect(() => {
    Promise.all([
      axios.get(`${API}/wallet`),
      axios.get(`${API}/leaderboard`)
    ]).then(([walletRes, usersRes]) => {
      setWallet(walletRes.data);
      setUsers(usersRes.data.leaderboard || []);
    }).catch(console.error).finally(() => setLoading(false));
  }, []);
  
  const handleTransfer = async (e) => {
    e.preventDefault();
    try {
      const res = await axios.post(`${API}/wallet/transfer`, {
        ...transfer,
        amount: parseFloat(transfer.amount)
      });
      alert(`Transferred! Amount: ${res.data.amount_sent} RLM, Burned: ${res.data.amount_burned} RLM`);
      refreshUser();
      setShowTransfer(false);
      setTransfer({ to_user_id: '', amount: '', reason: '' });
      // Refresh wallet
      axios.get(`${API}/wallet`).then(res => setWallet(res.data));
    } catch (err) {
      alert(err.response?.data?.detail || 'Transfer failed');
    }
  };
  
  const transactions = wallet?.transactions?.slice(-20).reverse() || [];
  
  return (
    <div className="min-h-screen pt-16 sm:pt-20 pb-20 lg:pb-12 px-3 sm:px-4" data-testid="wallet-page">
      <div className="max-w-4xl mx-auto">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-6 sm:mb-8">
          <h1 className="text-2xl sm:text-3xl md:text-4xl font-orbitron font-black flex items-center gap-3">
            <WalletIcon className="w-8 h-8 sm:w-10 sm:h-10 text-neon-cyan" />
            {t('wallet')}
          </h1>
          <p className="text-white/60 mt-2 text-sm sm:text-base">Manage your RLM tokens</p>
        </motion.div>
        
        {loading ? (
          <div className="text-center text-white/50">{t('loading')}</div>
        ) : (
          <>
            {/* Balance Card */}
            <CyberCard className="mb-6" glow>
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                <div>
                  <div className="text-xs sm:text-sm text-white/50 mb-1">Current Balance</div>
                  <div className="text-3xl sm:text-4xl md:text-5xl font-orbitron font-black text-neon-cyan" data-testid="wallet-balance">
                    {user?.realum_balance?.toFixed(2)} <span className="text-lg sm:text-xl">RLM</span>
                  </div>
                </div>
                <CyberButton onClick={() => setShowTransfer(!showTransfer)} className="w-full sm:w-auto">
                  <Send className="w-4 h-4 inline mr-2" /> {t('transfer')}
                </CyberButton>
              </div>
            </CyberCard>
            
            {/* Transfer Form */}
            {showTransfer && (
              <CyberCard className="mb-6">
                <h3 className="font-orbitron font-bold mb-4 text-sm sm:text-base">Send RLM</h3>
                <form onSubmit={handleTransfer} className="space-y-4">
                  <div>
                    <label className="text-xs uppercase tracking-wider text-white/50 mb-1 block">Recipient</label>
                    <select
                      value={transfer.to_user_id}
                      onChange={(e) => setTransfer({...transfer, to_user_id: e.target.value})}
                      required
                      className="w-full bg-black/50 border border-white/20 px-4 py-3 text-white focus:border-neon-cyan focus:outline-none text-sm"
                    >
                      <option value="">Select user...</option>
                      {users.filter(u => u.id !== user?.id).map(u => (
                        <option key={u.id} value={u.id}>{u.username}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="text-xs uppercase tracking-wider text-white/50 mb-1 block">Amount (RLM)</label>
                    <input
                      type="number"
                      value={transfer.amount}
                      onChange={(e) => setTransfer({...transfer, amount: e.target.value})}
                      required
                      min="1"
                      max={user?.realum_balance}
                      step="0.01"
                      className="w-full bg-black/50 border border-white/20 px-4 py-3 text-white focus:border-neon-cyan focus:outline-none text-sm"
                    />
                    <div className="text-xs text-white/40 mt-1">2% will be burned as transaction tax</div>
                  </div>
                  <div>
                    <label className="text-xs uppercase tracking-wider text-white/50 mb-1 block">Reason (optional)</label>
                    <input
                      type="text"
                      value={transfer.reason}
                      onChange={(e) => setTransfer({...transfer, reason: e.target.value})}
                      className="w-full bg-black/50 border border-white/20 px-4 py-3 text-white focus:border-neon-cyan focus:outline-none text-sm"
                    />
                  </div>
                  <div className="flex gap-2">
                    <CyberButton type="submit" className="flex-1">Send</CyberButton>
                    <CyberButton type="button" variant="ghost" onClick={() => setShowTransfer(false)}>{t('cancel')}</CyberButton>
                  </div>
                </form>
              </CyberCard>
            )}
            
            {/* Transactions */}
            <CyberCard>
              <h3 className="font-orbitron font-bold mb-4 text-sm sm:text-base">Recent Transactions</h3>
              {transactions.length === 0 ? (
                <div className="text-center text-white/50 py-8">{t('noData')}</div>
              ) : (
                <div className="space-y-2">
                  {transactions.map(tx => (
                    <div key={tx.id} className="flex items-center justify-between p-3 bg-black/30 border border-white/10">
                      <div className="flex items-center gap-3">
                        <div className={`w-8 h-8 sm:w-10 sm:h-10 flex items-center justify-center ${
                          tx.type === 'credit' ? 'bg-neon-green/10 text-neon-green' : 'bg-neon-red/10 text-neon-red'
                        }`}>
                          {tx.type === 'credit' ? <ArrowDownRight className="w-4 h-4 sm:w-5 sm:h-5" /> : <ArrowUpRight className="w-4 h-4 sm:w-5 sm:h-5" />}
                        </div>
                        <div>
                          <div className="text-xs sm:text-sm font-mono">{tx.description}</div>
                          <div className="text-[10px] sm:text-xs text-white/50">
                            {new Date(tx.timestamp).toLocaleString()}
                          </div>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className={`font-mono text-sm sm:text-base ${tx.type === 'credit' ? 'text-neon-green' : 'text-neon-red'}`}>
                          {tx.type === 'credit' ? '+' : '-'}{tx.amount.toFixed(2)}
                        </div>
                        {tx.burned > 0 && (
                          <div className="text-[10px] text-neon-red/70 flex items-center gap-1 justify-end">
                            <Flame className="w-3 h-3" /> {tx.burned.toFixed(2)}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CyberCard>
          </>
        )}
      </div>
    </div>
  );
};

export default WalletPage;
