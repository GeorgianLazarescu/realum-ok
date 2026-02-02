import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Vote, ThumbsUp, ThumbsDown, Plus } from 'lucide-react';
import axios from 'axios';
import { API } from '../../utils/api';
import { useAuth } from '../../context/AuthContext';
import { useTranslation } from '../../context/LanguageContext';
import { CyberCard, CyberButton } from '../../components/common/CyberUI';

const VotingPage = () => {
  const { user } = useAuth();
  const t = useTranslation();
  const [proposals, setProposals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newProposal, setNewProposal] = useState({ title: '', description: '' });
  
  const fetchProposals = () => {
    axios.get(`${API}/proposals`).then(res => setProposals(res.data)).catch(console.error).finally(() => setLoading(false));
  };
  
  useEffect(() => { fetchProposals(); }, []);
  
  const voteOnProposal = async (proposalId, voteType) => {
    try {
      await axios.post(`${API}/proposals/${proposalId}/vote`, { vote_type: voteType });
      fetchProposals();
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to vote');
    }
  };
  
  const createProposal = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API}/proposals`, newProposal);
      setNewProposal({ title: '', description: '' });
      setShowCreateForm(false);
      fetchProposals();
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to create proposal');
    }
  };
  
  return (
    <div className="min-h-screen pt-16 sm:pt-20 pb-20 lg:pb-12 px-3 sm:px-4" data-testid="voting-page">
      <div className="max-w-4xl mx-auto">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-6 sm:mb-8">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h1 className="text-2xl sm:text-3xl md:text-4xl font-orbitron font-black flex items-center gap-3">
                <Vote className="w-8 h-8 sm:w-10 sm:h-10 text-neon-cyan" />
                DAO <span className="text-neon-cyan">{t('voting')}</span>
              </h1>
              <p className="text-white/60 mt-2 text-sm sm:text-base">Participate in community governance</p>
            </div>
            {user?.level >= 2 && (
              <CyberButton onClick={() => setShowCreateForm(!showCreateForm)} className="w-full sm:w-auto">
                <Plus className="w-4 h-4 inline mr-2" /> New Proposal
              </CyberButton>
            )}
          </div>
        </motion.div>
        
        {/* Create Form */}
        {showCreateForm && (
          <CyberCard className="mb-6" glow>
            <h3 className="font-orbitron font-bold mb-4 text-sm sm:text-base">Create Proposal</h3>
            <form onSubmit={createProposal} className="space-y-4">
              <div>
                <label className="text-xs uppercase tracking-wider text-white/50 mb-1 block">Title</label>
                <input
                  type="text"
                  value={newProposal.title}
                  onChange={(e) => setNewProposal({...newProposal, title: e.target.value})}
                  required
                  className="w-full bg-black/50 border border-white/20 px-4 py-3 text-white focus:border-neon-cyan focus:outline-none text-sm"
                />
              </div>
              <div>
                <label className="text-xs uppercase tracking-wider text-white/50 mb-1 block">Description</label>
                <textarea
                  value={newProposal.description}
                  onChange={(e) => setNewProposal({...newProposal, description: e.target.value})}
                  required
                  rows={4}
                  className="w-full bg-black/50 border border-white/20 px-4 py-3 text-white focus:border-neon-cyan focus:outline-none text-sm resize-none"
                />
              </div>
              <div className="flex gap-2">
                <CyberButton type="submit" className="flex-1">{t('create')}</CyberButton>
                <CyberButton type="button" variant="ghost" onClick={() => setShowCreateForm(false)}>{t('cancel')}</CyberButton>
              </div>
            </form>
          </CyberCard>
        )}
        
        {/* Proposals List */}
        {loading ? (
          <div className="text-center text-white/50">{t('loading')}</div>
        ) : (
          <div className="space-y-3 sm:space-y-4">
            {proposals.map(proposal => {
              const totalVotes = proposal.votes_for + proposal.votes_against;
              const forPercent = totalVotes > 0 ? (proposal.votes_for / totalVotes) * 100 : 50;
              const hasVoted = proposal.voters?.includes(user?.id);
              
              return (
                <CyberCard key={proposal.id} className="p-4">
                  <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-2 mb-3">
                    <div>
                      <h4 className="font-mono font-bold text-sm sm:text-base">{proposal.title}</h4>
                      <p className="text-xs text-white/50">by {proposal.proposer_name}</p>
                    </div>
                    <span className={`px-2 py-1 text-[10px] sm:text-xs border self-start ${
                      proposal.status === 'active' ? 'border-neon-green text-neon-green' : 'border-white/30 text-white/50'
                    }`}>
                      {proposal.status}
                    </span>
                  </div>
                  
                  <p className="text-xs sm:text-sm text-white/70 mb-4">{proposal.description}</p>
                  
                  {/* Vote Bar */}
                  <div className="mb-4">
                    <div className="flex justify-between text-xs mb-1">
                      <span className="text-neon-green flex items-center gap-1">
                        <ThumbsUp className="w-3 h-3" /> {proposal.votes_for}
                      </span>
                      <span className="text-neon-red flex items-center gap-1">
                        {proposal.votes_against} <ThumbsDown className="w-3 h-3" />
                      </span>
                    </div>
                    <div className="h-2 bg-white/10 overflow-hidden flex">
                      <div className="h-full bg-neon-green transition-all" style={{ width: `${forPercent}%` }} />
                      <div className="h-full bg-neon-red transition-all" style={{ width: `${100 - forPercent}%` }} />
                    </div>
                  </div>
                  
                  {/* Vote Buttons */}
                  {proposal.status === 'active' && !hasVoted && (
                    <div className="flex gap-2">
                      <CyberButton 
                        variant="success" 
                        className="flex-1 text-xs sm:text-sm"
                        onClick={() => voteOnProposal(proposal.id, 'for')}
                        data-testid={`vote-for-${proposal.id}`}
                      >
                        <ThumbsUp className="w-4 h-4 inline mr-1" /> {t('voteFor')}
                      </CyberButton>
                      <CyberButton 
                        variant="danger" 
                        className="flex-1 text-xs sm:text-sm"
                        onClick={() => voteOnProposal(proposal.id, 'against')}
                        data-testid={`vote-against-${proposal.id}`}
                      >
                        <ThumbsDown className="w-4 h-4 inline mr-1" /> {t('voteAgainst')}
                      </CyberButton>
                    </div>
                  )}
                  {hasVoted && (
                    <div className="text-center text-xs text-white/50">You have voted on this proposal</div>
                  )}
                </CyberCard>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

export default VotingPage;
