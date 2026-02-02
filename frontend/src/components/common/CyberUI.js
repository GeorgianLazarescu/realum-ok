import React from 'react';
import { motion } from 'framer-motion';

export const CyberCard = ({ children, className = "", glow = false, ...props }) => (
  <motion.div
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    className={`relative bg-black/60 backdrop-blur-xl border border-white/10 p-4 sm:p-6 overflow-hidden ${glow ? 'shadow-[0_0_30px_rgba(0,240,255,0.15)]' : ''} ${className}`}
    {...props}
  >
    <div className="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-neon-cyan/50 to-transparent" />
    {children}
  </motion.div>
);

export const CyberButton = ({ children, variant = "primary", className = "", disabled = false, ...props }) => {
  const variants = {
    primary: "bg-neon-cyan/10 border-neon-cyan text-neon-cyan hover:bg-neon-cyan/20 hover:shadow-[0_0_20px_rgba(0,240,255,0.4)]",
    danger: "bg-neon-red/10 border-neon-red text-neon-red hover:bg-neon-red/20",
    success: "bg-neon-green/10 border-neon-green text-neon-green hover:bg-neon-green/20",
    ghost: "bg-transparent border-white/20 text-white hover:border-white/40"
  };
  
  return (
    <motion.button
      whileHover={{ scale: disabled ? 1 : 1.02 }}
      whileTap={{ scale: disabled ? 1 : 0.98 }}
      disabled={disabled}
      className={`px-4 sm:px-6 py-2 sm:py-3 border font-mono uppercase tracking-wider text-xs sm:text-sm transition-all duration-300 ${variants[variant]} ${disabled ? 'opacity-50 cursor-not-allowed' : ''} ${className}`}
      {...props}
    >
      {children}
    </motion.button>
  );
};
