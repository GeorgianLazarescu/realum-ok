import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { X, ChevronRight } from 'lucide-react';
import axios from 'axios';
import { API } from '../../utils/api';
import { useTranslation } from '../../context/LanguageContext';
import { CyberButton } from '../../components/common/CyberUI';

const IsometricZone = ({ zone, onClick, selected, index }) => {
  const [hovered, setHovered] = useState(false);
  const color = zone.color || '#00F0FF';
  
  const zoneIcons = {
    hub: '🏛️', marketplace: '🛒', learning: '📚', dao: '⚖️',
    'tech-district': '💻', residential: '🏘️', industrial: '🏭', cultural: '🎭'
  };
  
  const row = Math.floor(index / 4);
  const col = index % 4;
  const isoX = (col - row) * 100 + 300;
  const isoY = (col + row) * 50 + 80;
  
  return (
    <motion.div
      initial={{ opacity: 0, y: 50 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1 }}
      className="absolute cursor-pointer"
      style={{ left: `${isoX}px`, top: `${isoY}px`, zIndex: 100 - row * 10 + col }}
      onClick={onClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <motion.div
        animate={{ scale: hovered || selected ? 1.1 : 1, y: hovered ? -5 : 0 }}
        className="relative"
      >
        <div 
          className="w-24 sm:w-32 h-12 sm:h-16 relative"
          style={{
            background: `linear-gradient(135deg, ${color}40 0%, ${color}20 50%, ${color}10 100%)`,
            clipPath: 'polygon(50% 0%, 100% 50%, 50% 100%, 0% 50%)',
            boxShadow: selected ? `0 0 30px ${color}` : hovered ? `0 0 20px ${color}60` : 'none'
          }}
        >
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="text-2xl sm:text-3xl transform -translate-y-2">{zoneIcons[zone.id] || '🏢'}</span>
          </div>
        </div>
        
        <div 
          className={`absolute -bottom-6 sm:-bottom-8 left-1/2 -translate-x-1/2 whitespace-nowrap px-2 py-1 text-[10px] sm:text-xs font-mono transition-all ${
            hovered || selected ? 'bg-black/90' : 'bg-black/60'
          }`}
          style={{ color: color, border: `1px solid ${color}40` }}
        >
          {zone.name}
        </div>
        
        <div 
          className="absolute -top-2 -right-2 px-1.5 sm:px-2 py-0.5 text-[10px] sm:text-xs font-mono bg-black border"
          style={{ borderColor: color, color }}
        >
          {zone.jobs_count}
        </div>
      </motion.div>
    </motion.div>
  );
};

const MetaversePage = () => {
  const t = useTranslation();
  const navigate = useNavigate();
  const [zones, setZones] = useState([]);
  const [projects, setProjects] = useState([]);
  const [selectedZone, setSelectedZone] = useState(null);
  
  useEffect(() => {
    axios.get(`${API}/city/zones`).then(res => setZones(res.data)).catch(console.error);
    axios.get(`${API}/projects`).then(res => setProjects(res.data.projects || [])).catch(console.error);
  }, []);
  
  return (
    <div className="min-h-screen pt-16" data-testid="metaverse-page">
      <div className="h-[calc(100vh-64px)] relative overflow-hidden bg-[#0a0a1a]">
        <div className="absolute inset-0 bg-cyber-grid bg-[length:40px_40px] opacity-20" />
        <div className="absolute inset-0 bg-hero-glow opacity-30" />
        
        {/* Header */}
        <div className="absolute top-4 left-4 right-4 z-20">
          <h1 className="text-xl sm:text-2xl md:text-3xl font-orbitron font-black text-white">
            REALUM <span className="text-neon-cyan neon-text">{t('metaverse')}</span>
          </h1>
          <p className="text-xs sm:text-sm text-white/60">Explore the city • Click zones to view details</p>
        </div>
        
        {/* Isometric Map Container - Scrollable on mobile */}
        <div className="absolute inset-0 pt-20 overflow-auto">
          <div className="relative min-w-[700px] min-h-[500px] w-full h-full">
            {zones.map((zone, index) => (
              <IsometricZone
                key={zone.id}
                zone={zone}
                index={index}
                onClick={() => setSelectedZone(zone)}
                selected={selectedZone?.id === zone.id}
              />
            ))}
          </div>
        </div>
        
        {/* Selected Zone Panel */}
        <AnimatePresence>
          {selectedZone && (
            <motion.div
              initial={{ opacity: 0, x: 100 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 100 }}
              className="absolute bottom-20 sm:bottom-4 right-2 sm:right-4 w-[calc(100%-1rem)] sm:w-80 bg-black/95 border p-3 sm:p-4 z-30"
              style={{ borderColor: selectedZone.color }}
            >
              <div className="flex justify-between items-start mb-3">
                <div>
                  <h3 className="font-orbitron font-bold text-base sm:text-lg" style={{ color: selectedZone.color }}>
                    {selectedZone.name}
                  </h3>
                  <span className="text-[10px] sm:text-xs text-white/50 uppercase">{selectedZone.type} zone</span>
                </div>
                <button onClick={() => setSelectedZone(null)} className="text-white/50 hover:text-white p-1">
                  <X className="w-5 h-5" />
                </button>
              </div>
              
              <p className="text-xs sm:text-sm text-white/70 mb-3 sm:mb-4">{selectedZone.description}</p>
              
              <div className="grid grid-cols-2 gap-2 mb-3 sm:mb-4">
                <div className="p-2 bg-white/5 border border-white/10">
                  <div className="text-[10px] sm:text-xs text-white/50">Jobs</div>
                  <div className="font-mono text-sm sm:text-lg" style={{ color: selectedZone.color }}>{selectedZone.jobs_count}</div>
                </div>
                <div className="p-2 bg-white/5 border border-white/10">
                  <div className="text-[10px] sm:text-xs text-white/50">Buildings</div>
                  <div className="font-mono text-sm sm:text-lg" style={{ color: selectedZone.color }}>{selectedZone.buildings?.length || 0}</div>
                </div>
              </div>
              
              <CyberButton 
                className="w-full text-xs sm:text-sm"
                onClick={() => navigate(`/jobs?zone=${selectedZone.id}`)}
              >
                Explore Jobs <ChevronRight className="w-4 h-4 inline ml-1" />
              </CyberButton>
            </motion.div>
          )}
        </AnimatePresence>
        
        {/* Bottom Stats */}
        <div className="absolute bottom-20 sm:bottom-4 left-2 sm:left-4 flex gap-2 sm:gap-3">
          <div className="bg-black/80 border border-white/20 px-2 sm:px-3 py-1.5 sm:py-2 text-[10px] sm:text-xs">
            <span className="text-white/50">Zones:</span>{' '}
            <span className="text-neon-cyan font-mono">{zones.length}</span>
          </div>
          <div className="bg-black/80 border border-white/20 px-2 sm:px-3 py-1.5 sm:py-2 text-[10px] sm:text-xs">
            <span className="text-white/50">Projects:</span>{' '}
            <span className="text-neon-purple font-mono">{projects.length}</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MetaversePage;
