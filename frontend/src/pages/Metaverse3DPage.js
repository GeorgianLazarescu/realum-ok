import React, { useEffect, useRef, useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { 
  Home, Info, Layers, MapPin, Globe, Building2, Mountain,
  ZoomIn, ZoomOut, RotateCcw, Search, X, AlertTriangle, User,
  Users, Sun, Moon, Sunrise, Sunset, Calendar
} from 'lucide-react';
import axios from 'axios';
import { CyberCard, CyberButton } from '../components/common/CyberUI';
import LifeSimulationPanel from '../components/LifeSimulationPanel';

// Import Resium (React wrapper for Cesium)
import { Viewer, Entity, PointGraphics, LabelGraphics, CameraFlyTo } from 'resium';
import { Ion, Cartesian3, Color, createOsmBuildingsAsync, Math as CesiumMath, JulianDate, ClockRange, ClockStep } from 'cesium';

// Import Cesium CSS
import 'cesium/Build/Cesium/Widgets/widgets.css';

const API = process.env.REACT_APP_BACKEND_URL;

// Import Resium (React wrapper for Cesium)
import { Viewer, Entity, PointGraphics, LabelGraphics, CameraFlyTo } from 'resium';
import { Ion, Cartesian3, Color, createOsmBuildingsAsync, Math as CesiumMath } from 'cesium';

// Import Cesium CSS
import 'cesium/Build/Cesium/Widgets/widgets.css';

// Custom CSS to make Cesium fill container
const cesiumStyles = `
  #cesium-container .cesium-viewer,
  #cesium-container .cesium-viewer-cesiumWidgetContainer,
  #cesium-container .cesium-widget,
  #cesium-container .cesium-widget canvas {
    width: 100% !important;
    height: 100% !important;
    position: absolute !important;
    top: 0 !important;
    left: 0 !important;
  }
`;

// Set Cesium Ion token
const CESIUM_TOKEN = process.env.REACT_APP_CESIUM_ION_TOKEN;
if (CESIUM_TOKEN) {
  Ion.defaultAccessToken = CESIUM_TOKEN;
}

// Set base URL for Cesium assets
if (typeof window !== 'undefined') {
  window.CESIUM_BASE_URL = '/cesium/';
}

// REALUM zones mapped to real-world locations
const REALUM_ZONES = [
  { 
    id: 'learning', 
    name: 'Learning Zone', 
    city: 'Oxford, UK',
    coords: { lon: -1.2577, lat: 51.7520, height: 1000 },
    color: '#9D4EDD', 
    path: '/courses', 
    description: 'World-renowned education hub'
  },
  { 
    id: 'jobs', 
    name: 'Jobs Hub', 
    city: 'San Francisco, USA',
    coords: { lon: -122.4194, lat: 37.7749, height: 1000 },
    color: '#FF003C', 
    path: '/jobs', 
    description: 'Tech & innovation capital'
  },
  { 
    id: 'governance', 
    name: 'DAO Hall', 
    city: 'Zug, Switzerland',
    coords: { lon: 8.5156, lat: 47.1724, height: 1000 },
    color: '#40C4FF', 
    path: '/voting', 
    description: 'Crypto Valley governance'
  },
  { 
    id: 'marketplace', 
    name: 'Marketplace', 
    city: 'Dubai, UAE',
    coords: { lon: 55.2708, lat: 25.2048, height: 1000 },
    color: '#00FF88', 
    path: '/marketplace', 
    description: 'Global trade center'
  },
  { 
    id: 'social', 
    name: 'Social Plaza', 
    city: 'Tokyo, Japan',
    coords: { lon: 139.6917, lat: 35.6895, height: 1000 },
    color: '#00F0FF', 
    path: '/social', 
    description: 'Cultural connection hub'
  },
  { 
    id: 'treasury', 
    name: 'Treasury', 
    city: 'Singapore',
    coords: { lon: 103.8198, lat: 1.3521, height: 1000 },
    color: '#FFD700', 
    path: '/wallet', 
    description: 'Financial center'
  },
];

// WebGL support check
const checkWebGLSupport = () => {
  try {
    const canvas = document.createElement('canvas');
    const gl = canvas.getContext('webgl2') || canvas.getContext('webgl');
    return { supported: !!gl };
  } catch (e) {
    return { supported: false };
  }
};

// Browser compatibility error component
const BrowserCompatibilityError = () => {
  const navigate = useNavigate();
  
  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-900 via-black to-gray-900 flex items-center justify-center p-4">
      <CyberCard className="max-w-lg p-8 bg-black/90 border-red-500/50">
        <div className="text-center">
          <AlertTriangle className="w-16 h-16 text-red-500 mx-auto mb-4" />
          <h1 className="font-orbitron text-2xl font-bold text-red-500 mb-2">
            Browser Not Supported
          </h1>
          <p className="text-white/70 mb-6">
            The 3D Earth view requires WebGL. Please use Chrome, Firefox, or Edge.
          </p>
          <CyberButton onClick={() => navigate('/dashboard')}>
            <Home className="w-4 h-4 mr-2" />
            Back to Dashboard
          </CyberButton>
        </div>
      </CyberCard>
    </div>
  );
};

// Main Cesium 3D Page
const Metaverse3DPage = () => {
  const navigate = useNavigate();
  const viewerRef = useRef(null);
  
  const [isLoading, setIsLoading] = useState(true);
  const [selectedZone, setSelectedZone] = useState(null);
  const [showLayers, setShowLayers] = useState(false);
  const [showInfo, setShowInfo] = useState(true);
  const [showLifePanel, setShowLifePanel] = useState(false);
  const [showNPCs, setShowNPCs] = useState(true);
  const [flyToDestination, setFlyToDestination] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [webglSupport] = useState(() => checkWebGLSupport());
  const [worldTime, setWorldTime] = useState(null);
  const [npcs, setNpcs] = useState([]);
  const [activeEvents, setActiveEvents] = useState([]);
  const [selectedNPC, setSelectedNPC] = useState(null);

  // Fetch world time and NPCs on mount
  useEffect(() => {
    const fetchWorldData = async () => {
      try {
        const [timeRes, npcRes, eventsRes] = await Promise.all([
          axios.get(`${API}/api/events/world/time`),
          axios.get(`${API}/api/events/npcs`),
          axios.get(`${API}/api/events/calendar/active`)
        ]);
        setWorldTime(timeRes.data);
        setNpcs(npcRes.data.npcs || []);
        setActiveEvents(eventsRes.data.active_events || []);
      } catch (error) {
        console.error('Error fetching world data:', error);
      }
    };

    fetchWorldData();
    const interval = setInterval(fetchWorldData, 60000); // Update every minute
    return () => clearInterval(interval);
  }, []);

  // Handle viewer ready
  const handleViewerReady = useCallback(async (cesiumElement) => {
    if (!cesiumElement || !cesiumElement.cesiumElement) return;
    
    const viewer = cesiumElement.cesiumElement;
    viewerRef.current = viewer;

    // Set background color based on time of day
    const isNight = worldTime && !worldTime.is_day;
    viewer.scene.backgroundColor = Color.fromCssColorString(isNight ? '#000005' : '#000011');
    viewer.scene.globe.baseColor = Color.fromCssColorString(isNight ? '#050510' : '#0a0a1a');
    
    // Enable lighting for day/night cycle
    viewer.scene.globe.enableLighting = true;

    // Try to add OSM Buildings
    try {
      const osmBuildingsTileset = await createOsmBuildingsAsync();
      viewer.scene.primitives.add(osmBuildingsTileset);
    } catch (e) {
      console.warn('OSM Buildings not loaded:', e.message);
    }

    setIsLoading(false);
  }, [worldTime]);

  // Update scene lighting when world time changes
  useEffect(() => {
    if (viewerRef.current && worldTime) {
      const viewer = viewerRef.current;
      const isNight = !worldTime.is_day;
      viewer.scene.backgroundColor = Color.fromCssColorString(isNight ? '#000005' : '#000011');
      viewer.scene.globe.baseColor = Color.fromCssColorString(isNight ? '#050510' : '#0a0a1a');
    }
  }, [worldTime]);

  // Fly to zone
  const flyToZone = useCallback((zone) => {
    setSelectedZone(zone);
    setFlyToDestination({
      destination: Cartesian3.fromDegrees(
        zone.coords.lon,
        zone.coords.lat,
        zone.coords.height + 10000
      ),
      orientation: {
        heading: CesiumMath.toRadians(0),
        pitch: CesiumMath.toRadians(-35),
        roll: 0,
      },
      duration: 2,
    });
  }, []);

  // NPC locations mapped to real coordinates
  const getNPCLocation = (npc) => {
    const locationMap = {
      'Learning Zone': { lon: -1.2577, lat: 51.7520, height: 800 }, // Oxford
      'Marketplace': { lon: 55.2708, lat: 25.2048, height: 800 }, // Dubai
      'Social Plaza': { lon: 139.6917, lat: 35.6895, height: 800 }, // Tokyo
      'Wellness Center': { lon: 103.8198, lat: 1.3521, height: 800 }, // Singapore
      'Treasury': { lon: 103.8198, lat: 1.3521, height: 1200 }, // Singapore (higher)
      'Jobs Hub': { lon: -122.4194, lat: 37.7749, height: 800 }, // San Francisco
    };
    return locationMap[npc.location] || { lon: 0, lat: 0, height: 800 };
  };

  // Fly to NPC
  const flyToNPC = useCallback((npc) => {
    const loc = getNPCLocation(npc);
    setSelectedNPC(npc);
    setFlyToDestination({
      destination: Cartesian3.fromDegrees(loc.lon, loc.lat, loc.height + 5000),
      orientation: {
        heading: CesiumMath.toRadians(0),
        pitch: CesiumMath.toRadians(-45),
        roll: 0,
      },
      duration: 2,
    });
  }, []);

  // Reset view
  const resetView = useCallback(() => {
    setSelectedZone(null);
    setSelectedNPC(null);
    setFlyToDestination({
      destination: Cartesian3.fromDegrees(10, 20, 25000000),
      duration: 2,
    });
  }, []);

  // Search handler
  const handleSearch = useCallback(async (e) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;

    try {
      const response = await fetch(
        `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(searchQuery)}`
      );
      const data = await response.json();
      
      if (data && data.length > 0) {
        setFlyToDestination({
          destination: Cartesian3.fromDegrees(
            parseFloat(data[0].lon),
            parseFloat(data[0].lat),
            10000
          ),
          duration: 2,
        });
      }
    } catch (err) {
      console.error('Search failed:', err);
    }
  }, [searchQuery]);

  // Handle entity click
  const handleEntityClick = useCallback((entity) => {
    if (entity && entity.id && entity.id.properties) {
      const zoneData = entity.id.properties.zoneData;
      if (zoneData) {
        setSelectedZone(zoneData.getValue());
      }
    }
  }, []);

  // Show WebGL error if not supported
  if (!webglSupport.supported) {
    return <BrowserCompatibilityError />;
  }

  return (
    <div className="fixed inset-0 bg-black" data-testid="metaverse-3d-cesium-page">
      {/* Inject Cesium styles */}
      <style>{cesiumStyles}</style>
      
      {/* Cesium Viewer Container - Full Screen below navbar */}
      <div 
        id="cesium-container"
        style={{ 
          position: 'fixed',
          top: '64px',
          left: 0,
          right: 0,
          bottom: 0,
          overflow: 'hidden'
        }}
      >
        <Viewer
          ref={handleViewerReady}
          animation={false}
          baseLayerPicker={false}
          fullscreenButton={false}
          vrButton={false}
          geocoder={false}
          homeButton={false}
          infoBox={false}
          sceneModePicker={false}
          selectionIndicator={true}
          timeline={false}
          navigationHelpButton={false}
          onClick={handleEntityClick}
          className="cesium-fullscreen"
        >
          {/* Camera fly to */}
          {flyToDestination && (
            <CameraFlyTo
              destination={flyToDestination.destination}
              orientation={flyToDestination.orientation}
              duration={flyToDestination.duration}
              onComplete={() => setFlyToDestination(null)}
            />
          )}

          {/* REALUM Zone Markers */}
          {REALUM_ZONES.map(zone => (
            <Entity
              key={zone.id}
              name={zone.name}
              position={Cartesian3.fromDegrees(zone.coords.lon, zone.coords.lat, zone.coords.height)}
              properties={{ zoneData: zone }}
              onClick={() => flyToZone(zone)}
            >
              <PointGraphics
                pixelSize={20}
                color={Color.fromCssColorString(zone.color)}
                outlineColor={Color.WHITE}
                outlineWidth={3}
              />
              <LabelGraphics
                text={zone.name}
                font="16px sans-serif"
                fillColor={Color.fromCssColorString(zone.color)}
                outlineColor={Color.BLACK}
                outlineWidth={2}
                pixelOffset={new Cartesian3(0, -30, 0)}
              />
            </Entity>
          ))}

          {/* NPC Markers */}
          {showNPCs && npcs.map(npc => {
            const loc = getNPCLocation(npc);
            return (
              <Entity
                key={npc.id}
                name={npc.name}
                position={Cartesian3.fromDegrees(loc.lon, loc.lat, loc.height)}
                onClick={() => flyToNPC(npc)}
              >
                <PointGraphics
                  pixelSize={npc.available ? 14 : 10}
                  color={Color.fromCssColorString(npc.available ? '#FFD700' : '#666666')}
                  outlineColor={Color.WHITE}
                  outlineWidth={2}
                />
                <LabelGraphics
                  text={`${npc.avatar} ${npc.name}`}
                  font="12px sans-serif"
                  fillColor={Color.fromCssColorString(npc.available ? '#FFD700' : '#888888')}
                  outlineColor={Color.BLACK}
                  outlineWidth={2}
                  pixelOffset={new Cartesian3(0, -25, 0)}
                />
              </Entity>
            );
          })}
        </Viewer>
      </div>

      {/* Loading Overlay */}
      {isLoading && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/90" style={{ top: '64px' }}>
          <div className="text-center">
            <div className="relative w-24 h-24 mx-auto mb-6">
              <Globe className="w-24 h-24 text-neon-cyan animate-pulse" />
              <div className="absolute inset-0 border-4 border-neon-cyan/30 border-t-neon-cyan rounded-full animate-spin" />
            </div>
            <p className="text-neon-cyan font-mono text-lg">Loading 3D Earth...</p>
            <p className="text-white/40 text-sm mt-2">Powered by OpenStreetMap & Cesium</p>
          </div>
        </div>
      )}

      {/* Life Simulation Panel */}
      <LifeSimulationPanel isOpen={showLifePanel} onClose={() => setShowLifePanel(false)} />

      {/* UI Overlay */}
      {!isLoading && (
        <div className="fixed pointer-events-none" style={{ top: '64px', left: 0, right: 0, bottom: 0 }}>
          {/* Top controls */}
          <div className="absolute top-4 left-4 right-4 flex justify-between items-start pointer-events-auto">
            {/* Left controls */}
            <div className="flex flex-col gap-2">
              <button
                onClick={() => navigate('/dashboard')}
                className="p-2 bg-black/80 border border-white/30 hover:border-neon-cyan transition-colors"
                title="Dashboard"
              >
                <Home className="w-5 h-5 text-white" />
              </button>
              <button
                onClick={() => setShowLayers(!showLayers)}
                className={`p-2 bg-black/80 border transition-colors ${showLayers ? 'border-neon-cyan' : 'border-white/30 hover:border-neon-cyan'}`}
                title="Layers"
              >
                <Layers className="w-5 h-5 text-white" />
              </button>
              <button
                onClick={() => setShowNPCs(!showNPCs)}
                className={`p-2 bg-black/80 border transition-colors ${showNPCs ? 'border-yellow-500' : 'border-white/30 hover:border-yellow-500'}`}
                title="Toggle NPCs"
              >
                <Users className="w-5 h-5 text-yellow-400" />
              </button>
              <button
                onClick={() => setShowLifePanel(true)}
                className="p-2 bg-black/80 border border-purple-500/50 hover:border-purple-500 transition-colors"
                title="Life Simulation"
              >
                <User className="w-5 h-5 text-purple-400" />
              </button>
            </div>

            {/* Search bar */}
            <form onSubmit={handleSearch} className="flex-1 max-w-md mx-4">
              <div className="relative">
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search any location..."
                  className="w-full px-4 py-2 pl-10 bg-black/80 border border-white/30 focus:border-neon-cyan text-white placeholder-white/40 outline-none transition-colors"
                />
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/50" />
              </div>
            </form>

            {/* Right controls */}
            <div className="flex flex-col gap-2">
              <button
                onClick={() => setShowInfo(!showInfo)}
                className={`p-2 bg-black/80 border transition-colors ${showInfo ? 'border-neon-cyan' : 'border-white/30 hover:border-neon-cyan'}`}
              >
                <Info className="w-5 h-5 text-white" />
              </button>
            </div>
          </div>

          {/* Zoom controls */}
          <div className="absolute right-4 top-1/2 -translate-y-1/2 flex flex-col gap-2 pointer-events-auto">
            <button
              onClick={resetView}
              className="p-2 bg-black/80 border border-white/30 hover:border-neon-cyan transition-colors"
              title="Reset View"
            >
              <RotateCcw className="w-5 h-5 text-white" />
            </button>
          </div>

          {/* Info panel */}
          <AnimatePresence>
            {showInfo && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 20 }}
                className="absolute top-20 right-4 w-72 pointer-events-auto"
              >
                <CyberCard className="p-4 bg-black/95">
                  <h3 className="font-orbitron font-bold text-neon-cyan mb-2">REALUM 3D EARTH</h3>
                  
                  {/* World Time Display */}
                  {worldTime && (
                    <div className="mb-3 p-2 bg-white/5 rounded-lg">
                      <div className="flex items-center gap-2 text-sm">
                        {worldTime.period === 'morning' && <Sunrise className="w-4 h-4 text-orange-400" />}
                        {worldTime.period === 'afternoon' && <Sun className="w-4 h-4 text-yellow-400" />}
                        {worldTime.period === 'evening' && <Sunset className="w-4 h-4 text-orange-500" />}
                        {worldTime.period === 'night' && <Moon className="w-4 h-4 text-blue-300" />}
                        <span className="text-white/80">{worldTime.description}</span>
                      </div>
                      <div className="text-xs text-white/40 mt-1">
                        Virtual Hour: {worldTime.virtual_hour}:00
                      </div>
                    </div>
                  )}
                  
                  <p className="text-xs text-white/60 mb-3">
                    Explore the world with real OpenStreetMap data and 3D buildings.
                    REALUM zones are marked at key global locations.
                  </p>
                  <div className="text-xs text-white/40 space-y-1">
                    <p>• Drag to rotate globe</p>
                    <p>• Scroll to zoom</p>
                    <p>• Click markers for zones</p>
                    <p>• Yellow markers = NPCs</p>
                  </div>
                </CyberCard>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Active Events Banner */}
          {activeEvents.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="absolute top-20 left-1/2 -translate-x-1/2 pointer-events-auto"
            >
              <CyberCard className="px-4 py-2 bg-gradient-to-r from-purple-900/90 to-pink-900/90 border-purple-500/50">
                <div className="flex items-center gap-3">
                  <Calendar className="w-5 h-5 text-purple-400" />
                  <div>
                    <p className="text-xs text-purple-300 font-bold">{activeEvents[0].name}</p>
                    <p className="text-xs text-white/60">
                      {activeEvents[0].bonus_rlm > 0 && `+${activeEvents[0].bonus_rlm} RLM bonus`}
                      {activeEvents[0].bonus_xp > 1 && ` • ${activeEvents[0].bonus_xp}x XP`}
                      {activeEvents[0].days_remaining !== undefined && ` • ${activeEvents[0].days_remaining} days left`}
                    </p>
                  </div>
                </div>
              </CyberCard>
            </motion.div>
          )}

          {/* Zone list */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            className="absolute bottom-24 lg:bottom-8 left-4 hidden lg:block pointer-events-auto"
          >
            <CyberCard className="p-3 bg-black/95">
              <h4 className="text-xs font-mono text-white/50 mb-2 flex items-center gap-2">
                <MapPin className="w-3 h-3" />
                REALUM ZONES
              </h4>
              <div className="space-y-1 max-h-64 overflow-y-auto">
                {REALUM_ZONES.map(zone => (
                  <button
                    key={zone.id}
                    onClick={() => flyToZone(zone)}
                    className={`w-full flex items-center gap-2 px-2 py-1.5 text-xs transition-colors rounded ${
                      selectedZone?.id === zone.id ? 'bg-white/10' : 'hover:bg-white/5'
                    }`}
                  >
                    <div 
                      className="w-2 h-2 rounded-full flex-shrink-0"
                      style={{ backgroundColor: zone.color }}
                    />
                    <div className="text-left flex-1 min-w-0">
                      <span 
                        className="block truncate"
                        style={{ color: selectedZone?.id === zone.id ? zone.color : 'white' }}
                      >
                        {zone.name}
                      </span>
                      <span className="block text-white/40 truncate text-[10px]">
                        {zone.city}
                      </span>
                    </div>
                  </button>
                ))}
              </div>
            </CyberCard>
          </motion.div>

          {/* Selected zone panel */}
          <AnimatePresence>
            {selectedZone && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 20 }}
                className="absolute bottom-24 lg:bottom-8 right-4 lg:w-80 pointer-events-auto"
              >
                <CyberCard 
                  className="p-4 bg-black/95" 
                  style={{ borderColor: selectedZone.color }}
                >
                  <button
                    onClick={() => setSelectedZone(null)}
                    className="absolute top-2 right-2 p-1 hover:bg-white/10 rounded transition-colors"
                  >
                    <X className="w-4 h-4 text-white/60" />
                  </button>
                  
                  <div className="flex items-center gap-3 mb-3">
                    <div 
                      className="w-12 h-12 flex items-center justify-center border rounded"
                      style={{ borderColor: selectedZone.color, backgroundColor: `${selectedZone.color}20` }}
                    >
                      <MapPin className="w-6 h-6" style={{ color: selectedZone.color }} />
                    </div>
                    <div>
                      <h3 className="font-orbitron font-bold" style={{ color: selectedZone.color }}>
                        {selectedZone.name}
                      </h3>
                      <p className="text-xs text-white/60">{selectedZone.city}</p>
                    </div>
                  </div>
                  
                  <p className="text-sm text-white/70 mb-4">{selectedZone.description}</p>
                  
                  <CyberButton 
                    onClick={() => navigate(selectedZone.path)}
                    className="w-full"
                  >
                    Enter Zone
                  </CyberButton>
                </CyberCard>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      )}
    </div>
  );
};

export default Metaverse3DPage;
