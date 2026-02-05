import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Heart, HeartCrack, Users, Baby, Gift, Send, Check, X,
  Loader2, User, Crown, BookOpen, Utensils, Gamepad2, Sparkles,
  Trophy, Calendar, Cake, PartyPopper
} from 'lucide-react';
import axios from 'axios';
import { API } from '../utils/api';
import { useAuth } from '../context/AuthContext';
import { CyberCard, CyberButton } from '../components/common/CyberUI';
import { toast } from 'sonner';

const FamilyPage = () => {
  const { user, refreshUser } = useAuth();
  
  const [familyStatus, setFamilyStatus] = useState(null);
  const [achievements, setAchievements] = useState([]);
  const [familyEvents, setFamilyEvents] = useState({ active_events: [], upcoming_events: [] });
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [activeTab, setActiveTab] = useState('family'); // family, achievements, events
  
  // Modal states
  const [showProposeModal, setShowProposeModal] = useState(false);
  const [showAdoptModal, setShowAdoptModal] = useState(false);
  const [showChildModal, setShowChildModal] = useState(false);
  
  // Form states
  const [proposeUserId, setProposeUserId] = useState('');
  const [proposeMessage, setProposeMessage] = useState('Will you marry me in REALUM?');
  const [childName, setChildName] = useState('');
  const [childGender, setChildGender] = useState('boy');
  
  // User search
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  
  useEffect(() => {
    fetchAllData();
  }, []);
  
  const fetchAllData = async () => {
    try {
      const [statusRes, achievementsRes, eventsRes] = await Promise.all([
        axios.get(`${API}/family/status`),
        axios.get(`${API}/family/achievements`),
        axios.get(`${API}/family/events`)
      ]);
      setFamilyStatus(statusRes.data);
      setAchievements(achievementsRes.data.achievements || []);
      setFamilyEvents(eventsRes.data);
    } catch (error) {
      console.error('Failed to load family data:', error);
    }
    setLoading(false);
  };
  
  const fetchFamilyStatus = async () => {
    try {
      const res = await axios.get(`${API}/family/status`);
      setFamilyStatus(res.data);
    } catch (error) {
      toast.error('Failed to load family status');
    }
  };
  
  const searchUsers = async (query) => {
    if (query.length < 2) {
      setSearchResults([]);
      return;
    }
    try {
      const res = await axios.get(`${API}/users/search?q=${query}`);
      setSearchResults(res.data.users?.filter(u => u.id !== user?.id) || []);
    } catch (error) {
      console.error('Search failed:', error);
    }
  };
  
  const handlePropose = async () => {
    if (!proposeUserId) {
      toast.error('Please select a user to propose to');
      return;
    }
    setProcessing(true);
    try {
      const res = await axios.post(`${API}/family/propose`, {
        partner_id: proposeUserId,
        message: proposeMessage
      });
      toast.success(res.data.message);
      setShowProposeModal(false);
      setProposeUserId('');
      fetchFamilyStatus();
      refreshUser();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to send proposal');
    }
    setProcessing(false);
  };
  
  const handleRespondProposal = async (proposalId, accept) => {
    setProcessing(true);
    try {
      const res = await axios.post(`${API}/family/proposal/respond`, {
        proposal_id: proposalId,
        accept
      });
      toast.success(res.data.message);
      fetchFamilyStatus();
      refreshUser();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to respond to proposal');
    }
    setProcessing(false);
  };
  
  const handleDivorce = async () => {
    if (!window.confirm('Are you sure you want to file for divorce? This costs 100 RLM.')) return;
    setProcessing(true);
    try {
      const res = await axios.post(`${API}/family/divorce`);
      toast.success(res.data.message);
      fetchFamilyStatus();
      refreshUser();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to file divorce');
    }
    setProcessing(false);
  };
  
  const handleAdopt = async () => {
    if (!childName) {
      toast.error('Please enter a name for your child');
      return;
    }
    setProcessing(true);
    try {
      const res = await axios.post(`${API}/family/adopt`, {
        child_name: childName,
        child_gender: childGender
      });
      toast.success(res.data.message);
      setShowAdoptModal(false);
      setChildName('');
      fetchFamilyStatus();
      refreshUser();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to adopt');
    }
    setProcessing(false);
  };
  
  const handleCreateChild = async () => {
    if (!childName) {
      toast.error('Please enter a name for your child');
      return;
    }
    setProcessing(true);
    try {
      const res = await axios.post(`${API}/family/create-child`, {
        child_name: childName,
        child_gender: childGender
      });
      toast.success(res.data.message);
      setShowChildModal(false);
      setChildName('');
      fetchFamilyStatus();
      refreshUser();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to have child');
    }
    setProcessing(false);
  };
  
  const handleInteractChild = async (childId, interactionType) => {
    try {
      const res = await axios.post(`${API}/family/children/${childId}/interact?interaction_type=${interactionType}`);
      toast.success(res.data.message);
      fetchAllData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Interaction failed');
    }
  };
  
  const handleClaimAchievement = async (achievementId) => {
    setProcessing(true);
    try {
      const res = await axios.post(`${API}/family/achievements/${achievementId}/claim`);
      toast.success(res.data.message);
      fetchAllData();
      refreshUser();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to claim achievement');
    }
    setProcessing(false);
  };
  
  const handleClaimEvent = async (eventType, childId = null) => {
    setProcessing(true);
    try {
      const url = childId 
        ? `${API}/family/events/claim?event_type=${eventType}&child_id=${childId}`
        : `${API}/family/events/claim?event_type=${eventType}`;
      const res = await axios.post(url);
      toast.success(res.data.message);
      fetchAllData();
      refreshUser();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to claim event bonus');
    }
    setProcessing(false);
  };
  
  if (loading) {
    return (
      <div className="min-h-screen pt-20 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-pink-500" />
      </div>
    );
  }
  
  return (
    <div className="min-h-screen pt-20 pb-20 px-4" data-testid="family-page">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-6"
        >
          <h1 className="text-3xl md:text-4xl font-orbitron font-black mb-2">
            <span className="text-pink-500">Family</span> & Relationships
          </h1>
          <p className="text-white/60">Build your virtual family in REALUM</p>
        </motion.div>
        
        {/* Tab Navigation */}
        <div className="flex justify-center gap-2 mb-6">
          {[
            { id: 'family', label: 'Family', icon: Heart },
            { id: 'achievements', label: 'Achievements', icon: Trophy },
            { id: 'events', label: 'Events', icon: Calendar }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg border transition-all ${
                activeTab === tab.id
                  ? 'bg-pink-500/20 border-pink-500 text-pink-400'
                  : 'bg-white/5 border-white/20 text-white/60 hover:border-white/40'
              }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
              {tab.id === 'achievements' && (
                <span className="text-xs bg-pink-500/30 px-1.5 rounded">
                  {achievements.filter(a => a.can_claim).length}
                </span>
              )}
              {tab.id === 'events' && familyEvents.active_events?.length > 0 && (
                <span className="text-xs bg-yellow-500/30 px-1.5 rounded">
                  {familyEvents.active_events.length}
                </span>
              )}
            </button>
          ))}
        </div>
        
        {/* Family Tab */}
        {activeTab === 'family' && (
          <>
        {/* Marriage Status Card */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="mb-8"
        >
          <CyberCard className="p-6 bg-gradient-to-r from-pink-900/30 to-purple-900/30 border-pink-500/30">
            <div className="flex items-center justify-between flex-wrap gap-4">
              <div className="flex items-center gap-4">
                <div className="w-16 h-16 rounded-full bg-pink-500/20 flex items-center justify-center">
                  {familyStatus?.status === 'married' ? (
                    <Heart className="w-8 h-8 text-pink-500 fill-pink-500" />
                  ) : (
                    <Heart className="w-8 h-8 text-pink-500" />
                  )}
                </div>
                <div>
                  <h2 className="text-xl font-orbitron font-bold text-pink-400">
                    {familyStatus?.status === 'married' ? 'Married' : 'Single'}
                  </h2>
                  {familyStatus?.marriage?.partner && (
                    <p className="text-white/60">
                      To <span className="text-pink-300 font-bold">{familyStatus.marriage.partner.username}</span>
                    </p>
                  )}
                  {familyStatus?.status === 'married' && familyStatus?.marriage?.married_at && (
                    <p className="text-xs text-white/40">
                      Since {new Date(familyStatus.marriage.married_at).toLocaleDateString()}
                    </p>
                  )}
                </div>
              </div>
              
              <div className="flex gap-2">
                {familyStatus?.status === 'married' ? (
                  <CyberButton 
                    onClick={handleDivorce}
                    disabled={processing}
                    className="bg-red-500/20 border-red-500 hover:bg-red-500/30"
                  >
                    <HeartCrack className="w-4 h-4 mr-2" />
                    Divorce ({familyStatus?.costs?.divorce} RLM)
                  </CyberButton>
                ) : (
                  <CyberButton 
                    onClick={() => setShowProposeModal(true)}
                    disabled={!familyStatus?.can_marry}
                    className="bg-pink-500/20 border-pink-500 hover:bg-pink-500/30"
                  >
                    <Heart className="w-4 h-4 mr-2" />
                    Propose ({familyStatus?.costs?.proposal} RLM)
                  </CyberButton>
                )}
              </div>
            </div>
            
            {!familyStatus?.can_marry && familyStatus?.marry_reason && (
              <p className="mt-4 text-yellow-400 text-sm">{familyStatus.marry_reason}</p>
            )}
          </CyberCard>
        </motion.div>
        
        {/* Pending Proposals */}
        {familyStatus?.pending_proposals?.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="mb-8"
          >
            <h3 className="font-orbitron font-bold text-lg mb-4 flex items-center gap-2">
              <Gift className="w-5 h-5 text-pink-500" />
              Pending Proposals
            </h3>
            
            <div className="space-y-3">
              {familyStatus.pending_proposals.map(proposal => (
                <CyberCard key={proposal.id} className="p-4">
                  <div className="flex items-center justify-between flex-wrap gap-4">
                    <div className="flex items-center gap-3">
                      <div className="w-12 h-12 rounded-full bg-pink-500/20 flex items-center justify-center">
                        <User className="w-6 h-6 text-pink-400" />
                      </div>
                      <div>
                        <p className="font-bold text-pink-300">
                          {proposal.from_user?.username || proposal.from_username}
                        </p>
                        <p className="text-sm text-white/60 italic">"{proposal.message}"</p>
                      </div>
                    </div>
                    
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleRespondProposal(proposal.id, true)}
                        disabled={processing}
                        className="px-4 py-2 bg-green-500/20 border border-green-500 rounded-lg text-green-400 hover:bg-green-500/30 transition-all flex items-center gap-2"
                      >
                        <Check className="w-4 h-4" />
                        Accept ({familyStatus?.costs?.wedding} RLM)
                      </button>
                      <button
                        onClick={() => handleRespondProposal(proposal.id, false)}
                        disabled={processing}
                        className="px-4 py-2 bg-red-500/20 border border-red-500 rounded-lg text-red-400 hover:bg-red-500/30 transition-all flex items-center gap-2"
                      >
                        <X className="w-4 h-4" />
                        Decline
                      </button>
                    </div>
                  </div>
                </CyberCard>
              ))}
            </div>
          </motion.div>
        )}
        
        {/* Children Section */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
        >
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-orbitron font-bold text-lg flex items-center gap-2">
              <Baby className="w-5 h-5 text-blue-400" />
              Children ({familyStatus?.children_count || 0})
            </h3>
            
            <div className="flex gap-2">
              <CyberButton 
                onClick={() => setShowAdoptModal(true)}
                className="text-sm bg-blue-500/20 border-blue-500"
              >
                <Users className="w-4 h-4 mr-1" />
                Adopt ({familyStatus?.costs?.adoption} RLM)
              </CyberButton>
              
              {familyStatus?.status === 'married' && (
                <CyberButton 
                  onClick={() => setShowChildModal(true)}
                  className="text-sm bg-purple-500/20 border-purple-500"
                >
                  <Baby className="w-4 h-4 mr-1" />
                  Have Child ({familyStatus?.costs?.child_creation} RLM)
                </CyberButton>
              )}
            </div>
          </div>
          
          {familyStatus?.children?.length > 0 ? (
            <div className="grid md:grid-cols-2 gap-4">
              {familyStatus.children.map(child => (
                <CyberCard key={child.id} className="p-4">
                  <div className="flex items-start gap-4">
                    <div className="w-16 h-16 rounded-lg bg-gradient-to-br from-blue-500/20 to-purple-500/20 flex items-center justify-center text-3xl">
                      {child.gender === 'boy' ? '👦' : child.gender === 'girl' ? '👧' : '🧒'}
                    </div>
                    <div className="flex-1">
                      <h4 className="font-bold text-lg">{child.name}</h4>
                      <p className="text-xs text-white/40 mb-2">
                        {child.type === 'adopted' ? 'Adopted' : 'Biological'} • Age {child.age}
                      </p>
                      
                      <div className="grid grid-cols-3 gap-2 mb-3">
                        <div className="text-center">
                          <div className="text-xs text-white/40">Happiness</div>
                          <div className="text-pink-400 font-bold">{child.happiness}%</div>
                        </div>
                        <div className="text-center">
                          <div className="text-xs text-white/40">Health</div>
                          <div className="text-green-400 font-bold">{child.health}%</div>
                        </div>
                        <div className="text-center">
                          <div className="text-xs text-white/40">Education</div>
                          <div className="text-blue-400 font-bold">Lv.{child.education_level}</div>
                        </div>
                      </div>
                      
                      <div className="flex gap-2">
                        <button
                          onClick={() => handleInteractChild(child.id, 'play')}
                          className="flex-1 px-2 py-1 bg-pink-500/20 border border-pink-500/50 rounded text-xs text-pink-400 hover:bg-pink-500/30 flex items-center justify-center gap-1"
                        >
                          <Gamepad2 className="w-3 h-3" /> Play
                        </button>
                        <button
                          onClick={() => handleInteractChild(child.id, 'feed')}
                          className="flex-1 px-2 py-1 bg-green-500/20 border border-green-500/50 rounded text-xs text-green-400 hover:bg-green-500/30 flex items-center justify-center gap-1"
                        >
                          <Utensils className="w-3 h-3" /> Feed
                        </button>
                        <button
                          onClick={() => handleInteractChild(child.id, 'educate')}
                          className="flex-1 px-2 py-1 bg-blue-500/20 border border-blue-500/50 rounded text-xs text-blue-400 hover:bg-blue-500/30 flex items-center justify-center gap-1"
                        >
                          <BookOpen className="w-3 h-3" /> Educate
                        </button>
                      </div>
                    </div>
                  </div>
                </CyberCard>
              ))}
            </div>
          ) : (
            <CyberCard className="p-8 text-center">
              <Baby className="w-12 h-12 mx-auto mb-3 text-white/20" />
              <p className="text-white/40">No children yet</p>
              <p className="text-sm text-white/30">Adopt a child or have one with your spouse</p>
            </CyberCard>
          )}
        </motion.div>
        
        {/* Propose Modal */}
        <AnimatePresence>
          {showProposeModal && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4"
              onClick={() => setShowProposeModal(false)}
            >
              <motion.div
                initial={{ scale: 0.9, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.9, opacity: 0 }}
                className="bg-gray-900 border border-pink-500/30 rounded-xl p-6 max-w-md w-full"
                onClick={e => e.stopPropagation()}
              >
                <h3 className="font-orbitron font-bold text-xl text-pink-400 mb-4 flex items-center gap-2">
                  <Heart className="w-6 h-6" />
                  Send Proposal
                </h3>
                
                <div className="space-y-4">
                  <div>
                    <label className="text-sm text-white/60 mb-1 block">Search User</label>
                    <input
                      type="text"
                      value={searchQuery}
                      onChange={(e) => {
                        setSearchQuery(e.target.value);
                        searchUsers(e.target.value);
                      }}
                      placeholder="Enter username..."
                      className="w-full bg-white/5 border border-white/20 rounded-lg px-4 py-2 text-white"
                    />
                    
                    {searchResults.length > 0 && (
                      <div className="mt-2 bg-white/5 border border-white/10 rounded-lg max-h-40 overflow-y-auto">
                        {searchResults.map(u => (
                          <button
                            key={u.id}
                            onClick={() => {
                              setProposeUserId(u.id);
                              setSearchQuery(u.username);
                              setSearchResults([]);
                            }}
                            className="w-full px-4 py-2 text-left hover:bg-white/10 flex items-center gap-2"
                          >
                            <User className="w-4 h-4 text-pink-400" />
                            {u.username}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                  
                  <div>
                    <label className="text-sm text-white/60 mb-1 block">Your Message</label>
                    <textarea
                      value={proposeMessage}
                      onChange={(e) => setProposeMessage(e.target.value)}
                      className="w-full bg-white/5 border border-white/20 rounded-lg px-4 py-2 text-white h-24 resize-none"
                    />
                  </div>
                  
                  <div className="flex gap-2">
                    <button
                      onClick={() => setShowProposeModal(false)}
                      className="flex-1 px-4 py-2 bg-white/5 border border-white/20 rounded-lg text-white/60 hover:bg-white/10"
                    >
                      Cancel
                    </button>
                    <CyberButton 
                      onClick={handlePropose}
                      disabled={processing || !proposeUserId}
                      className="flex-1 bg-pink-500/20 border-pink-500"
                    >
                      {processing ? <Loader2 className="w-4 h-4 animate-spin" /> : (
                        <>
                          <Send className="w-4 h-4 mr-2" />
                          Send Proposal
                        </>
                      )}
                    </CyberButton>
                  </div>
                </div>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>
        
        {/* Adopt Modal */}
        <AnimatePresence>
          {showAdoptModal && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4"
              onClick={() => setShowAdoptModal(false)}
            >
              <motion.div
                initial={{ scale: 0.9, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.9, opacity: 0 }}
                className="bg-gray-900 border border-blue-500/30 rounded-xl p-6 max-w-md w-full"
                onClick={e => e.stopPropagation()}
              >
                <h3 className="font-orbitron font-bold text-xl text-blue-400 mb-4 flex items-center gap-2">
                  <Users className="w-6 h-6" />
                  Adopt a Child
                </h3>
                
                <div className="space-y-4">
                  <div>
                    <label className="text-sm text-white/60 mb-1 block">Child's Name</label>
                    <input
                      type="text"
                      value={childName}
                      onChange={(e) => setChildName(e.target.value)}
                      placeholder="Enter name..."
                      className="w-full bg-white/5 border border-white/20 rounded-lg px-4 py-2 text-white"
                    />
                  </div>
                  
                  <div>
                    <label className="text-sm text-white/60 mb-1 block">Gender</label>
                    <div className="flex gap-2">
                      {['boy', 'girl', 'other'].map(g => (
                        <button
                          key={g}
                          onClick={() => setChildGender(g)}
                          className={`flex-1 px-4 py-2 rounded-lg border ${
                            childGender === g 
                              ? 'bg-blue-500/20 border-blue-500 text-blue-400' 
                              : 'bg-white/5 border-white/20 text-white/60'
                          }`}
                        >
                          {g === 'boy' ? '👦' : g === 'girl' ? '👧' : '🧒'} {g}
                        </button>
                      ))}
                    </div>
                  </div>
                  
                  <div className="flex gap-2">
                    <button
                      onClick={() => setShowAdoptModal(false)}
                      className="flex-1 px-4 py-2 bg-white/5 border border-white/20 rounded-lg text-white/60 hover:bg-white/10"
                    >
                      Cancel
                    </button>
                    <CyberButton 
                      onClick={handleAdopt}
                      disabled={processing || !childName}
                      className="flex-1 bg-blue-500/20 border-blue-500"
                    >
                      {processing ? <Loader2 className="w-4 h-4 animate-spin" /> : (
                        <>
                          <Heart className="w-4 h-4 mr-2" />
                          Adopt ({familyStatus?.costs?.adoption} RLM)
                        </>
                      )}
                    </CyberButton>
                  </div>
                </div>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>
        
        {/* Create Child Modal */}
        <AnimatePresence>
          {showChildModal && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4"
              onClick={() => setShowChildModal(false)}
            >
              <motion.div
                initial={{ scale: 0.9, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.9, opacity: 0 }}
                className="bg-gray-900 border border-purple-500/30 rounded-xl p-6 max-w-md w-full"
                onClick={e => e.stopPropagation()}
              >
                <h3 className="font-orbitron font-bold text-xl text-purple-400 mb-4 flex items-center gap-2">
                  <Baby className="w-6 h-6" />
                  Have a Child
                </h3>
                
                <p className="text-sm text-white/60 mb-4">
                  You and {familyStatus?.marriage?.partner?.username} will have a child together!
                </p>
                
                <div className="space-y-4">
                  <div>
                    <label className="text-sm text-white/60 mb-1 block">Child's Name</label>
                    <input
                      type="text"
                      value={childName}
                      onChange={(e) => setChildName(e.target.value)}
                      placeholder="Enter name..."
                      className="w-full bg-white/5 border border-white/20 rounded-lg px-4 py-2 text-white"
                    />
                  </div>
                  
                  <div>
                    <label className="text-sm text-white/60 mb-1 block">Gender</label>
                    <div className="flex gap-2">
                      {['boy', 'girl', 'other'].map(g => (
                        <button
                          key={g}
                          onClick={() => setChildGender(g)}
                          className={`flex-1 px-4 py-2 rounded-lg border ${
                            childGender === g 
                              ? 'bg-purple-500/20 border-purple-500 text-purple-400' 
                              : 'bg-white/5 border-white/20 text-white/60'
                          }`}
                        >
                          {g === 'boy' ? '👦' : g === 'girl' ? '👧' : '🧒'} {g}
                        </button>
                      ))}
                    </div>
                  </div>
                  
                  <div className="flex gap-2">
                    <button
                      onClick={() => setShowChildModal(false)}
                      className="flex-1 px-4 py-2 bg-white/5 border border-white/20 rounded-lg text-white/60 hover:bg-white/10"
                    >
                      Cancel
                    </button>
                    <CyberButton 
                      onClick={handleCreateChild}
                      disabled={processing || !childName}
                      className="flex-1 bg-purple-500/20 border-purple-500"
                    >
                      {processing ? <Loader2 className="w-4 h-4 animate-spin" /> : (
                        <>
                          <Sparkles className="w-4 h-4 mr-2" />
                          Have Child ({familyStatus?.costs?.child_creation} RLM)
                        </>
                      )}
                    </CyberButton>
                  </div>
                </div>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
};

export default FamilyPage;
