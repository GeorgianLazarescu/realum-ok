import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Users, Heart, MessageCircle, Share2, UserPlus, UserMinus,
  TrendingUp, Sparkles, Send, MoreHorizontal
} from 'lucide-react';
import axios from 'axios';
import { API } from '../utils/api';
import { useAuth } from '../context/AuthContext';
import { CyberCard, CyberButton } from '../components/common/CyberUI';

const SocialPage = () => {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState('feed');
  const [feed, setFeed] = useState([]);
  const [globalFeed, setGlobalFeed] = useState([]);
  const [followers, setFollowers] = useState([]);
  const [following, setFollowing] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [reactionTypes, setReactionTypes] = useState([]);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [feedRes, globalRes, statsRes, reactionsRes] = await Promise.all([
        axios.get(`${API}/social/feed`).catch(() => ({ data: { feed: [] } })),
        axios.get(`${API}/social/feed/global`).catch(() => ({ data: { feed: [] } })),
        axios.get(`${API}/social/stats/${user.id}`).catch(() => ({ data: { stats: {} } })),
        axios.get(`${API}/social/reaction-types`).catch(() => ({ data: { reactions: [] } }))
      ]);
      
      setFeed(feedRes.data.feed || []);
      setGlobalFeed(globalRes.data.feed || []);
      setStats(statsRes.data.stats || {});
      setReactionTypes(reactionsRes.data.reactions || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const loadFollowers = async () => {
    try {
      const res = await axios.get(`${API}/social/followers/${user.id}`);
      setFollowers(res.data.followers || []);
    } catch (err) {
      console.error(err);
    }
  };

  const loadFollowing = async () => {
    try {
      const res = await axios.get(`${API}/social/following/${user.id}`);
      setFollowing(res.data.following || []);
    } catch (err) {
      console.error(err);
    }
  };

  const handleFollow = async (userId) => {
    try {
      await axios.post(`${API}/social/follow/${userId}`);
      loadData();
      if (activeTab === 'following') loadFollowing();
    } catch (err) {
      console.error(err);
    }
  };

  const handleUnfollow = async (userId) => {
    try {
      await axios.delete(`${API}/social/follow/${userId}`);
      loadData();
      if (activeTab === 'following') loadFollowing();
    } catch (err) {
      console.error(err);
    }
  };

  const formatTimeAgo = (dateStr) => {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    const now = new Date();
    const diff = Math.floor((now - date) / 1000);
    
    if (diff < 60) return 'just now';
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return `${Math.floor(diff / 86400)}d ago`;
  };

  const ActivityCard = ({ activity }) => (
    <CyberCard className="p-4">
      <div className="flex items-start gap-3">
        <div className="w-10 h-10 bg-gradient-to-br from-neon-cyan to-neon-purple rounded-full flex items-center justify-center text-sm font-bold">
          {activity.username?.[0]?.toUpperCase() || '?'}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="font-mono text-sm font-bold">{activity.username}</span>
            <span className="text-white/40 text-xs">{formatTimeAgo(activity.created_at)}</span>
          </div>
          <p className="text-sm text-white/80">{activity.description || activity.action}</p>
          {activity.content && (
            <p className="mt-2 p-3 bg-black/30 border-l-2 border-neon-cyan/50 text-sm text-white/70">
              {activity.content}
            </p>
          )}
          <div className="flex items-center gap-4 mt-3">
            {reactionTypes.slice(0, 3).map(r => (
              <button key={r.type} className="flex items-center gap-1 text-white/50 hover:text-white transition-colors">
                <span>{r.emoji}</span>
                <span className="text-xs">0</span>
              </button>
            ))}
            <button className="flex items-center gap-1 text-white/50 hover:text-white transition-colors">
              <MessageCircle className="w-4 h-4" />
              <span className="text-xs">Comment</span>
            </button>
          </div>
        </div>
      </div>
    </CyberCard>
  );

  const UserCard = ({ userData, showFollowButton = true }) => (
    <div className="p-3 bg-black/30 border border-white/10 flex items-center gap-3">
      <div className="w-10 h-10 bg-gradient-to-br from-neon-purple to-neon-cyan rounded-full flex items-center justify-center text-sm font-bold">
        {userData.username?.[0]?.toUpperCase() || '?'}
      </div>
      <div className="flex-1 min-w-0">
        <span className="font-mono text-sm block truncate">{userData.username}</span>
        {userData.bio && (
          <span className="text-xs text-white/50 line-clamp-1">{userData.bio}</span>
        )}
      </div>
      {showFollowButton && userData.id !== user?.id && (
        <button
          onClick={() => userData.is_following ? handleUnfollow(userData.id) : handleFollow(userData.id)}
          className={`p-2 border transition-colors ${
            userData.is_following 
              ? 'border-white/30 text-white/50 hover:border-neon-red hover:text-neon-red' 
              : 'border-neon-cyan text-neon-cyan hover:bg-neon-cyan/10'
          }`}
        >
          {userData.is_following ? <UserMinus className="w-4 h-4" /> : <UserPlus className="w-4 h-4" />}
        </button>
      )}
    </div>
  );

  if (loading) {
    return (
      <div className="min-h-screen pt-20 flex items-center justify-center">
        <div className="text-neon-cyan font-mono">Loading social feed...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen pt-16 sm:pt-20 pb-20 lg:pb-12 px-3 sm:px-4" data-testid="social-page">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-6">
          <h1 className="text-2xl sm:text-3xl font-orbitron font-black mb-2">
            <Users className="inline w-8 h-8 mr-2 text-neon-purple" />
            Social
          </h1>
          <p className="text-white/60 text-sm">Connect with the REALUM community</p>
        </motion.div>

        {/* Stats */}
        <div className="grid grid-cols-4 gap-3 mb-6">
          <CyberCard className="text-center p-3">
            <div className="text-xl font-orbitron font-bold text-neon-cyan">
              {stats?.followers || 0}
            </div>
            <div className="text-[10px] text-white/50 uppercase">Followers</div>
          </CyberCard>
          <CyberCard className="text-center p-3">
            <div className="text-xl font-orbitron font-bold text-neon-purple">
              {stats?.following || 0}
            </div>
            <div className="text-[10px] text-white/50 uppercase">Following</div>
          </CyberCard>
          <CyberCard className="text-center p-3">
            <div className="text-xl font-orbitron font-bold text-neon-green">
              {stats?.comments || 0}
            </div>
            <div className="text-[10px] text-white/50 uppercase">Comments</div>
          </CyberCard>
          <CyberCard className="text-center p-3">
            <div className="text-xl font-orbitron font-bold text-neon-yellow">
              {stats?.reactions_received || 0}
            </div>
            <div className="text-[10px] text-white/50 uppercase">Reactions</div>
          </CyberCard>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
          {[
            { key: 'feed', label: 'My Feed', icon: Sparkles },
            { key: 'global', label: 'Global', icon: TrendingUp },
            { key: 'followers', label: 'Followers', icon: Users },
            { key: 'following', label: 'Following', icon: Heart }
          ].map(tab => (
            <button
              key={tab.key}
              onClick={() => {
                setActiveTab(tab.key);
                if (tab.key === 'followers') loadFollowers();
                if (tab.key === 'following') loadFollowing();
              }}
              className={`px-4 py-2 border text-sm font-mono flex items-center gap-2 whitespace-nowrap transition-colors ${
                activeTab === tab.key 
                  ? 'border-neon-cyan bg-neon-cyan/10 text-neon-cyan' 
                  : 'border-white/20 text-white/60 hover:border-white/40'
              }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <AnimatePresence mode="wait">
          {activeTab === 'feed' && (
            <motion.div
              key="feed"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="space-y-4"
            >
              {feed.length > 0 ? (
                feed.map((activity, i) => (
                  <ActivityCard key={i} activity={activity} />
                ))
              ) : (
                <CyberCard className="p-8 text-center">
                  <Users className="w-12 h-12 mx-auto mb-4 text-white/30" />
                  <h3 className="font-orbitron font-bold mb-2">Your Feed is Empty</h3>
                  <p className="text-white/50 text-sm mb-4">
                    Follow other users to see their activity here
                  </p>
                  <CyberButton onClick={() => setActiveTab('global')}>
                    Explore Global Feed
                  </CyberButton>
                </CyberCard>
              )}
            </motion.div>
          )}

          {activeTab === 'global' && (
            <motion.div
              key="global"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="space-y-4"
            >
              {globalFeed.length > 0 ? (
                globalFeed.map((activity, i) => (
                  <ActivityCard key={i} activity={activity} />
                ))
              ) : (
                <CyberCard className="p-8 text-center">
                  <TrendingUp className="w-12 h-12 mx-auto mb-4 text-white/30" />
                  <h3 className="font-orbitron font-bold mb-2">No Global Activity Yet</h3>
                  <p className="text-white/50 text-sm">
                    Be the first to make waves in the REALUM community!
                  </p>
                </CyberCard>
              )}
            </motion.div>
          )}

          {activeTab === 'followers' && (
            <motion.div
              key="followers"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <CyberCard className="p-4">
                <h3 className="font-orbitron font-bold mb-4">
                  Your Followers ({followers.length})
                </h3>
                <div className="space-y-2">
                  {followers.length > 0 ? (
                    followers.map((f, i) => (
                      <UserCard key={i} userData={f} />
                    ))
                  ) : (
                    <p className="text-white/50 text-sm text-center py-8">
                      No followers yet. Share your profile to grow your network!
                    </p>
                  )}
                </div>
              </CyberCard>
            </motion.div>
          )}

          {activeTab === 'following' && (
            <motion.div
              key="following"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <CyberCard className="p-4">
                <h3 className="font-orbitron font-bold mb-4">
                  Following ({following.length})
                </h3>
                <div className="space-y-2">
                  {following.length > 0 ? (
                    following.map((f, i) => (
                      <UserCard key={i} userData={{...f, is_following: true}} />
                    ))
                  ) : (
                    <p className="text-white/50 text-sm text-center py-8">
                      You're not following anyone yet. Explore the community!
                    </p>
                  )}
                </div>
              </CyberCard>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Reaction Types Legend */}
        <CyberCard className="mt-6 p-4">
          <h4 className="text-xs text-white/50 uppercase mb-3">Available Reactions</h4>
          <div className="flex flex-wrap gap-3">
            {reactionTypes.map(r => (
              <div key={r.type} className="flex items-center gap-2 text-sm">
                <span className="text-lg">{r.emoji}</span>
                <span className="text-white/70">{r.name}</span>
              </div>
            ))}
          </div>
        </CyberCard>
      </div>
    </div>
  );
};

export default SocialPage;
