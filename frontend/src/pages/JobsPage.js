import React, { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Clock } from 'lucide-react';
import axios from 'axios';
import { API } from '../../utils/api';
import { useAuth } from '../../context/AuthContext';
import { useConfetti } from '../../context/ConfettiContext';
import { useTranslation } from '../../context/LanguageContext';
import { CyberCard, CyberButton } from '../../components/common/CyberUI';

const JobsPage = () => {
  const { user, refreshUser } = useAuth();
  const { triggerConfetti } = useConfetti();
  const t = useTranslation();
  const location = useLocation();
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeJobs, setActiveJobs] = useState([]);
  const [filter, setFilter] = useState(new URLSearchParams(location.search).get('zone') || '');
  
  const fetchJobs = async () => {
    try {
      const params = filter ? `?zone=${filter}` : '';
      const [jobsRes, activeRes] = await Promise.all([
        axios.get(`${API}/jobs${params}`),
        axios.get(`${API}/jobs/active`)
      ]);
      setJobs(jobsRes.data);
      setActiveJobs(activeRes.data.active_jobs || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };
  
  useEffect(() => { fetchJobs(); }, [filter]);
  
  const applyForJob = async (jobId) => {
    try {
      await axios.post(`${API}/jobs/${jobId}/apply`);
      fetchJobs();
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to apply');
    }
  };
  
  const completeJob = async (jobId) => {
    try {
      const res = await axios.post(`${API}/jobs/${jobId}/complete`);
      triggerConfetti();
      refreshUser();
      fetchJobs();
      alert(`Completed! +${res.data.reward} RLM, +${res.data.xp_gained} XP`);
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to complete');
    }
  };
  
  const zoneColors = {
    hub: '#FFD700', marketplace: '#FF6B35', learning: '#9D4EDD', dao: '#40C4FF',
    'tech-district': '#FF003C', residential: '#00FF88', industrial: '#F9F871', cultural: '#E040FB'
  };
  
  return (
    <div className="min-h-screen pt-16 sm:pt-20 pb-20 lg:pb-12 px-3 sm:px-4" data-testid="jobs-page">
      <div className="max-w-6xl mx-auto">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-6 sm:mb-8">
          <h1 className="text-2xl sm:text-3xl md:text-4xl font-orbitron font-black">
            {t('jobs')} <span className="text-neon-cyan">BOARD</span>
          </h1>
          <p className="text-white/60 mt-2 text-sm sm:text-base">Find tasks, earn RLM, level up your skills</p>
        </motion.div>
        
        {/* Active Jobs */}
        {activeJobs.length > 0 && (
          <CyberCard className="mb-4 sm:mb-6" glow>
            <h3 className="font-orbitron font-bold mb-3 sm:mb-4 flex items-center gap-2 text-sm sm:text-base">
              <Clock className="w-4 h-4 sm:w-5 sm:h-5 text-neon-yellow" />
              Active Jobs
            </h3>
            <div className="space-y-2 sm:space-y-3">
              {activeJobs.map(aj => (
                <div key={aj.id} className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 sm:gap-0 p-3 bg-black/30 border border-neon-yellow/30">
                  <div>
                    <div className="font-mono text-sm sm:text-base">{aj.job?.title}</div>
                    <div className="text-xs text-white/50">{aj.job?.company}</div>
                  </div>
                  <CyberButton variant="success" onClick={() => completeJob(aj.job_id)} className="w-full sm:w-auto">
                    {t('complete')}
                  </CyberButton>
                </div>
              ))}
            </div>
          </CyberCard>
        )}
        
        {/* Zone Filter */}
        <div className="flex flex-wrap gap-2 mb-4 sm:mb-6 overflow-x-auto pb-2">
          <button 
            onClick={() => setFilter('')}
            className={`px-3 py-1.5 text-xs border whitespace-nowrap ${!filter ? 'border-neon-cyan text-neon-cyan' : 'border-white/20 text-white/50'}`}
          >
            All
          </button>
          {Object.entries(zoneColors).map(([zone, color]) => (
            <button
              key={zone}
              onClick={() => setFilter(zone)}
              className="px-3 py-1.5 text-xs border transition-colors whitespace-nowrap"
              style={{ 
                borderColor: filter === zone ? color : 'rgba(255,255,255,0.2)',
                color: filter === zone ? color : 'rgba(255,255,255,0.5)'
              }}
            >
              {zone.replace('-', ' ')}
            </button>
          ))}
        </div>
        
        {/* Jobs Grid */}
        {loading ? (
          <div className="text-center text-white/50">{t('loading')}</div>
        ) : (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4">
            {jobs.map(job => (
              <CyberCard key={job.id} className="p-4">
                <div className="flex items-start justify-between mb-2 sm:mb-3">
                  <div className="flex-1 min-w-0">
                    <h4 className="font-mono font-bold text-sm sm:text-base truncate">{job.title}</h4>
                    <p className="text-xs text-white/50 truncate">{job.company}</p>
                  </div>
                  <span 
                    className="px-2 py-1 text-[10px] sm:text-xs border ml-2 flex-shrink-0"
                    style={{ borderColor: zoneColors[job.zone], color: zoneColors[job.zone] }}
                  >
                    {job.zone}
                  </span>
                </div>
                
                <p className="text-xs sm:text-sm text-white/70 mb-3 sm:mb-4 line-clamp-2">{job.description}</p>
                
                <div className="flex flex-wrap gap-1.5 sm:gap-2 mb-3 sm:mb-4">
                  <span className="px-2 py-1 text-[10px] sm:text-xs bg-neon-cyan/10 text-neon-cyan border border-neon-cyan/30">
                    +{job.reward} RLM
                  </span>
                  <span className="px-2 py-1 text-[10px] sm:text-xs bg-neon-purple/10 text-neon-purple border border-neon-purple/30">
                    +{job.xp_reward} XP
                  </span>
                  <span className="px-2 py-1 text-[10px] sm:text-xs bg-white/5 text-white/50 border border-white/10">
                    {job.duration_minutes}m
                  </span>
                </div>
                
                {job.required_role && (
                  <div className="text-[10px] sm:text-xs text-white/40 mb-2">Requires: {job.required_role}</div>
                )}
                
                <CyberButton 
                  className="w-full text-xs sm:text-sm" 
                  onClick={() => applyForJob(job.id)}
                  disabled={job.required_level > user?.level || (job.required_role && job.required_role !== user?.role)}
                  data-testid={`apply-job-${job.id}`}
                >
                  {job.required_level > user?.level ? `Req. Lv.${job.required_level}` : t('apply')}
                </CyberButton>
              </CyberCard>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default JobsPage;
