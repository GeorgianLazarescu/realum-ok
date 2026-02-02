import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { ShoppingBag, Download, Star } from 'lucide-react';
import axios from 'axios';
import { API } from '../utils/api';
import { useAuth } from '../context/AuthContext';
import { useConfetti } from '../context/ConfettiContext';
import { useTranslation } from '../context/LanguageContext';
import { CyberCard, CyberButton } from '../components/common/CyberUI';

const MarketplacePage = () => {
  const { user, refreshUser } = useAuth();
  const { triggerConfetti } = useConfetti();
  const t = useTranslation();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [categoryFilter, setCategoryFilter] = useState('');
  
  useEffect(() => {
    axios.get(`${API}/marketplace`).then(res => setItems(res.data.items || [])).catch(console.error).finally(() => setLoading(false));
  }, []);
  
  const purchaseItem = async (itemId) => {
    try {
      const res = await axios.post(`${API}/marketplace/${itemId}/purchase`);
      triggerConfetti();
      refreshUser();
      alert(`Purchased! Paid ${res.data.amount_paid} RLM (${res.data.amount_burned} burned)`);
      // Refresh items
      axios.get(`${API}/marketplace`).then(res => setItems(res.data.items || []));
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to purchase');
    }
  };
  
  const categories = ['design', 'code', 'document', 'template', 'course', 'service'];
  const categoryColors = {
    design: '#E040FB', code: '#00FF88', document: '#40C4FF', template: '#FFD700', course: '#9D4EDD', service: '#FF6B35'
  };
  
  const filteredItems = categoryFilter 
    ? items.filter(i => i.category === categoryFilter)
    : items;
  
  return (
    <div className="min-h-screen pt-16 sm:pt-20 pb-20 lg:pb-12 px-3 sm:px-4" data-testid="marketplace-page">
      <div className="max-w-6xl mx-auto">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-6 sm:mb-8">
          <h1 className="text-2xl sm:text-3xl md:text-4xl font-orbitron font-black flex items-center gap-3">
            <ShoppingBag className="w-8 h-8 sm:w-10 sm:h-10 text-neon-cyan" />
            {t('marketplace')}
          </h1>
          <p className="text-white/60 mt-2 text-sm sm:text-base">Buy and sell digital resources with RLM</p>
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
        
        {/* Items Grid */}
        {loading ? (
          <div className="text-center text-white/50">{t('loading')}</div>
        ) : (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4">
            {filteredItems.map(item => (
              <CyberCard key={item.id} className="p-4">
                <div className="flex items-start justify-between mb-2 sm:mb-3">
                  <h4 className="font-mono font-bold text-sm sm:text-base flex-1">{item.title}</h4>
                  <span 
                    className="px-2 py-1 text-[10px] sm:text-xs border ml-2 capitalize"
                    style={{ borderColor: categoryColors[item.category], color: categoryColors[item.category] }}
                  >
                    {item.category}
                  </span>
                </div>
                
                <p className="text-xs sm:text-sm text-white/70 mb-3 line-clamp-2">{item.description}</p>
                
                <div className="flex items-center justify-between mb-3 text-xs text-white/50">
                  <span>by {item.seller_name}</span>
                  <div className="flex items-center gap-2">
                    <span className="flex items-center gap-1"><Download className="w-3 h-3" /> {item.downloads}</span>
                    {item.rating > 0 && <span className="flex items-center gap-1"><Star className="w-3 h-3 text-neon-yellow" /> {item.rating}</span>}
                  </div>
                </div>
                
                <div className="flex items-center justify-between">
                  <span className="font-mono text-lg sm:text-xl text-neon-cyan">{item.price_rlm} RLM</span>
                  <CyberButton 
                    onClick={() => purchaseItem(item.id)}
                    disabled={item.seller_id === user?.id || user?.realum_balance < item.price_rlm}
                    className="text-xs sm:text-sm"
                    data-testid={`purchase-item-${item.id}`}
                  >
                    {item.seller_id === user?.id ? 'Your Item' : t('purchase')}
                  </CyberButton>
                </div>
              </CyberCard>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default MarketplacePage;
