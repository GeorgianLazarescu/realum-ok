import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronRight, Globe, Sparkles, Users, Coins, GraduationCap, Shield } from 'lucide-react';
import { CyberButton } from './common/CyberUI';

const STORY_SLIDES = [
  {
    id: 1,
    title: "Welcome to REALUM",
    subtitle: "A New World Awaits",
    content: "In a world where physical boundaries no longer limit human potential, a new civilization has emerged...",
    icon: Globe,
    color: "#00F0FF",
    background: "linear-gradient(135deg, #0a0a2e 0%, #1a1a4e 100%)"
  },
  {
    id: 2,
    title: "Your Digital Self",
    subtitle: "Create Your Identity",
    content: "Here, you are more than a username. You are a citizen with dreams, relationships, and a story to write.",
    icon: Users,
    color: "#9D4EDD",
    background: "linear-gradient(135deg, #1a0a2e 0%, #2a1a4e 100%)"
  },
  {
    id: 3,
    title: "Learn & Grow",
    subtitle: "Knowledge is Currency",
    content: "In REALUM, education isn't just learning—it's earning. Every skill you master opens new doors.",
    icon: GraduationCap,
    color: "#00FF88",
    background: "linear-gradient(135deg, #0a2e1a 0%, #1a4e2a 100%)"
  },
  {
    id: 4,
    title: "Build Wealth",
    subtitle: "RLM Tokens",
    content: "Your contributions have real value. Earn RLM tokens through work, creativity, and community participation.",
    icon: Coins,
    color: "#FFD700",
    background: "linear-gradient(135deg, #2e2a0a 0%, #4e3a1a 100%)"
  },
  {
    id: 5,
    title: "Shape the Future",
    subtitle: "Democratic Governance",
    content: "This world belongs to its citizens. Vote on decisions, propose changes, and govern together.",
    icon: Shield,
    color: "#40C4FF",
    background: "linear-gradient(135deg, #0a1a2e 0%, #1a2a4e 100%)"
  },
  {
    id: 6,
    title: "Your Journey Begins",
    subtitle: "Enter the Metaverse",
    content: "The 3D Earth awaits. Six zones, infinite possibilities. Your story starts now.",
    icon: Sparkles,
    color: "#FF003C",
    background: "linear-gradient(135deg, #2e0a0a 0%, #4e1a1a 100%)"
  }
];

const StorytellingIntro = ({ onComplete, onSkip }) => {
  const [currentSlide, setCurrentSlide] = useState(0);
  const [isAnimating, setIsAnimating] = useState(false);

  const slide = STORY_SLIDES[currentSlide];
  const Icon = slide.icon;
  const isLastSlide = currentSlide === STORY_SLIDES.length - 1;

  const nextSlide = () => {
    if (isAnimating) return;
    
    if (isLastSlide) {
      onComplete();
    } else {
      setIsAnimating(true);
      setCurrentSlide(prev => prev + 1);
      setTimeout(() => setIsAnimating(false), 500);
    }
  };

  // Auto-advance with keyboard
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Enter' || e.key === ' ' || e.key === 'ArrowRight') {
        nextSlide();
      } else if (e.key === 'Escape') {
        onSkip();
      }
    };
    
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [currentSlide, isAnimating]);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-[200] flex items-center justify-center"
      style={{ background: slide.background }}
    >
      {/* Background particles */}
      <div className="absolute inset-0 overflow-hidden">
        {[...Array(30)].map((_, i) => (
          <motion.div
            key={i}
            className="absolute w-1 h-1 rounded-full"
            style={{ backgroundColor: slide.color, opacity: 0.3 }}
            initial={{ 
              x: Math.random() * window.innerWidth,
              y: Math.random() * window.innerHeight 
            }}
            animate={{ 
              y: [null, Math.random() * -500],
              opacity: [0.3, 0]
            }}
            transition={{ 
              duration: Math.random() * 5 + 3,
              repeat: Infinity,
              ease: "linear"
            }}
          />
        ))}
      </div>

      {/* Skip button */}
      <button
        onClick={onSkip}
        className="absolute top-6 right-6 px-4 py-2 text-sm text-white/50 hover:text-white transition-colors"
      >
        Skip Intro
      </button>

      {/* Content */}
      <div className="relative max-w-2xl mx-auto px-6 text-center">
        <AnimatePresence mode="wait">
          <motion.div
            key={currentSlide}
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -30 }}
            transition={{ duration: 0.5 }}
          >
            {/* Icon */}
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ delay: 0.2, type: "spring" }}
              className="w-24 h-24 mx-auto mb-8 rounded-full flex items-center justify-center"
              style={{ 
                backgroundColor: `${slide.color}20`,
                border: `2px solid ${slide.color}50`
              }}
            >
              <Icon className="w-12 h-12" style={{ color: slide.color }} />
            </motion.div>

            {/* Text */}
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.3 }}
              className="text-sm uppercase tracking-widest mb-2"
              style={{ color: slide.color }}
            >
              {slide.subtitle}
            </motion.p>

            <motion.h1
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.4 }}
              className="text-4xl md:text-5xl font-orbitron font-bold text-white mb-6"
            >
              {slide.title}
            </motion.h1>

            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.5 }}
              className="text-lg text-white/70 leading-relaxed mb-12"
            >
              {slide.content}
            </motion.p>

            {/* Progress dots */}
            <div className="flex justify-center gap-2 mb-8">
              {STORY_SLIDES.map((_, index) => (
                <div
                  key={index}
                  className="w-2 h-2 rounded-full transition-all duration-300"
                  style={{
                    backgroundColor: index === currentSlide ? slide.color : 'rgba(255,255,255,0.2)',
                    transform: index === currentSlide ? 'scale(1.5)' : 'scale(1)'
                  }}
                />
              ))}
            </div>

            {/* Continue button */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.6 }}
            >
              <CyberButton
                onClick={nextSlide}
                className="px-8 py-3 text-lg"
                style={{ borderColor: slide.color, color: slide.color }}
              >
                {isLastSlide ? 'Enter REALUM' : 'Continue'}
                <ChevronRight className="w-5 h-5 ml-2 inline" />
              </CyberButton>
            </motion.div>

            <p className="text-xs text-white/30 mt-4">
              Press Enter or Space to continue • Esc to skip
            </p>
          </motion.div>
        </AnimatePresence>
      </div>
    </motion.div>
  );
};

export default StorytellingIntro;
