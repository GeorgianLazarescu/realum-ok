import React, { useState, useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import { 
  MessageSquare, Send, Users, Hash, Globe, Lock, Loader2
} from 'lucide-react';
import axios from 'axios';
import { API } from '../utils/api';
import { useAuth } from '../context/AuthContext';
import { CyberCard, CyberButton } from '../components/common/CyberUI';
import { toast } from 'sonner';

const ChatPage = () => {
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  
  const [channels, setChannels] = useState({});
  const [activeChannel, setActiveChannel] = useState('global');
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [conversations, setConversations] = useState([]);
  const [activeConvo, setActiveConvo] = useState(null);
  const [privateMessages, setPrivateMessages] = useState([]);
  const [pmUsername, setPmUsername] = useState('');
  
  const messagesEndRef = useRef(null);
  const pollInterval = useRef(null);

  useEffect(() => {
    fetchChannels();
    return () => {
      if (pollInterval.current) clearInterval(pollInterval.current);
    };
  }, []);

  useEffect(() => {
    if (activeChannel) {
      fetchMessages(activeChannel);
      pollInterval.current = setInterval(() => fetchMessages(activeChannel), 5000);
    }
    return () => {
      if (pollInterval.current) clearInterval(pollInterval.current);
    };
  }, [activeChannel]);

  useEffect(() => {
    scrollToBottom();
  }, [messages, privateMessages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const fetchChannels = async () => {
    try {
      const res = await axios.get(`${API}/chat/channels`);
      setChannels(res.data.channels || {});
    } catch (error) {
      console.error('Failed to load channels:', error);
    }
    setLoading(false);
  };

  const fetchMessages = async (channel) => {
    try {
      const res = await axios.get(`${API}/chat/messages/${channel}`);
      setMessages(res.data.messages || []);
    } catch (error) {
      console.error('Failed to load messages:', error);
    }
  };

  const fetchConversations = async () => {
    try {
      const res = await axios.get(`${API}/chat/private`);
      setConversations(res.data.conversations || []);
    } catch (error) {
      console.error('Failed to load conversations:', error);
    }
  };

  const fetchPrivateMessages = async (userId) => {
    try {
      const res = await axios.get(`${API}/chat/private/${userId}`);
      setPrivateMessages(res.data.messages || []);
    } catch (error) {
      console.error('Failed to load private messages:', error);
    }
  };

  const sendMessage = async () => {
    if (!newMessage.trim()) return;
    
    setSending(true);
    try {
      await axios.post(`${API}/chat/send`, {
        content: newMessage,
        channel: activeChannel
      });
      setNewMessage('');
      fetchMessages(activeChannel);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to send message');
    }
    setSending(false);
  };

  const sendPrivateMessage = async () => {
    if (!newMessage.trim() || !activeConvo) return;
    
    setSending(true);
    try {
      await axios.post(`${API}/chat/private/send`, {
        recipient_username: activeConvo.username,
        content: newMessage
      });
      setNewMessage('');
      fetchPrivateMessages(activeConvo.user_id);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to send message');
    }
    setSending(false);
  };

  const startNewConversation = async () => {
    if (!pmUsername.trim()) return;
    
    try {
      await axios.post(`${API}/chat/private/send`, {
        recipient_username: pmUsername,
        content: '👋 Salut!'
      });
      fetchConversations();
      setPmUsername('');
      toast.success('Conversation started!');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'User not found');
    }
  };

  const channelIcons = { global: Globe, trade: Hash, politics: Hash, help: Hash };

  if (loading) {
    return (
      <div className="min-h-screen pt-20 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-neon-cyan" />
      </div>
    );
  }

  return (
    <div className="min-h-screen pt-16 sm:pt-20 pb-20 lg:pb-12 px-3 sm:px-4" data-testid="chat-page">
      <div className="max-w-7xl mx-auto">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-6">
          <h1 className="text-2xl sm:text-3xl font-orbitron font-black flex items-center gap-3">
            <MessageSquare className="w-8 h-8 text-neon-green" />
            <span>Chat <span className="text-neon-cyan">REALUM</span></span>
          </h1>
        </motion.div>

        <div className="grid lg:grid-cols-4 gap-4 h-[calc(100vh-200px)]">
          <CyberCard className="p-4 lg:col-span-1 overflow-y-auto">
            <h3 className="font-orbitron text-sm mb-4">Canale</h3>
            <div className="space-y-2">
              {Object.entries(channels).map(([id, channel]) => {
                const Icon = channelIcons[id] || Hash;
                return (
                  <button key={id} onClick={() => { setActiveChannel(id); setActiveConvo(null); }}
                    className={`w-full p-2 text-left flex items-center gap-2 ${activeChannel === id && !activeConvo ? 'bg-neon-cyan/20 border border-neon-cyan text-neon-cyan' : 'border border-transparent text-white/60 hover:text-white'}`}>
                    <Icon className="w-4 h-4" />
                    <span className="font-mono text-sm">{channel.name}</span>
                  </button>
                );
              })}
            </div>
            <hr className="border-white/10 my-4" />
            <h3 className="font-orbitron text-sm mb-4">Mesaje Private</h3>
            <div className="flex gap-2 mb-3">
              <input type="text" value={pmUsername} onChange={e => setPmUsername(e.target.value)}
                placeholder="Username..." className="flex-1 bg-black/50 border border-white/20 p-1 text-sm text-white" />
              <CyberButton variant="outline" size="sm" onClick={startNewConversation}>+</CyberButton>
            </div>
            <div className="space-y-2">
              {conversations.map(convo => (
                <button key={convo.user_id} onClick={() => { setActiveConvo(convo); setActiveChannel(null); fetchPrivateMessages(convo.user_id); }}
                  className={`w-full p-2 text-left ${activeConvo?.user_id === convo.user_id ? 'bg-neon-purple/20 border border-neon-purple' : 'border border-transparent hover:bg-white/5'}`}>
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-sm text-neon-cyan">{convo.username}</span>
                    {convo.unread_count > 0 && <span className="px-2 py-0.5 text-xs bg-neon-red rounded-full">{convo.unread_count}</span>}
                  </div>
                  <p className="text-xs text-white/40 truncate">{convo.last_message}</p>
                </button>
              ))}
            </div>
          </CyberCard>

          <CyberCard className="p-4 lg:col-span-3 flex flex-col">
            <div className="pb-3 border-b border-white/10 mb-4">
              {activeChannel ? (
                <div className="flex items-center gap-2">
                  <Hash className="w-5 h-5 text-neon-cyan" />
                  <span className="font-orbitron">{channels[activeChannel]?.name}</span>
                </div>
              ) : activeConvo ? (
                <div className="flex items-center gap-2">
                  <Lock className="w-5 h-5 text-neon-purple" />
                  <span className="font-orbitron text-neon-cyan">{activeConvo.username}</span>
                </div>
              ) : <span className="text-white/40">Selectează un canal</span>}
            </div>

            <div className="flex-1 overflow-y-auto space-y-3 mb-4">
              {(activeChannel ? messages : privateMessages).map(msg => (
                <div key={msg.id} className={`flex ${msg.sender_id === user?.id ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-[70%] p-3 ${msg.sender_id === user?.id ? 'bg-neon-cyan/20 border border-neon-cyan/30' : 'bg-black/30 border border-white/10'}`}>
                    {msg.sender_id !== user?.id && <div className="text-xs text-neon-cyan mb-1">{msg.sender_username}</div>}
                    <p className="text-sm text-white/90">{msg.content}</p>
                    <div className="text-xs text-white/30 mt-1">{new Date(msg.created_at).toLocaleTimeString()}</div>
                  </div>
                </div>
              ))}
              <div ref={messagesEndRef} />
            </div>

            <div className="flex gap-2">
              <input type="text" value={newMessage} onChange={e => setNewMessage(e.target.value)}
                onKeyPress={e => { if (e.key === 'Enter') activeChannel ? sendMessage() : sendPrivateMessage(); }}
                placeholder="Scrie un mesaj..." className="flex-1 bg-black/50 border border-white/20 p-3 text-white" maxLength={500} />
              <CyberButton variant="primary" onClick={activeChannel ? sendMessage : sendPrivateMessage} disabled={sending || !newMessage.trim()}>
                {sending ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
              </CyberButton>
            </div>
          </CyberCard>
        </div>
      </div>
    </div>
  );
};

export default ChatPage;
