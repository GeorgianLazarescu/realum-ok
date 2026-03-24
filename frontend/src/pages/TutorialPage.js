import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  BookOpen, ChevronRight, Gift, Check, Star, Sparkles,
  Loader2, X, Play, SkipForward
} from 'lucide-react';
import axios from 'axios';
import { API } from '../utils/api';
import { useAuth } from '../context/AuthContext';
import { CyberCard, CyberButton } from '../components/common/CyberUI';
import { toast } from 'sonner';
import { useNavigate } from 'react-router-dom';

const TutorialPage = () => {
  const { user, refreshUser } = useAuth();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  
  const [steps, setSteps] = useState([]);
  const [progress, setProgress] = useState(null);
  const [currentStep, setCurrentStep] = useState(null);
  const [npcs, setNpcs] = useState([]);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [stepsRes, progressRes, npcsRes] = await Promise.all([
        axios.get(`${API}/tutorial/steps`),
        axios.get(`${API}/tutorial/progress`),
        axios.get(`${API}/tutorial/npcs`)
      ]);
      
      setSteps(stepsRes.data.steps || []);
      setProgress(progressRes.data);
      setCurrentStep(progressRes.data.current_step_data);
      setNpcs(npcsRes.data.npcs || []);
    } catch (error) {
      console.error('Failed to load tutorial:', error);
    }
    setLoading(false);
  };

  const handleCompleteStep = async () => {
    if (!currentStep) return;
    setProcessing(true);
    
    try {
      const res = await axios.post(`${API}/tutorial/complete-step/${currentStep.id}`);
      toast.success(`${currentStep.title} completat! +${res.data.rewards.rlm} RLM`);
      
      if (res.data.is_tutorial_complete) {
        toast.success('Felicitări! Ai completat tutorialul! 🎉');
      }
      
      fetchData();
      refreshUser();
      
      // Navigate if action requires it
      if (res.data.next_step?.action?.type === 'navigate') {
        setTimeout(() => {
          navigate(res.data.next_step.action.target);
        }, 1500);
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to complete step');
    }
    setProcessing(false);
  };

  const handleSkipTutorial = async () => {
    if (!confirm('Ești sigur că vrei să sari peste tutorial?')) return;
    
    try {
      await axios.post(`${API}/tutorial/skip`);
      toast.info('Tutorial sărit. Poți relua oricând din setări.');
      navigate('/dashboard');
    } catch (error) {
      toast.error('Failed to skip tutorial');
    }
  };

  const getNpc = (npcName) => {
    return npcs.find(n => n.name === npcName) || { avatar: '🤖', name: npcName };
  };

  if (loading) {
    return (
      <div className="min-h-screen pt-20 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-neon-cyan" />
      </div>
    );
  }

  if (progress?.is_completed) {
    return (
      <div className="min-h-screen pt-16 sm:pt-20 pb-20 px-3 sm:px-4">
        <div className="max-w-2xl mx-auto text-center py-20">
          <Sparkles className="w-20 h-20 text-neon-yellow mx-auto mb-6" />
          <h1 className="text-3xl font-orbitron mb-4">Tutorial Completat!</h1>
          <p className="text-white/60 mb-8">
            Ai învățat bazele REALUM. Acum e timpul să explorezi singur!
          </p>
          <div className="flex justify-center gap-4">
            <CyberButton variant="primary" onClick={() => navigate('/dashboard')}>
              Mergi la Dashboard
            </CyberButton>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen pt-16 sm:pt-20 pb-20 lg:pb-12 px-3 sm:px-4" data-testid="tutorial-page">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl sm:text-3xl font-orbitron font-black flex items-center gap-3">
              <BookOpen className="w-8 h-8 text-neon-cyan" />
              <span>Tutorial <span className="text-neon-yellow">REALUM</span></span>
            </h1>
            <p className="text-white/60 text-sm mt-1">
              Pas {progress?.current_step || 1} din {steps.length}
            </p>
          </div>
          <CyberButton variant="outline" size="sm" onClick={handleSkipTutorial}>
            <SkipForward className="w-4 h-4 mr-2" /> Sari Tutorial
          </CyberButton>
        </div>

        {/* Progress Bar */}
        <div className="mb-8">
          <div className="h-2 bg-black/50 border border-white/20">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${progress?.progress_percentage || 0}%` }}
              className="h-full bg-gradient-to-r from-neon-cyan to-neon-purple"
            />
          </div>
          <div className="flex justify-between mt-2 text-xs text-white/50">
            <span>{progress?.progress_percentage || 0}% completat</span>
            <span>+{progress?.total_rlm_earned || 0} RLM câștigați</span>
          </div>
        </div>

        {/* Current Step */}
        {currentStep && (
          <CyberCard className="p-6 mb-6">
            <div className="flex items-start gap-4">
              {/* NPC Avatar */}
              <div className="text-4xl">{getNpc(currentStep.npc).avatar}</div>
              
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-xs px-2 py-0.5 bg-neon-purple/20 border border-neon-purple/50 text-neon-purple">
                    {getNpc(currentStep.npc).name}
                  </span>
                  <span className="text-xs text-white/40">#{currentStep.order}</span>
                </div>
                
                <h2 className="text-xl font-orbitron text-neon-cyan mb-2">{currentStep.title}</h2>
                <p className="text-white/70 mb-4">{currentStep.description}</p>
                
                {/* NPC Message */}
                <div className="p-4 bg-black/30 border-l-4 border-neon-cyan mb-4">
                  <p className="text-white/80 italic">"{currentStep.npc_message}"</p>
                </div>
                
                {/* Rewards */}
                <div className="flex items-center gap-4 mb-4">
                  <div className="flex items-center gap-2">
                    <Gift className="w-4 h-4 text-neon-yellow" />
                    <span className="text-neon-yellow font-mono">
                      +{(currentStep.reward_rlm || 0) + (currentStep.bonus_rlm || 0)} RLM
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Star className="w-4 h-4 text-neon-purple" />
                    <span className="text-neon-purple font-mono">+{currentStep.reward_xp || 0} XP</span>
                  </div>
                </div>
                
                {/* Action Button */}
                <CyberButton
                  variant="primary"
                  onClick={handleCompleteStep}
                  disabled={processing}
                >
                  {processing ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <>
                      {currentStep.action?.type === 'navigate' ? 'Continuă' : 'Completează'}
                      <ChevronRight className="w-4 h-4 ml-2" />
                    </>
                  )}
                </CyberButton>
              </div>
            </div>
          </CyberCard>
        )}

        {/* Steps Overview */}
        <CyberCard className="p-4">
          <h3 className="font-orbitron text-lg mb-4">Toți Pașii</h3>
          <div className="space-y-2">
            {steps.map((step, i) => {
              const isCompleted = progress?.completed_steps?.includes(step.id);
              const isCurrent = step.order === progress?.current_step;
              
              return (
                <div
                  key={step.id}
                  className={`flex items-center gap-3 p-3 border ${
                    isCompleted 
                      ? 'border-neon-green/50 bg-neon-green/10' 
                      : isCurrent 
                        ? 'border-neon-cyan bg-neon-cyan/10' 
                        : 'border-white/10 bg-black/20 opacity-50'
                  }`}
                >
                  <div className={`w-8 h-8 flex items-center justify-center border ${
                    isCompleted ? 'border-neon-green bg-neon-green/20' : 'border-white/30'
                  }`}>
                    {isCompleted ? (
                      <Check className="w-4 h-4 text-neon-green" />
                    ) : (
                      <span className="text-xs font-mono">{step.order}</span>
                    )}
                  </div>
                  <div className="flex-1">
                    <div className="font-mono text-sm">{step.title}</div>
                    <div className="text-xs text-white/40">{step.npc}</div>
                  </div>
                  <div className="text-xs text-neon-yellow">
                    +{step.reward_rlm || 0} RLM
                  </div>
                </div>
              );
            })}
          </div>
        </CyberCard>
      </div>
    </div>
  );
};

export default TutorialPage;
