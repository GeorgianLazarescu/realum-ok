import React, { useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { Globe } from 'lucide-react';
import { useLanguage } from '../context/LanguageContext';

const LanguageSelector = () => {
  const { language, changeLanguage } = useLanguage();
  const [open, setOpen] = useState(false);
  
  const languages = [
    { code: 'en', name: 'English', flag: '🇬🇧' },
    { code: 'ro', name: 'Română', flag: '🇷🇴' },
    { code: 'es', name: 'Español', flag: '🇪🇸' }
  ];
  
  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 px-3 py-2 border border-white/20 hover:border-neon-cyan/50 transition-colors"
        data-testid="language-selector"
      >
        <Globe className="w-4 h-4" />
        <span className="text-sm">{languages.find(l => l.code === language)?.flag}</span>
      </button>
      
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="absolute top-full right-0 mt-2 bg-black/90 border border-white/20 z-50"
          >
            {languages.map(lang => (
              <button
                key={lang.code}
                onClick={() => { changeLanguage(lang.code); setOpen(false); }}
                className={`w-full px-4 py-2 text-left text-sm hover:bg-white/10 flex items-center gap-2 ${language === lang.code ? 'text-neon-cyan' : ''}`}
              >
                <span>{lang.flag}</span>
                <span>{lang.name}</span>
              </button>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default LanguageSelector;
