import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Users, Shield, Crown, Award, Plus, LogOut, Settings,
  Loader2, Send, Bell, Wallet, UserPlus, MessageSquare
} from 'lucide-react';
import axios from 'axios';
import { API } from '../utils/api';
import { useAuth } from '../context/AuthContext';
import { CyberCard, CyberButton } from '../components/common/CyberUI';
import { toast } from 'sonner';

const GuildsPage = () => {
  const { user, refreshUser } = useAuth();
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [activeTab, setActiveTab] = useState('my-guild');
  
  const [myGuild, setMyGuild] = useState(null);
  const [guildList, setGuildList] = useState([]);
  const [leaderboard, setLeaderboard] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [showAnnounceModal, setShowAnnounceModal] = useState(false);
  
  const [createForm, setCreateForm] = useState({
    name: '', tag: '', description: '', color: '#00F0FF', is_public: true
  });
  const [inviteUsername, setInviteUsername] = useState('');
  const [announcement, setAnnouncement] = useState({ title: '', content: '' });
  const [depositAmount, setDepositAmount] = useState(100);

  useEffect(() => {
    fetchAllData();
  }, []);

  const fetchAllData = async () => {
    try {
      const [listRes, leaderRes] = await Promise.all([
        axios.get(`${API}/guilds/list`),
        axios.get(`${API}/guilds/leaderboard`)
      ]);
      setGuildList(listRes.data.guilds || []);
      setLeaderboard(leaderRes.data.leaderboard || []);
      
      try {
        const myRes = await axios.get(`${API}/guilds/my-guild`);
        setMyGuild(myRes.data);
      } catch (e) {}
    } catch (error) {
      console.error('Failed to load guilds:', error);
    }
    setLoading(false);
  };

  const handleCreateGuild = async () => {
    setProcessing(true);
    try {
      const res = await axios.post(`${API}/guilds/create`, createForm);
      toast.success(res.data.message);
      setShowCreateModal(false);
      fetchAllData();
      refreshUser();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create guild');
    }
    setProcessing(false);
  };

  const handleJoinGuild = async (guildId) => {
    setProcessing(true);
    try {
      const res = await axios.post(`${API}/guilds/${guildId}/join`);
      toast.success(res.data.message);
      fetchAllData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to join guild');
    }
    setProcessing(false);
  };

  const handleLeaveGuild = async () => {
    if (!window.confirm('Sigur vrei să părăsești guild-ul?')) return;
    setProcessing(true);
    try {
      const res = await axios.post(`${API}/guilds/leave`);
      toast.success(res.data.message);
      fetchAllData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to leave guild');
    }
    setProcessing(false);
  };

  const handleInvite = async () => {
    setProcessing(true);
    try {
      const res = await axios.post(`${API}/guilds/${myGuild.guild.id}/invite`, {
        username: inviteUsername
      });
      toast.success(res.data.message);
      setShowInviteModal(false);
      setInviteUsername('');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to invite');
    }
    setProcessing(false);
  };

  const handleAnnounce = async () => {
    setProcessing(true);
    try {
      const res = await axios.post(`${API}/guilds/${myGuild.guild.id}/announce`, announcement);
      toast.success('Announcement posted!');
      setShowAnnounceModal(false);
      setAnnouncement({ title: '', content: '' });
      fetchAllData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to post');
    }
    setProcessing(false);
  };

  const handleDeposit = async () => {
    setProcessing(true);
    try {
      const res = await axios.post(`${API}/guilds/${myGuild.guild.id}/bank/deposit`, {
        amount: depositAmount
      });
      toast.success(res.data.message);
      fetchAllData();
      refreshUser();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to deposit');
    }
    setProcessing(false);
  };

  const filteredGuilds = guildList.filter(g =>
    g.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    g.tag.toLowerCase().includes(searchQuery.toLowerCase())
  );

  if (loading) {
    return (
      <div className="min-h-screen pt-20 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-neon-cyan" />
      </div>
    );
  }

  return (
    <div className="min-h-screen pt-16 sm:pt-20 pb-20 lg:pb-12 px-3 sm:px-4" data-testid="guilds-page">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-6">
          <h1 className="text-2xl sm:text-3xl font-orbitron font-black flex items-center gap-3">
            <Shield className="w-8 h-8 text-neon-blue" />
            <span>Gilde & <span className="text-neon-cyan">Alianțe</span></span>
          </h1>
          <p className="text-white/60 text-sm mt-1">Unește-te cu alți jucători pentru beneficii comune</p>
        </motion.div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
          {[
            { id: 'my-guild', label: 'Guild-ul Meu', icon: Shield },
            { id: 'browse', label: 'Găsește Guild', icon: Users },
            { id: 'leaderboard', label: 'Clasament', icon: Award }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-2 font-mono text-sm whitespace-nowrap flex items-center gap-2 transition-all ${
                activeTab === tab.id 
                  ? 'bg-blue-500/20 border border-blue-400 text-blue-400' 
                  : 'border border-white/20 text-white/60 hover:border-white/40'
              }`}
            >
              <tab.icon className="w-4 h-4" /> {tab.label}
            </button>
          ))}
        </div>

        {/* My Guild Tab */}
        {activeTab === 'my-guild' && (
          <div>
            {myGuild?.has_guild ? (
              <div className="space-y-6">
                {/* Guild Info */}
                <CyberCard className="p-6" style={{ borderColor: myGuild.guild.color + '40' }}>
                  <div className="flex flex-wrap items-start justify-between gap-4 mb-4">
                    <div>
                      <div className="flex items-center gap-3">
                        <h2 className="text-2xl font-orbitron" style={{ color: myGuild.guild.color }}>
                          {myGuild.guild.name}
                        </h2>
                        <span className="px-2 py-1 text-sm font-mono border" style={{ borderColor: myGuild.guild.color, color: myGuild.guild.color }}>
                          [{myGuild.guild.tag}]
                        </span>
                      </div>
                      <p className="text-white/60 mt-2">{myGuild.guild.description}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="px-3 py-1 bg-neon-purple/20 border border-neon-purple text-neon-purple text-sm">
                        Lvl {myGuild.guild.level}
                      </span>
                      <span className="px-3 py-1 bg-white/10 border border-white/20 text-sm">
                        {myGuild.membership.rank}
                      </span>
                    </div>
                  </div>
                  
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                    <div className="p-3 bg-black/30 border border-white/10 text-center">
                      <div className="text-xl font-orbitron text-neon-cyan">{myGuild.members?.length || 0}</div>
                      <div className="text-xs text-white/50">Membri / {myGuild.max_members}</div>
                    </div>
                    <div className="p-3 bg-black/30 border border-white/10 text-center">
                      <div className="text-xl font-orbitron text-neon-green">{myGuild.guild.bank_balance?.toFixed(0) || 0}</div>
                      <div className="text-xs text-white/50">Bank RLM</div>
                    </div>
                    <div className="p-3 bg-black/30 border border-white/10 text-center">
                      <div className="text-xl font-orbitron text-neon-yellow">{myGuild.guild.total_xp || 0}</div>
                      <div className="text-xs text-white/50">Total XP</div>
                    </div>
                    <div className="p-3 bg-black/30 border border-white/10 text-center">
                      <div className="text-xl font-orbitron text-neon-purple">{myGuild.perks?.length || 0}</div>
                      <div className="text-xs text-white/50">Perks Active</div>
                    </div>
                  </div>
                  
                  <div className="flex flex-wrap gap-2">
                    {['leader', 'officer'].includes(myGuild.membership.rank) && (
                      <>
                        <CyberButton variant="outline" size="sm" onClick={() => setShowInviteModal(true)}>
                          <UserPlus className="w-4 h-4 mr-1" /> Invită
                        </CyberButton>
                        <CyberButton variant="outline" size="sm" onClick={() => setShowAnnounceModal(true)}>
                          <Bell className="w-4 h-4 mr-1" /> Anunță
                        </CyberButton>
                      </>
                    )}
                    {myGuild.guild.level >= 3 && (
                      <div className="flex items-center gap-2">
                        <input
                          type="number"
                          value={depositAmount}
                          onChange={e => setDepositAmount(parseInt(e.target.value) || 0)}
                          className="w-24 bg-black/50 border border-white/20 p-1 text-white text-center"
                          min={1}
                        />
                        <CyberButton variant="outline" size="sm" onClick={handleDeposit} disabled={processing}>
                          <Wallet className="w-4 h-4 mr-1" /> Depune
                        </CyberButton>
                      </div>
                    )}
                    {myGuild.membership.rank !== 'leader' && (
                      <CyberButton variant="outline" size="sm" onClick={handleLeaveGuild} disabled={processing}>
                        <LogOut className="w-4 h-4 mr-1" /> Părăsește
                      </CyberButton>
                    )}
                  </div>
                </CyberCard>

                {/* Members */}
                <CyberCard className="p-4">
                  <h3 className="font-orbitron text-lg mb-4">Membri</h3>
                  <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-3">
                    {myGuild.members?.map(member => (
                      <div key={member.id} className="p-3 bg-black/30 border border-white/10 flex items-center justify-between">
                        <div>
                          <div className="font-mono text-neon-cyan">{member.username}</div>
                          <div className="text-xs text-white/40">{myGuild.ranks[member.rank]?.name || member.rank}</div>
                        </div>
                        {member.rank === 'leader' && <Crown className="w-4 h-4 text-neon-yellow" />}
                      </div>
                    ))}
                  </div>
                </CyberCard>

                {/* Announcements */}
                {myGuild.announcements?.length > 0 && (
                  <CyberCard className="p-4">
                    <h3 className="font-orbitron text-lg mb-4">Anunțuri</h3>
                    <div className="space-y-3">
                      {myGuild.announcements.map(ann => (
                        <div key={ann.id} className="p-3 bg-black/30 border border-white/10">
                          <div className="font-mono text-neon-cyan">{ann.title}</div>
                          <p className="text-sm text-white/70 mt-1">{ann.content}</p>
                          <div className="text-xs text-white/40 mt-2">
                            by {ann.author_username} • {new Date(ann.created_at).toLocaleDateString()}
                          </div>
                        </div>
                      ))}
                    </div>
                  </CyberCard>
                )}

                {/* Perks */}
                {myGuild.perks?.length > 0 && (
                  <CyberCard className="p-4">
                    <h3 className="font-orbitron text-lg mb-4">Perks Active</h3>
                    <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-3">
                      {myGuild.perks.map((perk, i) => (
                        <div key={i} className="p-3 bg-neon-green/10 border border-neon-green/30">
                          <div className="font-mono text-neon-green">{perk.name}</div>
                          <div className="text-xs text-white/50 mt-1">{perk.description}</div>
                        </div>
                      ))}
                    </div>
                  </CyberCard>
                )}
              </div>
            ) : (
              <CyberCard className="p-8 text-center">
                <Shield className="w-16 h-16 mx-auto mb-4 text-blue-400/50" />
                <h3 className="font-orbitron text-xl mb-2">Nu faci parte dintr-un Guild</h3>
                <p className="text-white/50 mb-6">Creează-ți propriul guild sau alătură-te unuia existent!</p>
                
                {myGuild?.can_create ? (
                  <CyberButton variant="primary" onClick={() => setShowCreateModal(true)}>
                    <Plus className="w-4 h-4 mr-2" /> Creează Guild ({3000} RLM)
                  </CyberButton>
                ) : (
                  <p className="text-neon-red">Ai nevoie de 3000 RLM pentru a crea un guild</p>
                )}
              </CyberCard>
            )}
          </div>
        )}

        {/* Browse Tab */}
        {activeTab === 'browse' && (
          <div>
            <div className="mb-4">
              <input
                type="text"
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                placeholder="Caută guild..."
                className="w-full bg-black/50 border border-white/20 p-2 text-white"
              />
            </div>
            
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredGuilds.map(guild => (
                <CyberCard key={guild.id} className="p-4" style={{ borderColor: guild.color + '40' }}>
                  <div className="flex items-center justify-between mb-3">
                    <div>
                      <h4 className="font-orbitron" style={{ color: guild.color }}>{guild.name}</h4>
                      <span className="text-sm text-white/50">[{guild.tag}]</span>
                    </div>
                    <span className="px-2 py-1 text-xs bg-neon-purple/20 text-neon-purple">Lvl {guild.level}</span>
                  </div>
                  <p className="text-sm text-white/60 mb-3 line-clamp-2">{guild.description}</p>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-white/50">{guild.member_count} membri</span>
                    <CyberButton 
                      variant="outline" 
                      size="sm"
                      onClick={() => handleJoinGuild(guild.id)}
                      disabled={processing || myGuild?.has_guild}
                    >
                      Alătură-te
                    </CyberButton>
                  </div>
                </CyberCard>
              ))}
            </div>
          </div>
        )}

        {/* Leaderboard Tab */}
        {activeTab === 'leaderboard' && (
          <CyberCard className="p-4">
            <h3 className="font-orbitron text-lg mb-4">Top Gilde</h3>
            <div className="space-y-3">
              {leaderboard.map((guild, i) => (
                <div key={guild.id} className="flex items-center justify-between p-3 bg-black/30 border border-white/10">
                  <div className="flex items-center gap-3">
                    <span className={`text-2xl font-orbitron ${i < 3 ? 'text-neon-yellow' : 'text-white/50'}`}>
                      #{guild.rank}
                    </span>
                    <div>
                      <div className="font-mono" style={{ color: guild.color }}>{guild.name} [{guild.tag}]</div>
                      <div className="text-xs text-white/40">{guild.member_count} membri</div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="font-orbitron text-neon-purple">Lvl {guild.level}</div>
                    <div className="text-xs text-white/40">{guild.total_xp} XP</div>
                  </div>
                </div>
              ))}
            </div>
          </CyberCard>
        )}

        {/* Create Modal */}
        <AnimatePresence>
          {showCreateModal && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4"
              onClick={() => setShowCreateModal(false)}
            >
              <motion.div
                initial={{ scale: 0.9 }}
                animate={{ scale: 1 }}
                exit={{ scale: 0.9 }}
                className="bg-gray-900 border border-blue-400 p-6 max-w-md w-full"
                onClick={e => e.stopPropagation()}
              >
                <h3 className="font-orbitron text-xl mb-4">Creează Guild</h3>
                <div className="space-y-4">
                  <input type="text" placeholder="Nume Guild" value={createForm.name}
                    onChange={e => setCreateForm({...createForm, name: e.target.value})}
                    className="w-full bg-black/50 border border-white/20 p-2 text-white" />
                  <input type="text" placeholder="Tag (2-5 caractere)" value={createForm.tag} maxLength={5}
                    onChange={e => setCreateForm({...createForm, tag: e.target.value.toUpperCase()})}
                    className="w-full bg-black/50 border border-white/20 p-2 text-white" />
                  <textarea placeholder="Descriere" value={createForm.description}
                    onChange={e => setCreateForm({...createForm, description: e.target.value})}
                    className="w-full bg-black/50 border border-white/20 p-2 text-white h-20" />
                  <div className="flex items-center gap-4">
                    <input type="color" value={createForm.color}
                      onChange={e => setCreateForm({...createForm, color: e.target.value})}
                      className="w-12 h-10 bg-black/50 border border-white/20" />
                    <label className="flex items-center gap-2 text-white/70">
                      <input type="checkbox" checked={createForm.is_public}
                        onChange={e => setCreateForm({...createForm, is_public: e.target.checked})} />
                      Public
                    </label>
                  </div>
                </div>
                <div className="flex gap-3 mt-6">
                  <CyberButton variant="outline" className="flex-1" onClick={() => setShowCreateModal(false)}>
                    Anulează
                  </CyberButton>
                  <CyberButton variant="primary" className="flex-1" onClick={handleCreateGuild} disabled={processing}>
                    {processing ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Creează (3000 RLM)'}
                  </CyberButton>
                </div>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Invite Modal */}
        <AnimatePresence>
          {showInviteModal && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4"
              onClick={() => setShowInviteModal(false)}
            >
              <motion.div
                initial={{ scale: 0.9 }}
                animate={{ scale: 1 }}
                className="bg-gray-900 border border-neon-cyan p-6 max-w-sm w-full"
                onClick={e => e.stopPropagation()}
              >
                <h3 className="font-orbitron text-xl mb-4">Invită Jucător</h3>
                <input type="text" placeholder="Username" value={inviteUsername}
                  onChange={e => setInviteUsername(e.target.value)}
                  className="w-full bg-black/50 border border-white/20 p-2 text-white mb-4" />
                <div className="flex gap-3">
                  <CyberButton variant="outline" className="flex-1" onClick={() => setShowInviteModal(false)}>
                    Anulează
                  </CyberButton>
                  <CyberButton variant="primary" className="flex-1" onClick={handleInvite} disabled={processing}>
                    {processing ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Invită'}
                  </CyberButton>
                </div>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Announce Modal */}
        <AnimatePresence>
          {showAnnounceModal && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4"
              onClick={() => setShowAnnounceModal(false)}
            >
              <motion.div
                initial={{ scale: 0.9 }}
                animate={{ scale: 1 }}
                className="bg-gray-900 border border-neon-yellow p-6 max-w-md w-full"
                onClick={e => e.stopPropagation()}
              >
                <h3 className="font-orbitron text-xl mb-4">Anunț Guild</h3>
                <input type="text" placeholder="Titlu" value={announcement.title}
                  onChange={e => setAnnouncement({...announcement, title: e.target.value})}
                  className="w-full bg-black/50 border border-white/20 p-2 text-white mb-3" />
                <textarea placeholder="Conținut" value={announcement.content}
                  onChange={e => setAnnouncement({...announcement, content: e.target.value})}
                  className="w-full bg-black/50 border border-white/20 p-2 text-white h-24 mb-4" />
                <div className="flex gap-3">
                  <CyberButton variant="outline" className="flex-1" onClick={() => setShowAnnounceModal(false)}>
                    Anulează
                  </CyberButton>
                  <CyberButton variant="primary" className="flex-1" onClick={handleAnnounce} disabled={processing}>
                    {processing ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Postează'}
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

export default GuildsPage;
