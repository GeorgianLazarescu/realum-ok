import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Play, RefreshCw, Users, ArrowRight, Flame } from 'lucide-react';
import axios from 'axios';
import { API } from '../utils/api';
import { useTranslation } from '../context/LanguageContext';
import { CyberCard, CyberButton } from '../components/common/CyberUI';

const SimulationPage = () => {
  const t = useTranslation();
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [stepResult, setStepResult] = useState(null);
  const [currentStep, setCurrentStep] = useState(0);
  
  const fetchStatus = () => {
    axios.get(`${API}/simulation/status`).then(res => setStatus(res.data)).catch(console.error).finally(() => setLoading(false));
  };
  
  useEffect(() => { fetchStatus(); }, []);
  
  const setupSimulation = async () => {
    setLoading(true);
    try {
      await axios.post(`${API}/simulation/setup`);
      setCurrentStep(0);
      setStepResult(null);
      fetchStatus();
    } catch (err) {
      alert(err.response?.data?.detail || 'Setup failed');
      setLoading(false);
    }
  };
  
  const runStep = async (step) => {
    try {
      const res = await axios.post(`${API}/simulation/step/${step}`);
      setStepResult(res.data);
      setCurrentStep(step);
      fetchStatus();
    } catch (err) {
      alert(err.response?.data?.detail || 'Step failed');
    }
  };
  
  const steps = [
    { num: 1, title: 'Purchase', desc: 'Vlad buys Andreea\'s UI Design Kit', icon: '🛒' },
    { num: 2, title: 'Task', desc: 'Vlad completes a task using the design', icon: '💼' },
    { num: 3, title: 'Validate', desc: 'Sorin validates Vlad\'s work', icon: '✅' }
  ];
  
  return (
    <div className="min-h-screen pt-16 sm:pt-20 pb-20 lg:pb-12 px-3 sm:px-4" data-testid="simulation-page">
      <div className="max-w-4xl mx-auto">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-6 sm:mb-8">
          <h1 className="text-2xl sm:text-3xl md:text-4xl font-orbitron font-black flex items-center gap-3">
            <Play className="w-8 h-8 sm:w-10 sm:h-10 text-neon-cyan" />
            Token <span className="text-neon-cyan">{t('simulation')}</span>
          </h1>
          <p className="text-white/60 mt-2 text-sm sm:text-base">
            Experience the RLM economy flow between Andreea, Vlad, and Sorin
          </p>
        </motion.div>
        
        {loading ? (
          <div className="text-center text-white/50">{t('loading')}</div>
        ) : status?.status === 'not_initialized' ? (
          <CyberCard className="text-center py-8">
            <Users className="w-12 h-12 sm:w-16 sm:h-16 mx-auto mb-4 text-neon-purple" />
            <h3 className="text-lg sm:text-xl font-orbitron mb-2">Simulation Not Initialized</h3>
            <p className="text-white/60 mb-6 text-sm">Click below to create the simulation users and marketplace item</p>
            <CyberButton onClick={setupSimulation} data-testid="setup-simulation">
              <RefreshCw className="w-4 h-4 inline mr-2" /> Initialize Simulation
            </CyberButton>
          </CyberCard>
        ) : (
          <>
            {/* Users Status */}
            <div className="grid grid-cols-3 gap-2 sm:gap-4 mb-6">
              {['andreea', 'vlad', 'sorin'].map(name => (
                <CyberCard key={name} className="p-3 sm:p-4 text-center">
                  <div className="text-2xl sm:text-3xl mb-2">
                    {name === 'andreea' ? '👩‍🎨' : name === 'vlad' ? '👨‍💻' : '👨‍🔬'}
                  </div>
                  <h4 className="font-mono font-bold text-sm sm:text-base capitalize">{name}</h4>
                  <div className="text-[10px] sm:text-xs text-white/50 mb-2">
                    {status?.users?.[name]?.role}
                  </div>
                  <div className="font-mono text-neon-cyan text-sm sm:text-lg">
                    {status?.users?.[name]?.balance?.toFixed(0)} RLM
                  </div>
                  <div className="text-[10px] sm:text-xs text-white/50">
                    {status?.users?.[name]?.xp} XP
                  </div>
                </CyberCard>
              ))}
            </div>
            
            {/* Steps */}
            <CyberCard className="mb-6">
              <h3 className="font-orbitron font-bold mb-4 text-sm sm:text-base">Simulation Steps</h3>
              <div className="space-y-3">
                {steps.map(step => (
                  <div 
                    key={step.num}
                    className={`flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3 border ${
                      currentStep >= step.num ? 'border-neon-green/50 bg-neon-green/5' : 'border-white/10'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <span className="text-2xl">{step.icon}</span>
                      <div>
                        <div className="font-mono font-bold text-sm">Step {step.num}: {step.title}</div>
                        <div className="text-xs text-white/60">{step.desc}</div>
                      </div>
                    </div>
                    <CyberButton 
                      onClick={() => runStep(step.num)}
                      disabled={currentStep >= step.num}
                      variant={currentStep >= step.num ? 'ghost' : 'primary'}
                      className="w-full sm:w-auto text-xs sm:text-sm"
                      data-testid={`run-step-${step.num}`}
                    >
                      {currentStep >= step.num ? 'Completed' : 'Run Step'}
                    </CyberButton>
                  </div>
                ))}
              </div>
            </CyberCard>
            
            {/* Step Result */}
            {stepResult && (
              <CyberCard glow>
                <h3 className="font-orbitron font-bold mb-4 flex items-center gap-2 text-sm sm:text-base">
                  <ArrowRight className="w-5 h-5 text-neon-green" />
                  Step {stepResult.step} Result
                </h3>
                <div className="bg-black/30 p-4 border border-white/10 text-xs sm:text-sm font-mono overflow-x-auto">
                  <pre className="whitespace-pre-wrap">{JSON.stringify(stepResult, null, 2)}</pre>
                </div>
              </CyberCard>
            )}
            
            {/* Reset Button */}
            <div className="mt-6 text-center">
              <CyberButton variant="ghost" onClick={setupSimulation}>
                <RefreshCw className="w-4 h-4 inline mr-2" /> Reset Simulation
              </CyberButton>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default SimulationPage;
