import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Search, Users, GraduationCap, Briefcase, FolderKanban, Vote,
  Filter, TrendingUp, Sparkles, ChevronRight, X
} from 'lucide-react';
import axios from 'axios';
import { API } from '../utils/api';
import { useAuth } from '../context/AuthContext';
import { CyberCard, CyberButton } from '../components/common/CyberUI';

const SearchPage = () => {
  const { user } = useAuth();
  const [query, setQuery] = useState('');
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [activeTypes, setActiveTypes] = useState(['users', 'courses', 'projects', 'jobs', 'proposals']);
  const [trending, setTrending] = useState(null);
  const [suggestions, setSuggestions] = useState([]);
  const [showFilters, setShowFilters] = useState(false);

  // Fetch trending on mount
  useEffect(() => {
    axios.get(`${API}/search/trending`)
      .then(res => setTrending(res.data.trending))
      .catch(console.error);
  }, []);

  // Debounced search
  const performSearch = useCallback(async (searchQuery) => {
    if (!searchQuery || searchQuery.length < 2) {
      setResults(null);
      return;
    }
    
    setLoading(true);
    try {
      const types = activeTypes.join(',');
      const res = await axios.get(`${API}/search/?q=${encodeURIComponent(searchQuery)}&types=${types}&limit=10`);
      setResults(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [activeTypes]);

  // Get suggestions
  useEffect(() => {
    if (query.length >= 1) {
      axios.get(`${API}/search/suggest?q=${encodeURIComponent(query)}&limit=5`)
        .then(res => setSuggestions(res.data.suggestions || []))
        .catch(() => setSuggestions([]));
    } else {
      setSuggestions([]);
    }
  }, [query]);

  // Search on enter or button click
  const handleSearch = () => {
    performSearch(query);
    setSuggestions([]);
  };

  const toggleType = (type) => {
    setActiveTypes(prev => 
      prev.includes(type) 
        ? prev.filter(t => t !== type)
        : [...prev, type]
    );
  };

  const typeIcons = {
    users: Users,
    courses: GraduationCap,
    projects: FolderKanban,
    jobs: Briefcase,
    proposals: Vote
  };

  const typeColors = {
    users: '#00F0FF',
    courses: '#9D4EDD',
    projects: '#00FF88',
    jobs: '#FF003C',
    proposals: '#40C4FF'
  };

  return (
    <div className="min-h-screen pt-16 sm:pt-20 pb-20 lg:pb-12 px-3 sm:px-4" data-testid="search-page">
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-6">
          <h1 className="text-2xl sm:text-3xl font-orbitron font-black mb-2">
            <Search className="inline w-8 h-8 mr-2 text-neon-cyan" />
            Search & Discover
          </h1>
          <p className="text-white/60 text-sm">Find users, courses, projects, jobs, and proposals</p>
        </motion.div>

        {/* Search Box */}
        <CyberCard className="p-4 sm:p-6 mb-6" glow>
          <div className="relative">
            <div className="flex gap-2">
              <div className="flex-1 relative">
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                  placeholder="Search REALUM..."
                  className="w-full bg-black/50 border border-white/20 px-4 py-3 pl-12 font-mono text-white placeholder-white/30 focus:border-neon-cyan focus:outline-none transition-colors"
                  data-testid="search-input"
                />
                <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-white/50" />
              </div>
              <CyberButton onClick={handleSearch} disabled={loading || query.length < 2}>
                {loading ? 'Searching...' : 'Search'}
              </CyberButton>
              <button
                onClick={() => setShowFilters(!showFilters)}
                className={`p-3 border transition-colors ${showFilters ? 'border-neon-cyan bg-neon-cyan/10' : 'border-white/20 hover:border-white/40'}`}
              >
                <Filter className="w-5 h-5" />
              </button>
            </div>

            {/* Suggestions Dropdown */}
            <AnimatePresence>
              {suggestions.length > 0 && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  className="absolute top-full left-0 right-0 mt-2 bg-black/95 border border-white/20 z-50"
                >
                  {suggestions.map((s, i) => (
                    <button
                      key={i}
                      onClick={() => { setQuery(s.text); performSearch(s.text); setSuggestions([]); }}
                      className="w-full px-4 py-2 text-left hover:bg-white/10 flex items-center gap-3 transition-colors"
                    >
                      {React.createElement(typeIcons[s.type] || Search, { 
                        className: 'w-4 h-4',
                        style: { color: typeColors[s.type] || '#fff' }
                      })}
                      <span className="text-sm">{s.text}</span>
                      <span className="text-xs text-white/40 ml-auto">{s.type}</span>
                    </button>
                  ))}
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Filters */}
          <AnimatePresence>
            {showFilters && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="overflow-hidden"
              >
                <div className="pt-4 mt-4 border-t border-white/10">
                  <p className="text-xs text-white/50 mb-2">FILTER BY TYPE</p>
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(typeIcons).map(([type, Icon]) => (
                      <button
                        key={type}
                        onClick={() => toggleType(type)}
                        className={`px-3 py-2 border text-xs font-mono uppercase flex items-center gap-2 transition-all ${
                          activeTypes.includes(type)
                            ? 'border-neon-cyan bg-neon-cyan/10 text-neon-cyan'
                            : 'border-white/20 text-white/50 hover:border-white/40'
                        }`}
                      >
                        <Icon className="w-4 h-4" />
                        {type}
                      </button>
                    ))}
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </CyberCard>

        {/* Results */}
        {results && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-4 mb-8">
            <div className="flex items-center justify-between">
              <h2 className="font-orbitron font-bold text-lg">
                Results <span className="text-neon-cyan">({results.total})</span>
              </h2>
              <button onClick={() => setResults(null)} className="text-white/50 hover:text-white text-sm flex items-center gap-1">
                <X className="w-4 h-4" /> Clear
              </button>
            </div>

            {Object.entries(results.results).map(([type, items]) => (
              items.length > 0 && (
                <CyberCard key={type} className="p-4">
                  <div className="flex items-center gap-2 mb-3">
                    {React.createElement(typeIcons[type], { 
                      className: 'w-5 h-5',
                      style: { color: typeColors[type] }
                    })}
                    <h3 className="font-orbitron text-sm uppercase" style={{ color: typeColors[type] }}>
                      {type} ({items.length})
                    </h3>
                  </div>
                  <div className="space-y-2">
                    {items.map((item, i) => (
                      <div key={i} className="p-3 bg-black/30 border border-white/10 hover:border-white/20 transition-colors">
                        <div className="flex items-center justify-between">
                          <span className="font-mono text-sm">
                            {item.username || item.title || item.name}
                          </span>
                          <ChevronRight className="w-4 h-4 text-white/30" />
                        </div>
                        {item.description && (
                          <p className="text-xs text-white/50 mt-1 line-clamp-1">{item.description}</p>
                        )}
                      </div>
                    ))}
                  </div>
                </CyberCard>
              )
            ))}
          </motion.div>
        )}

        {/* Trending Section (shown when no search) */}
        {!results && trending && (
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
            <div className="flex items-center gap-2 mb-4">
              <TrendingUp className="w-5 h-5 text-neon-purple" />
              <h2 className="font-orbitron font-bold">Trending This Week</h2>
            </div>

            <div className="grid sm:grid-cols-2 gap-4">
              {/* Trending Courses */}
              {trending.courses?.length > 0 && (
                <CyberCard className="p-4">
                  <div className="flex items-center gap-2 mb-3">
                    <GraduationCap className="w-5 h-5 text-neon-purple" />
                    <h3 className="text-sm font-bold text-neon-purple">Hot Courses</h3>
                  </div>
                  <div className="space-y-2">
                    {trending.courses.slice(0, 3).map((c, i) => (
                      <div key={i} className="p-2 bg-black/30 text-sm flex items-center gap-2">
                        <span className="text-neon-purple font-mono">#{i + 1}</span>
                        <span className="truncate">{c.title}</span>
                      </div>
                    ))}
                  </div>
                </CyberCard>
              )}

              {/* Active Proposals */}
              {trending.proposals?.length > 0 && (
                <CyberCard className="p-4">
                  <div className="flex items-center gap-2 mb-3">
                    <Vote className="w-5 h-5 text-neon-cyan" />
                    <h3 className="text-sm font-bold text-neon-cyan">Active Votes</h3>
                  </div>
                  <div className="space-y-2">
                    {trending.proposals.slice(0, 3).map((p, i) => (
                      <div key={i} className="p-2 bg-black/30 text-sm flex items-center justify-between">
                        <span className="truncate">{p.title}</span>
                        <span className="text-xs text-white/50">{p.voter_count || 0} votes</span>
                      </div>
                    ))}
                  </div>
                </CyberCard>
              )}

              {/* Open Bounties */}
              {trending.bounties?.length > 0 && (
                <CyberCard className="p-4">
                  <div className="flex items-center gap-2 mb-3">
                    <Sparkles className="w-5 h-5 text-neon-yellow" />
                    <h3 className="text-sm font-bold text-neon-yellow">Top Bounties</h3>
                  </div>
                  <div className="space-y-2">
                    {trending.bounties.slice(0, 3).map((b, i) => (
                      <div key={i} className="p-2 bg-black/30 text-sm flex items-center justify-between">
                        <span className="truncate">{b.title}</span>
                        <span className="text-neon-yellow font-mono">{b.reward_amount} RLM</span>
                      </div>
                    ))}
                  </div>
                </CyberCard>
              )}

              {/* New Projects */}
              {trending.projects?.length > 0 && (
                <CyberCard className="p-4">
                  <div className="flex items-center gap-2 mb-3">
                    <FolderKanban className="w-5 h-5 text-neon-green" />
                    <h3 className="text-sm font-bold text-neon-green">New Projects</h3>
                  </div>
                  <div className="space-y-2">
                    {trending.projects.slice(0, 3).map((p, i) => (
                      <div key={i} className="p-2 bg-black/30 text-sm">
                        <span className="truncate">{p.title}</span>
                      </div>
                    ))}
                  </div>
                </CyberCard>
              )}
            </div>
          </motion.div>
        )}
      </div>
    </div>
  );
};

export default SearchPage;
