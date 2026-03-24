import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Repeat, Gavel, Package, Clock, CheckCircle, XCircle,
  Loader2, Plus, Search, Filter, ArrowUpRight, ArrowDownRight,
  ShoppingCart, DollarSign, Send, X
} from 'lucide-react';
import axios from 'axios';
import { API } from '../utils/api';
import { useAuth } from '../context/AuthContext';
import { CyberCard, CyberButton } from '../components/common/CyberUI';
import { toast } from 'sonner';

const TradingPage = () => {
  const { user, refreshUser } = useAuth();
  const [activeTab, setActiveTab] = useState('auctions'); // auctions, p2p, my-trades
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  
  // Auction states
  const [auctions, setAuctions] = useState([]);
  const [auctionCategories] = useState([
    'collectibles', 'equipment', 'resources', 'cosmetics', 
    'property_deeds', 'company_shares', 'other'
  ]);
  const [selectedCategory, setSelectedCategory] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState('ending_soon');
  
  // P2P Trading states
  const [incomingOffers, setIncomingOffers] = useState([]);
  const [outgoingOffers, setOutgoingOffers] = useState([]);
  const [myAuctions, setMyAuctions] = useState({ selling: [], bidding: [] });
  
  // Modal states
  const [showCreateOfferModal, setShowCreateOfferModal] = useState(false);
  const [showCreateAuctionModal, setShowCreateAuctionModal] = useState(false);
  const [showBidModal, setShowBidModal] = useState(false);
  const [selectedAuction, setSelectedAuction] = useState(null);
  
  // Form states
  const [offerForm, setOfferForm] = useState({
    target_username: '', offer_rlm: 0, request_rlm: 0, message: ''
  });
  const [auctionForm, setAuctionForm] = useState({
    item_id: '', item_name: '', item_type: 'other', 
    starting_price: 100, buyout_price: '', duration_hours: 24, description: ''
  });
  const [bidAmount, setBidAmount] = useState(0);

  useEffect(() => {
    fetchAllData();
  }, []);

  useEffect(() => {
    if (activeTab === 'auctions') {
      fetchAuctions();
    }
  }, [selectedCategory, sortBy]);

  const fetchAllData = async () => {
    await Promise.all([
      fetchAuctions(),
      fetchP2POffers(),
      fetchMyAuctions()
    ]);
    setLoading(false);
  };

  const fetchAuctions = async () => {
    try {
      let url = `${API}/trading/auctions?sort_by=${sortBy}&limit=50`;
      if (selectedCategory) url += `&category=${selectedCategory}`;
      if (searchQuery) url += `&search=${searchQuery}`;
      const res = await axios.get(url);
      setAuctions(res.data.auctions || []);
    } catch (error) {
      console.error('Failed to load auctions:', error);
    }
  };

  const fetchP2POffers = async () => {
    try {
      const [inRes, outRes] = await Promise.all([
        axios.get(`${API}/trading/offers/incoming`),
        axios.get(`${API}/trading/offers/outgoing`)
      ]);
      setIncomingOffers(inRes.data.offers || []);
      setOutgoingOffers(outRes.data.offers || []);
    } catch (error) {
      console.error('Failed to load P2P offers:', error);
    }
  };

  const fetchMyAuctions = async () => {
    try {
      const res = await axios.get(`${API}/trading/my-auctions`);
      setMyAuctions(res.data);
    } catch (error) {
      console.error('Failed to load my auctions:', error);
    }
  };

  const handleCreateOffer = async () => {
    setProcessing(true);
    try {
      const res = await axios.post(`${API}/trading/offers/create`, offerForm);
      toast.success(res.data.message);
      setShowCreateOfferModal(false);
      setOfferForm({ target_username: '', offer_rlm: 0, request_rlm: 0, message: '' });
      fetchP2POffers();
      refreshUser();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create offer');
    }
    setProcessing(false);
  };

  const handleAcceptOffer = async (offerId) => {
    setProcessing(true);
    try {
      const res = await axios.post(`${API}/trading/offers/${offerId}/accept`);
      toast.success(res.data.message);
      fetchP2POffers();
      refreshUser();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to accept offer');
    }
    setProcessing(false);
  };

  const handleDeclineOffer = async (offerId) => {
    setProcessing(true);
    try {
      const res = await axios.post(`${API}/trading/offers/${offerId}/decline`);
      toast.success(res.data.message);
      fetchP2POffers();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to decline offer');
    }
    setProcessing(false);
  };

  const handleCancelOffer = async (offerId) => {
    setProcessing(true);
    try {
      const res = await axios.post(`${API}/trading/offers/${offerId}/cancel`);
      toast.success(res.data.message);
      fetchP2POffers();
      refreshUser();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to cancel offer');
    }
    setProcessing(false);
  };

  const handleCreateAuction = async () => {
    setProcessing(true);
    try {
      const payload = {
        ...auctionForm,
        buyout_price: auctionForm.buyout_price ? parseFloat(auctionForm.buyout_price) : null
      };
      const res = await axios.post(`${API}/trading/auctions/create`, payload);
      toast.success(res.data.message);
      setShowCreateAuctionModal(false);
      setAuctionForm({ item_id: '', item_name: '', item_type: 'other', starting_price: 100, buyout_price: '', duration_hours: 24, description: '' });
      fetchMyAuctions();
      fetchAuctions();
      refreshUser();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create auction');
    }
    setProcessing(false);
  };

  const handlePlaceBid = async () => {
    if (!selectedAuction) return;
    setProcessing(true);
    try {
      const res = await axios.post(`${API}/trading/auctions/${selectedAuction.id}/bid`, {
        amount: bidAmount
      });
      toast.success(res.data.message);
      setShowBidModal(false);
      setBidAmount(0);
      fetchAuctions();
      refreshUser();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to place bid');
    }
    setProcessing(false);
  };

  const handleBuyout = async (auctionId) => {
    setProcessing(true);
    try {
      const res = await axios.post(`${API}/trading/auctions/${auctionId}/buyout`);
      toast.success(res.data.message);
      fetchAuctions();
      refreshUser();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to buyout');
    }
    setProcessing(false);
  };

  const getTimeRemaining = (endsAt) => {
    const diff = new Date(endsAt) - new Date();
    if (diff <= 0) return 'Terminat';
    const hours = Math.floor(diff / (1000 * 60 * 60));
    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
    if (hours > 24) return `${Math.floor(hours / 24)}z ${hours % 24}h`;
    return `${hours}h ${minutes}m`;
  };

  const categoryLabels = {
    collectibles: 'Colecții', equipment: 'Echipament', resources: 'Resurse',
    cosmetics: 'Cosmetice', property_deeds: 'Acte Proprietate', 
    company_shares: 'Acțiuni Companii', other: 'Altele'
  };

  if (loading) {
    return (
      <div className="min-h-screen pt-20 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-neon-cyan" />
      </div>
    );
  }

  return (
    <div className="min-h-screen pt-16 sm:pt-20 pb-20 lg:pb-12 px-3 sm:px-4" data-testid="trading-page">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-6">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <h1 className="text-2xl sm:text-3xl font-orbitron font-black flex items-center gap-3">
                <Gavel className="w-8 h-8 text-neon-yellow" />
                <span>Trading & <span className="text-neon-cyan">Licitații</span></span>
              </h1>
              <p className="text-white/60 text-sm mt-1">Schimbă cu alți jucători sau licitează pentru iteme rare</p>
            </div>
            <div className="flex gap-2">
              <CyberButton variant="outline" onClick={() => setShowCreateOfferModal(true)}>
                <Repeat className="w-4 h-4 mr-2" /> Ofertă P2P
              </CyberButton>
              <CyberButton variant="primary" onClick={() => setShowCreateAuctionModal(true)}>
                <Plus className="w-4 h-4 mr-2" /> Licitație Nouă
              </CyberButton>
            </div>
          </div>
        </motion.div>

        {/* Quick Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
          <CyberCard className="p-4 text-center">
            <div className="text-xl font-orbitron text-neon-cyan">{auctions.length}</div>
            <div className="text-xs text-white/50">Licitații Active</div>
          </CyberCard>
          <CyberCard className="p-4 text-center">
            <div className="text-xl font-orbitron text-neon-green">{incomingOffers.length}</div>
            <div className="text-xs text-white/50">Oferte Primite</div>
          </CyberCard>
          <CyberCard className="p-4 text-center">
            <div className="text-xl font-orbitron text-neon-purple">{outgoingOffers.length}</div>
            <div className="text-xs text-white/50">Oferte Trimise</div>
          </CyberCard>
          <CyberCard className="p-4 text-center">
            <div className="text-xl font-orbitron text-neon-yellow">{myAuctions.bidding?.length || 0}</div>
            <div className="text-xs text-white/50">Licitez La</div>
          </CyberCard>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
          {[
            { id: 'auctions', label: 'Licitații', icon: Gavel },
            { id: 'p2p', label: 'Trading P2P', icon: Repeat },
            { id: 'my-trades', label: 'Tradurile Mele', icon: Package }
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

        {/* Auctions Tab */}
        {activeTab === 'auctions' && (
          <div>
            {/* Filters */}
            <div className="flex flex-wrap gap-3 mb-4">
              <div className="relative flex-1 min-w-[200px]">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/40" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={e => setSearchQuery(e.target.value)}
                  onKeyPress={e => e.key === 'Enter' && fetchAuctions()}
                  placeholder="Caută iteme..."
                  className="w-full bg-black/50 border border-white/20 pl-10 pr-4 py-2 text-white"
                />
              </div>
              <select
                value={selectedCategory}
                onChange={e => setSelectedCategory(e.target.value)}
                className="bg-black/50 border border-white/20 px-4 py-2 text-white"
              >
                <option value="">Toate Categoriile</option>
                {auctionCategories.map(cat => (
                  <option key={cat} value={cat}>{categoryLabels[cat]}</option>
                ))}
              </select>
              <select
                value={sortBy}
                onChange={e => setSortBy(e.target.value)}
                className="bg-black/50 border border-white/20 px-4 py-2 text-white"
              >
                <option value="ending_soon">Se Termină Curând</option>
                <option value="price_low">Preț Crescător</option>
                <option value="price_high">Preț Descrescător</option>
                <option value="newest">Cele Mai Noi</option>
              </select>
            </div>

            {/* Auction Grid */}
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
              {auctions.map(auction => (
                <CyberCard key={auction.id} className="p-4" data-testid={`auction-${auction.id}`}>
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <h4 className="font-orbitron text-neon-cyan">{auction.item_name}</h4>
                      <span className="text-xs px-2 py-0.5 bg-white/10 text-white/60">
                        {categoryLabels[auction.item_type]}
                      </span>
                    </div>
                    <div className="text-right">
                      <div className="flex items-center gap-1 text-neon-yellow">
                        <Clock className="w-3 h-3" />
                        <span className="text-sm font-mono">{getTimeRemaining(auction.ends_at)}</span>
                      </div>
                    </div>
                  </div>
                  
                  {auction.description && (
                    <p className="text-sm text-white/60 mb-3 line-clamp-2">{auction.description}</p>
                  )}
                  
                  <div className="space-y-2 mb-4">
                    <div className="flex justify-between text-sm">
                      <span className="text-white/50">Preț Curent:</span>
                      <span className="font-orbitron text-neon-green">{auction.current_price?.toFixed(2)} RLM</span>
                    </div>
                    {auction.buyout_price && (
                      <div className="flex justify-between text-sm">
                        <span className="text-white/50">Cumpără Acum:</span>
                        <span className="font-mono text-neon-yellow">{auction.buyout_price?.toFixed(2)} RLM</span>
                      </div>
                    )}
                    <div className="flex justify-between text-sm">
                      <span className="text-white/50">Licitații:</span>
                      <span className="text-white/70">{auction.bid_count}</span>
                    </div>
                  </div>
                  
                  <div className="flex gap-2">
                    <CyberButton 
                      variant="outline" 
                      size="sm" 
                      className="flex-1"
                      onClick={() => {
                        setSelectedAuction(auction);
                        setBidAmount(Math.ceil(auction.current_price * 1.05));
                        setShowBidModal(true);
                      }}
                      disabled={auction.seller_id === user?.id}
                    >
                      Licitează
                    </CyberButton>
                    {auction.buyout_price && (
                      <CyberButton 
                        variant="primary" 
                        size="sm" 
                        className="flex-1"
                        onClick={() => handleBuyout(auction.id)}
                        disabled={processing || auction.seller_id === user?.id}
                      >
                        Cumpără Acum
                      </CyberButton>
                    )}
                  </div>
                  
                  <div className="mt-3 pt-3 border-t border-white/10 text-xs text-white/40">
                    Vânzător: {auction.seller_username}
                  </div>
                </CyberCard>
              ))}
              
              {auctions.length === 0 && (
                <div className="col-span-full text-center py-12 text-white/50">
                  <Gavel className="w-12 h-12 mx-auto mb-4 opacity-50" />
                  <p>Nicio licitație activă. Fii primul care listează!</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* P2P Tab */}
        {activeTab === 'p2p' && (
          <div className="space-y-6">
            {/* Incoming Offers */}
            <CyberCard className="p-4">
              <h3 className="font-orbitron text-lg mb-4 flex items-center gap-2">
                <ArrowDownRight className="w-5 h-5 text-neon-green" /> Oferte Primite
              </h3>
              {incomingOffers.length > 0 ? (
                <div className="space-y-3">
                  {incomingOffers.map(offer => (
                    <div key={offer.id} className="p-4 bg-black/30 border border-neon-green/30">
                      <div className="flex flex-wrap items-start justify-between gap-4 mb-3">
                        <div>
                          <div className="font-mono text-neon-cyan">{offer.sender_username}</div>
                          <div className="text-xs text-white/40">
                            Expiră: {new Date(offer.expires_at).toLocaleString()}
                          </div>
                        </div>
                        <div className="flex gap-2">
                          <CyberButton variant="primary" size="sm" onClick={() => handleAcceptOffer(offer.id)} disabled={processing}>
                            <CheckCircle className="w-4 h-4 mr-1" /> Accept
                          </CyberButton>
                          <CyberButton variant="outline" size="sm" onClick={() => handleDeclineOffer(offer.id)} disabled={processing}>
                            <XCircle className="w-4 h-4 mr-1" /> Refuz
                          </CyberButton>
                        </div>
                      </div>
                      <div className="grid grid-cols-2 gap-4">
                        <div className="p-2 bg-neon-green/10 border border-neon-green/30">
                          <div className="text-xs text-white/50 mb-1">Oferă</div>
                          <div className="font-mono text-neon-green">{offer.offer_rlm} RLM</div>
                        </div>
                        <div className="p-2 bg-neon-red/10 border border-neon-red/30">
                          <div className="text-xs text-white/50 mb-1">Cere</div>
                          <div className="font-mono text-neon-red">{offer.request_rlm} RLM</div>
                        </div>
                      </div>
                      {offer.message && <p className="text-sm text-white/60 mt-3">"{offer.message}"</p>}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-white/50 text-center py-8">Nicio ofertă primită</p>
              )}
            </CyberCard>

            {/* Outgoing Offers */}
            <CyberCard className="p-4">
              <h3 className="font-orbitron text-lg mb-4 flex items-center gap-2">
                <ArrowUpRight className="w-5 h-5 text-neon-purple" /> Oferte Trimise
              </h3>
              {outgoingOffers.length > 0 ? (
                <div className="space-y-3">
                  {outgoingOffers.map(offer => (
                    <div key={offer.id} className="p-4 bg-black/30 border border-neon-purple/30">
                      <div className="flex flex-wrap items-start justify-between gap-4 mb-3">
                        <div>
                          <div className="font-mono text-neon-cyan">Către: {offer.recipient_username}</div>
                          <div className="text-xs text-white/40">
                            Expiră: {new Date(offer.expires_at).toLocaleString()}
                          </div>
                        </div>
                        <CyberButton variant="outline" size="sm" onClick={() => handleCancelOffer(offer.id)} disabled={processing}>
                          <X className="w-4 h-4 mr-1" /> Anulează
                        </CyberButton>
                      </div>
                      <div className="grid grid-cols-2 gap-4">
                        <div className="p-2 bg-neon-green/10 border border-neon-green/30">
                          <div className="text-xs text-white/50 mb-1">Oferi</div>
                          <div className="font-mono text-neon-green">{offer.offer_rlm} RLM</div>
                        </div>
                        <div className="p-2 bg-neon-red/10 border border-neon-red/30">
                          <div className="text-xs text-white/50 mb-1">Ceri</div>
                          <div className="font-mono text-neon-red">{offer.request_rlm} RLM</div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-white/50 text-center py-8">Nicio ofertă trimisă</p>
              )}
            </CyberCard>
          </div>
        )}

        {/* My Trades Tab */}
        {activeTab === 'my-trades' && (
          <div className="space-y-6">
            {/* My Auctions */}
            <CyberCard className="p-4">
              <h3 className="font-orbitron text-lg mb-4">Licitațiile Mele</h3>
              {myAuctions.selling?.length > 0 ? (
                <div className="space-y-3">
                  {myAuctions.selling.map(auction => (
                    <div key={auction.id} className="p-4 bg-black/30 border border-white/10 flex flex-wrap justify-between gap-4">
                      <div>
                        <div className="font-orbitron text-neon-cyan">{auction.item_name}</div>
                        <div className="text-sm text-white/50">
                          {auction.bid_count} licitații • {getTimeRemaining(auction.ends_at)} rămas
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="font-orbitron text-neon-green">{auction.current_price?.toFixed(2)} RLM</div>
                        <span className={`text-xs px-2 py-0.5 ${auction.status === 'active' ? 'bg-neon-green/20 text-neon-green' : 'bg-white/20 text-white/60'}`}>
                          {auction.status.toUpperCase()}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-white/50 text-center py-8">Nu ai licitații active</p>
              )}
            </CyberCard>

            {/* Bidding On */}
            <CyberCard className="p-4">
              <h3 className="font-orbitron text-lg mb-4">Licitez La</h3>
              {myAuctions.bidding?.length > 0 ? (
                <div className="space-y-3">
                  {myAuctions.bidding.map(auction => (
                    <div key={auction.id} className="p-4 bg-black/30 border border-neon-yellow/30 flex flex-wrap justify-between gap-4">
                      <div>
                        <div className="font-orbitron text-neon-cyan">{auction.item_name}</div>
                        <div className="text-sm text-white/50">
                          Vânzător: {auction.seller_username} • {getTimeRemaining(auction.ends_at)} rămas
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="font-orbitron text-neon-yellow">{auction.current_price?.toFixed(2)} RLM</div>
                        <span className="text-xs text-neon-green">Lider licitație</span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-white/50 text-center py-8">Nu licitezi la nimic momentan</p>
              )}
            </CyberCard>
          </div>
        )}

        {/* Create P2P Offer Modal */}
        <AnimatePresence>
          {showCreateOfferModal && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4"
              onClick={() => setShowCreateOfferModal(false)}
            >
              <motion.div
                initial={{ scale: 0.9 }}
                animate={{ scale: 1 }}
                exit={{ scale: 0.9 }}
                className="bg-gray-900 border border-neon-cyan p-6 max-w-md w-full"
                onClick={e => e.stopPropagation()}
              >
                <h3 className="font-orbitron text-xl mb-4 flex items-center gap-2">
                  <Repeat className="w-5 h-5 text-neon-cyan" /> Crează Ofertă P2P
                </h3>
                
                <div className="space-y-4">
                  <div>
                    <label className="text-sm text-white/60 block mb-1">Către (username)</label>
                    <input
                      type="text"
                      value={offerForm.target_username}
                      onChange={e => setOfferForm({...offerForm, target_username: e.target.value})}
                      className="w-full bg-black/50 border border-white/20 p-2 text-white"
                      placeholder="Username jucător"
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-sm text-white/60 block mb-1">Oferi RLM</label>
                      <input
                        type="number"
                        value={offerForm.offer_rlm}
                        onChange={e => setOfferForm({...offerForm, offer_rlm: parseFloat(e.target.value) || 0})}
                        className="w-full bg-black/50 border border-white/20 p-2 text-white"
                        min={0}
                      />
                    </div>
                    <div>
                      <label className="text-sm text-white/60 block mb-1">Ceri RLM</label>
                      <input
                        type="number"
                        value={offerForm.request_rlm}
                        onChange={e => setOfferForm({...offerForm, request_rlm: parseFloat(e.target.value) || 0})}
                        className="w-full bg-black/50 border border-white/20 p-2 text-white"
                        min={0}
                      />
                    </div>
                  </div>
                  <div>
                    <label className="text-sm text-white/60 block mb-1">Mesaj (opțional)</label>
                    <textarea
                      value={offerForm.message}
                      onChange={e => setOfferForm({...offerForm, message: e.target.value})}
                      className="w-full bg-black/50 border border-white/20 p-2 text-white h-20"
                      placeholder="Adaugă un mesaj..."
                    />
                  </div>
                </div>
                
                <div className="flex gap-3 mt-6">
                  <CyberButton variant="outline" className="flex-1" onClick={() => setShowCreateOfferModal(false)}>
                    Anulează
                  </CyberButton>
                  <CyberButton 
                    variant="primary" 
                    className="flex-1" 
                    onClick={handleCreateOffer}
                    disabled={processing || !offerForm.target_username}
                  >
                    {processing ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Trimite Ofertă'}
                  </CyberButton>
                </div>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Create Auction Modal */}
        <AnimatePresence>
          {showCreateAuctionModal && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4"
              onClick={() => setShowCreateAuctionModal(false)}
            >
              <motion.div
                initial={{ scale: 0.9 }}
                animate={{ scale: 1 }}
                exit={{ scale: 0.9 }}
                className="bg-gray-900 border border-neon-yellow p-6 max-w-md w-full max-h-[90vh] overflow-y-auto"
                onClick={e => e.stopPropagation()}
              >
                <h3 className="font-orbitron text-xl mb-4 flex items-center gap-2">
                  <Gavel className="w-5 h-5 text-neon-yellow" /> Crează Licitație
                </h3>
                
                <div className="space-y-4">
                  <div>
                    <label className="text-sm text-white/60 block mb-1">ID Item</label>
                    <input
                      type="text"
                      value={auctionForm.item_id}
                      onChange={e => setAuctionForm({...auctionForm, item_id: e.target.value})}
                      className="w-full bg-black/50 border border-white/20 p-2 text-white"
                      placeholder="ID-ul itemului din inventar"
                    />
                  </div>
                  <div>
                    <label className="text-sm text-white/60 block mb-1">Nume Item</label>
                    <input
                      type="text"
                      value={auctionForm.item_name}
                      onChange={e => setAuctionForm({...auctionForm, item_name: e.target.value})}
                      className="w-full bg-black/50 border border-white/20 p-2 text-white"
                      placeholder="Numele itemului"
                    />
                  </div>
                  <div>
                    <label className="text-sm text-white/60 block mb-1">Categorie</label>
                    <select
                      value={auctionForm.item_type}
                      onChange={e => setAuctionForm({...auctionForm, item_type: e.target.value})}
                      className="w-full bg-black/50 border border-white/20 p-2 text-white"
                    >
                      {auctionCategories.map(cat => (
                        <option key={cat} value={cat}>{categoryLabels[cat]}</option>
                      ))}
                    </select>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-sm text-white/60 block mb-1">Preț Start</label>
                      <input
                        type="number"
                        value={auctionForm.starting_price}
                        onChange={e => setAuctionForm({...auctionForm, starting_price: parseFloat(e.target.value) || 0})}
                        className="w-full bg-black/50 border border-white/20 p-2 text-white"
                        min={1}
                      />
                    </div>
                    <div>
                      <label className="text-sm text-white/60 block mb-1">Buyout (opțional)</label>
                      <input
                        type="number"
                        value={auctionForm.buyout_price}
                        onChange={e => setAuctionForm({...auctionForm, buyout_price: e.target.value})}
                        className="w-full bg-black/50 border border-white/20 p-2 text-white"
                        placeholder="0 = fără"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="text-sm text-white/60 block mb-1">Durată (ore)</label>
                    <select
                      value={auctionForm.duration_hours}
                      onChange={e => setAuctionForm({...auctionForm, duration_hours: parseInt(e.target.value)})}
                      className="w-full bg-black/50 border border-white/20 p-2 text-white"
                    >
                      <option value={1}>1 oră</option>
                      <option value={6}>6 ore</option>
                      <option value={12}>12 ore</option>
                      <option value={24}>24 ore</option>
                      <option value={48}>2 zile</option>
                      <option value={72}>3 zile</option>
                      <option value={168}>7 zile</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-sm text-white/60 block mb-1">Descriere</label>
                    <textarea
                      value={auctionForm.description}
                      onChange={e => setAuctionForm({...auctionForm, description: e.target.value})}
                      className="w-full bg-black/50 border border-white/20 p-2 text-white h-20"
                      placeholder="Descriere item..."
                    />
                  </div>
                  <div className="p-3 bg-neon-yellow/10 border border-neon-yellow/30 text-sm">
                    <span className="text-white/60">Taxă listare: </span>
                    <span className="text-neon-yellow font-mono">{(auctionForm.starting_price * 0.025).toFixed(2)} RLM (2.5%)</span>
                  </div>
                </div>
                
                <div className="flex gap-3 mt-6">
                  <CyberButton variant="outline" className="flex-1" onClick={() => setShowCreateAuctionModal(false)}>
                    Anulează
                  </CyberButton>
                  <CyberButton 
                    variant="primary" 
                    className="flex-1" 
                    onClick={handleCreateAuction}
                    disabled={processing || !auctionForm.item_id || !auctionForm.item_name}
                  >
                    {processing ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Listează'}
                  </CyberButton>
                </div>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Bid Modal */}
        <AnimatePresence>
          {showBidModal && selectedAuction && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4"
              onClick={() => setShowBidModal(false)}
            >
              <motion.div
                initial={{ scale: 0.9 }}
                animate={{ scale: 1 }}
                exit={{ scale: 0.9 }}
                className="bg-gray-900 border border-neon-green p-6 max-w-md w-full"
                onClick={e => e.stopPropagation()}
              >
                <h3 className="font-orbitron text-xl mb-4">Licitează pentru {selectedAuction.item_name}</h3>
                
                <div className="space-y-4">
                  <div className="p-4 bg-black/30 border border-white/10">
                    <div className="flex justify-between mb-2">
                      <span className="text-white/60">Preț Curent:</span>
                      <span className="font-orbitron text-neon-cyan">{selectedAuction.current_price?.toFixed(2)} RLM</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-white/60">Minim Bid (+5%):</span>
                      <span className="text-neon-yellow">{(selectedAuction.current_price * 1.05).toFixed(2)} RLM</span>
                    </div>
                  </div>
                  
                  <div>
                    <label className="text-sm text-white/60 block mb-1">Suma Licitată</label>
                    <input
                      type="number"
                      value={bidAmount}
                      onChange={e => setBidAmount(parseFloat(e.target.value) || 0)}
                      className="w-full bg-black/50 border border-white/20 p-3 text-white text-center text-xl font-mono"
                      min={selectedAuction.current_price * 1.05}
                    />
                  </div>
                  
                  <div className="text-sm text-white/50">
                    Balanța ta: <span className="text-neon-cyan">{user?.realum_balance?.toFixed(2)} RLM</span>
                  </div>
                </div>
                
                <div className="flex gap-3 mt-6">
                  <CyberButton variant="outline" className="flex-1" onClick={() => setShowBidModal(false)}>
                    Anulează
                  </CyberButton>
                  <CyberButton 
                    variant="primary" 
                    className="flex-1" 
                    onClick={handlePlaceBid}
                    disabled={processing || bidAmount < selectedAuction.current_price * 1.05}
                  >
                    {processing ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Plasează Bid'}
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

export default TradingPage;
