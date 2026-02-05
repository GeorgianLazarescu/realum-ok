import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Building2, Wallet, PiggyBank, CreditCard, TrendingUp, ArrowDownRight,
  ArrowUpRight, Clock, Gift, AlertTriangle, Check, X, Loader2,
  DollarSign, Percent, Calendar, Users, Trophy, Send
} from 'lucide-react';
import axios from 'axios';
import { API } from '../utils/api';
import { useAuth } from '../context/AuthContext';
import { CyberCard, CyberButton } from '../components/common/CyberUI';
import { toast } from 'sonner';

const BankPage = () => {
  const { user, refreshUser } = useAuth();
  
  const [bankInfo, setBankInfo] = useState(null);
  const [account, setAccount] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [leaderboard, setLeaderboard] = useState([]);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [activeTab, setActiveTab] = useState('overview');
  
  // Modal states
  const [showDepositModal, setShowDepositModal] = useState(false);
  const [showWithdrawModal, setShowWithdrawModal] = useState(false);
  const [showTermDepositModal, setShowTermDepositModal] = useState(false);
  const [showLoanModal, setShowLoanModal] = useState(false);
  const [showTransferModal, setShowTransferModal] = useState(false);
  
  // Form states
  const [amount, setAmount] = useState('');
  const [selectedTerm, setSelectedTerm] = useState('7_days');
  const [loanPurpose, setLoanPurpose] = useState('');
  const [transferTo, setTransferTo] = useState('');
  const [transferNote, setTransferNote] = useState('');
  const [loanEligibility, setLoanEligibility] = useState(null);
  
  useEffect(() => {
    fetchAllData();
  }, []);
  
  const fetchAllData = async () => {
    try {
      const [infoRes, accountRes, txRes, lbRes] = await Promise.all([
        axios.get(`${API}/bank/info`),
        axios.get(`${API}/bank/account`),
        axios.get(`${API}/bank/transactions?limit=20`),
        axios.get(`${API}/bank/leaderboard`)
      ]);
      setBankInfo(infoRes.data);
      setAccount(accountRes.data);
      setTransactions(txRes.data.transactions || []);
      setLeaderboard(lbRes.data.leaderboard || []);
    } catch (error) {
      console.error('Failed to load bank data:', error);
    }
    setLoading(false);
  };
  
  const handleDeposit = async (accountType = 'savings') => {
    if (!amount || parseFloat(amount) <= 0) {
      toast.error('Enter a valid amount');
      return;
    }
    setProcessing(true);
    try {
      const res = await axios.post(`${API}/bank/deposit/wallet?account_type=${accountType}`, {
        amount: parseFloat(amount)
      });
      toast.success(res.data.message);
      setShowDepositModal(false);
      setAmount('');
      fetchAllData();
      refreshUser();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Deposit failed');
    }
    setProcessing(false);
  };
  
  const handleWithdraw = async (accountType = 'savings') => {
    if (!amount || parseFloat(amount) <= 0) {
      toast.error('Enter a valid amount');
      return;
    }
    setProcessing(true);
    try {
      const res = await axios.post(`${API}/bank/withdraw/wallet?account_type=${accountType}`, {
        amount: parseFloat(amount)
      });
      toast.success(res.data.message);
      setShowWithdrawModal(false);
      setAmount('');
      fetchAllData();
      refreshUser();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Withdrawal failed');
    }
    setProcessing(false);
  };
  
  const handleTermDeposit = async () => {
    if (!amount || parseFloat(amount) <= 0) {
      toast.error('Enter a valid amount');
      return;
    }
    setProcessing(true);
    try {
      const res = await axios.post(`${API}/bank/deposit/term`, {
        amount: parseFloat(amount),
        term: selectedTerm
      });
      toast.success(res.data.message);
      setShowTermDepositModal(false);
      setAmount('');
      fetchAllData();
      refreshUser();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Term deposit failed');
    }
    setProcessing(false);
  };
  
  const handleWithdrawDeposit = async (depositId) => {
    setProcessing(true);
    try {
      const res = await axios.post(`${API}/bank/deposit/${depositId}/withdraw`);
      toast.success(res.data.message);
      fetchAllData();
      refreshUser();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Withdrawal failed');
    }
    setProcessing(false);
  };
  
  const fetchLoanEligibility = async () => {
    try {
      const res = await axios.get(`${API}/bank/loan/eligibility`);
      setLoanEligibility(res.data);
    } catch (error) {
      console.error('Failed to check eligibility:', error);
    }
  };
  
  const handleApplyLoan = async () => {
    if (!amount || parseFloat(amount) <= 0) {
      toast.error('Enter a valid amount');
      return;
    }
    setProcessing(true);
    try {
      const res = await axios.post(`${API}/bank/loan/apply`, {
        amount: parseFloat(amount),
        purpose: loanPurpose || 'General'
      });
      toast.success(res.data.message);
      setShowLoanModal(false);
      setAmount('');
      setLoanPurpose('');
      fetchAllData();
      refreshUser();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Loan application failed');
    }
    setProcessing(false);
  };
  
  const handleRepayLoan = async (loanId, repayAmount) => {
    setProcessing(true);
    try {
      const res = await axios.post(`${API}/bank/loan/repay`, {
        loan_id: loanId,
        amount: repayAmount
      });
      toast.success(res.data.message);
      fetchAllData();
      refreshUser();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Repayment failed');
    }
    setProcessing(false);
  };
  
  const handleTransfer = async () => {
    if (!amount || parseFloat(amount) <= 0 || !transferTo) {
      toast.error('Enter amount and recipient');
      return;
    }
    setProcessing(true);
    try {
      const res = await axios.post(`${API}/bank/transfer`, {
        to_user_id: transferTo,
        amount: parseFloat(amount),
        note: transferNote
      });
      toast.success(res.data.message);
      setShowTransferModal(false);
      setAmount('');
      setTransferTo('');
      setTransferNote('');
      fetchAllData();
      refreshUser();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Transfer failed');
    }
    setProcessing(false);
  };
  
  if (loading) {
    return (
      <div className="min-h-screen pt-20 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-green-500" />
      </div>
    );
  }
  
  return (
    <div className="min-h-screen pt-20 pb-20 px-4" data-testid="bank-page">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-6"
        >
          <div className="flex items-center justify-center gap-3 mb-2">
            <Building2 className="w-10 h-10 text-green-500" />
            <h1 className="text-3xl md:text-4xl font-orbitron font-black">
              <span className="text-green-500">REALUM</span> Central Bank
            </h1>
          </div>
          <p className="text-white/60">Secure banking services for the metaverse</p>
        </motion.div>
        
        {/* Quick Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <CyberCard className="p-4 text-center border-green-500/30">
            <Wallet className="w-6 h-6 mx-auto mb-2 text-yellow-400" />
            <p className="text-xs text-white/40">Wallet</p>
            <p className="text-xl font-bold text-yellow-400">{user?.realum_balance?.toFixed(0) || 0} RLM</p>
          </CyberCard>
          <CyberCard className="p-4 text-center border-green-500/30">
            <PiggyBank className="w-6 h-6 mx-auto mb-2 text-green-400" />
            <p className="text-xs text-white/40">Savings</p>
            <p className="text-xl font-bold text-green-400">{account?.account?.savings_balance?.toFixed(2) || 0} RLM</p>
          </CyberCard>
          <CyberCard className="p-4 text-center border-green-500/30">
            <TrendingUp className="w-6 h-6 mx-auto mb-2 text-blue-400" />
            <p className="text-xs text-white/40">In Deposits</p>
            <p className="text-xl font-bold text-blue-400">{account?.total_in_deposits?.toFixed(2) || 0} RLM</p>
          </CyberCard>
          <CyberCard className="p-4 text-center border-red-500/30">
            <CreditCard className="w-6 h-6 mx-auto mb-2 text-red-400" />
            <p className="text-xs text-white/40">Debt</p>
            <p className="text-xl font-bold text-red-400">{account?.total_debt?.toFixed(2) || 0} RLM</p>
          </CyberCard>
        </div>
        
        {/* Tab Navigation */}
        <div className="flex flex-wrap justify-center gap-2 mb-6">
          {[
            { id: 'overview', label: 'Overview', icon: Building2 },
            { id: 'deposits', label: 'Deposits', icon: PiggyBank },
            { id: 'loans', label: 'Loans', icon: CreditCard },
            { id: 'history', label: 'History', icon: Clock },
            { id: 'leaderboard', label: 'Top Holders', icon: Trophy }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg border transition-all ${
                activeTab === tab.id
                  ? 'bg-green-500/20 border-green-500 text-green-400'
                  : 'bg-white/5 border-white/20 text-white/60 hover:border-white/40'
              }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </div>
        
        {/* Overview Tab */}
        {activeTab === 'overview' && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6">
            {/* Quick Actions */}
            <div className="grid md:grid-cols-4 gap-4">
              <CyberButton onClick={() => setShowDepositModal(true)} className="bg-green-500/20 border-green-500">
                <ArrowDownRight className="w-5 h-5 mr-2" />
                Deposit
              </CyberButton>
              <CyberButton onClick={() => setShowWithdrawModal(true)} className="bg-yellow-500/20 border-yellow-500">
                <ArrowUpRight className="w-5 h-5 mr-2" />
                Withdraw
              </CyberButton>
              <CyberButton onClick={() => { setShowTermDepositModal(true); }} className="bg-blue-500/20 border-blue-500">
                <TrendingUp className="w-5 h-5 mr-2" />
                Term Deposit
              </CyberButton>
              <CyberButton onClick={() => { fetchLoanEligibility(); setShowLoanModal(true); }} className="bg-purple-500/20 border-purple-500">
                <CreditCard className="w-5 h-5 mr-2" />
                Apply Loan
              </CyberButton>
            </div>
            
            {/* Bank Rates */}
            <CyberCard className="p-6 border-green-500/30">
              <h3 className="font-orbitron font-bold text-lg mb-4 flex items-center gap-2">
                <Percent className="w-5 h-5 text-green-400" />
                Current Rates
              </h3>
              <div className="grid md:grid-cols-2 gap-6">
                <div>
                  <h4 className="text-green-400 font-bold mb-2">Savings Interest</h4>
                  <p className="text-3xl font-bold">{bankInfo?.rates?.savings_apy?.toFixed(1)}% <span className="text-sm text-white/40">APY</span></p>
                  <p className="text-sm text-white/40">{bankInfo?.rates?.savings_daily?.toFixed(2)}% daily</p>
                </div>
                <div>
                  <h4 className="text-red-400 font-bold mb-2">Loan Interest</h4>
                  <p className="text-3xl font-bold">{bankInfo?.rates?.loan_apr?.toFixed(1)}% <span className="text-sm text-white/40">APR</span></p>
                  <p className="text-sm text-white/40">{bankInfo?.rates?.loan_daily?.toFixed(2)}% daily</p>
                </div>
              </div>
            </CyberCard>
            
            {/* Credit Score */}
            <CyberCard className="p-6 border-green-500/30">
              <h3 className="font-orbitron font-bold text-lg mb-4">Credit Score</h3>
              <div className="flex items-center gap-6">
                <div className="text-5xl font-bold text-green-400">
                  {account?.account?.credit_score || 700}
                </div>
                <div className="flex-1">
                  <div className="h-4 bg-white/10 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-gradient-to-r from-red-500 via-yellow-500 to-green-500"
                      style={{ width: `${((account?.account?.credit_score || 700) / 850) * 100}%` }}
                    />
                  </div>
                  <div className="flex justify-between text-xs text-white/40 mt-1">
                    <span>300</span>
                    <span>850</span>
                  </div>
                </div>
              </div>
            </CyberCard>
          </motion.div>
        )}
        
        {/* Deposits Tab */}
        {activeTab === 'deposits' && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6">
            {/* Term Deposit Options */}
            <h3 className="font-orbitron font-bold text-lg">Term Deposit Options</h3>
            <div className="grid md:grid-cols-5 gap-4">
              {bankInfo?.deposit_terms && Object.entries(bankInfo.deposit_terms).map(([key, term]) => (
                <CyberCard key={key} className="p-4 text-center">
                  <p className="font-bold text-lg">{term.days} Days</p>
                  <p className="text-2xl text-green-400 font-bold">{term.bonus_percent}%</p>
                  <p className="text-xs text-white/40">bonus</p>
                </CyberCard>
              ))}
            </div>
            
            {/* Active Deposits */}
            <h3 className="font-orbitron font-bold text-lg">Active Deposits ({account?.active_deposits_count || 0})</h3>
            {account?.deposits?.length > 0 ? (
              <div className="space-y-3">
                {account.deposits.map(deposit => {
                  const maturity = new Date(deposit.maturity_date);
                  const now = new Date();
                  const daysLeft = Math.max(0, Math.ceil((maturity - now) / (1000 * 60 * 60 * 24)));
                  const isMature = daysLeft === 0;
                  
                  return (
                    <CyberCard key={deposit.id} className={`p-4 ${isMature ? 'border-green-500' : ''}`}>
                      <div className="flex items-center justify-between flex-wrap gap-4">
                        <div>
                          <p className="font-bold">{deposit.amount} RLM</p>
                          <p className="text-sm text-white/40">{deposit.term_days} days @ {deposit.bonus_percent}%</p>
                        </div>
                        <div className="text-center">
                          <p className="text-sm text-white/40">Expected Return</p>
                          <p className="text-green-400 font-bold">{deposit.expected_return?.toFixed(2)} RLM</p>
                        </div>
                        <div className="text-center">
                          {isMature ? (
                            <span className="text-green-400 font-bold">MATURE!</span>
                          ) : (
                            <>
                              <p className="text-sm text-white/40">Days Left</p>
                              <p className="font-bold">{daysLeft}</p>
                            </>
                          )}
                        </div>
                        <CyberButton
                          onClick={() => handleWithdrawDeposit(deposit.id)}
                          disabled={processing}
                          className={isMature ? 'bg-green-500/20 border-green-500' : 'bg-yellow-500/20 border-yellow-500'}
                        >
                          {isMature ? 'Claim' : 'Early Withdraw (-10%)'}
                        </CyberButton>
                      </div>
                    </CyberCard>
                  );
                })}
              </div>
            ) : (
              <CyberCard className="p-8 text-center">
                <PiggyBank className="w-12 h-12 mx-auto mb-3 text-white/20" />
                <p className="text-white/40">No active deposits</p>
              </CyberCard>
            )}
          </motion.div>
        )}
        
        {/* Loans Tab */}
        {activeTab === 'loans' && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6">
            <CyberButton onClick={() => { fetchLoanEligibility(); setShowLoanModal(true); }} className="bg-purple-500/20 border-purple-500">
              <CreditCard className="w-5 h-5 mr-2" />
              Apply for New Loan
            </CyberButton>
            
            {/* Active Loans */}
            <h3 className="font-orbitron font-bold text-lg">Active Loans ({account?.active_loans_count || 0})</h3>
            {account?.loans?.length > 0 ? (
              <div className="space-y-3">
                {account.loans.map(loan => {
                  const due = new Date(loan.due_date);
                  const now = new Date();
                  const daysLeft = Math.ceil((due - now) / (1000 * 60 * 60 * 24));
                  const isOverdue = daysLeft < 0;
                  
                  return (
                    <CyberCard key={loan.id} className={`p-4 ${isOverdue ? 'border-red-500' : ''}`}>
                      <div className="flex items-center justify-between flex-wrap gap-4">
                        <div>
                          <p className="font-bold">{loan.principal} RLM Loan</p>
                          <p className="text-sm text-white/40">{loan.purpose}</p>
                        </div>
                        <div className="text-center">
                          <p className="text-sm text-white/40">Remaining</p>
                          <p className="text-red-400 font-bold">{loan.remaining_amount?.toFixed(2)} RLM</p>
                        </div>
                        <div className="text-center">
                          {isOverdue ? (
                            <span className="text-red-400 font-bold">OVERDUE!</span>
                          ) : (
                            <>
                              <p className="text-sm text-white/40">Days Left</p>
                              <p className="font-bold">{daysLeft}</p>
                            </>
                          )}
                        </div>
                        <CyberButton
                          onClick={() => handleRepayLoan(loan.id, loan.remaining_amount)}
                          disabled={processing}
                          className="bg-green-500/20 border-green-500"
                        >
                          Pay Full ({loan.remaining_amount?.toFixed(0)} RLM)
                        </CyberButton>
                      </div>
                    </CyberCard>
                  );
                })}
              </div>
            ) : (
              <CyberCard className="p-8 text-center">
                <Check className="w-12 h-12 mx-auto mb-3 text-green-500" />
                <p className="text-white/40">No active loans - debt free!</p>
              </CyberCard>
            )}
          </motion.div>
        )}
        
        {/* History Tab */}
        {activeTab === 'history' && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            <div className="space-y-2">
              {transactions.length > 0 ? (
                transactions.map(tx => (
                  <CyberCard key={tx.id} className="p-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                          tx.amount > 0 ? 'bg-green-500/20' : 'bg-red-500/20'
                        }`}>
                          {tx.amount > 0 ? (
                            <ArrowDownRight className="w-5 h-5 text-green-400" />
                          ) : (
                            <ArrowUpRight className="w-5 h-5 text-red-400" />
                          )}
                        </div>
                        <div>
                          <p className="font-medium">{tx.description}</p>
                          <p className="text-xs text-white/40">
                            {new Date(tx.created_at).toLocaleDateString()} {new Date(tx.created_at).toLocaleTimeString()}
                          </p>
                        </div>
                      </div>
                      <p className={`font-bold ${tx.amount > 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {tx.amount > 0 ? '+' : ''}{tx.amount?.toFixed(2)} RLM
                      </p>
                    </div>
                  </CyberCard>
                ))
              ) : (
                <CyberCard className="p-8 text-center">
                  <Clock className="w-12 h-12 mx-auto mb-3 text-white/20" />
                  <p className="text-white/40">No transactions yet</p>
                </CyberCard>
              )}
            </div>
          </motion.div>
        )}
        
        {/* Leaderboard Tab */}
        {activeTab === 'leaderboard' && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            <div className="space-y-2">
              {leaderboard.map((entry, idx) => (
                <CyberCard key={idx} className={`p-4 ${idx < 3 ? 'border-yellow-500/50' : ''}`}>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold ${
                        idx === 0 ? 'bg-yellow-500/30 text-yellow-400' :
                        idx === 1 ? 'bg-gray-400/30 text-gray-300' :
                        idx === 2 ? 'bg-orange-500/30 text-orange-400' :
                        'bg-white/10 text-white/60'
                      }`}>
                        {entry.rank}
                      </div>
                      <div>
                        <p className="font-bold">{entry.username}</p>
                        <p className="text-xs text-white/40">Credit Score: {entry.credit_score}</p>
                      </div>
                    </div>
                    <p className="text-green-400 font-bold">{entry.total_wealth?.toFixed(0)} RLM</p>
                  </div>
                </CyberCard>
              ))}
            </div>
          </motion.div>
        )}
        
        {/* Deposit Modal */}
        <AnimatePresence>
          {showDepositModal && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4"
              onClick={() => setShowDepositModal(false)}
            >
              <motion.div
                initial={{ scale: 0.9 }}
                animate={{ scale: 1 }}
                exit={{ scale: 0.9 }}
                className="bg-gray-900 border border-green-500/30 rounded-xl p-6 max-w-md w-full"
                onClick={e => e.stopPropagation()}
              >
                <h3 className="font-orbitron font-bold text-xl text-green-400 mb-4">Deposit to Savings</h3>
                <p className="text-sm text-white/60 mb-4">Wallet Balance: {user?.realum_balance?.toFixed(2)} RLM</p>
                <input
                  type="number"
                  value={amount}
                  onChange={e => setAmount(e.target.value)}
                  placeholder="Amount"
                  className="w-full bg-white/5 border border-white/20 rounded-lg px-4 py-3 text-white mb-4"
                />
                <div className="flex gap-2">
                  <button onClick={() => setShowDepositModal(false)} className="flex-1 px-4 py-2 bg-white/5 border border-white/20 rounded-lg">Cancel</button>
                  <CyberButton onClick={() => handleDeposit('savings')} disabled={processing} className="flex-1 bg-green-500/20 border-green-500">
                    {processing ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Deposit'}
                  </CyberButton>
                </div>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>
        
        {/* Withdraw Modal */}
        <AnimatePresence>
          {showWithdrawModal && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4"
              onClick={() => setShowWithdrawModal(false)}
            >
              <motion.div
                initial={{ scale: 0.9 }}
                animate={{ scale: 1 }}
                exit={{ scale: 0.9 }}
                className="bg-gray-900 border border-yellow-500/30 rounded-xl p-6 max-w-md w-full"
                onClick={e => e.stopPropagation()}
              >
                <h3 className="font-orbitron font-bold text-xl text-yellow-400 mb-4">Withdraw to Wallet</h3>
                <p className="text-sm text-white/60 mb-4">Savings Balance: {account?.account?.savings_balance?.toFixed(2)} RLM</p>
                <input
                  type="number"
                  value={amount}
                  onChange={e => setAmount(e.target.value)}
                  placeholder="Amount"
                  className="w-full bg-white/5 border border-white/20 rounded-lg px-4 py-3 text-white mb-4"
                />
                <div className="flex gap-2">
                  <button onClick={() => setShowWithdrawModal(false)} className="flex-1 px-4 py-2 bg-white/5 border border-white/20 rounded-lg">Cancel</button>
                  <CyberButton onClick={() => handleWithdraw('savings')} disabled={processing} className="flex-1 bg-yellow-500/20 border-yellow-500">
                    {processing ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Withdraw'}
                  </CyberButton>
                </div>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>
        
        {/* Term Deposit Modal */}
        <AnimatePresence>
          {showTermDepositModal && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4"
              onClick={() => setShowTermDepositModal(false)}
            >
              <motion.div
                initial={{ scale: 0.9 }}
                animate={{ scale: 1 }}
                exit={{ scale: 0.9 }}
                className="bg-gray-900 border border-blue-500/30 rounded-xl p-6 max-w-md w-full"
                onClick={e => e.stopPropagation()}
              >
                <h3 className="font-orbitron font-bold text-xl text-blue-400 mb-4">Create Term Deposit</h3>
                <p className="text-sm text-white/60 mb-4">Lock your RLM for higher returns!</p>
                
                <div className="mb-4">
                  <label className="text-sm text-white/60 mb-2 block">Select Term</label>
                  <div className="grid grid-cols-5 gap-2">
                    {bankInfo?.deposit_terms && Object.entries(bankInfo.deposit_terms).map(([key, term]) => (
                      <button
                        key={key}
                        onClick={() => setSelectedTerm(key)}
                        className={`p-2 rounded-lg border text-center ${
                          selectedTerm === key ? 'bg-blue-500/20 border-blue-500' : 'bg-white/5 border-white/20'
                        }`}
                      >
                        <p className="text-sm font-bold">{term.days}d</p>
                        <p className="text-xs text-green-400">{term.bonus_percent}%</p>
                      </button>
                    ))}
                  </div>
                </div>
                
                <input
                  type="number"
                  value={amount}
                  onChange={e => setAmount(e.target.value)}
                  placeholder="Amount"
                  className="w-full bg-white/5 border border-white/20 rounded-lg px-4 py-3 text-white mb-4"
                />
                
                {amount && bankInfo?.deposit_terms?.[selectedTerm] && (
                  <div className="bg-white/5 rounded-lg p-3 mb-4">
                    <p className="text-sm text-white/60">Expected Return:</p>
                    <p className="text-xl text-green-400 font-bold">
                      {(parseFloat(amount) * (1 + bankInfo.deposit_terms[selectedTerm].rate)).toFixed(2)} RLM
                    </p>
                  </div>
                )}
                
                <div className="flex gap-2">
                  <button onClick={() => setShowTermDepositModal(false)} className="flex-1 px-4 py-2 bg-white/5 border border-white/20 rounded-lg">Cancel</button>
                  <CyberButton onClick={handleTermDeposit} disabled={processing} className="flex-1 bg-blue-500/20 border-blue-500">
                    {processing ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Create Deposit'}
                  </CyberButton>
                </div>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>
        
        {/* Loan Modal */}
        <AnimatePresence>
          {showLoanModal && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4"
              onClick={() => setShowLoanModal(false)}
            >
              <motion.div
                initial={{ scale: 0.9 }}
                animate={{ scale: 1 }}
                exit={{ scale: 0.9 }}
                className="bg-gray-900 border border-purple-500/30 rounded-xl p-6 max-w-md w-full"
                onClick={e => e.stopPropagation()}
              >
                <h3 className="font-orbitron font-bold text-xl text-purple-400 mb-4">Apply for Loan</h3>
                
                {loanEligibility && (
                  <div className="bg-white/5 rounded-lg p-3 mb-4">
                    <p className="text-sm text-white/60">You can borrow up to:</p>
                    <p className="text-xl text-purple-400 font-bold">{loanEligibility.max_loan_amount?.toFixed(0)} RLM</p>
                    <p className="text-xs text-white/40">Interest: {loanEligibility.interest_rate_daily}% daily for {loanEligibility.loan_duration_days} days</p>
                  </div>
                )}
                
                <input
                  type="number"
                  value={amount}
                  onChange={e => setAmount(e.target.value)}
                  placeholder="Loan Amount"
                  className="w-full bg-white/5 border border-white/20 rounded-lg px-4 py-3 text-white mb-4"
                />
                
                <input
                  type="text"
                  value={loanPurpose}
                  onChange={e => setLoanPurpose(e.target.value)}
                  placeholder="Purpose (optional)"
                  className="w-full bg-white/5 border border-white/20 rounded-lg px-4 py-3 text-white mb-4"
                />
                
                <div className="flex gap-2">
                  <button onClick={() => setShowLoanModal(false)} className="flex-1 px-4 py-2 bg-white/5 border border-white/20 rounded-lg">Cancel</button>
                  <CyberButton onClick={handleApplyLoan} disabled={processing || !loanEligibility?.eligible} className="flex-1 bg-purple-500/20 border-purple-500">
                    {processing ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Apply'}
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

export default BankPage;
