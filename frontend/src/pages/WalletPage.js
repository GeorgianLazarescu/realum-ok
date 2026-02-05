import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Wallet as WalletIcon, Send, ArrowUpRight, ArrowDownRight, Flame, ExternalLink, Link2 } from 'lucide-react';
import axios from 'axios';
import { API } from '../utils/api';
import { useAuth } from '../context/AuthContext';
import { useWeb3 } from '../context/Web3Context';
import { useTranslation } from '../context/LanguageContext';
import { CyberCard, CyberButton } from '../components/common/CyberUI';
import WalletConnect from '../components/common/WalletConnect';

const WalletPage = () => {
  const { user, refreshUser } = useAuth();
  const { account, chainName, isConnected, formatAddress } = useWeb3();
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
      axios.get(`${API}/wallet`).then(res => setWallet(res.data));
    } catch (err) {
      alert(err.response?.data?.detail || 'Transfer failed');
    }
  };
  
  const transactions = wallet?.transactions?.slice(-20).reverse() || [];
  const linkedWallet = user?.wallet_address;
  
  return (
    <div className="min-h-screen pt-16 sm:pt-20 pb-20 lg:pb-12 px-3 sm:px-4" data-testid="wallet-page">
      <div className="max-w-4xl mx-auto">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-6 sm:mb-8">
          <h1 className="text-2xl sm:text-3xl md:text-4xl font-orbitron font-black flex items-center gap-3">
            <WalletIcon className="w-8 h-8 sm:w-10 sm:h-10 text-neon-cyan" />
            {t('wallet')}
          </h1>
          <p className="text-white/60 mt-2 text-sm sm:text-base">Manage your RLM tokens and Web3 wallet</p>
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
                <div className="flex flex-col sm:flex-row gap-2">
                  <CyberButton onClick={() => setShowTransfer(!showTransfer)} className="w-full sm:w-auto">
                    <Send className="w-4 h-4 inline mr-2" /> {t('transfer')}
                  </CyberButton>
                  <CyberButton 
                    onClick={() => window.location.href = '/purchase-rlm'} 
                    className="w-full sm:w-auto bg-green-500/20 border-green-500 hover:bg-green-500/30"
                  >
                    <ArrowDownRight className="w-4 h-4 inline mr-2" /> Buy RLM
                  </CyberButton>
                </div>
              </div>
            </CyberCard>

            {/* Web3 Wallet Section */}
            <CyberCard className="mb-6">
              <h3 className="font-orbitron font-bold mb-4 text-sm sm:text-base flex items-center gap-2">
                <Link2 className="w-5 h-5 text-neon-purple" />
                Web3 Wallet
              </h3>
              
              <div className="grid sm:grid-cols-2 gap-4">
                {/* Connected MetaMask */}
                <div className="p-4 bg-white/5 border border-white/10">
                  <div className="text-xs text-white/50 mb-2">MetaMask Status</div>
                  {isConnected ? (
                    <div>
                      <div className="flex items-center gap-2 mb-2">
                        <div className="w-2 h-2 bg-neon-green rounded-full animate-pulse" />
                        <span className="text-sm text-neon-green">Connected</span>
                      </div>
                      <div className="font-mono text-xs text-white/70 break-all">{account}</div>
                      <div className="text-xs text-white/50 mt-1">{chainName}</div>
                    </div>
                  ) : (
                    <div>
                      <div className="flex items-center gap-2 mb-3">
                        <div className="w-2 h-2 bg-white/30 rounded-full" />
                        <span className="text-sm text-white/50">Not Connected</span>
                      </div>
                      <WalletConnect />
                    </div>
                  )}
                </div>

                {/* Linked Wallet */}
                <div className="p-4 bg-white/5 border border-white/10">
                  <div className="text-xs text-white/50 mb-2">Linked to REALUM</div>
                  {linkedWallet ? (
                    <div>
                      <div className="flex items-center gap-2 mb-2">
                        <div className="w-2 h-2 bg-neon-cyan rounded-full" />
                        <span className="text-sm text-neon-cyan">Linked</span>
                      </div>
                      <div className="font-mono text-xs text-white/70 break-all">{linkedWallet}</div>
                      <a 
                        href={`https://etherscan.io/address/${linkedWallet}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs text-neon-cyan hover:underline mt-2 inline-flex items-center gap-1"
                      >
                        View on Etherscan <ExternalLink className="w-3 h-3" />
                      </a>
                    </div>
                  ) : (
                    <div>
                      <div className="flex items-center gap-2 mb-3">
                        <div className="w-2 h-2 bg-white/30 rounded-full" />
                        <span className="text-sm text-white/50">Not Linked</span>
                      </div>
                      <p className="text-xs text-white/40">
                        Connect MetaMask and link to enable Web3 features
                      </p>
                    </div>
                  )}
                </div>
              </div>

              {/* Future Features Notice */}
              <div className="mt-4 p-3 bg-neon-purple/10 border border-neon-purple/30">
                <div className="text-xs text-neon-purple font-medium mb-1">Coming Soon</div>
                <p className="text-xs text-white/60">
                  Real blockchain integration with MultiversX/Polygon for on-chain RLM tokens, NFT badges, and decentralized identity
                </p>
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
