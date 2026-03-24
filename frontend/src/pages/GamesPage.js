import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Gamepad2, Brain, Coins, Target, CircleDot, Loader2,
  Trophy, CheckCircle, Clock, Gift, Sparkles, Star
} from 'lucide-react';
import axios from 'axios';
import { API } from '../utils/api';
import { useAuth } from '../context/AuthContext';
import { CyberCard, CyberButton } from '../components/common/CyberUI';
import { toast } from 'sonner';

const GamesPage = () => {
  const { user, refreshUser } = useAuth();
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [activeTab, setActiveTab] = useState('games');
  
  const [games, setGames] = useState({});
  const [gamesStatus, setGamesStatus] = useState({});
  const [missions, setMissions] = useState({ daily: [], weekly: [] });
  const [leaderboard, setLeaderboard] = useState([]);
  
  // Quiz state
  const [quizSession, setQuizSession] = useState(null);
  const [currentQuestion, setCurrentQuestion] = useState(null);
  const [quizResult, setQuizResult] = useState(null);
  
  // Game modals
  const [showSpinModal, setShowSpinModal] = useState(false);
  const [showGuessModal, setShowGuessModal] = useState(false);
  const [showFlipModal, setShowFlipModal] = useState(false);
  const [spinResult, setSpinResult] = useState(null);
  const [guessInput, setGuessInput] = useState(5);
  const [flipChoice, setFlipChoice] = useState('heads');
  const [flipAmount, setFlipAmount] = useState(50);

  useEffect(() => {
    fetchAllData();
  }, []);

  const fetchAllData = async () => {
    try {
      const [gamesRes, leaderRes] = await Promise.all([
        axios.get(`${API}/games/list`),
        axios.get(`${API}/games/leaderboard`)
      ]);
      setGames(gamesRes.data.games || {});
      setLeaderboard(leaderRes.data.leaderboard || []);
      
      try {
        const [statusRes, missionsRes] = await Promise.all([
          axios.get(`${API}/games/status`),
          axios.get(`${API}/games/missions`)
        ]);
        setGamesStatus(statusRes.data.status || {});
        setMissions(missionsRes.data);
      } catch (e) {}
    } catch (error) {
      console.error('Failed to load games:', error);
    }
    setLoading(false);
  };

  // Quiz handlers
  const startQuiz = async () => {
    setProcessing(true);
    try {
      const res = await axios.post(`${API}/games/quiz/start`);
      setQuizSession(res.data.session_id);
      setCurrentQuestion(res.data.current_question);
      setQuizResult(null);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to start quiz');
    }
    setProcessing(false);
  };

  const answerQuiz = async (answerIndex) => {
    if (!quizSession || !currentQuestion) return;
    setProcessing(true);
    try {
      const res = await axios.post(`${API}/games/quiz/${quizSession}/answer`, {
        question_index: currentQuestion.index,
        answer_index: answerIndex
      });
      
      if (res.data.finished) {
        setQuizResult(res.data);
        setQuizSession(null);
        setCurrentQuestion(null);
        fetchAllData();
        refreshUser();
      } else {
        setCurrentQuestion(res.data.next_question);
      }
      
      toast[res.data.is_correct ? 'success' : 'error'](
        res.data.is_correct ? 'Corect! ✅' : `Greșit! Răspunsul era ${res.data.correct_answer + 1}`
      );
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error submitting answer');
    }
    setProcessing(false);
  };

  // Lucky Spin
  const playLuckySpin = async () => {
    setProcessing(true);
    setSpinResult(null);
    try {
      const res = await axios.post(`${API}/games/lucky-spin`);
      // Simulate spin animation
      setTimeout(() => {
        setSpinResult(res.data);
        toast.success(res.data.message);
        refreshUser();
      }, 2000);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to spin');
    }
    setProcessing(false);
  };

  // Number Guess
  const playNumberGuess = async () => {
    setProcessing(true);
    try {
      const res = await axios.post(`${API}/games/number-guess`, { guess: guessInput });
      toast[res.data.won ? 'success' : 'error'](res.data.message);
      setShowGuessModal(false);
      fetchAllData();
      refreshUser();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to play');
    }
    setProcessing(false);
  };

  // Coin Flip
  const playCoinFlip = async () => {
    setProcessing(true);
    try {
      const res = await axios.post(`${API}/games/coin-flip`, {
        choice: flipChoice,
        amount: flipAmount
      });
      toast[res.data.won ? 'success' : 'error'](res.data.message);
      setShowFlipModal(false);
      fetchAllData();
      refreshUser();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to play');
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
    <div className="min-h-screen pt-16 sm:pt-20 pb-20 lg:pb-12 px-3 sm:px-4" data-testid="games-page">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-6">
          <h1 className="text-2xl sm:text-3xl font-orbitron font-black flex items-center gap-3">
            <Gamepad2 className="w-8 h-8 text-neon-pink" />
            <span>Jocuri & <span className="text-neon-cyan">Misiuni</span></span>
          </h1>
          <p className="text-white/60 text-sm mt-1">Joacă și câștigă RLM și XP!</p>
        </motion.div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
          {[
            { id: 'games', label: 'Mini-Jocuri', icon: Gamepad2 },
            { id: 'missions', label: 'Misiuni', icon: Target },
            { id: 'leaderboard', label: 'Clasament', icon: Trophy }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-2 font-mono text-sm whitespace-nowrap flex items-center gap-2 transition-all ${
                activeTab === tab.id 
                  ? 'bg-neon-pink/20 border border-neon-pink text-neon-pink' 
                  : 'border border-white/20 text-white/60 hover:border-white/40'
              }`}
            >
              <tab.icon className="w-4 h-4" /> {tab.label}
            </button>
          ))}
        </div>

        {/* Games Tab */}
        {activeTab === 'games' && (
          <div className="space-y-6">
            {/* Active Quiz */}
            {quizSession && currentQuestion && (
              <CyberCard className="p-6 border-neon-cyan">
                <h3 className="font-orbitron text-lg mb-4 flex items-center gap-2">
                  <Brain className="w-5 h-5 text-neon-cyan" /> Quiz în Desfășurare
                </h3>
                <div className="text-sm text-white/50 mb-4">Întrebarea {currentQuestion.index + 1}/5</div>
                <p className="text-lg mb-4">{currentQuestion.question}</p>
                <div className="grid grid-cols-2 gap-3">
                  {currentQuestion.options.map((option, idx) => (
                    <CyberButton
                      key={idx}
                      variant="outline"
                      onClick={() => answerQuiz(idx)}
                      disabled={processing}
                      className="justify-start"
                    >
                      <span className="mr-2 text-neon-cyan">{idx + 1}.</span> {option}
                    </CyberButton>
                  ))}
                </div>
              </CyberCard>
            )}

            {/* Quiz Result */}
            {quizResult && (
              <CyberCard className="p-6 border-neon-green text-center">
                <Sparkles className="w-12 h-12 mx-auto mb-4 text-neon-yellow" />
                <h3 className="font-orbitron text-xl mb-2">Quiz Completat!</h3>
                <p className="text-2xl font-orbitron text-neon-green mb-2">{quizResult.final_score}</p>
                <p className="text-neon-cyan">+{quizResult.reward} RLM | +{quizResult.xp_earned} XP</p>
                <CyberButton variant="outline" className="mt-4" onClick={() => setQuizResult(null)}>
                  Închide
                </CyberButton>
              </CyberCard>
            )}

            {/* Games Grid */}
            {!quizSession && !quizResult && (
              <div className="grid md:grid-cols-2 gap-4">
                {/* Daily Quiz */}
                <CyberCard className="p-4">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="p-2 bg-neon-cyan/20 border border-neon-cyan">
                      <Brain className="w-6 h-6 text-neon-cyan" />
                    </div>
                    <div>
                      <h4 className="font-orbitron">Quiz Zilnic</h4>
                      <p className="text-xs text-white/50">Răspunde la 5 întrebări</p>
                    </div>
                  </div>
                  <div className="text-sm text-white/60 mb-3">
                    Recompensă: <span className="text-neon-green">5-25 RLM</span> + <span className="text-neon-purple">50 XP</span>
                  </div>
                  <CyberButton 
                    variant="primary" 
                    className="w-full"
                    onClick={startQuiz}
                    disabled={processing || !gamesStatus.daily_quiz?.can_play}
                  >
                    {gamesStatus.daily_quiz?.can_play ? 'Începe Quiz' : 'Disponibil Mâine'}
                  </CyberButton>
                </CyberCard>

                {/* Lucky Spin */}
                <CyberCard className="p-4">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="p-2 bg-neon-yellow/20 border border-neon-yellow">
                      <CircleDot className="w-6 h-6 text-neon-yellow" />
                    </div>
                    <div>
                      <h4 className="font-orbitron">Roata Norocului</h4>
                      <p className="text-xs text-white/50">Învârte pentru premii</p>
                    </div>
                  </div>
                  <div className="text-sm text-white/60 mb-3">
                    Cost: <span className="text-neon-red">10 RLM</span> | Premii până la <span className="text-neon-green">500 RLM</span>
                  </div>
                  <CyberButton 
                    variant="primary" 
                    className="w-full"
                    onClick={() => setShowSpinModal(true)}
                  >
                    Învârte (10 RLM)
                  </CyberButton>
                </CyberCard>

                {/* Number Guess */}
                <CyberCard className="p-4">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="p-2 bg-neon-green/20 border border-neon-green">
                      <Target className="w-6 h-6 text-neon-green" />
                    </div>
                    <div>
                      <h4 className="font-orbitron">Ghicește Numărul</h4>
                      <p className="text-xs text-white/50">Alege 1-10, câștigă 25 RLM</p>
                    </div>
                  </div>
                  <div className="text-sm text-white/60 mb-3">
                    Cost: <span className="text-neon-red">5 RLM</span> | Câștig: <span className="text-neon-green">25 RLM</span>
                  </div>
                  <CyberButton 
                    variant="primary" 
                    className="w-full"
                    onClick={() => setShowGuessModal(true)}
                  >
                    Joacă (5 RLM)
                  </CyberButton>
                </CyberCard>

                {/* Coin Flip */}
                <CyberCard className="p-4">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="p-2 bg-neon-purple/20 border border-neon-purple">
                      <Coins className="w-6 h-6 text-neon-purple" />
                    </div>
                    <div>
                      <h4 className="font-orbitron">Cap sau Pajură</h4>
                      <p className="text-xs text-white/50">50/50 să-ți dublezi miza</p>
                    </div>
                  </div>
                  <div className="text-sm text-white/60 mb-3">
                    Miză: <span className="text-neon-cyan">10-1000 RLM</span>
                  </div>
                  <CyberButton 
                    variant="primary" 
                    className="w-full"
                    onClick={() => setShowFlipModal(true)}
                  >
                    Joacă
                  </CyberButton>
                </CyberCard>
              </div>
            )}
          </div>
        )}

        {/* Missions Tab */}
        {activeTab === 'missions' && (
          <div className="space-y-6">
            {/* Daily Missions */}
            <CyberCard className="p-4">
              <h3 className="font-orbitron text-lg mb-4 flex items-center gap-2">
                <Clock className="w-5 h-5 text-neon-cyan" /> Misiuni Zilnice
              </h3>
              <div className="space-y-3">
                {missions.daily?.map(mission => (
                  <div 
                    key={mission.id} 
                    className={`p-3 border ${mission.completed ? 'bg-neon-green/10 border-neon-green/30' : 'bg-black/30 border-white/10'}`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        {mission.completed ? (
                          <CheckCircle className="w-5 h-5 text-neon-green" />
                        ) : (
                          <div className="w-5 h-5 border border-white/30 rounded-full" />
                        )}
                        <span className={mission.completed ? 'text-white/50 line-through' : ''}>{mission.name}</span>
                      </div>
                      <div className="text-sm">
                        <span className="text-neon-green">+{mission.reward} RLM</span>
                        <span className="text-neon-purple ml-2">+{mission.xp} XP</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CyberCard>

            {/* Weekly Missions */}
            <CyberCard className="p-4">
              <h3 className="font-orbitron text-lg mb-4 flex items-center gap-2">
                <Star className="w-5 h-5 text-neon-yellow" /> Misiuni Săptămânale
              </h3>
              <div className="space-y-3">
                {missions.weekly?.map(mission => (
                  <div 
                    key={mission.id} 
                    className={`p-3 border ${mission.completed ? 'bg-neon-green/10 border-neon-green/30' : 'bg-black/30 border-white/10'}`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        {mission.completed ? (
                          <CheckCircle className="w-5 h-5 text-neon-green" />
                        ) : (
                          <div className="w-5 h-5 border border-white/30 rounded-full" />
                        )}
                        <span className={mission.completed ? 'text-white/50 line-through' : ''}>{mission.name}</span>
                      </div>
                      <div className="text-sm">
                        <span className="text-neon-green">+{mission.reward} RLM</span>
                        <span className="text-neon-purple ml-2">+{mission.xp} XP</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CyberCard>
          </div>
        )}

        {/* Leaderboard Tab */}
        {activeTab === 'leaderboard' && (
          <CyberCard className="p-4">
            <h3 className="font-orbitron text-lg mb-4">Top Jucători</h3>
            <div className="space-y-3">
              {leaderboard.map((player, i) => (
                <div key={i} className="flex items-center justify-between p-3 bg-black/30 border border-white/10">
                  <div className="flex items-center gap-3">
                    <span className={`text-2xl font-orbitron ${i < 3 ? 'text-neon-yellow' : 'text-white/50'}`}>
                      #{player.rank}
                    </span>
                    <div>
                      <div className="font-mono text-neon-cyan">{player.username}</div>
                      <div className="text-xs text-white/40">{player.total_plays} jocuri</div>
                    </div>
                  </div>
                  <div className="font-orbitron text-neon-green">{player.total_won} RLM</div>
                </div>
              ))}
              {leaderboard.length === 0 && (
                <div className="text-center py-8 text-white/50">
                  Niciun jucător încă. Fii primul!
                </div>
              )}
            </div>
          </CyberCard>
        )}

        {/* Lucky Spin Modal */}
        <AnimatePresence>
          {showSpinModal && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4"
              onClick={() => !processing && setShowSpinModal(false)}
            >
              <motion.div
                initial={{ scale: 0.9 }}
                animate={{ scale: 1 }}
                exit={{ scale: 0.9 }}
                className="bg-gray-900 border border-neon-yellow p-6 max-w-sm w-full text-center"
                onClick={e => e.stopPropagation()}
              >
                <CircleDot className={`w-16 h-16 mx-auto mb-4 text-neon-yellow ${processing ? 'animate-spin' : ''}`} />
                <h3 className="font-orbitron text-xl mb-4">Roata Norocului</h3>
                
                {spinResult ? (
                  <div className="mb-4">
                    <p className="text-2xl font-orbitron text-neon-green mb-2">{spinResult.message}</p>
                    {spinResult.result.type !== 'nothing' && (
                      <p className="text-neon-cyan">
                        +{spinResult.result.value} {spinResult.result.type.toUpperCase()}
                      </p>
                    )}
                  </div>
                ) : (
                  <p className="text-white/60 mb-4">Învârte roata pentru șansa de a câștiga până la 500 RLM!</p>
                )}
                
                <div className="flex gap-3">
                  <CyberButton variant="outline" className="flex-1" onClick={() => setShowSpinModal(false)} disabled={processing}>
                    Închide
                  </CyberButton>
                  {!spinResult && (
                    <CyberButton variant="primary" className="flex-1" onClick={playLuckySpin} disabled={processing}>
                      {processing ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Învârte (10 RLM)'}
                    </CyberButton>
                  )}
                </div>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Number Guess Modal */}
        <AnimatePresence>
          {showGuessModal && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4"
              onClick={() => setShowGuessModal(false)}
            >
              <motion.div
                initial={{ scale: 0.9 }}
                animate={{ scale: 1 }}
                exit={{ scale: 0.9 }}
                className="bg-gray-900 border border-neon-green p-6 max-w-sm w-full text-center"
                onClick={e => e.stopPropagation()}
              >
                <Target className="w-12 h-12 mx-auto mb-4 text-neon-green" />
                <h3 className="font-orbitron text-xl mb-4">Ghicește Numărul</h3>
                <p className="text-white/60 mb-4">Alege un număr între 1 și 10</p>
                
                <input
                  type="range"
                  min={1}
                  max={10}
                  value={guessInput}
                  onChange={e => setGuessInput(parseInt(e.target.value))}
                  className="w-full mb-2"
                />
                <div className="text-3xl font-orbitron text-neon-cyan mb-4">{guessInput}</div>
                
                <div className="flex gap-3">
                  <CyberButton variant="outline" className="flex-1" onClick={() => setShowGuessModal(false)}>
                    Anulează
                  </CyberButton>
                  <CyberButton variant="primary" className="flex-1" onClick={playNumberGuess} disabled={processing}>
                    {processing ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Ghicește (5 RLM)'}
                  </CyberButton>
                </div>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Coin Flip Modal */}
        <AnimatePresence>
          {showFlipModal && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4"
              onClick={() => setShowFlipModal(false)}
            >
              <motion.div
                initial={{ scale: 0.9 }}
                animate={{ scale: 1 }}
                exit={{ scale: 0.9 }}
                className="bg-gray-900 border border-neon-purple p-6 max-w-sm w-full"
                onClick={e => e.stopPropagation()}
              >
                <Coins className="w-12 h-12 mx-auto mb-4 text-neon-purple" />
                <h3 className="font-orbitron text-xl mb-4 text-center">Cap sau Pajură</h3>
                
                <div className="mb-4">
                  <label className="text-sm text-white/60 block mb-2">Alege:</label>
                  <div className="grid grid-cols-2 gap-3">
                    <button
                      onClick={() => setFlipChoice('heads')}
                      className={`p-3 border ${flipChoice === 'heads' ? 'border-neon-cyan bg-neon-cyan/20' : 'border-white/20'}`}
                    >
                      Cap 🪙
                    </button>
                    <button
                      onClick={() => setFlipChoice('tails')}
                      className={`p-3 border ${flipChoice === 'tails' ? 'border-neon-cyan bg-neon-cyan/20' : 'border-white/20'}`}
                    >
                      Pajură 🔄
                    </button>
                  </div>
                </div>
                
                <div className="mb-4">
                  <label className="text-sm text-white/60 block mb-2">Miză (RLM):</label>
                  <input
                    type="number"
                    value={flipAmount}
                    onChange={e => setFlipAmount(Math.max(10, Math.min(1000, parseInt(e.target.value) || 10)))}
                    className="w-full bg-black/50 border border-white/20 p-2 text-white text-center text-xl"
                    min={10}
                    max={1000}
                  />
                  <div className="text-xs text-white/40 mt-1 text-center">
                    Câștig potențial: <span className="text-neon-green">{flipAmount * 2} RLM</span>
                  </div>
                </div>
                
                <div className="flex gap-3">
                  <CyberButton variant="outline" className="flex-1" onClick={() => setShowFlipModal(false)}>
                    Anulează
                  </CyberButton>
                  <CyberButton variant="primary" className="flex-1" onClick={playCoinFlip} disabled={processing}>
                    {processing ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Aruncă'}
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

export default GamesPage;
