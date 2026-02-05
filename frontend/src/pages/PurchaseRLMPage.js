import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { 
  Coins, CreditCard, Bitcoin, Check, Sparkles, Gift, 
  ArrowRight, Loader2, AlertCircle, Wallet
} from 'lucide-react';
import axios from 'axios';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { API } from '../utils/api';
import { useAuth } from '../context/AuthContext';
import { CyberCard, CyberButton } from '../components/common/CyberUI';
import { toast } from 'sonner';

const PurchaseRLMPage = () => {
  const { user, refreshUser } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  
  const [packages, setPackages] = useState([]);
  const [cryptoRates, setCryptoRates] = useState({});
  const [selectedPackage, setSelectedPackage] = useState(null);
  const [paymentMethod, setPaymentMethod] = useState('card');
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  
  // Crypto purchase state
  const [cryptoType, setCryptoType] = useState('ETH');
  const [walletAddress, setWalletAddress] = useState('');
  const [cryptoTransaction, setCryptoTransaction] = useState(null);
  
  // Check for payment return
  useEffect(() => {
    const sessionId = searchParams.get('session_id');
    const paymentStatus = searchParams.get('payment');
    
    if (sessionId && paymentStatus === 'success') {
      checkPaymentStatus(sessionId);
    } else if (paymentStatus === 'cancelled') {
      toast.error('Payment was cancelled');
    }
  }, [searchParams]);
  
  // Load packages
  useEffect(() => {
    const fetchPackages = async () => {
      try {
        const res = await axios.get(`${API}/payments/packages`);
        setPackages(res.data.packages);
        setCryptoRates(res.data.crypto_rates);
      } catch (error) {
        toast.error('Failed to load packages');
      }
      setLoading(false);
    };
    fetchPackages();
  }, []);
  
  const checkPaymentStatus = async (sessionId) => {
    setProcessing(true);
    try {
      const res = await axios.get(`${API}/payments/checkout/status/${sessionId}`);
      if (res.data.payment_status === 'paid') {
        toast.success(`Success! ${res.data.rlm_credited} RLM added to your wallet!`);
        refreshUser();
        // Clear URL params
        navigate('/wallet', { replace: true });
      }
    } catch (error) {
      toast.error('Failed to verify payment');
    }
    setProcessing(false);
  };
  
  const handleCardPurchase = async () => {
    if (!selectedPackage) return;
    setProcessing(true);
    
    try {
      const res = await axios.post(`${API}/payments/checkout/create`, {
        package_id: selectedPackage.id,
        origin_url: window.location.origin,
        payment_method: 'card'
      });
      
      // Redirect to Stripe
      window.location.href = res.data.checkout_url;
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create checkout');
      setProcessing(false);
    }
  };
  
  const handleCryptoPurchase = async () => {
    if (!selectedPackage || !walletAddress) return;
    setProcessing(true);
    
    try {
      const res = await axios.post(`${API}/payments/crypto/initiate`, {
        package_id: selectedPackage.id,
        crypto_type: cryptoType,
        wallet_address: walletAddress
      });
      
      setCryptoTransaction(res.data);
      toast.success('Crypto purchase initiated!');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to initiate crypto purchase');
    }
    setProcessing(false);
  };
  
  const simulateCryptoPayment = async () => {
    if (!cryptoTransaction) return;
    setProcessing(true);
    
    try {
      const res = await axios.post(`${API}/payments/crypto/simulate-payment`, {
        transaction_id: cryptoTransaction.transaction_id,
        tx_hash: `0x${Math.random().toString(16).slice(2)}${Math.random().toString(16).slice(2)}`
      });
      
      toast.success(res.data.message);
      refreshUser();
      setCryptoTransaction(null);
      setSelectedPackage(null);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Payment simulation failed');
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
    <div className="min-h-screen pt-20 pb-20 px-4" data-testid="purchase-rlm-page">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-10"
        >
          <h1 className="text-3xl md:text-4xl font-orbitron font-black mb-2">
            Purchase <span className="text-neon-cyan">RLM</span> Tokens
          </h1>
          <p className="text-white/60">Power your REALUM experience with RLM tokens</p>
          <div className="mt-4 inline-flex items-center gap-2 px-4 py-2 bg-neon-cyan/10 border border-neon-cyan/30 rounded-lg">
            <Wallet className="w-5 h-5 text-neon-cyan" />
            <span className="text-neon-cyan font-bold">{user?.realum_balance?.toFixed(0) || 0} RLM</span>
            <span className="text-white/40">current balance</span>
          </div>
        </motion.div>
        
        {/* Payment Method Toggle */}
        <div className="flex justify-center gap-4 mb-8">
          <button
            onClick={() => setPaymentMethod('card')}
            className={`flex items-center gap-2 px-6 py-3 rounded-lg border transition-all ${
              paymentMethod === 'card' 
                ? 'bg-neon-cyan/20 border-neon-cyan text-neon-cyan' 
                : 'bg-white/5 border-white/20 text-white/60 hover:border-white/40'
            }`}
          >
            <CreditCard className="w-5 h-5" />
            Card Payment
          </button>
          <button
            onClick={() => setPaymentMethod('crypto')}
            className={`flex items-center gap-2 px-6 py-3 rounded-lg border transition-all ${
              paymentMethod === 'crypto' 
                ? 'bg-orange-500/20 border-orange-500 text-orange-400' 
                : 'bg-white/5 border-white/20 text-white/60 hover:border-white/40'
            }`}
          >
            <Bitcoin className="w-5 h-5" />
            Crypto (Simulated)
          </button>
        </div>
        
        {/* Packages Grid */}
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          {packages.map((pkg, index) => (
            <motion.div
              key={pkg.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
            >
              <CyberCard 
                className={`p-6 cursor-pointer transition-all relative ${
                  selectedPackage?.id === pkg.id 
                    ? 'border-neon-cyan bg-neon-cyan/10' 
                    : 'hover:border-white/40'
                }`}
                onClick={() => setSelectedPackage(pkg)}
              >
                {pkg.popular && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 bg-gradient-to-r from-purple-500 to-pink-500 text-xs font-bold rounded-full">
                    POPULAR
                  </div>
                )}
                
                <div className="text-center">
                  <Coins className="w-10 h-10 mx-auto mb-3 text-yellow-400" />
                  <h3 className="font-orbitron font-bold text-lg mb-1">{pkg.name}</h3>
                  
                  <div className="text-3xl font-bold text-neon-cyan mb-1">
                    {pkg.rlm_amount.toLocaleString()}
                    <span className="text-sm text-white/60 ml-1">RLM</span>
                  </div>
                  
                  {pkg.bonus > 0 && (
                    <div className="flex items-center justify-center gap-1 text-green-400 text-sm mb-3">
                      <Gift className="w-4 h-4" />
                      +{pkg.bonus} bonus!
                    </div>
                  )}
                  
                  <div className="text-2xl font-bold text-white">
                    ${pkg.price_usd}
                  </div>
                  
                  {paymentMethod === 'crypto' && (
                    <div className="mt-2 text-xs text-white/40">
                      ≈ {(pkg.price_usd / cryptoRates[cryptoType]).toFixed(6)} {cryptoType}
                    </div>
                  )}
                </div>
                
                {selectedPackage?.id === pkg.id && (
                  <div className="absolute top-2 right-2">
                    <Check className="w-6 h-6 text-neon-cyan" />
                  </div>
                )}
              </CyberCard>
            </motion.div>
          ))}
        </div>
        
        {/* Purchase Section */}
        {selectedPackage && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="max-w-md mx-auto"
          >
            <CyberCard className="p-6">
              <h3 className="font-orbitron font-bold text-lg mb-4 text-center">
                Complete Purchase
              </h3>
              
              <div className="bg-white/5 rounded-lg p-4 mb-4">
                <div className="flex justify-between mb-2">
                  <span className="text-white/60">Package</span>
                  <span className="font-bold">{selectedPackage.name}</span>
                </div>
                <div className="flex justify-between mb-2">
                  <span className="text-white/60">RLM Amount</span>
                  <span className="text-neon-cyan font-bold">
                    {(selectedPackage.rlm_amount + selectedPackage.bonus).toLocaleString()} RLM
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-white/60">Total</span>
                  <span className="text-xl font-bold">${selectedPackage.price_usd}</span>
                </div>
              </div>
              
              {paymentMethod === 'card' ? (
                <CyberButton 
                  onClick={handleCardPurchase}
                  disabled={processing}
                  className="w-full"
                >
                  {processing ? (
                    <Loader2 className="w-5 h-5 animate-spin" />
                  ) : (
                    <>
                      <CreditCard className="w-5 h-5 mr-2" />
                      Pay with Card
                    </>
                  )}
                </CyberButton>
              ) : (
                <div className="space-y-4">
                  {!cryptoTransaction ? (
                    <>
                      <div>
                        <label className="text-sm text-white/60 mb-1 block">Cryptocurrency</label>
                        <select
                          value={cryptoType}
                          onChange={(e) => setCryptoType(e.target.value)}
                          className="w-full bg-white/5 border border-white/20 rounded-lg px-4 py-2 text-white"
                        >
                          <option value="ETH">Ethereum (ETH)</option>
                          <option value="USDT">Tether (USDT)</option>
                          <option value="BTC">Bitcoin (BTC)</option>
                        </select>
                      </div>
                      <div>
                        <label className="text-sm text-white/60 mb-1 block">Your Wallet Address</label>
                        <input
                          type="text"
                          value={walletAddress}
                          onChange={(e) => setWalletAddress(e.target.value)}
                          placeholder="0x..."
                          className="w-full bg-white/5 border border-white/20 rounded-lg px-4 py-2 text-white"
                        />
                      </div>
                      <CyberButton 
                        onClick={handleCryptoPurchase}
                        disabled={processing || !walletAddress}
                        className="w-full bg-orange-500/20 border-orange-500"
                      >
                        {processing ? (
                          <Loader2 className="w-5 h-5 animate-spin" />
                        ) : (
                          <>
                            <Bitcoin className="w-5 h-5 mr-2" />
                            Initiate Crypto Payment
                          </>
                        )}
                      </CyberButton>
                    </>
                  ) : (
                    <div className="space-y-4">
                      <div className="bg-orange-500/10 border border-orange-500/30 rounded-lg p-4">
                        <p className="text-sm text-orange-400 mb-2">Send exactly:</p>
                        <p className="text-2xl font-bold text-white">
                          {cryptoTransaction.crypto_amount} {cryptoTransaction.crypto_type}
                        </p>
                        <p className="text-sm text-white/60 mt-2">To address:</p>
                        <p className="text-xs font-mono text-white/80 break-all">
                          {cryptoTransaction.deposit_address}
                        </p>
                      </div>
                      
                      <div className="flex items-center gap-2 text-yellow-400 text-sm">
                        <AlertCircle className="w-4 h-4" />
                        <span>This is a simulated crypto payment for testing</span>
                      </div>
                      
                      <CyberButton 
                        onClick={simulateCryptoPayment}
                        disabled={processing}
                        className="w-full bg-green-500/20 border-green-500"
                      >
                        {processing ? (
                          <Loader2 className="w-5 h-5 animate-spin" />
                        ) : (
                          <>
                            <Check className="w-5 h-5 mr-2" />
                            Simulate Payment Complete
                          </>
                        )}
                      </CyberButton>
                    </div>
                  )}
                </div>
              )}
            </CyberCard>
          </motion.div>
        )}
      </div>
    </div>
  );
};

export default PurchaseRLMPage;
