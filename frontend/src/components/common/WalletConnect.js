import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Wallet, ExternalLink, Copy, Check, X, AlertCircle, Link2 } from 'lucide-react';
import axios from 'axios';
import { API } from '../../utils/api';
import { useWeb3 } from '../../context/Web3Context';
import { useAuth } from '../../context/AuthContext';
import { CyberButton } from './CyberUI';

const WalletConnect = ({ onConnect }) => {
  const { refreshUser } = useAuth();
  const {
    account,
    chainName,
    isConnecting,
    error,
    isMetaMaskInstalled,
    isConnected,
    connectWallet,
    disconnectWallet,
    formatAddress,
    signMessage
  } = useWeb3();

  const [showModal, setShowModal] = useState(false);
  const [copied, setCopied] = useState(false);
  const [linking, setLinking] = useState(false);
  const [linkError, setLinkError] = useState(null);

  const handleConnect = async () => {
    const addr = await connectWallet();
    if (addr && onConnect) {
      onConnect(addr);
    }
  };

  const handleLinkWallet = async () => {
    if (!account) return;
    
    setLinking(true);
    setLinkError(null);
    
    try {
      // Sign a message to verify ownership
      const message = `Link wallet to REALUM\nAddress: ${account}\nTimestamp: ${Date.now()}`;
      const signature = await signMessage(message);
      
      if (!signature) {
        setLinkError('Failed to sign message');
        setLinking(false);
        return;
      }

      // Send to backend
      await axios.post(`${API}/wallet/connect`, {
        wallet_address: account,
        signature: signature,
        message: message
      });

      await refreshUser();
      setShowModal(false);
    } catch (err) {
      console.error('Error linking wallet:', err);
      setLinkError(err.response?.data?.detail || 'Failed to link wallet');
    } finally {
      setLinking(false);
    }
  };

  const copyAddress = () => {
    navigator.clipboard.writeText(account);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <>
      {/* Connect Button */}
      {!isConnected ? (
        <CyberButton
          onClick={() => setShowModal(true)}
          className="flex items-center gap-2"
          data-testid="connect-wallet-btn"
        >
          <Wallet className="w-4 h-4" />
          Connect Wallet
        </CyberButton>
      ) : (
        <button
          onClick={() => setShowModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-neon-green/10 border border-neon-green/50 text-neon-green hover:bg-neon-green/20 transition-colors"
          data-testid="wallet-connected-btn"
        >
          <div className="w-2 h-2 bg-neon-green rounded-full animate-pulse" />
          <span className="font-mono text-sm">{formatAddress(account)}</span>
        </button>
      )}

      {/* Modal */}
      <AnimatePresence>
        {showModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4"
            onClick={() => setShowModal(false)}
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              onClick={(e) => e.stopPropagation()}
              className="bg-black border border-neon-cyan w-full max-w-md relative"
            >
              {/* Header */}
              <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-neon-cyan via-neon-purple to-neon-cyan" />
              
              <button
                onClick={() => setShowModal(false)}
                className="absolute top-4 right-4 text-white/50 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>

              <div className="p-6">
                <div className="text-center mb-6">
                  <div className="w-16 h-16 mx-auto mb-4 bg-gradient-to-br from-neon-cyan to-neon-purple rounded-full flex items-center justify-center">
                    <Wallet className="w-8 h-8 text-white" />
                  </div>
                  <h3 className="font-orbitron font-bold text-xl">
                    {isConnected ? 'Wallet Connected' : 'Connect Wallet'}
                  </h3>
                </div>

                {/* Error Message */}
                {(error || linkError) && (
                  <div className="mb-4 p-3 bg-neon-red/10 border border-neon-red/50 flex items-start gap-2">
                    <AlertCircle className="w-5 h-5 text-neon-red flex-shrink-0 mt-0.5" />
                    <span className="text-sm text-neon-red">{error || linkError}</span>
                  </div>
                )}

                {!isConnected ? (
                  <>
                    {/* Not Connected State */}
                    <p className="text-white/60 text-sm text-center mb-6">
                      Connect your MetaMask wallet to link it with your REALUM account
                    </p>

                    {!isMetaMaskInstalled ? (
                      <div className="text-center">
                        <p className="text-white/60 text-sm mb-4">
                          MetaMask is not installed in your browser
                        </p>
                        <CyberButton
                          onClick={() => window.open('https://metamask.io/download/', '_blank')}
                          className="w-full"
                        >
                          Install MetaMask <ExternalLink className="w-4 h-4 inline ml-2" />
                        </CyberButton>
                      </div>
                    ) : (
                      <CyberButton
                        onClick={handleConnect}
                        disabled={isConnecting}
                        className="w-full"
                        data-testid="metamask-connect-btn"
                      >
                        {isConnecting ? (
                          <>Connecting...</>
                        ) : (
                          <>
                            <img 
                              src="https://upload.wikimedia.org/wikipedia/commons/3/36/MetaMask_Fox.svg" 
                              alt="MetaMask" 
                              className="w-5 h-5 inline mr-2"
                            />
                            Connect MetaMask
                          </>
                        )}
                      </CyberButton>
                    )}
                  </>
                ) : (
                  <>
                    {/* Connected State */}
                    <div className="bg-white/5 border border-white/10 p-4 mb-4">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs text-white/50">Address</span>
                        <button onClick={copyAddress} className="text-white/50 hover:text-white">
                          {copied ? <Check className="w-4 h-4 text-neon-green" /> : <Copy className="w-4 h-4" />}
                        </button>
                      </div>
                      <div className="font-mono text-sm text-neon-cyan break-all">
                        {account}
                      </div>
                    </div>

                    <div className="bg-white/5 border border-white/10 p-4 mb-6">
                      <div className="text-xs text-white/50 mb-1">Network</div>
                      <div className="flex items-center gap-2">
                        <div className="w-2 h-2 bg-neon-green rounded-full" />
                        <span className="text-sm">{chainName}</span>
                      </div>
                    </div>

                    <div className="space-y-3">
                      <CyberButton
                        onClick={handleLinkWallet}
                        disabled={linking}
                        className="w-full"
                        data-testid="link-wallet-btn"
                      >
                        <Link2 className="w-4 h-4 inline mr-2" />
                        {linking ? 'Linking...' : 'Link to REALUM Account'}
                      </CyberButton>

                      <CyberButton
                        variant="ghost"
                        onClick={disconnectWallet}
                        className="w-full"
                      >
                        Disconnect
                      </CyberButton>
                    </div>
                  </>
                )}

                {/* Footer Info */}
                <p className="text-[10px] text-white/40 text-center mt-6">
                  By connecting, you agree to REALUM's Terms of Service
                </p>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
};

export default WalletConnect;
