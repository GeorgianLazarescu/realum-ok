import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { 
  Search, Filter, ShoppingCart, Lock, Clock, Star,
  Sparkles, Crown, Zap, Shield, Gem, Gift
} from 'lucide-react';
import { CyberCard, CyberButton } from '../components/common/CyberUI';
import { toast } from 'sonner';

// Fake marketplace items with blur preview
const MARKETPLACE_ITEMS = [
  {
    id: 1,
    name: "Premium Avatar Skin",
    category: "cosmetics",
    price: 500,
    icon: Crown,
    color: "#FFD700",
    status: "coming_soon",
    description: "Exclusive golden avatar appearance",
    rarity: "legendary"
  },
  {
    id: 2,
    name: "XP Booster Pack",
    category: "boosters",
    price: 150,
    icon: Zap,
    color: "#00FF88",
    status: "coming_soon",
    description: "2x experience points for 24 hours",
    rarity: "rare"
  },
  {
    id: 3,
    name: "Virtual Land Plot",
    category: "real_estate",
    price: 2500,
    icon: Shield,
    color: "#40C4FF",
    status: "coming_soon",
    description: "Own your piece of the metaverse",
    rarity: "epic"
  },
  {
    id: 4,
    name: "Rare NFT Badge",
    category: "collectibles",
    price: 1000,
    icon: Gem,
    color: "#9D4EDD",
    status: "coming_soon",
    description: "Limited edition collector's badge",
    rarity: "legendary"
  },
  {
    id: 5,
    name: "Skill Accelerator",
    category: "education",
    price: 300,
    icon: Sparkles,
    color: "#FF003C",
    status: "coming_soon",
    description: "Learn skills 50% faster",
    rarity: "rare"
  },
  {
    id: 6,
    name: "Mystery Box",
    category: "mystery",
    price: 100,
    icon: Gift,
    color: "#FF6B35",
    status: "coming_soon",
    description: "Contains random valuable items",
    rarity: "common"
  },
  {
    id: 7,
    name: "VIP Zone Access",
    category: "access",
    price: 750,
    icon: Crown,
    color: "#E040FB",
    status: "coming_soon",
    description: "Exclusive access to VIP areas",
    rarity: "epic"
  },
  {
    id: 8,
    name: "Custom Emote Pack",
    category: "cosmetics",
    price: 200,
    icon: Star,
    color: "#FFD700",
    status: "coming_soon",
    description: "10 unique animated emotes",
    rarity: "rare"
  },
];

const CATEGORIES = [
  { id: 'all', name: 'All Items', icon: ShoppingCart },
  { id: 'cosmetics', name: 'Cosmetics', icon: Crown },
  { id: 'boosters', name: 'Boosters', icon: Zap },
  { id: 'real_estate', name: 'Real Estate', icon: Shield },
  { id: 'collectibles', name: 'Collectibles', icon: Gem },
  { id: 'education', name: 'Education', icon: Sparkles },
];

const rarityColors = {
  common: { bg: 'bg-gray-500/20', border: 'border-gray-500/50', text: 'text-gray-400' },
  rare: { bg: 'bg-blue-500/20', border: 'border-blue-500/50', text: 'text-blue-400' },
  epic: { bg: 'bg-purple-500/20', border: 'border-purple-500/50', text: 'text-purple-400' },
  legendary: { bg: 'bg-yellow-500/20', border: 'border-yellow-500/50', text: 'text-yellow-400' },
};

const MarketplacePage = () => {
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [cartItems, setCartItems] = useState([]);

  const filteredItems = MARKETPLACE_ITEMS.filter(item => {
    const matchesCategory = selectedCategory === 'all' || item.category === selectedCategory;
    const matchesSearch = item.name.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  const handleNotifyMe = (item) => {
    toast.success('Notification set!', {
      description: `We'll notify you when "${item.name}" becomes available.`
    });
  };

  return (
    <div className="min-h-screen pt-20 pb-12 px-4" data-testid="marketplace-page">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <h1 className="text-3xl md:text-4xl font-orbitron font-bold text-white mb-2">
            <ShoppingCart className="inline w-8 h-8 mr-3 text-neon-cyan" />
            Marketplace
          </h1>
          <p className="text-white/60">
            Discover exclusive items, boosters, and collectibles
          </p>
        </motion.div>

        {/* Coming Soon Banner */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="mb-8 p-6 bg-gradient-to-r from-purple-500/20 to-neon-cyan/20 rounded-xl border border-purple-500/30"
        >
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 rounded-full bg-purple-500/20 flex items-center justify-center">
              <Sparkles className="w-8 h-8 text-purple-400 animate-pulse" />
            </div>
            <div>
              <h2 className="text-xl font-orbitron font-bold text-white">
                Marketplace Coming Soon!
              </h2>
              <p className="text-white/60 mt-1">
                We're preparing amazing items for you. Set notifications to be the first to know!
              </p>
            </div>
          </div>
        </motion.div>

        {/* Search and Filters */}
        <div className="flex flex-col md:flex-row gap-4 mb-6">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-white/40" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search items..."
              className="w-full pl-10 pr-4 py-3 bg-white/5 border border-white/20 rounded-lg text-white placeholder-white/40 focus:border-neon-cyan outline-none transition-colors"
            />
          </div>
          <div className="flex gap-2 overflow-x-auto pb-2">
            {CATEGORIES.map(cat => (
              <button
                key={cat.id}
                onClick={() => setSelectedCategory(cat.id)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg whitespace-nowrap transition-all ${
                  selectedCategory === cat.id
                    ? 'bg-neon-cyan/20 border border-neon-cyan text-neon-cyan'
                    : 'bg-white/5 border border-white/20 text-white/60 hover:text-white'
                }`}
              >
                <cat.icon className="w-4 h-4" />
                {cat.name}
              </button>
            ))}
          </div>
        </div>

        {/* Items Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {filteredItems.map((item, index) => {
            const rarity = rarityColors[item.rarity];
            const Icon = item.icon;
            
            return (
              <motion.div
                key={item.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.05 }}
              >
                <CyberCard className="p-0 overflow-hidden bg-black/50 hover:bg-black/70 transition-colors group">
                  {/* Item Preview (Blurred) */}
                  <div className="relative h-40 flex items-center justify-center overflow-hidden"
                    style={{ background: `linear-gradient(135deg, ${item.color}10, ${item.color}30)` }}
                  >
                    {/* Blur overlay */}
                    <div className="absolute inset-0 backdrop-blur-md bg-black/30" />
                    
                    {/* Icon */}
                    <Icon 
                      className="w-16 h-16 relative z-10 opacity-50 group-hover:opacity-70 transition-opacity"
                      style={{ color: item.color }}
                    />
                    
                    {/* Coming Soon Badge */}
                    <div className="absolute top-3 right-3 z-20">
                      <span className="flex items-center gap-1 px-2 py-1 bg-black/80 rounded-full text-xs text-white/80">
                        <Clock className="w-3 h-3" />
                        Coming Soon
                      </span>
                    </div>

                    {/* Rarity Badge */}
                    <div className="absolute top-3 left-3 z-20">
                      <span className={`px-2 py-1 rounded-full text-xs ${rarity.bg} ${rarity.text} border ${rarity.border}`}>
                        {item.rarity}
                      </span>
                    </div>

                    {/* Lock Icon */}
                    <div className="absolute inset-0 flex items-center justify-center z-10">
                      <Lock className="w-8 h-8 text-white/20" />
                    </div>
                  </div>

                  {/* Item Info */}
                  <div className="p-4">
                    <h3 className="font-orbitron font-bold text-white mb-1">
                      {item.name}
                    </h3>
                    <p className="text-xs text-white/50 mb-3 line-clamp-2">
                      {item.description}
                    </p>
                    
                    <div className="flex items-center justify-between">
                      <span className="text-lg font-bold text-yellow-500">
                        {item.price} RLM
                      </span>
                      <button
                        onClick={() => handleNotifyMe(item)}
                        className="flex items-center gap-1 px-3 py-1.5 bg-purple-500/20 text-purple-400 border border-purple-500/50 rounded-lg text-xs hover:bg-purple-500/30 transition-colors"
                      >
                        <Sparkles className="w-3 h-3" />
                        Notify Me
                      </button>
                    </div>
                  </div>
                </CyberCard>
              </motion.div>
            );
          })}
        </div>

        {/* Empty State */}
        {filteredItems.length === 0 && (
          <div className="text-center py-12">
            <ShoppingCart className="w-16 h-16 text-white/20 mx-auto mb-4" />
            <p className="text-white/60">No items found matching your criteria</p>
          </div>
        )}

        {/* Footer Info */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
          className="mt-12 text-center"
        >
          <CyberCard className="p-6 bg-black/30 inline-block">
            <h3 className="font-orbitron text-lg text-neon-cyan mb-2">
              🚀 Be Part of the Launch!
            </h3>
            <p className="text-white/60 text-sm max-w-md">
              The marketplace is being carefully curated with exclusive items.
              Complete objectives and earn RLM tokens to be ready for the launch!
            </p>
          </CyberCard>
        </motion.div>
      </div>
    </div>
  );
};

export default MarketplacePage;
