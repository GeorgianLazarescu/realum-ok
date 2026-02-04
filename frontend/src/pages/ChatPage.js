import React, { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  MessageCircle, Send, Users, Hash, Plus, Settings,
  MoreVertical, Reply, Edit3, Trash2, Smile, Paperclip, X, Wifi, WifiOff
} from 'lucide-react';
import axios from 'axios';
import { API } from '../utils/api';
import { useAuth } from '../context/AuthContext';
import { CyberCard, CyberButton } from '../components/common/CyberUI';

const ChatPage = () => {
  const { user, token } = useAuth();
  const [channels, setChannels] = useState([]);
  const [selectedChannel, setSelectedChannel] = useState(null);
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [loading, setLoading] = useState(true);
  const [ws, setWs] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const [onlineUsers, setOnlineUsers] = useState([]);
  const [typingUsers, setTypingUsers] = useState([]);
  const [showNewChannel, setShowNewChannel] = useState(false);
  const [newChannelName, setNewChannelName] = useState('');
  const messagesEndRef = useRef(null);
  const typingTimeoutRef = useRef(null);

  // Load channels
  useEffect(() => {
    loadChannels();
  }, []);

  const loadChannels = async () => {
    try {
      const res = await axios.get(`${API}/chat/channels`);
      setChannels(res.data.channels || []);
      if (res.data.channels?.length > 0 && !selectedChannel) {
        setSelectedChannel(res.data.channels[0]);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  // Load messages when channel changes
  useEffect(() => {
    if (selectedChannel) {
      loadMessages();
    }
  }, [selectedChannel]);

  const loadMessages = async () => {
    if (!selectedChannel) return;
    try {
      const res = await axios.get(`${API}/chat/channels/${selectedChannel.id}/messages?limit=50`);
      setMessages(res.data.messages || []);
      scrollToBottom();
    } catch (err) {
      console.error(err);
    }
  };

  // WebSocket connection
  useEffect(() => {
    if (!selectedChannel || !token) return;

    // Get WebSocket URL
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const apiHost = API.replace(/^https?:\/\//, '').replace('/api', '');
    const wsUrl = `${wsProtocol}//${apiHost}/api/chat/ws/${selectedChannel.id}?token=${token}`;

    const websocket = new WebSocket(wsUrl);

    websocket.onopen = () => {
      console.log('WebSocket connected');
      setIsConnected(true);
    };

    websocket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      handleWebSocketMessage(data);
    };

    websocket.onclose = () => {
      console.log('WebSocket disconnected');
      setIsConnected(false);
    };

    websocket.onerror = (error) => {
      console.error('WebSocket error:', error);
      setIsConnected(false);
    };

    setWs(websocket);

    return () => {
      if (websocket.readyState === WebSocket.OPEN) {
        websocket.close();
      }
    };
  }, [selectedChannel, token]);

  const handleWebSocketMessage = useCallback((data) => {
    switch (data.type) {
      case 'connected':
        setOnlineUsers(data.online_users || []);
        break;
      case 'new_message':
        setMessages(prev => [...prev, data.message]);
        scrollToBottom();
        break;
      case 'user_joined':
        setOnlineUsers(prev => [...new Set([...prev, data.user_id])]);
        break;
      case 'user_left':
        setOnlineUsers(prev => prev.filter(id => id !== data.user_id));
        break;
      case 'typing':
        if (data.is_typing) {
          setTypingUsers(prev => [...new Set([...prev, data.user_id])]);
        } else {
          setTypingUsers(prev => prev.filter(id => id !== data.user_id));
        }
        break;
      case 'read_receipt':
        // Could update message read status here
        break;
      default:
        break;
    }
  }, []);

  const scrollToBottom = () => {
    setTimeout(() => {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, 100);
  };

  const sendMessage = () => {
    if (!newMessage.trim() || !ws || ws.readyState !== WebSocket.OPEN) return;

    ws.send(JSON.stringify({
      type: 'message',
      content: newMessage.trim()
    }));

    setNewMessage('');
    
    // Stop typing indicator
    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current);
    }
    ws.send(JSON.stringify({ type: 'typing', is_typing: false }));
  };

  const handleTyping = (e) => {
    setNewMessage(e.target.value);
    
    if (!ws || ws.readyState !== WebSocket.OPEN) return;

    // Send typing indicator
    ws.send(JSON.stringify({ type: 'typing', is_typing: true }));

    // Clear previous timeout
    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current);
    }

    // Stop typing after 2 seconds of no input
    typingTimeoutRef.current = setTimeout(() => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'typing', is_typing: false }));
      }
    }, 2000);
  };

  const createChannel = async () => {
    if (!newChannelName.trim()) return;
    try {
      await axios.post(`${API}/chat/channels`, {
        name: newChannelName.trim(),
        channel_type: 'group'
      });
      setNewChannelName('');
      setShowNewChannel(false);
      loadChannels();
    } catch (err) {
      console.error(err);
    }
  };

  const formatTime = (dateStr) => {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  if (loading) {
    return (
      <div className="min-h-screen pt-20 flex items-center justify-center">
        <div className="text-neon-cyan font-mono">Loading chat...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen pt-16 sm:pt-20 pb-20 lg:pb-4 px-3 sm:px-4" data-testid="chat-page">
      <div className="max-w-6xl mx-auto h-[calc(100vh-140px)]">
        <div className="grid lg:grid-cols-4 gap-4 h-full">
          {/* Channels Sidebar */}
          <CyberCard className="lg:col-span-1 p-3 overflow-hidden flex flex-col">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-orbitron font-bold text-sm">Channels</h3>
              <button 
                onClick={() => setShowNewChannel(true)}
                className="p-1 text-neon-cyan hover:bg-neon-cyan/10 transition-colors"
              >
                <Plus className="w-5 h-5" />
              </button>
            </div>

            {/* New Channel Form */}
            <AnimatePresence>
              {showNewChannel && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  className="mb-3 overflow-hidden"
                >
                  <div className="p-2 bg-black/30 border border-white/10">
                    <input
                      type="text"
                      value={newChannelName}
                      onChange={(e) => setNewChannelName(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && createChannel()}
                      placeholder="Channel name..."
                      className="w-full bg-transparent border-b border-white/20 px-2 py-1 text-sm focus:border-neon-cyan focus:outline-none"
                    />
                    <div className="flex gap-2 mt-2">
                      <button onClick={createChannel} className="text-xs text-neon-green">Create</button>
                      <button onClick={() => setShowNewChannel(false)} className="text-xs text-white/50">Cancel</button>
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            <div className="flex-1 overflow-y-auto space-y-1">
              {channels.map(channel => (
                <button
                  key={channel.id}
                  onClick={() => setSelectedChannel(channel)}
                  className={`w-full p-2 text-left flex items-center gap-2 transition-colors ${
                    selectedChannel?.id === channel.id 
                      ? 'bg-neon-cyan/10 border-l-2 border-neon-cyan' 
                      : 'hover:bg-white/5'
                  }`}
                >
                  <Hash className="w-4 h-4 text-white/50" />
                  <span className="text-sm truncate">{channel.name}</span>
                  {channel.unread_count > 0 && (
                    <span className="ml-auto bg-neon-cyan text-black text-[10px] px-1.5 py-0.5 rounded-full">
                      {channel.unread_count}
                    </span>
                  )}
                </button>
              ))}
              {channels.length === 0 && (
                <p className="text-white/40 text-sm text-center py-4">No channels yet</p>
              )}
            </div>
          </CyberCard>

          {/* Chat Area */}
          <CyberCard className="lg:col-span-3 flex flex-col overflow-hidden">
            {selectedChannel ? (
              <>
                {/* Channel Header */}
                <div className="p-3 border-b border-white/10 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Hash className="w-5 h-5 text-neon-cyan" />
                    <div>
                      <h3 className="font-orbitron font-bold text-sm">{selectedChannel.name}</h3>
                      <span className="text-xs text-white/50">
                        {onlineUsers.length} online
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {isConnected ? (
                      <span className="flex items-center gap-1 text-neon-green text-xs">
                        <Wifi className="w-4 h-4" /> Live
                      </span>
                    ) : (
                      <span className="flex items-center gap-1 text-neon-red text-xs">
                        <WifiOff className="w-4 h-4" /> Offline
                      </span>
                    )}
                    <button className="p-1 text-white/50 hover:text-white">
                      <Users className="w-5 h-5" />
                    </button>
                  </div>
                </div>

                {/* Messages */}
                <div className="flex-1 overflow-y-auto p-4 space-y-4">
                  {messages.map((msg, i) => (
                    <motion.div
                      key={msg.id || i}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      className={`flex gap-3 ${msg.sender_id === user?.id ? 'flex-row-reverse' : ''}`}
                    >
                      <div className="w-8 h-8 bg-gradient-to-br from-neon-cyan to-neon-purple rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0">
                        {msg.sender_username?.[0]?.toUpperCase() || '?'}
                      </div>
                      <div className={`max-w-[70%] ${msg.sender_id === user?.id ? 'text-right' : ''}`}>
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-xs font-mono text-neon-cyan">{msg.sender_username}</span>
                          <span className="text-[10px] text-white/40">{formatTime(msg.created_at)}</span>
                        </div>
                        <div className={`p-3 text-sm ${
                          msg.sender_id === user?.id 
                            ? 'bg-neon-cyan/10 border border-neon-cyan/30' 
                            : 'bg-white/5 border border-white/10'
                        }`}>
                          {msg.content}
                        </div>
                      </div>
                    </motion.div>
                  ))}
                  <div ref={messagesEndRef} />
                </div>

                {/* Typing Indicator */}
                <AnimatePresence>
                  {typingUsers.length > 0 && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      className="px-4 pb-2"
                    >
                      <span className="text-xs text-white/50 italic">
                        Someone is typing...
                      </span>
                    </motion.div>
                  )}
                </AnimatePresence>

                {/* Message Input */}
                <div className="p-3 border-t border-white/10">
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={newMessage}
                      onChange={handleTyping}
                      onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
                      placeholder={`Message #${selectedChannel.name}...`}
                      className="flex-1 bg-black/50 border border-white/20 px-4 py-2 text-sm focus:border-neon-cyan focus:outline-none"
                      disabled={!isConnected}
                    />
                    <CyberButton 
                      onClick={sendMessage} 
                      disabled={!newMessage.trim() || !isConnected}
                    >
                      <Send className="w-4 h-4" />
                    </CyberButton>
                  </div>
                </div>
              </>
            ) : (
              <div className="flex-1 flex items-center justify-center">
                <div className="text-center">
                  <MessageCircle className="w-16 h-16 mx-auto mb-4 text-white/20" />
                  <h3 className="font-orbitron font-bold mb-2">No Channel Selected</h3>
                  <p className="text-white/50 text-sm">Select a channel or create one to start chatting</p>
                </div>
              </div>
            )}
          </CyberCard>
        </div>
      </div>
    </div>
  );
};

export default ChatPage;
