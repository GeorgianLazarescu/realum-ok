import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Vote, Users, Building2, Crown, Scale, Flag, 
  Briefcase, Check, X, Loader2, Plus, Award,
  Globe, MapPin, Gavel, FileText, TrendingUp,
  ChevronRight, UserPlus, LogOut, Megaphone
} from 'lucide-react';
import axios from 'axios';
import { API } from '../utils/api';
import { useAuth } from '../context/AuthContext';
import { CyberCard, CyberButton } from '../components/common/CyberUI';
import { toast } from 'sonner';

const PoliticsPage = () => {
  const { user, refreshUser } = useAuth();
  
  const [activeTab, setActiveTab] = useState('overview'); // overview, parties, elections, government, laws
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  
  // Data states
  const [myStatus, setMyStatus] = useState(null);
  const [parties, setParties] = useState([]);
  const [elections, setElections] = useState([]);
  const [worldGov, setWorldGov] = useState(null);
  const [zoneGovs, setZoneGovs] = useState([]);
  const [laws, setLaws] = useState([]);
  const [statistics, setStatistics] = useState(null);
  const [availablePositions, setAvailablePositions] = useState([]);
  
  // Modal states
  const [showCreatePartyModal, setShowCreatePartyModal] = useState(false);
  const [showCampaignModal, setShowCampaignModal] = useState(false);
  const [showProposeLawModal, setShowProposeLawModal] = useState(false);
  const [selectedElection, setSelectedElection] = useState(null);
  
  // Form states
  const [partyForm, setPartyForm] = useState({
    name: '', abbreviation: '', ideology: 'centrist', description: '', color: '#00F0FF'
  });
  const [campaignForm, setCampaignForm] = useState({
    position: '', zone_id: '', platform: '', slogan: ''
  });
  const [lawForm, setLawForm] = useState({
    title: '', description: '', law_type: 'world', zone_id: ''
  });
  
  useEffect(() => {
    fetchAllData();
  }, []);
  
  const fetchAllData = async () => {
    try {
      const [statusRes, partiesRes, electionsRes, statsRes] = await Promise.all([
        axios.get(`${API}/politics/my-status`),
        axios.get(`${API}/politics/parties`),
        axios.get(`${API}/politics/elections`),
        axios.get(`${API}/politics/statistics`)
      ]);
      setMyStatus(statusRes.data);
      setParties(partiesRes.data.parties || []);
      setElections(electionsRes.data.elections || []);
      setStatistics(statsRes.data);
      
      // Fetch governments
      const [worldRes, zonesRes, lawsRes, positionsRes] = await Promise.all([
        axios.get(`${API}/politics/government/world`),
        axios.get(`${API}/politics/government/zones`),
        axios.get(`${API}/politics/laws`),
        axios.get(`${API}/politics/positions/available`)
      ]);
      setWorldGov(worldRes.data);
      setZoneGovs(zonesRes.data.zones || []);
      setLaws(lawsRes.data.laws || []);
      setAvailablePositions(positionsRes.data.positions || []);
    } catch (error) {
      console.error('Failed to load political data:', error);
    }
    setLoading(false);
  };
  
  const handleCreateParty = async () => {
    setProcessing(true);
    try {
      const res = await axios.post(`${API}/politics/parties/create`, partyForm);
      toast.success(res.data.message);
      setShowCreatePartyModal(false);
      setPartyForm({ name: '', abbreviation: '', ideology: 'centrist', description: '', color: '#00F0FF' });
      fetchAllData();
      refreshUser();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create party');
    }
    setProcessing(false);
  };
  
  const handleJoinParty = async (partyId) => {
    setProcessing(true);
    try {
      const res = await axios.post(`${API}/politics/parties/${partyId}/join`);
      toast.success(res.data.message);
      fetchAllData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to join party');
    }
    setProcessing(false);
  };
  
  const handleLeaveParty = async () => {
    setProcessing(true);
    try {
      const res = await axios.post(`${API}/politics/parties/leave`);
      toast.success(res.data.message);
      fetchAllData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to leave party');
    }
    setProcessing(false);
  };
  
  const handleStartCampaign = async () => {
    setProcessing(true);
    try {
      const res = await axios.post(`${API}/politics/elections/campaign`, campaignForm);
      toast.success(res.data.message);
      setShowCampaignModal(false);
      setCampaignForm({ position: '', zone_id: '', platform: '', slogan: '' });
      fetchAllData();
      refreshUser();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to start campaign');
    }
    setProcessing(false);
  };
  
  const handleVote = async (electionId, candidateId) => {
    setProcessing(true);
    try {
      const res = await axios.post(`${API}/politics/elections/vote`, {
        election_id: electionId,
        candidate_id: candidateId
      });
      toast.success(res.data.message);
      setSelectedElection(null);
      fetchAllData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to cast vote');
    }
    setProcessing(false);
  };
  
  const handleProposeLaw = async () => {
    setProcessing(true);
    try {
      const res = await axios.post(`${API}/politics/laws/propose`, lawForm);
      toast.success(res.data.message);
      setShowProposeLawModal(false);
      setLawForm({ title: '', description: '', law_type: 'world', zone_id: '' });
      fetchAllData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to propose law');
    }
    setProcessing(false);
  };
  
  const handleVoteLaw = async (lawId, vote) => {
    try {
      const res = await axios.post(`${API}/politics/laws/${lawId}/vote?vote=${vote}`);
      toast.success(res.data.message);
      fetchAllData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to vote on law');
    }
  };
  
  const ideologies = [
    { value: 'progressive', label: 'Progresist', color: '#22C55E' },
    { value: 'conservative', label: 'Conservator', color: '#3B82F6' },
    { value: 'libertarian', label: 'Libertarian', color: '#F59E0B' },
    { value: 'socialist', label: 'Socialist', color: '#EF4444' },
    { value: 'centrist', label: 'Centrist', color: '#8B5CF6' }
  ];
  
  if (loading) {
    return (
      <div className="min-h-screen pt-20 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-neon-cyan" />
      </div>
    );
  }
  
  return (
    <div className="min-h-screen pt-16 sm:pt-20 pb-20 lg:pb-12 px-3 sm:px-4" data-testid="politics-page">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-6">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <h1 className="text-2xl sm:text-3xl font-orbitron font-black flex items-center gap-3">
                <Scale className="w-8 h-8 text-neon-purple" />
                <span>Sistem Politic <span className="text-neon-cyan">REALUM</span></span>
              </h1>
              <p className="text-white/60 text-sm mt-1">Guvernare mondială și locală, alegeri, partide și legi</p>
            </div>
            
            {/* Quick Stats */}
            <div className="flex gap-4">
              <div className="text-center">
                <div className="text-xl font-orbitron text-neon-cyan">{statistics?.total_parties || 0}</div>
                <div className="text-xs text-white/50">Partide</div>
              </div>
              <div className="text-center">
                <div className="text-xl font-orbitron text-neon-green">{statistics?.active_elections || 0}</div>
                <div className="text-xs text-white/50">Alegeri Active</div>
              </div>
              <div className="text-center">
                <div className="text-xl font-orbitron text-neon-purple">{statistics?.total_officials || 0}</div>
                <div className="text-xs text-white/50">Oficiali</div>
              </div>
            </div>
          </div>
        </motion.div>
        
        {/* My Political Status Card */}
        {myStatus && (
          <CyberCard className="p-4 mb-6 border-neon-purple/30" data-testid="political-status">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <h3 className="font-orbitron text-sm text-white/70 mb-1">Statusul Tău Politic</h3>
                <div className="flex flex-wrap items-center gap-3">
                  {myStatus.party ? (
                    <span className="px-3 py-1 text-sm border" style={{ borderColor: myStatus.party.color, color: myStatus.party.color }}>
                      {myStatus.party.name} ({myStatus.party_role})
                    </span>
                  ) : (
                    <span className="px-3 py-1 text-sm border border-white/30 text-white/50">Independent</span>
                  )}
                  {myStatus.positions?.length > 0 && myStatus.positions.map(pos => (
                    <span key={pos.id} className="px-3 py-1 text-sm bg-neon-green/20 border border-neon-green text-neon-green flex items-center gap-1">
                      <Crown className="w-3 h-3" /> {pos.position_title}
                    </span>
                  ))}
                </div>
              </div>
              <div className="flex gap-2">
                {myStatus.party && myStatus.party_role !== 'leader' && (
                  <CyberButton variant="outline" size="sm" onClick={handleLeaveParty} disabled={processing}>
                    <LogOut className="w-4 h-4 mr-1" /> Părăsește
                  </CyberButton>
                )}
                <CyberButton variant="primary" size="sm" onClick={() => setShowCampaignModal(true)}>
                  <Megaphone className="w-4 h-4 mr-1" /> Candidează
                </CyberButton>
              </div>
            </div>
          </CyberCard>
        )}
        
        {/* Tabs */}
        <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
          {[
            { id: 'overview', label: 'Prezentare', icon: Globe },
            { id: 'parties', label: 'Partide', icon: Flag },
            { id: 'elections', label: 'Alegeri', icon: Vote },
            { id: 'government', label: 'Guvern', icon: Building2 },
            { id: 'laws', label: 'Legi', icon: Gavel }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-2 font-mono text-sm whitespace-nowrap flex items-center gap-2 transition-all ${
                activeTab === tab.id 
                  ? 'bg-neon-cyan/20 border border-neon-cyan text-neon-cyan' 
                  : 'border border-white/20 text-white/60 hover:border-white/40'
              }`}
              data-testid={`tab-${tab.id}`}
            >
              <tab.icon className="w-4 h-4" /> {tab.label}
            </button>
          ))}
        </div>
        
        {/* Tab Content */}
        <AnimatePresence mode="wait">
          {/* Overview Tab */}
          {activeTab === 'overview' && (
            <motion.div
              key="overview"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="grid md:grid-cols-2 lg:grid-cols-3 gap-4"
            >
              {/* World President */}
              <CyberCard className="p-4" data-testid="world-president-card">
                <div className="flex items-center gap-3 mb-3">
                  <div className="p-2 bg-neon-yellow/20 border border-neon-yellow">
                    <Crown className="w-5 h-5 text-neon-yellow" />
                  </div>
                  <div>
                    <h3 className="font-orbitron text-sm">Președinte Mondial</h3>
                    <p className="text-xs text-white/50">Lider REALUM</p>
                  </div>
                </div>
                {worldGov?.world_president ? (
                  <div className="p-3 bg-black/30 border border-white/10">
                    <div className="font-mono text-neon-cyan">{worldGov.world_president.holder_username}</div>
                    <div className="text-xs text-white/50 mt-1">{worldGov.world_president.party_name || 'Independent'}</div>
                  </div>
                ) : (
                  <div className="p-3 bg-black/30 border border-white/10 text-center text-white/50 text-sm">
                    Poziție Vacantă
                  </div>
                )}
              </CyberCard>
              
              {/* Top Parties */}
              <CyberCard className="p-4" data-testid="top-parties-card">
                <h3 className="font-orbitron text-sm mb-3 flex items-center gap-2">
                  <Flag className="w-4 h-4 text-neon-purple" /> Top Partide
                </h3>
                <div className="space-y-2">
                  {statistics?.top_parties?.slice(0, 3).map((party, i) => (
                    <div key={i} className="flex items-center justify-between p-2 bg-black/30 border-l-2" style={{ borderColor: party.color }}>
                      <span className="font-mono text-sm">{party.name}</span>
                      <span className="text-xs text-white/50">{party.member_count} membri</span>
                    </div>
                  )) || <p className="text-white/50 text-sm">Niciun partid încă</p>}
                </div>
              </CyberCard>
              
              {/* Active Elections */}
              <CyberCard className="p-4" data-testid="active-elections-card">
                <h3 className="font-orbitron text-sm mb-3 flex items-center gap-2">
                  <Vote className="w-4 h-4 text-neon-green" /> Alegeri Active
                </h3>
                <div className="space-y-2">
                  {elections.filter(e => e.status === 'active').slice(0, 3).map(election => (
                    <div key={election.id} className="p-2 bg-black/30 border border-white/10">
                      <div className="font-mono text-sm text-neon-cyan">{election.position_title}</div>
                      <div className="text-xs text-white/50">{election.candidate_count} candidați</div>
                    </div>
                  ))}
                  {elections.filter(e => e.status === 'active').length === 0 && (
                    <p className="text-white/50 text-sm">Nicio alegere activă</p>
                  )}
                </div>
              </CyberCard>
              
              {/* Zone Governments */}
              <CyberCard className="p-4 md:col-span-2 lg:col-span-3" data-testid="zones-overview">
                <h3 className="font-orbitron text-sm mb-3 flex items-center gap-2">
                  <MapPin className="w-4 h-4 text-neon-cyan" /> Zone REALUM
                </h3>
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
                  {zoneGovs.map(zone => (
                    <div key={zone.zone.id} className="p-3 bg-black/30 border border-white/10 text-center">
                      <div className="font-mono text-sm text-neon-cyan mb-1">{zone.zone.name}</div>
                      <div className="text-xs text-white/50 mb-2">{zone.zone.city}</div>
                      {zone.governor ? (
                        <div className="text-xs text-neon-green flex items-center justify-center gap-1">
                          <Crown className="w-3 h-3" /> {zone.governor.holder_username}
                        </div>
                      ) : (
                        <div className="text-xs text-white/40">Niciun Guvernator</div>
                      )}
                    </div>
                  ))}
                </div>
              </CyberCard>
            </motion.div>
          )}
          
          {/* Parties Tab */}
          {activeTab === 'parties' && (
            <motion.div
              key="parties"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <div className="flex justify-between items-center mb-4">
                <h3 className="font-orbitron text-lg">Partide Politice</h3>
                {myStatus?.can_create_party && !myStatus?.party && (
                  <CyberButton variant="primary" onClick={() => setShowCreatePartyModal(true)}>
                    <Plus className="w-4 h-4 mr-2" /> Creează Partid ({myStatus.party_creation_cost} RLM)
                  </CyberButton>
                )}
              </div>
              
              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                {parties.map(party => (
                  <CyberCard key={party.id} className="p-4" style={{ borderColor: `${party.color}40` }}>
                    <div className="flex items-start justify-between mb-3">
                      <div>
                        <h4 className="font-orbitron text-lg" style={{ color: party.color }}>{party.name}</h4>
                        <div className="text-sm text-white/60">{party.abbreviation}</div>
                      </div>
                      <div className="px-2 py-1 text-xs border" style={{ borderColor: party.color, color: party.color }}>
                        {ideologies.find(i => i.value === party.ideology)?.label || party.ideology}
                      </div>
                    </div>
                    <p className="text-sm text-white/70 mb-3 line-clamp-2">{party.description}</p>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2 text-sm text-white/50">
                        <Users className="w-4 h-4" /> {party.member_count} membri
                      </div>
                      {!myStatus?.party && (
                        <CyberButton 
                          variant="outline" 
                          size="sm" 
                          onClick={() => handleJoinParty(party.id)}
                          disabled={processing}
                        >
                          <UserPlus className="w-4 h-4 mr-1" /> Alătură-te
                        </CyberButton>
                      )}
                    </div>
                    <div className="mt-3 pt-3 border-t border-white/10 text-xs text-white/40">
                      Lider: {party.leader_username}
                    </div>
                  </CyberCard>
                ))}
                
                {parties.length === 0 && (
                  <div className="col-span-full text-center py-12 text-white/50">
                    <Flag className="w-12 h-12 mx-auto mb-4 opacity-50" />
                    <p>Niciun partid creat încă. Fii primul care creează unul!</p>
                  </div>
                )}
              </div>
            </motion.div>
          )}
          
          {/* Elections Tab */}
          {activeTab === 'elections' && (
            <motion.div
              key="elections"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <h3 className="font-orbitron text-lg mb-4">Alegeri</h3>
              
              <div className="space-y-4">
                {elections.map(election => (
                  <CyberCard key={election.id} className="p-4" data-testid={`election-${election.id}`}>
                    <div className="flex flex-wrap items-start justify-between gap-4">
                      <div>
                        <h4 className="font-orbitron text-lg text-neon-cyan">{election.position_title}</h4>
                        {election.zone_name && (
                          <div className="text-sm text-white/60 flex items-center gap-1">
                            <MapPin className="w-3 h-3" /> {election.zone_name}
                          </div>
                        )}
                        <div className="flex gap-4 mt-2 text-sm">
                          <span className={`px-2 py-1 ${election.status === 'active' ? 'bg-neon-green/20 text-neon-green' : 'bg-white/10 text-white/50'}`}>
                            {election.status === 'active' ? 'ACTIV' : election.status.toUpperCase()}
                          </span>
                          <span className="text-white/50">{election.candidate_count} candidați</span>
                        </div>
                      </div>
                      <CyberButton 
                        variant="outline" 
                        size="sm"
                        onClick={async () => {
                          try {
                            const res = await axios.get(`${API}/politics/elections/${election.id}`);
                            setSelectedElection(res.data);
                          } catch (error) {
                            toast.error('Failed to load election details');
                          }
                        }}
                      >
                        Detalii <ChevronRight className="w-4 h-4" />
                      </CyberButton>
                    </div>
                    <div className="mt-3 text-xs text-white/40">
                      Votare: {new Date(election.voting_starts).toLocaleDateString()} - {new Date(election.voting_ends).toLocaleDateString()}
                    </div>
                  </CyberCard>
                ))}
                
                {elections.length === 0 && (
                  <div className="text-center py-12 text-white/50">
                    <Vote className="w-12 h-12 mx-auto mb-4 opacity-50" />
                    <p>Nicio alegere în desfășurare. Începe o campanie pentru a crea una!</p>
                  </div>
                )}
              </div>
            </motion.div>
          )}
          
          {/* Government Tab */}
          {activeTab === 'government' && (
            <motion.div
              key="government"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="space-y-6"
            >
              {/* World Government */}
              <CyberCard className="p-4">
                <h3 className="font-orbitron text-lg mb-4 flex items-center gap-2">
                  <Globe className="w-5 h-5 text-neon-yellow" /> Guvernul Mondial REALUM
                </h3>
                <div className="grid md:grid-cols-3 gap-4">
                  <div className="p-4 bg-neon-yellow/10 border border-neon-yellow/30">
                    <div className="text-sm text-white/60 mb-1">Președinte Mondial</div>
                    {worldGov?.world_president ? (
                      <>
                        <div className="font-orbitron text-neon-yellow">{worldGov.world_president.holder_username}</div>
                        <div className="text-xs text-white/40 mt-1">{worldGov.world_president.party_name || 'Independent'}</div>
                      </>
                    ) : (
                      <div className="text-white/40">Vacant</div>
                    )}
                  </div>
                  <div className="p-4 bg-neon-purple/10 border border-neon-purple/30">
                    <div className="text-sm text-white/60 mb-1">Miniștri</div>
                    <div className="font-orbitron text-neon-purple">{worldGov?.ministers?.length || 0}</div>
                  </div>
                  <div className="p-4 bg-neon-cyan/10 border border-neon-cyan/30">
                    <div className="text-sm text-white/60 mb-1">Senatori</div>
                    <div className="font-orbitron text-neon-cyan">{worldGov?.senators?.length || 0}</div>
                  </div>
                </div>
              </CyberCard>
              
              {/* Zone Governments */}
              <CyberCard className="p-4">
                <h3 className="font-orbitron text-lg mb-4 flex items-center gap-2">
                  <MapPin className="w-5 h-5 text-neon-green" /> Guverne Zonale
                </h3>
                <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {zoneGovs.map(zone => (
                    <div key={zone.zone.id} className="p-4 bg-black/30 border border-white/10">
                      <div className="font-orbitron text-neon-cyan mb-1">{zone.zone.name}</div>
                      <div className="text-xs text-white/50 mb-3">{zone.zone.city}</div>
                      <div className="space-y-2">
                        <div className="flex justify-between text-sm">
                          <span className="text-white/60">Guvernator:</span>
                          <span className={zone.governor ? 'text-neon-green' : 'text-white/40'}>
                            {zone.governor?.holder_username || 'Vacant'}
                          </span>
                        </div>
                        <div className="flex justify-between text-sm">
                          <span className="text-white/60">Consilieri:</span>
                          <span className="text-neon-purple">{zone.councilor_count || 0}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CyberCard>
            </motion.div>
          )}
          
          {/* Laws Tab */}
          {activeTab === 'laws' && (
            <motion.div
              key="laws"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <div className="flex justify-between items-center mb-4">
                <h3 className="font-orbitron text-lg">Legi și Politici</h3>
                {myStatus?.positions?.length > 0 && (
                  <CyberButton variant="primary" onClick={() => setShowProposeLawModal(true)}>
                    <Plus className="w-4 h-4 mr-2" /> Propune Lege
                  </CyberButton>
                )}
              </div>
              
              <div className="space-y-4">
                {laws.map(law => (
                  <CyberCard key={law.id} className="p-4" data-testid={`law-${law.id}`}>
                    <div className="flex flex-wrap items-start justify-between gap-4">
                      <div>
                        <h4 className="font-orbitron text-lg">{law.title}</h4>
                        <p className="text-sm text-white/60 mt-1">{law.description}</p>
                        <div className="flex gap-3 mt-2 text-xs">
                          <span className={`px-2 py-1 ${law.law_type === 'world' ? 'bg-neon-yellow/20 text-neon-yellow' : 'bg-neon-cyan/20 text-neon-cyan'}`}>
                            {law.law_type === 'world' ? 'MONDIAL' : 'ZONAL'}
                          </span>
                          <span className={`px-2 py-1 ${law.status === 'active' ? 'bg-neon-green/20 text-neon-green' : 'bg-neon-purple/20 text-neon-purple'}`}>
                            {law.status === 'active' ? 'ACTIV' : law.status === 'voting' ? 'LA VOT' : law.status.toUpperCase()}
                          </span>
                        </div>
                      </div>
                      {law.status === 'voting' && myStatus?.positions?.length > 0 && (
                        <div className="flex gap-2">
                          <CyberButton variant="primary" size="sm" onClick={() => handleVoteLaw(law.id, 'for')}>
                            <Check className="w-4 h-4" /> Pentru
                          </CyberButton>
                          <CyberButton variant="outline" size="sm" onClick={() => handleVoteLaw(law.id, 'against')}>
                            <X className="w-4 h-4" /> Contra
                          </CyberButton>
                        </div>
                      )}
                    </div>
                    {law.status === 'voting' && (
                      <div className="mt-3 pt-3 border-t border-white/10 flex gap-6 text-sm">
                        <span className="text-neon-green">Pentru: {law.votes_for}</span>
                        <span className="text-neon-red">Contra: {law.votes_against}</span>
                      </div>
                    )}
                  </CyberCard>
                ))}
                
                {laws.length === 0 && (
                  <div className="text-center py-12 text-white/50">
                    <Gavel className="w-12 h-12 mx-auto mb-4 opacity-50" />
                    <p>Nicio lege încă. Oficialii aleși pot propune legi.</p>
                  </div>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
        
        {/* Create Party Modal */}
        <AnimatePresence>
          {showCreatePartyModal && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4"
              onClick={() => setShowCreatePartyModal(false)}
            >
              <motion.div
                initial={{ scale: 0.9 }}
                animate={{ scale: 1 }}
                exit={{ scale: 0.9 }}
                className="bg-gray-900 border border-neon-purple p-6 max-w-md w-full"
                onClick={e => e.stopPropagation()}
              >
                <h3 className="font-orbitron text-xl mb-4 flex items-center gap-2">
                  <Flag className="w-5 h-5 text-neon-purple" /> Creează Partid
                </h3>
                
                <div className="space-y-4">
                  <div>
                    <label className="text-sm text-white/60 block mb-1">Nume Partid</label>
                    <input
                      type="text"
                      value={partyForm.name}
                      onChange={e => setPartyForm({...partyForm, name: e.target.value})}
                      className="w-full bg-black/50 border border-white/20 p-2 text-white"
                      placeholder="Partidul Progresist"
                    />
                  </div>
                  <div>
                    <label className="text-sm text-white/60 block mb-1">Abreviere</label>
                    <input
                      type="text"
                      value={partyForm.abbreviation}
                      onChange={e => setPartyForm({...partyForm, abbreviation: e.target.value.toUpperCase()})}
                      className="w-full bg-black/50 border border-white/20 p-2 text-white"
                      placeholder="PP"
                      maxLength={5}
                    />
                  </div>
                  <div>
                    <label className="text-sm text-white/60 block mb-1">Ideologie</label>
                    <select
                      value={partyForm.ideology}
                      onChange={e => setPartyForm({...partyForm, ideology: e.target.value})}
                      className="w-full bg-black/50 border border-white/20 p-2 text-white"
                    >
                      {ideologies.map(i => (
                        <option key={i.value} value={i.value}>{i.label}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="text-sm text-white/60 block mb-1">Descriere</label>
                    <textarea
                      value={partyForm.description}
                      onChange={e => setPartyForm({...partyForm, description: e.target.value})}
                      className="w-full bg-black/50 border border-white/20 p-2 text-white h-20"
                      placeholder="Descrie viziunea partidului tău..."
                    />
                  </div>
                  <div>
                    <label className="text-sm text-white/60 block mb-1">Culoare</label>
                    <input
                      type="color"
                      value={partyForm.color}
                      onChange={e => setPartyForm({...partyForm, color: e.target.value})}
                      className="w-full h-10 bg-black/50 border border-white/20"
                    />
                  </div>
                </div>
                
                <div className="flex gap-3 mt-6">
                  <CyberButton variant="outline" className="flex-1" onClick={() => setShowCreatePartyModal(false)}>
                    Anulează
                  </CyberButton>
                  <CyberButton 
                    variant="primary" 
                    className="flex-1" 
                    onClick={handleCreateParty}
                    disabled={processing || !partyForm.name || !partyForm.abbreviation}
                  >
                    {processing ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Creează (2000 RLM)'}
                  </CyberButton>
                </div>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>
        
        {/* Campaign Modal */}
        <AnimatePresence>
          {showCampaignModal && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4"
              onClick={() => setShowCampaignModal(false)}
            >
              <motion.div
                initial={{ scale: 0.9 }}
                animate={{ scale: 1 }}
                exit={{ scale: 0.9 }}
                className="bg-gray-900 border border-neon-cyan p-6 max-w-lg w-full max-h-[90vh] overflow-y-auto"
                onClick={e => e.stopPropagation()}
              >
                <h3 className="font-orbitron text-xl mb-4 flex items-center gap-2">
                  <Megaphone className="w-5 h-5 text-neon-cyan" /> Începe Campanie
                </h3>
                
                <div className="space-y-4">
                  <div>
                    <label className="text-sm text-white/60 block mb-1">Poziție</label>
                    <select
                      value={campaignForm.position}
                      onChange={e => setCampaignForm({...campaignForm, position: e.target.value, zone_id: ''})}
                      className="w-full bg-black/50 border border-white/20 p-2 text-white"
                    >
                      <option value="">Selectează poziție...</option>
                      {availablePositions.filter(p => p.can_run).map(pos => (
                        <option key={pos.position} value={pos.position}>
                          {pos.title} - {pos.campaign_cost} RLM ({pos.level})
                        </option>
                      ))}
                    </select>
                  </div>
                  
                  {campaignForm.position && availablePositions.find(p => p.position === campaignForm.position)?.level === 'local' && (
                    <div>
                      <label className="text-sm text-white/60 block mb-1">Zonă</label>
                      <select
                        value={campaignForm.zone_id}
                        onChange={e => setCampaignForm({...campaignForm, zone_id: e.target.value})}
                        className="w-full bg-black/50 border border-white/20 p-2 text-white"
                      >
                        <option value="">Selectează zonă...</option>
                        {statistics?.zones?.map(zone => (
                          <option key={zone.id} value={zone.id}>{zone.name} ({zone.city})</option>
                        ))}
                      </select>
                    </div>
                  )}
                  
                  <div>
                    <label className="text-sm text-white/60 block mb-1">Platforma ta</label>
                    <textarea
                      value={campaignForm.platform}
                      onChange={e => setCampaignForm({...campaignForm, platform: e.target.value})}
                      className="w-full bg-black/50 border border-white/20 p-2 text-white h-24"
                      placeholder="Ce promisiuni faci alegătorilor?"
                    />
                  </div>
                  
                  <div>
                    <label className="text-sm text-white/60 block mb-1">Slogan</label>
                    <input
                      type="text"
                      value={campaignForm.slogan}
                      onChange={e => setCampaignForm({...campaignForm, slogan: e.target.value})}
                      className="w-full bg-black/50 border border-white/20 p-2 text-white"
                      placeholder="Un REALUM mai bun pentru toți!"
                    />
                  </div>
                </div>
                
                <div className="flex gap-3 mt-6">
                  <CyberButton variant="outline" className="flex-1" onClick={() => setShowCampaignModal(false)}>
                    Anulează
                  </CyberButton>
                  <CyberButton 
                    variant="primary" 
                    className="flex-1" 
                    onClick={handleStartCampaign}
                    disabled={processing || !campaignForm.position || !campaignForm.platform || !campaignForm.slogan}
                  >
                    {processing ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Lansează Campanie'}
                  </CyberButton>
                </div>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>
        
        {/* Election Details Modal */}
        <AnimatePresence>
          {selectedElection && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4"
              onClick={() => setSelectedElection(null)}
            >
              <motion.div
                initial={{ scale: 0.9 }}
                animate={{ scale: 1 }}
                exit={{ scale: 0.9 }}
                className="bg-gray-900 border border-neon-green p-6 max-w-2xl w-full max-h-[90vh] overflow-y-auto"
                onClick={e => e.stopPropagation()}
              >
                <h3 className="font-orbitron text-xl mb-2">{selectedElection.election.position_title}</h3>
                {selectedElection.election.zone_name && (
                  <p className="text-sm text-white/60 mb-4 flex items-center gap-1">
                    <MapPin className="w-3 h-3" /> {selectedElection.election.zone_name}
                  </p>
                )}
                
                <h4 className="font-orbitron text-sm text-white/70 mb-3">Candidați ({selectedElection.candidates.length})</h4>
                <div className="space-y-3">
                  {selectedElection.candidates.map(candidate => (
                    <div 
                      key={candidate.id} 
                      className="p-4 bg-black/30 border-l-2"
                      style={{ borderColor: candidate.party_color }}
                    >
                      <div className="flex justify-between items-start">
                        <div>
                          <div className="font-orbitron text-neon-cyan">{candidate.username}</div>
                          <div className="text-sm text-white/60">{candidate.party_name}</div>
                          <p className="text-sm mt-2 text-white/70">{candidate.platform}</p>
                          <p className="text-xs mt-1 italic text-neon-purple">"{candidate.slogan}"</p>
                        </div>
                        <div className="text-right">
                          <div className="text-2xl font-orbitron text-neon-green">{candidate.votes || 0}</div>
                          <div className="text-xs text-white/50">voturi</div>
                        </div>
                      </div>
                      <div className="mt-3">
                        <CyberButton 
                          variant="primary" 
                          size="sm"
                          onClick={() => handleVote(selectedElection.election.id, candidate.id)}
                          disabled={processing}
                        >
                          <Vote className="w-4 h-4 mr-1" /> Votează
                        </CyberButton>
                      </div>
                    </div>
                  ))}
                </div>
                
                <CyberButton variant="outline" className="w-full mt-4" onClick={() => setSelectedElection(null)}>
                  Închide
                </CyberButton>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>
        
        {/* Propose Law Modal */}
        <AnimatePresence>
          {showProposeLawModal && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4"
              onClick={() => setShowProposeLawModal(false)}
            >
              <motion.div
                initial={{ scale: 0.9 }}
                animate={{ scale: 1 }}
                exit={{ scale: 0.9 }}
                className="bg-gray-900 border border-neon-yellow p-6 max-w-md w-full"
                onClick={e => e.stopPropagation()}
              >
                <h3 className="font-orbitron text-xl mb-4 flex items-center gap-2">
                  <Gavel className="w-5 h-5 text-neon-yellow" /> Propune Lege
                </h3>
                
                <div className="space-y-4">
                  <div>
                    <label className="text-sm text-white/60 block mb-1">Titlu</label>
                    <input
                      type="text"
                      value={lawForm.title}
                      onChange={e => setLawForm({...lawForm, title: e.target.value})}
                      className="w-full bg-black/50 border border-white/20 p-2 text-white"
                      placeholder="Legea economiei verzi"
                    />
                  </div>
                  <div>
                    <label className="text-sm text-white/60 block mb-1">Descriere</label>
                    <textarea
                      value={lawForm.description}
                      onChange={e => setLawForm({...lawForm, description: e.target.value})}
                      className="w-full bg-black/50 border border-white/20 p-2 text-white h-24"
                      placeholder="Descrie efectele și scopul legii..."
                    />
                  </div>
                  <div>
                    <label className="text-sm text-white/60 block mb-1">Tip</label>
                    <select
                      value={lawForm.law_type}
                      onChange={e => setLawForm({...lawForm, law_type: e.target.value})}
                      className="w-full bg-black/50 border border-white/20 p-2 text-white"
                    >
                      <option value="world">Mondial</option>
                      <option value="zone">Zonal</option>
                    </select>
                  </div>
                </div>
                
                <div className="flex gap-3 mt-6">
                  <CyberButton variant="outline" className="flex-1" onClick={() => setShowProposeLawModal(false)}>
                    Anulează
                  </CyberButton>
                  <CyberButton 
                    variant="primary" 
                    className="flex-1" 
                    onClick={handleProposeLaw}
                    disabled={processing || !lawForm.title || !lawForm.description}
                  >
                    {processing ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Propune'}
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

export default PoliticsPage;
