import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Building2, Plus, Users } from 'lucide-react';
import axios from 'axios';
import { API } from '../utils/api';
import { useAuth } from '../context/AuthContext';
import { useTranslation } from '../context/LanguageContext';
import { CyberCard, CyberButton } from '../components/common/CyberUI';

const ProjectsPage = () => {
  const { user } = useAuth();
  const t = useTranslation();
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newProject, setNewProject] = useState({ title: '', description: '', category: 'tech', budget_rlm: 100 });
  
  const fetchProjects = () => {
    axios.get(`${API}/projects`).then(res => setProjects(res.data.projects || [])).catch(console.error).finally(() => setLoading(false));
  };
  
  useEffect(() => { fetchProjects(); }, []);
  
  const createProject = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API}/projects`, newProject);
      setNewProject({ title: '', description: '', category: 'tech', budget_rlm: 100 });
      setShowCreateForm(false);
      fetchProjects();
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to create');
    }
  };
  
  const joinProject = async (projectId) => {
    try {
      await axios.post(`${API}/projects/${projectId}/join`);
      fetchProjects();
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to join');
    }
  };
  
  const categories = ['tech', 'creative', 'education', 'commerce', 'civic'];
  const categoryColors = {
    tech: '#FF003C', creative: '#E040FB', education: '#9D4EDD', commerce: '#FF6B35', civic: '#40C4FF'
  };
  
  const canCreate = user?.role === 'creator' || user?.role === 'partner';
  
  return (
    <div className="min-h-screen pt-16 sm:pt-20 pb-20 lg:pb-12 px-3 sm:px-4" data-testid="projects-page">
      <div className="max-w-6xl mx-auto">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-6 sm:mb-8">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h1 className="text-2xl sm:text-3xl md:text-4xl font-orbitron font-black flex items-center gap-3">
                <Building2 className="w-8 h-8 sm:w-10 sm:h-10 text-neon-green" />
                {t('projects')}
              </h1>
              <p className="text-white/60 mt-2 text-sm sm:text-base">Collaborate on community initiatives</p>
            </div>
            {canCreate && (
              <CyberButton onClick={() => setShowCreateForm(!showCreateForm)} className="w-full sm:w-auto">
                <Plus className="w-4 h-4 inline mr-2" /> New Project
              </CyberButton>
            )}
          </div>
        </motion.div>
        
        {/* Create Form */}
        {showCreateForm && (
          <CyberCard className="mb-6" glow>
            <h3 className="font-orbitron font-bold mb-4 text-sm sm:text-base">Create Project</h3>
            <form onSubmit={createProject} className="space-y-4">
              <div>
                <label className="text-xs uppercase tracking-wider text-white/50 mb-1 block">Title</label>
                <input
                  type="text"
                  value={newProject.title}
                  onChange={(e) => setNewProject({...newProject, title: e.target.value})}
                  required
                  className="w-full bg-black/50 border border-white/20 px-4 py-3 text-white focus:border-neon-cyan focus:outline-none text-sm"
                />
              </div>
              <div>
                <label className="text-xs uppercase tracking-wider text-white/50 mb-1 block">Description</label>
                <textarea
                  value={newProject.description}
                  onChange={(e) => setNewProject({...newProject, description: e.target.value})}
                  required
                  rows={3}
                  className="w-full bg-black/50 border border-white/20 px-4 py-3 text-white focus:border-neon-cyan focus:outline-none text-sm resize-none"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs uppercase tracking-wider text-white/50 mb-1 block">Category</label>
                  <select
                    value={newProject.category}
                    onChange={(e) => setNewProject({...newProject, category: e.target.value})}
                    className="w-full bg-black/50 border border-white/20 px-4 py-3 text-white focus:border-neon-cyan focus:outline-none text-sm"
                  >
                    {categories.map(cat => (
                      <option key={cat} value={cat}>{cat}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-xs uppercase tracking-wider text-white/50 mb-1 block">Budget (RLM)</label>
                  <input
                    type="number"
                    value={newProject.budget_rlm}
                    onChange={(e) => setNewProject({...newProject, budget_rlm: parseFloat(e.target.value)})}
                    required
                    min="10"
                    className="w-full bg-black/50 border border-white/20 px-4 py-3 text-white focus:border-neon-cyan focus:outline-none text-sm"
                  />
                </div>
              </div>
              <div className="flex gap-2">
                <CyberButton type="submit" className="flex-1">{t('create')}</CyberButton>
                <CyberButton type="button" variant="ghost" onClick={() => setShowCreateForm(false)}>{t('cancel')}</CyberButton>
              </div>
            </form>
          </CyberCard>
        )}
        
        {/* Projects Grid */}
        {loading ? (
          <div className="text-center text-white/50">{t('loading')}</div>
        ) : (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4">
            {projects.map(project => {
              const isParticipant = project.participants?.includes(user?.id);
              return (
                <CyberCard key={project.id} className="p-4">
                  <div className="flex items-start justify-between mb-2 sm:mb-3">
                    <h4 className="font-mono font-bold text-sm sm:text-base flex-1">{project.title}</h4>
                    <span 
                      className="px-2 py-1 text-[10px] sm:text-xs border ml-2 capitalize"
                      style={{ borderColor: categoryColors[project.category], color: categoryColors[project.category] }}
                    >
                      {project.category}
                    </span>
                  </div>
                  
                  <p className="text-xs sm:text-sm text-white/70 mb-3 line-clamp-2">{project.description}</p>
                  
                  <div className="flex items-center justify-between mb-3 text-xs text-white/50">
                    <span>by {project.creator_name}</span>
                    <span className="flex items-center gap-1">
                      <Users className="w-3 h-3" /> {project.participants?.length || 0}
                    </span>
                  </div>
                  
                  {/* Progress Bar */}
                  <div className="mb-3">
                    <div className="flex justify-between text-[10px] mb-1">
                      <span className="text-white/50">Progress</span>
                      <span className="text-neon-green">{project.progress?.toFixed(0)}%</span>
                    </div>
                    <div className="h-1.5 bg-white/10 overflow-hidden">
                      <div 
                        className="h-full bg-neon-green transition-all" 
                        style={{ width: `${project.progress || 0}%` }} 
                      />
                    </div>
                  </div>
                  
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-sm text-neon-cyan">{project.budget_rlm} RLM</span>
                    <CyberButton 
                      onClick={() => joinProject(project.id)}
                      disabled={isParticipant}
                      variant={isParticipant ? 'ghost' : 'primary'}
                      className="text-xs sm:text-sm"
                      data-testid={`join-project-${project.id}`}
                    >
                      {isParticipant ? 'Joined' : t('join')}
                    </CyberButton>
                  </div>
                </CyberCard>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

export default ProjectsPage;
