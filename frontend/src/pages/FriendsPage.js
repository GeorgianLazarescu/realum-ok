import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { 
  Users, UserPlus, Gift, MessageSquare, Check, X, Clock,
  Loader2, Search, Circle, Send
} from 'lucide-react';
import axios from 'axios';
import { API } from '../utils/api';
import { useAuth } from '../context/AuthContext';
import { CyberCard, CyberButton } from '../components/common/CyberUI';
import { toast } from 'sonner';

const FriendsPage = () => {
  const { user, refreshUser } = useAuth();
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  
  const [activeTab, setActiveTab] = useState('friends'); // friends, requests, gifts
  const [friends, setFriends] = useState([]);
  const [requests, setRequests] = useState({ incoming: [], outgoing: [] });
  const [receivedGifts, setReceivedGifts] = useState([]);
  const [giftTypes, setGiftTypes] = useState({});
  
  const [showAddModal, setShowAddModal] = useState(false);
  const [showGiftModal, setShowGiftModal] = useState(false);
  const [searchUsername, setSearchUsername] = useState('');
  const [selectedFriend, setSelectedFriend] = useState(null);
  const [giftForm, setGiftForm] = useState({ gift_type: 'flowers', amount: 0, message: '' });

  useEffect(() => {
    fetchAllData();
  }, []);

  const fetchAllData = async () => {
    try {
      const [friendsRes, requestsRes, giftsRes, giftTypesRes] = await Promise.all([
        axios.get(`${API}/friends/list`),
        axios.get(`${API}/friends/requests`),
        axios.get(`${API}/friends/gifts/received`),
        axios.get(`${API}/friends/gift-types`)
      ]);
      
      setFriends(friendsRes.data.friends || []);
      setRequests(requestsRes.data);
      setReceivedGifts(giftsRes.data.gifts || []);
      setGiftTypes(giftTypesRes.data.gift_types || {});
    } catch (error) {
      console.error('Failed to load friends:', error);
    }
    setLoading(false);
  };

  const handleSendRequest = async () => {
    if (!searchUsername.trim()) return;
    setProcessing(true);
    
    try {
      const res = await axios.post(`${API}/friends/request`, {
        target_username: searchUsername.trim()
      });
      toast.success(res.data.message);
      setShowAddModal(false);
      setSearchUsername('');
      fetchAllData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to send request');
    }
    setProcessing(false);
  };

  const handleAcceptRequest = async (requestId) => {
    setProcessing(true);
    try {
      const res = await axios.post(`${API}/friends/requests/${requestId}/accept`);
      toast.success(res.data.message);
      fetchAllData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to accept');
    }
    setProcessing(false);
  };

  const handleDeclineRequest = async (requestId) => {
    setProcessing(true);
    try {
      await axios.post(`${API}/friends/requests/${requestId}/decline`);
      toast.info('Request declined');
      fetchAllData();
    } catch (error) {
      toast.error('Failed to decline');
    }
    setProcessing(false);
  };

  const handleSendGift = async () => {
    if (!selectedFriend) return;
    setProcessing(true);
    
    try {
      const payload = {
        friend_id: selectedFriend.id,
        gift_type: giftForm.gift_type,
        message: giftForm.message || null
      };
      
      if (giftForm.gift_type === 'rlm') {
        payload.amount = giftForm.amount;
      }
      
      const res = await axios.post(`${API}/friends/gift`, payload);
      toast.success(res.data.message);
      setShowGiftModal(false);
      setGiftForm({ gift_type: 'flowers', amount: 0, message: '' });
      refreshUser();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to send gift');
    }
    setProcessing(false);
  };

  const handleRemoveFriend = async (friendId) => {
    if (!confirm('Ești sigur că vrei să elimini acest prieten?')) return;
    
    try {
      await axios.delete(`${API}/friends/${friendId}`);
      toast.info('Friend removed');
      fetchAllData();
    } catch (error) {
      toast.error('Failed to remove friend');
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen pt-20 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-neon-cyan" />
      </div>
    );
  }

  const onlineCount = friends.filter(f => f.is_online).length;

  return (
    <div className="min-h-screen pt-16 sm:pt-20 pb-20 lg:pb-12 px-3 sm:px-4" data-testid="friends-page">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl sm:text-3xl font-orbitron font-black flex items-center gap-3">
              <Users className="w-8 h-8 text-neon-green" />
              <span>Prieteni</span>
            </h1>
            <p className="text-white/60 text-sm mt-1">
              {friends.length} prieteni • {onlineCount} online
            </p>
          </div>
          <CyberButton variant="primary" onClick={() => setShowAddModal(true)}>
            <UserPlus className="w-4 h-4 mr-2" /> Adaugă Prieten
          </CyberButton>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-3 mb-6">
          <CyberCard className="p-4 text-center">
            <div className="text-2xl font-orbitron text-neon-green">{friends.length}</div>
            <div className="text-xs text-white/50">Total Prieteni</div>
          </CyberCard>
          <CyberCard className="p-4 text-center">
            <div className="text-2xl font-orbitron text-neon-cyan">{onlineCount}</div>
            <div className="text-xs text-white/50">Online Acum</div>
          </CyberCard>
          <CyberCard className="p-4 text-center">
            <div className="text-2xl font-orbitron text-neon-yellow">{requests.incoming?.length || 0}</div>
            <div className="text-xs text-white/50">Cereri Noi</div>
          </CyberCard>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6">
          {[
            { id: 'friends', label: 'Prieteni', icon: Users },
            { id: 'requests', label: `Cereri (${requests.incoming?.length || 0})`, icon: UserPlus },
            { id: 'gifts', label: 'Cadouri', icon: Gift }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-2 font-mono text-sm flex items-center gap-2 transition-all ${
                activeTab === tab.id 
                  ? 'bg-neon-green/20 border border-neon-green text-neon-green' 
                  : 'border border-white/20 text-white/60 hover:border-white/40'
              }`}
            >
              <tab.icon className="w-4 h-4" /> {tab.label}
            </button>
          ))}
        </div>

        {/* Friends List */}
        {activeTab === 'friends' && (
          <div className="space-y-2">
            {friends.map(friend => (
              <CyberCard key={friend.id} className="p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="relative">
                      <div className="w-12 h-12 bg-neon-purple/20 border border-neon-purple flex items-center justify-center text-xl">
                        {friend.username[0].toUpperCase()}
                      </div>
                      <Circle 
                        className={`absolute -bottom-1 -right-1 w-4 h-4 ${
                          friend.is_online ? 'text-neon-green fill-neon-green' : 'text-gray-500 fill-gray-500'
                        }`} 
                      />
                    </div>
                    <div>
                      <div className="font-mono text-neon-cyan">{friend.username}</div>
                      <div className="text-xs text-white/40">
                        {friend.is_online ? 'Online' : `Văzut ${new Date(friend.last_active).toLocaleDateString()}`}
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-2">
                    <CyberButton 
                      variant="outline" 
                      size="sm"
                      onClick={() => {
                        setSelectedFriend(friend);
                        setShowGiftModal(true);
                      }}
                    >
                      <Gift className="w-4 h-4" />
                    </CyberButton>
                    <CyberButton 
                      variant="outline" 
                      size="sm"
                      onClick={() => handleRemoveFriend(friend.id)}
                    >
                      <X className="w-4 h-4" />
                    </CyberButton>
                  </div>
                </div>
              </CyberCard>
            ))}
            
            {friends.length === 0 && (
              <div className="text-center py-12 text-white/50">
                <Users className="w-12 h-12 mx-auto mb-4 opacity-50" />
                <p>Nu ai prieteni încă. Trimite o cerere!</p>
              </div>
            )}
          </div>
        )}

        {/* Requests Tab */}
        {activeTab === 'requests' && (
          <div className="space-y-6">
            {/* Incoming */}
            <div>
              <h3 className="font-orbitron text-lg mb-3">Cereri Primite</h3>
              {requests.incoming?.length > 0 ? (
                <div className="space-y-2">
                  {requests.incoming.map(req => (
                    <CyberCard key={req.request_id} className="p-4">
                      <div className="flex items-center justify-between">
                        <div>
                          <div className="font-mono text-neon-cyan">{req.from_user?.username}</div>
                          {req.message && <div className="text-sm text-white/60">"{req.message}"</div>}
                          <div className="text-xs text-white/40">
                            <Clock className="w-3 h-3 inline mr-1" />
                            {new Date(req.sent_at).toLocaleDateString()}
                          </div>
                        </div>
                        <div className="flex gap-2">
                          <CyberButton 
                            variant="primary" 
                            size="sm"
                            onClick={() => handleAcceptRequest(req.request_id)}
                            disabled={processing}
                          >
                            <Check className="w-4 h-4" />
                          </CyberButton>
                          <CyberButton 
                            variant="outline" 
                            size="sm"
                            onClick={() => handleDeclineRequest(req.request_id)}
                            disabled={processing}
                          >
                            <X className="w-4 h-4" />
                          </CyberButton>
                        </div>
                      </div>
                    </CyberCard>
                  ))}
                </div>
              ) : (
                <p className="text-white/50 text-center py-6">Nicio cerere primită</p>
              )}
            </div>

            {/* Outgoing */}
            <div>
              <h3 className="font-orbitron text-lg mb-3">Cereri Trimise</h3>
              {requests.outgoing?.length > 0 ? (
                <div className="space-y-2">
                  {requests.outgoing.map(req => (
                    <CyberCard key={req.request_id} className="p-4 opacity-70">
                      <div className="flex items-center justify-between">
                        <div>
                          <div className="font-mono">Către: {req.to_user?.username}</div>
                          <div className="text-xs text-white/40">În așteptare...</div>
                        </div>
                      </div>
                    </CyberCard>
                  ))}
                </div>
              ) : (
                <p className="text-white/50 text-center py-6">Nicio cerere trimisă</p>
              )}
            </div>
          </div>
        )}

        {/* Gifts Tab */}
        {activeTab === 'gifts' && (
          <div className="space-y-2">
            <h3 className="font-orbitron text-lg mb-3">Cadouri Primite</h3>
            {receivedGifts.length > 0 ? (
              receivedGifts.map(gift => (
                <CyberCard key={gift.id} className="p-4 border-neon-yellow/30">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <Gift className="w-8 h-8 text-neon-yellow" />
                      <div>
                        <div className="font-mono text-neon-cyan">
                          De la: {gift.sender_name}
                        </div>
                        <div className="text-sm text-neon-yellow">
                          {gift.gift_type === 'rlm' ? `${gift.value} RLM` : giftTypes[gift.gift_type]?.name}
                        </div>
                        {gift.message && <div className="text-xs text-white/60">"{gift.message}"</div>}
                      </div>
                    </div>
                    <div className="text-xs text-white/40">
                      {new Date(gift.created_at).toLocaleDateString()}
                    </div>
                  </div>
                </CyberCard>
              ))
            ) : (
              <div className="text-center py-12 text-white/50">
                <Gift className="w-12 h-12 mx-auto mb-4 opacity-50" />
                <p>Nu ai primit cadouri încă</p>
              </div>
            )}
          </div>
        )}

        {/* Add Friend Modal */}
        {showAddModal && (
          <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4" onClick={() => setShowAddModal(false)}>
            <CyberCard className="p-6 max-w-md w-full" onClick={e => e.stopPropagation()}>
              <h3 className="font-orbitron text-xl mb-4">Adaugă Prieten</h3>
              <input
                type="text"
                value={searchUsername}
                onChange={e => setSearchUsername(e.target.value)}
                placeholder="Username prieten"
                className="w-full bg-black/50 border border-white/20 p-3 text-white mb-4"
              />
              <div className="flex gap-3">
                <CyberButton variant="outline" className="flex-1" onClick={() => setShowAddModal(false)}>
                  Anulează
                </CyberButton>
                <CyberButton variant="primary" className="flex-1" onClick={handleSendRequest} disabled={processing}>
                  {processing ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Trimite Cerere'}
                </CyberButton>
              </div>
            </CyberCard>
          </div>
        )}

        {/* Send Gift Modal */}
        {showGiftModal && selectedFriend && (
          <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4" onClick={() => setShowGiftModal(false)}>
            <CyberCard className="p-6 max-w-md w-full" onClick={e => e.stopPropagation()}>
              <h3 className="font-orbitron text-xl mb-4">Trimite Cadou către {selectedFriend.username}</h3>
              
              <div className="space-y-4">
                <div>
                  <label className="text-sm text-white/60 block mb-2">Tip Cadou</label>
                  <select
                    value={giftForm.gift_type}
                    onChange={e => setGiftForm({...giftForm, gift_type: e.target.value})}
                    className="w-full bg-black/50 border border-white/20 p-2 text-white"
                  >
                    {Object.entries(giftTypes).map(([key, info]) => (
                      <option key={key} value={key}>
                        {info.name} {info.cost ? `(${info.cost} RLM)` : ''}
                      </option>
                    ))}
                  </select>
                </div>
                
                {giftForm.gift_type === 'rlm' && (
                  <div>
                    <label className="text-sm text-white/60 block mb-2">Sumă RLM</label>
                    <input
                      type="number"
                      value={giftForm.amount}
                      onChange={e => setGiftForm({...giftForm, amount: parseInt(e.target.value) || 0})}
                      min={10}
                      className="w-full bg-black/50 border border-white/20 p-2 text-white"
                    />
                  </div>
                )}
                
                <div>
                  <label className="text-sm text-white/60 block mb-2">Mesaj (opțional)</label>
                  <input
                    type="text"
                    value={giftForm.message}
                    onChange={e => setGiftForm({...giftForm, message: e.target.value})}
                    placeholder="Un mesaj pentru prieten..."
                    className="w-full bg-black/50 border border-white/20 p-2 text-white"
                  />
                </div>
              </div>
              
              <div className="flex gap-3 mt-6">
                <CyberButton variant="outline" className="flex-1" onClick={() => setShowGiftModal(false)}>
                  Anulează
                </CyberButton>
                <CyberButton variant="primary" className="flex-1" onClick={handleSendGift} disabled={processing}>
                  {processing ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Trimite'}
                </CyberButton>
              </div>
            </CyberCard>
          </div>
        )}
      </div>
    </div>
  );
};

export default FriendsPage;
