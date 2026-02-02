import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { GraduationCap, Clock, Sparkles } from 'lucide-react';
import axios from 'axios';
import { API } from '../utils/api';
import { useAuth } from '../context/AuthContext';
import { useConfetti } from '../context/ConfettiContext';
import { useTranslation } from '../context/LanguageContext';
import { CyberCard, CyberButton } from '../components/common/CyberUI';

const CoursesPage = () => {
  const { user, refreshUser } = useAuth();
  const { triggerConfetti } = useConfetti();
  const t = useTranslation();
  const [courses, setCourses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [categoryFilter, setCategoryFilter] = useState('');
  
  useEffect(() => {
    axios.get(`${API}/courses`).then(res => setCourses(res.data.courses || [])).catch(console.error).finally(() => setLoading(false));
  }, []);
  
  const enrollInCourse = async (courseId) => {
    try {
      await axios.post(`${API}/courses/${courseId}/enroll`);
      triggerConfetti();
      alert('Enrolled successfully!');
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to enroll');
    }
  };
  
  const categories = ['tech', 'economics', 'civic', 'creative', 'basics'];
  const categoryColors = {
    tech: '#FF003C', economics: '#00FF88', civic: '#40C4FF', creative: '#E040FB', basics: '#FFD700'
  };
  
  const filteredCourses = categoryFilter 
    ? courses.filter(c => c.category === categoryFilter)
    : courses;
  
  return (
    <div className="min-h-screen pt-16 sm:pt-20 pb-20 lg:pb-12 px-3 sm:px-4" data-testid="courses-page">
      <div className="max-w-6xl mx-auto">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-6 sm:mb-8">
          <h1 className="text-2xl sm:text-3xl md:text-4xl font-orbitron font-black flex items-center gap-3">
            <GraduationCap className="w-8 h-8 sm:w-10 sm:h-10 text-neon-purple" />
            Learning <span className="text-neon-purple">Zone</span>
          </h1>
          <p className="text-white/60 mt-2 text-sm sm:text-base">Level up your skills and earn RLM rewards</p>
        </motion.div>
        
        {/* Category Filter */}
        <div className="flex flex-wrap gap-2 mb-4 sm:mb-6 overflow-x-auto pb-2">
          <button 
            onClick={() => setCategoryFilter('')}
            className={`px-3 py-1.5 text-xs border whitespace-nowrap ${!categoryFilter ? 'border-neon-cyan text-neon-cyan' : 'border-white/20 text-white/50'}`}
          >
            All
          </button>
          {categories.map(cat => (
            <button
              key={cat}
              onClick={() => setCategoryFilter(cat)}
              className="px-3 py-1.5 text-xs border transition-colors whitespace-nowrap capitalize"
              style={{ 
                borderColor: categoryFilter === cat ? categoryColors[cat] : 'rgba(255,255,255,0.2)',
                color: categoryFilter === cat ? categoryColors[cat] : 'rgba(255,255,255,0.5)'
              }}
            >
              {cat}
            </button>
          ))}
        </div>
        
        {/* Courses Grid */}
        {loading ? (
          <div className="text-center text-white/50">{t('loading')}</div>
        ) : (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4">
            {filteredCourses.map(course => (
              <CyberCard key={course.id} className="p-4">
                <div className="flex items-start justify-between mb-2 sm:mb-3">
                  <h4 className="font-mono font-bold text-sm sm:text-base flex-1">{course.title}</h4>
                  <span 
                    className="px-2 py-1 text-[10px] sm:text-xs border ml-2 capitalize"
                    style={{ borderColor: categoryColors[course.category], color: categoryColors[course.category] }}
                  >
                    {course.category}
                  </span>
                </div>
                
                <p className="text-xs sm:text-sm text-white/70 mb-3 sm:mb-4 line-clamp-2">{course.description}</p>
                
                <div className="flex flex-wrap gap-1.5 sm:gap-2 mb-3 sm:mb-4">
                  <span className="px-2 py-1 text-[10px] sm:text-xs bg-neon-cyan/10 text-neon-cyan border border-neon-cyan/30 flex items-center gap-1">
                    <Sparkles className="w-3 h-3" />
                    +{course.rlm_reward} RLM
                  </span>
                  <span className="px-2 py-1 text-[10px] sm:text-xs bg-neon-purple/10 text-neon-purple border border-neon-purple/30">
                    +{course.xp_reward} XP
                  </span>
                  <span className="px-2 py-1 text-[10px] sm:text-xs bg-white/5 text-white/50 border border-white/10 flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {course.duration_hours}h
                  </span>
                </div>
                
                <div className="text-[10px] sm:text-xs text-white/40 mb-3">
                  Difficulty: <span className="capitalize text-white/60">{course.difficulty}</span>
                </div>
                
                <CyberButton 
                  className="w-full text-xs sm:text-sm" 
                  onClick={() => enrollInCourse(course.id)}
                  data-testid={`enroll-course-${course.id}`}
                >
                  {t('enroll')}
                </CyberButton>
              </CyberCard>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default CoursesPage;
