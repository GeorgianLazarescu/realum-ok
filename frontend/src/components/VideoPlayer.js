import React, { useState, useRef, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Play, Pause, Volume2, VolumeX, Maximize, Minimize,
  SkipBack, SkipForward, Settings, BookmarkPlus, List,
  ChevronLeft, ChevronRight, Check, Clock, StickyNote
} from 'lucide-react';
import axios from 'axios';
import { API } from '../utils/api';
import { CyberCard, CyberButton } from '../components/common/CyberUI';

const VideoPlayer = ({ videoId, onComplete, onBack }) => {
  const videoRef = useRef(null);
  const progressRef = useRef(null);
  const [video, setVideo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(1);
  const [isMuted, setIsMuted] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [playbackRate, setPlaybackRate] = useState(1);
  const [showControls, setShowControls] = useState(true);
  const [showChapters, setShowChapters] = useState(false);
  const [showNotes, setShowNotes] = useState(false);
  const [notes, setNotes] = useState([]);
  const [newNote, setNewNote] = useState('');
  const [showSettings, setShowSettings] = useState(false);
  const controlsTimeoutRef = useRef(null);

  // Load video data
  useEffect(() => {
    loadVideo();
  }, [videoId]);

  const loadVideo = async () => {
    try {
      const res = await axios.get(`${API}/video/videos/${videoId}`);
      setVideo(res.data.video);
      setNotes(res.data.video.user_notes || []);
      
      // Resume from last position
      if (res.data.video.user_progress?.position_seconds) {
        setCurrentTime(res.data.video.user_progress.position_seconds);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  // Save progress periodically
  const saveProgress = useCallback(async (completed = false) => {
    if (!video) return;
    try {
      await axios.post(`${API}/video/progress`, {
        video_id: videoId,
        position_seconds: Math.floor(currentTime),
        completed
      });
    } catch (err) {
      console.error(err);
    }
  }, [videoId, currentTime, video]);

  // Auto-save progress every 10 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      if (isPlaying && currentTime > 0) {
        saveProgress();
      }
    }, 10000);
    return () => clearInterval(interval);
  }, [isPlaying, currentTime, saveProgress]);

  // Video event handlers
  const handleTimeUpdate = () => {
    if (videoRef.current) {
      setCurrentTime(videoRef.current.currentTime);
    }
  };

  const handleLoadedMetadata = () => {
    if (videoRef.current) {
      setDuration(videoRef.current.duration);
      // Resume from saved position
      if (video?.user_progress?.position_seconds) {
        videoRef.current.currentTime = video.user_progress.position_seconds;
      }
    }
  };

  const handleEnded = () => {
    setIsPlaying(false);
    saveProgress(true);
    if (onComplete) onComplete();
  };

  const togglePlay = () => {
    if (videoRef.current) {
      if (isPlaying) {
        videoRef.current.pause();
      } else {
        videoRef.current.play();
      }
      setIsPlaying(!isPlaying);
    }
  };

  const handleSeek = (e) => {
    if (progressRef.current && videoRef.current) {
      const rect = progressRef.current.getBoundingClientRect();
      const pos = (e.clientX - rect.left) / rect.width;
      videoRef.current.currentTime = pos * duration;
      setCurrentTime(pos * duration);
    }
  };

  const skip = (seconds) => {
    if (videoRef.current) {
      videoRef.current.currentTime = Math.max(0, Math.min(duration, currentTime + seconds));
    }
  };

  const toggleMute = () => {
    if (videoRef.current) {
      videoRef.current.muted = !isMuted;
      setIsMuted(!isMuted);
    }
  };

  const handleVolumeChange = (e) => {
    const val = parseFloat(e.target.value);
    setVolume(val);
    if (videoRef.current) {
      videoRef.current.volume = val;
      setIsMuted(val === 0);
    }
  };

  const toggleFullscreen = () => {
    const container = document.getElementById('video-container');
    if (!document.fullscreenElement) {
      container?.requestFullscreen();
      setIsFullscreen(true);
    } else {
      document.exitFullscreen();
      setIsFullscreen(false);
    }
  };

  const changePlaybackRate = (rate) => {
    if (videoRef.current) {
      videoRef.current.playbackRate = rate;
      setPlaybackRate(rate);
      setShowSettings(false);
    }
  };

  const jumpToChapter = (startTime) => {
    if (videoRef.current) {
      videoRef.current.currentTime = startTime;
      setCurrentTime(startTime);
      setShowChapters(false);
    }
  };

  const addNote = async () => {
    if (!newNote.trim()) return;
    try {
      const res = await axios.post(`${API}/video/notes`, {
        video_id: videoId,
        timestamp_seconds: Math.floor(currentTime),
        content: newNote.trim()
      });
      setNotes([...notes, res.data.note].sort((a, b) => a.timestamp_seconds - b.timestamp_seconds));
      setNewNote('');
    } catch (err) {
      console.error(err);
    }
  };

  const deleteNote = async (noteId) => {
    try {
      await axios.delete(`${API}/video/notes/${noteId}`);
      setNotes(notes.filter(n => n.id !== noteId));
    } catch (err) {
      console.error(err);
    }
  };

  const formatTime = (seconds) => {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.floor(seconds % 60);
    if (h > 0) {
      return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
    }
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  // Auto-hide controls
  const handleMouseMove = () => {
    setShowControls(true);
    if (controlsTimeoutRef.current) {
      clearTimeout(controlsTimeoutRef.current);
    }
    if (isPlaying) {
      controlsTimeoutRef.current = setTimeout(() => setShowControls(false), 3000);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96 bg-black">
        <div className="text-neon-cyan font-mono">Loading video...</div>
      </div>
    );
  }

  if (!video) {
    return (
      <div className="flex items-center justify-center h-96 bg-black">
        <div className="text-neon-red font-mono">Video not found</div>
      </div>
    );
  }

  const progress = duration > 0 ? (currentTime / duration) * 100 : 0;
  const currentChapter = video.chapters?.find((c, i) => {
    const next = video.chapters[i + 1];
    return currentTime >= c.start_time && (!next || currentTime < next.start_time);
  });

  return (
    <div className="space-y-4">
      {/* Video Container */}
      <div 
        id="video-container"
        className="relative bg-black aspect-video group"
        onMouseMove={handleMouseMove}
        onMouseLeave={() => isPlaying && setShowControls(false)}
      >
        <video
          ref={videoRef}
          src={video.video_url}
          poster={video.thumbnail_url}
          className="w-full h-full"
          onTimeUpdate={handleTimeUpdate}
          onLoadedMetadata={handleLoadedMetadata}
          onEnded={handleEnded}
          onClick={togglePlay}
        />

        {/* Play overlay */}
        {!isPlaying && (
          <div 
            className="absolute inset-0 flex items-center justify-center bg-black/30 cursor-pointer"
            onClick={togglePlay}
          >
            <div className="w-20 h-20 bg-neon-cyan/20 border-2 border-neon-cyan flex items-center justify-center">
              <Play className="w-10 h-10 text-neon-cyan ml-1" />
            </div>
          </div>
        )}

        {/* Controls */}
        <AnimatePresence>
          {showControls && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/90 to-transparent p-4"
            >
              {/* Progress bar */}
              <div 
                ref={progressRef}
                className="h-1 bg-white/20 cursor-pointer mb-4 relative group"
                onClick={handleSeek}
              >
                <div 
                  className="h-full bg-neon-cyan transition-all"
                  style={{ width: `${progress}%` }}
                />
                {/* Chapter markers */}
                {video.chapters?.map((chapter, i) => (
                  <div
                    key={i}
                    className="absolute top-0 w-1 h-full bg-white/50"
                    style={{ left: `${(chapter.start_time / duration) * 100}%` }}
                    title={chapter.title}
                  />
                ))}
                {/* Note markers */}
                {notes.map((note, i) => (
                  <div
                    key={i}
                    className="absolute top-0 w-2 h-2 bg-neon-yellow rounded-full -translate-y-1/2"
                    style={{ left: `${(note.timestamp_seconds / duration) * 100}%` }}
                    title={note.content}
                  />
                ))}
              </div>

              {/* Control buttons */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <button onClick={togglePlay} className="text-white hover:text-neon-cyan">
                    {isPlaying ? <Pause className="w-6 h-6" /> : <Play className="w-6 h-6" />}
                  </button>
                  <button onClick={() => skip(-10)} className="text-white hover:text-neon-cyan">
                    <SkipBack className="w-5 h-5" />
                  </button>
                  <button onClick={() => skip(10)} className="text-white hover:text-neon-cyan">
                    <SkipForward className="w-5 h-5" />
                  </button>
                  
                  {/* Volume */}
                  <div className="flex items-center gap-2">
                    <button onClick={toggleMute} className="text-white hover:text-neon-cyan">
                      {isMuted ? <VolumeX className="w-5 h-5" /> : <Volume2 className="w-5 h-5" />}
                    </button>
                    <input
                      type="range"
                      min="0"
                      max="1"
                      step="0.1"
                      value={isMuted ? 0 : volume}
                      onChange={handleVolumeChange}
                      className="w-20 accent-neon-cyan"
                    />
                  </div>

                  <span className="text-sm font-mono text-white/80">
                    {formatTime(currentTime)} / {formatTime(duration)}
                  </span>
                </div>

                <div className="flex items-center gap-3">
                  {/* Chapters */}
                  {video.chapters?.length > 0 && (
                    <button 
                      onClick={() => setShowChapters(!showChapters)}
                      className="text-white hover:text-neon-cyan"
                    >
                      <List className="w-5 h-5" />
                    </button>
                  )}
                  
                  {/* Notes */}
                  <button 
                    onClick={() => setShowNotes(!showNotes)}
                    className="text-white hover:text-neon-cyan"
                  >
                    <StickyNote className="w-5 h-5" />
                  </button>

                  {/* Settings */}
                  <div className="relative">
                    <button 
                      onClick={() => setShowSettings(!showSettings)}
                      className="text-white hover:text-neon-cyan"
                    >
                      <Settings className="w-5 h-5" />
                    </button>
                    {showSettings && (
                      <div className="absolute bottom-full right-0 mb-2 bg-black/95 border border-white/20 p-2 min-w-[120px]">
                        <p className="text-xs text-white/50 mb-2">Speed</p>
                        {[0.5, 0.75, 1, 1.25, 1.5, 2].map(rate => (
                          <button
                            key={rate}
                            onClick={() => changePlaybackRate(rate)}
                            className={`w-full text-left px-2 py-1 text-sm flex items-center justify-between ${
                              playbackRate === rate ? 'text-neon-cyan' : 'text-white hover:bg-white/10'
                            }`}
                          >
                            {rate}x
                            {playbackRate === rate && <Check className="w-4 h-4" />}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Fullscreen */}
                  <button onClick={toggleFullscreen} className="text-white hover:text-neon-cyan">
                    {isFullscreen ? <Minimize className="w-5 h-5" /> : <Maximize className="w-5 h-5" />}
                  </button>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Chapters panel */}
        <AnimatePresence>
          {showChapters && (
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
              className="absolute top-0 right-0 bottom-16 w-64 bg-black/95 border-l border-white/20 overflow-y-auto"
            >
              <div className="p-3 border-b border-white/10">
                <h4 className="font-mono text-sm text-neon-cyan">Chapters</h4>
              </div>
              <div className="p-2">
                {video.chapters?.map((chapter, i) => (
                  <button
                    key={i}
                    onClick={() => jumpToChapter(chapter.start_time)}
                    className={`w-full text-left p-2 text-sm hover:bg-white/10 ${
                      currentChapter?.title === chapter.title ? 'bg-neon-cyan/10 border-l-2 border-neon-cyan' : ''
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <span className="text-white/50 font-mono text-xs">{formatTime(chapter.start_time)}</span>
                      <span className="truncate">{chapter.title}</span>
                    </div>
                  </button>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Video info */}
      <CyberCard className="p-4">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="font-orbitron font-bold text-lg mb-1">{video.title}</h2>
            {video.description && <p className="text-sm text-white/60">{video.description}</p>}
            {currentChapter && (
              <p className="text-xs text-neon-cyan mt-2">
                <Clock className="inline w-3 h-3 mr-1" />
                {currentChapter.title}
              </p>
            )}
          </div>
          <div className="text-right text-sm text-white/50">
            <p>{video.views} views</p>
            <p>{video.likes} likes</p>
          </div>
        </div>
      </CyberCard>

      {/* Notes panel */}
      <AnimatePresence>
        {showNotes && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
          >
            <CyberCard className="p-4">
              <h3 className="font-orbitron font-bold text-sm mb-3 flex items-center gap-2">
                <StickyNote className="w-4 h-4 text-neon-yellow" />
                My Notes
              </h3>
              
              {/* Add note */}
              <div className="flex gap-2 mb-4">
                <input
                  type="text"
                  value={newNote}
                  onChange={(e) => setNewNote(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && addNote()}
                  placeholder={`Add note at ${formatTime(currentTime)}...`}
                  className="flex-1 bg-black/50 border border-white/20 px-3 py-2 text-sm focus:border-neon-cyan focus:outline-none"
                />
                <CyberButton onClick={addNote} disabled={!newNote.trim()}>
                  <BookmarkPlus className="w-4 h-4" />
                </CyberButton>
              </div>

              {/* Notes list */}
              <div className="space-y-2 max-h-60 overflow-y-auto">
                {notes.length > 0 ? notes.map(note => (
                  <div 
                    key={note.id}
                    className="p-2 bg-black/30 border border-white/10 flex items-start gap-2"
                  >
                    <button 
                      onClick={() => jumpToChapter(note.timestamp_seconds)}
                      className="text-neon-cyan font-mono text-xs hover:underline whitespace-nowrap"
                    >
                      {formatTime(note.timestamp_seconds)}
                    </button>
                    <p className="flex-1 text-sm">{note.content}</p>
                    <button 
                      onClick={() => deleteNote(note.id)}
                      className="text-white/30 hover:text-neon-red text-xs"
                    >
                      ×
                    </button>
                  </div>
                )) : (
                  <p className="text-white/40 text-sm text-center py-4">No notes yet</p>
                )}
              </div>
            </CyberCard>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default VideoPlayer;
