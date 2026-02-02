import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';

const Web3Context = createContext(null);

export const useWeb3 = () => useContext(Web3Context);

export const Web3Provider = ({ children }) => {
  const [account, setAccount] = useState(null);
  const [chainId, setChainId] = useState(null);
  const [isConnecting, setIsConnecting] = useState(false);
  const [error, setError] = useState(null);

  // Check if MetaMask is installed
  const isMetaMaskInstalled = typeof window !== 'undefined' && typeof window.ethereum !== 'undefined';

  // Get current chain name
  const getChainName = (id) => {
    const chains = {
      '0x1': 'Ethereum Mainnet',
      '0x5': 'Goerli Testnet',
      '0xaa36a7': 'Sepolia Testnet',
      '0x89': 'Polygon Mainnet',
      '0x13881': 'Mumbai Testnet',
      '0x38': 'BSC Mainnet',
      '0x61': 'BSC Testnet',
      '0xa86a': 'Avalanche C-Chain',
      '0xa4b1': 'Arbitrum One',
      '0xa': 'Optimism'
    };
    return chains[id] || `Chain ${id}`;
  };

  // Connect wallet
  const connectWallet = useCallback(async () => {
    if (!isMetaMaskInstalled) {
      setError('MetaMask is not installed. Please install MetaMask extension.');
      window.open('https://metamask.io/download/', '_blank');
      return null;
    }

    setIsConnecting(true);
    setError(null);

    try {
      // Request account access
      const accounts = await window.ethereum.request({
        method: 'eth_requestAccounts'
      });

      if (accounts.length > 0) {
        setAccount(accounts[0]);
        
        // Get chain ID
        const chainIdHex = await window.ethereum.request({
          method: 'eth_chainId'
        });
        setChainId(chainIdHex);

        return accounts[0];
      }
    } catch (err) {
      console.error('Error connecting wallet:', err);
      if (err.code === 4001) {
        setError('Connection rejected. Please approve the connection in MetaMask.');
      } else if (err.code === -32002) {
        setError('Connection request pending. Please check MetaMask.');
      } else {
        setError(err.message || 'Failed to connect wallet');
      }
    } finally {
      setIsConnecting(false);
    }
    return null;
  }, [isMetaMaskInstalled]);

  // Disconnect wallet (clear local state)
  const disconnectWallet = useCallback(() => {
    setAccount(null);
    setChainId(null);
    setError(null);
  }, []);

  // Sign a message for verification
  const signMessage = useCallback(async (message) => {
    if (!account) {
      setError('Please connect wallet first');
      return null;
    }

    try {
      const signature = await window.ethereum.request({
        method: 'personal_sign',
        params: [message, account]
      });
      return signature;
    } catch (err) {
      console.error('Error signing message:', err);
      setError(err.message || 'Failed to sign message');
      return null;
    }
  }, [account]);

  // Switch network
  const switchNetwork = useCallback(async (targetChainId) => {
    if (!isMetaMaskInstalled) return false;

    try {
      await window.ethereum.request({
        method: 'wallet_switchEthereumChain',
        params: [{ chainId: targetChainId }]
      });
      return true;
    } catch (err) {
      console.error('Error switching network:', err);
      // If chain not added, could add it here
      setError(err.message || 'Failed to switch network');
      return false;
    }
  }, [isMetaMaskInstalled]);

  // Listen for account changes
  useEffect(() => {
    if (!isMetaMaskInstalled) return;

    const handleAccountsChanged = (accounts) => {
      if (accounts.length === 0) {
        // User disconnected
        setAccount(null);
      } else if (accounts[0] !== account) {
        setAccount(accounts[0]);
      }
    };

    const handleChainChanged = (newChainId) => {
      setChainId(newChainId);
    };

    window.ethereum.on('accountsChanged', handleAccountsChanged);
    window.ethereum.on('chainChanged', handleChainChanged);

    // Check if already connected
    window.ethereum.request({ method: 'eth_accounts' })
      .then(accounts => {
        if (accounts.length > 0) {
          setAccount(accounts[0]);
          window.ethereum.request({ method: 'eth_chainId' })
            .then(setChainId);
        }
      })
      .catch(console.error);

    return () => {
      window.ethereum.removeListener('accountsChanged', handleAccountsChanged);
      window.ethereum.removeListener('chainChanged', handleChainChanged);
    };
  }, [isMetaMaskInstalled, account]);

  // Format address for display
  const formatAddress = (addr) => {
    if (!addr) return '';
    return `${addr.slice(0, 6)}...${addr.slice(-4)}`;
  };

  return (
    <Web3Context.Provider value={{
      account,
      chainId,
      chainName: getChainName(chainId),
      isConnecting,
      error,
      isMetaMaskInstalled,
      isConnected: !!account,
      connectWallet,
      disconnectWallet,
      signMessage,
      switchNetwork,
      formatAddress
    }}>
      {children}
    </Web3Context.Provider>
  );
};
