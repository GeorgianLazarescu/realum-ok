import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { 
  Trophy, Clock, Users, DollarSign, Target, Medal,
  Loader2, ChevronRight, Star, Crown, Zap
} from 'lucide-react';
import axios from 'axios';
import { API } from '../utils/api';
import { useAuth } from '../context/AuthContext';
import { CyberCard, CyberButton } from '../components/common/CyberUI';
import { toast } from 'sonner';

const TournamentsPage = () => {
  const { user, refreshUser } = useAuth();
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  
  const [activeTab, setActiveTab] = useState('active'); // active, my, past
  const [activeTournaments, setActiveTournaments] = useState([]);
  const [myTournaments, setMyTournaments] = useState([]);
  const [pastTournaments, setPastTournaments] = useState([]);
  const [tournamentTypes, setTournamentTypes] = useState({});
  const [globalLeaderboard, setGlobalLeaderboard] = useState([]);
  
  const [selectedTournament, setSelectedTournament] = useState(null);
  const [showDetailsModal, setShowDetailsModal] = useState(false);

  useEffect(() => {
    fetchAllData();
  }, []);

  const fetchAllData = async () => {
    try {
      const [activeRes, myRes, pastRes, typesRes, leaderRes] = await Promise.all([
        axios.get(`${API}/tournaments/active`),
        axios.get(`${API}/tournaments/my-tournaments`),
        axios.get(`${API}/tournaments/past`),
        axios.get(`${API}/tournaments/types`),
        axios.get(`${API}/tournaments/leaderboard/global`)
      ]);
      
      setActiveTournaments(activeRes.data.tournaments || []);
      setMyTournaments(myRes.data.my_tournaments || []);
      setPastTournaments(pastRes.data.tournaments || []);
      setTournamentTypes(typesRes.data.tournament_types || {});
      setGlobalLeaderboard(leaderRes.data.leaderboard || []);
    } catch (error) {
      console.error('Failed to load tournaments:', error);
    }
    setLoading(false);
  };

  const handleJoinTournament = async (tournamentId) => {
    setProcessing(true);
    try {
      const res = await axios.post(`${API}/tournaments/${tournamentId}/join`);
      toast.success(res.data.message);
      fetchAllData();
      refreshUser();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to join');
    }
    setProcessing(false);
  };

  const handleViewDetails = async (tournamentId) => {
    try {
      const res = await axios.get(`${API}/tournaments/${tournamentId}`);
      setSelectedTournament(res.data);
      setShowDetailsModal(true);
    } catch (error) {
      toast.error('Failed to load tournament details');
    }
  };

  const getTimeRemaining = (endTime) => {
    const diff = new Date(endTime) - new Date();
    if (diff <= 0) return 'Terminat';
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));
    const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
    if (days > 0) return `${days}z ${hours}h`;
    return `${hours}h`;
  };

  if (loading) {
    return (
      <div className="min-h-screen pt-20 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-neon-cyan" />
      </div>
    );
  }

  return (
    <div className="min-h-screen pt-16 sm:pt-20 pb-20 lg:pb-12 px-3 sm:px-4" data-testid="tournaments-page">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-2xl sm:text-3xl font-orbitron font-black flex items-center gap-3">
            <Trophy className="w-8 h-8 text-neon-yellow" />
            <span>Turnee & <span className="text-neon-cyan">Competiții</span></span>
          </h1>
          <p className="text-white/60 text-sm mt-1">Concurează pentru premii și glorie</p>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
          <CyberCard className="p-4 text-center">
            <div className="text-2xl font-orbitron text-neon-green">{activeTournaments.length}</div>
            <div className="text-xs text-white/50">Turnee Active</div>
          </CyberCard>
          <CyberCard className="p-4 text-center">
            <div className="text-2xl font-orbitron text-neon-cyan">{myTournaments.length}</div>
            <div className="text-xs text-white/50">Participări</div>
          </CyberCard>
          <CyberCard className="p-4 text-center">
            <div className="text-2xl font-orbitron text-neon-yellow">
              {myTournaments.filter(t => t.my_rank <= 3).length}
            </div>
            <div className="text-xs text-white/50">Top 3 Finishes</div>
          </CyberCard>
          <CyberCard className="p-4 text-center">
            <div className="text-2xl font-orbitron text-neon-purple">{Object.keys(tournamentTypes).length}</div>
            <div className="text-xs text-white/50">Tipuri Turnee</div>
          </CyberCard>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
          {[
            { id: 'active', label: 'Active', icon: Zap },
            { id: 'my', label: 'Participările Mele', icon: Target },
            { id: 'past', label: 'Încheiate', icon: Clock },
            { id: 'leaderboard', label: 'Hall of Fame', icon: Crown }
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

        {/* Active Tournaments */}
        {activeTab === 'active' && (
          <div className="grid md:grid-cols-2 gap-4">
            {activeTournaments.map(tournament => {
              const isJoined = myTournaments.some(t => t.tournament?.id === tournament.id);
              
              return (
                <CyberCard key={tournament.id} className="p-5">
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <h3 className="font-orbitron text-lg text-neon-cyan">{tournament.name}</h3>
                      <p className="text-sm text-white/60">{tournament.description}</p>
                    </div>
                    <div className="text-right">
                      <div className="flex items-center gap-1 text-neon-yellow">
                        <Clock className="w-4 h-4" />
                        <span className="font-mono">{getTimeRemaining(tournament.end_time)}</span>
                      </div>
                    </div>
                  </div>
                  
                  <div className="grid grid-cols-3 gap-3 mb-4">
                    <div className="text-center p-2 bg-black/30 border border-white/10">
                      <div className="text-xs text-white/50">Entry</div>
                      <div className="font-mono text-neon-green">
                        {tournament.entry_fee > 0 ? `${tournament.entry_fee} RLM` : 'FREE'}
                      </div>
                    </div>
                    <div className="text-center p-2 bg-black/30 border border-white/10">
                      <div className="text-xs text-white/50">Participants</div>
                      <div className="font-mono">{tournament.participant_count || 0}/{tournament.max_participants}</div>
                    </div>
                    <div className="text-center p-2 bg-black/30 border border-white/10">
                      <div className="text-xs text-white/50">Prize Pool</div>
                      <div className="font-mono text-neon-yellow">{tournament.prize_pool || 0} RLM</div>
                    </div>
                  </div>
                  
                  {/* Prizes */}
                  <div className="flex gap-2 mb-4">
                    {[1, 2, 3].map(place => {
                      const prize = tournament.prizes?.[place];
                      if (!prize) return null;
                      return (
                        <div key={place} className={`flex-1 p-2 text-center border ${
                          place === 1 ? 'border-neon-yellow bg-neon-yellow/10' :
                          place === 2 ? 'border-gray-400 bg-gray-400/10' :
                          'border-orange-600 bg-orange-600/10'
                        }`}>
                          <Medal className={`w-4 h-4 mx-auto mb-1 ${
                            place === 1 ? 'text-neon-yellow' :
                            place === 2 ? 'text-gray-400' : 'text-orange-600'
                          }`} />
                          <div className="text-xs font-mono">{prize.rlm} RLM</div>
                        </div>
                      );
                    })}
                  </div>
                  
                  <div className="flex gap-2">
                    <CyberButton 
                      variant="outline" 
                      className="flex-1"
                      onClick={() => handleViewDetails(tournament.id)}
                    >
                      Detalii
                    </CyberButton>
                    {isJoined ? (
                      <span className="flex-1 py-2 text-center text-neon-green border border-neon-green/50 bg-neon-green/10">
                        Înscris ✓
                      </span>
                    ) : (
                      <CyberButton 
                        variant="primary" 
                        className="flex-1"
                        onClick={() => handleJoinTournament(tournament.id)}
                        disabled={processing}
                      >
                        {processing ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Înscrie-te'}
                      </CyberButton>
                    )}
                  </div>
                </CyberCard>
              );
            })}
            
            {activeTournaments.length === 0 && (
              <div className="col-span-full text-center py-12 text-white/50">
                <Trophy className="w-12 h-12 mx-auto mb-4 opacity-50" />
                <p>Niciun turneu activ momentan</p>
              </div>
            )}
          </div>
        )}

        {/* My Tournaments */}
        {activeTab === 'my' && (
          <div className="space-y-3">
            {myTournaments.map(({ tournament, my_score, my_rank }) => (
              <CyberCard key={tournament?.id} className="p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className={`w-12 h-12 flex items-center justify-center text-2xl font-orbitron ${
                      my_rank === 1 ? 'text-neon-yellow' :
                      my_rank === 2 ? 'text-gray-300' :
                      my_rank === 3 ? 'text-orange-400' : 'text-white/50'
                    }`}>
                      #{my_rank}
                    </div>
                    <div>
                      <div className="font-orbitron text-neon-cyan">{tournament?.name}</div>
                      <div className="text-sm text-white/50">
                        Status: <span className={tournament?.status === 'active' ? 'text-neon-green' : 'text-white/60'}>
                          {tournament?.status}
                        </span>
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="font-orbitron text-neon-purple">{my_score} pts</div>
                    <div className="text-xs text-white/40">
                      {getTimeRemaining(tournament?.end_time)} rămas
                    </div>
                  </div>
                </div>
              </CyberCard>
            ))}
            
            {myTournaments.length === 0 && (
              <div className="text-center py-12 text-white/50">
                <Target className="w-12 h-12 mx-auto mb-4 opacity-50" />
                <p>Nu participi la niciun turneu</p>
              </div>
            )}
          </div>
        )}

        {/* Past Tournaments */}
        {activeTab === 'past' && (
          <div className="space-y-3">
            {pastTournaments.map(tournament => (
              <CyberCard key={tournament.id} className="p-4 opacity-80">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-orbitron">{tournament.name}</div>
                    <div className="text-sm text-white/50">
                      Încheiat: {new Date(tournament.end_time).toLocaleDateString()}
                    </div>
                  </div>
                  <CyberButton variant="outline" size="sm" onClick={() => handleViewDetails(tournament.id)}>
                    Rezultate
                  </CyberButton>
                </div>
              </CyberCard>
            ))}
          </div>
        )}

        {/* Hall of Fame */}
        {activeTab === 'leaderboard' && (
          <CyberCard className="p-4">
            <h3 className="font-orbitron text-lg mb-4 flex items-center gap-2">
              <Crown className="w-5 h-5 text-neon-yellow" /> Top Campioni
            </h3>
            <div className="space-y-2">
              {globalLeaderboard.map((entry, i) => (
                <div
                  key={entry.username}
                  className={`flex items-center justify-between p-3 ${
                    i < 3 ? 'bg-neon-yellow/10 border border-neon-yellow/30' : 'bg-black/30 border border-white/10'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <span className={`text-2xl font-orbitron ${
                      i === 0 ? 'text-neon-yellow' : i === 1 ? 'text-gray-300' : i === 2 ? 'text-orange-400' : 'text-white/50'
                    }`}>
                      #{entry.rank}
                    </span>
                    <div>
                      <div className="font-mono text-neon-cyan">{entry.username}</div>
                      <div className="text-xs text-white/40">
                        {entry.tournament_wins} victorii • {entry.top3_finishes} top 3
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="font-mono text-neon-green">{entry.total_earnings} RLM</div>
                    <div className="text-xs text-white/40">Câștiguri</div>
                  </div>
                </div>
              ))}
              
              {globalLeaderboard.length === 0 && (
                <p className="text-center text-white/50 py-8">Încă nu există campioni</p>
              )}
            </div>
          </CyberCard>
        )}

        {/* Tournament Details Modal */}
        {showDetailsModal && selectedTournament && (
          <div className="fixed inset-0 bg-black/90 z-50 flex items-center justify-center p-4" onClick={() => setShowDetailsModal(false)}>
            <CyberCard className="p-6 max-w-2xl w-full max-h-[80vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
              <h3 className="font-orbitron text-xl mb-4">{selectedTournament.tournament?.name}</h3>
              
              <p className="text-white/60 mb-4">{selectedTournament.tournament?.description}</p>
              
              {/* Leaderboard */}
              <h4 className="font-orbitron mb-2">Clasament</h4>
              <div className="space-y-2 mb-4">
                {selectedTournament.leaderboard?.slice(0, 10).map((entry, i) => (
                  <div key={i} className="flex items-center justify-between p-2 bg-black/30 border border-white/10">
                    <div className="flex items-center gap-2">
                      <span className={`font-orbitron ${i < 3 ? 'text-neon-yellow' : 'text-white/50'}`}>
                        #{entry.rank}
                      </span>
                      <span className="font-mono text-neon-cyan">{entry.username}</span>
                    </div>
                    <span className="font-mono">{entry.score} pts</span>
                  </div>
                ))}
              </div>
              
              <CyberButton variant="outline" className="w-full" onClick={() => setShowDetailsModal(false)}>
                Închide
              </CyberButton>
            </CyberCard>
          </div>
        )}
      </div>
    </div>
  );
};

export default TournamentsPage;
