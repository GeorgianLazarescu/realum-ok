import React, { useEffect, useRef, useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { 
  Home, Info, Layers, MapPin, Globe, Building2, Mountain,
  ZoomIn, ZoomOut, RotateCcw, Search, X, AlertTriangle
} from 'lucide-react';
import { CyberCard, CyberButton } from '../components/common/CyberUI';

// Set Cesium base URL before importing
window.CESIUM_BASE_URL = '/cesium/';

// Import Cesium
import {
  Ion,
  Viewer,
  Cartesian3,
  Color,
  OpenStreetMapImageryProvider,
  createOsmBuildingsAsync,
  Math as CesiumMath,
  ScreenSpaceEventType,
  defined,
  HeightReference,
  VerticalOrigin,
  Cartesian2,
  LabelStyle
} from 'cesium';
import 'cesium/Build/Cesium/Widgets/widgets.css';

// Set Cesium Ion token
const CESIUM_TOKEN = process.env.REACT_APP_CESIUM_ION_TOKEN;
if (CESIUM_TOKEN) {
  Ion.defaultAccessToken = CESIUM_TOKEN;
}

// REALUM zones mapped to real-world locations
const REALUM_ZONES = [
  { 
    id: 'learning', 
    name: 'Learning Zone', 
    city: 'Oxford, UK',
    coords: { lon: -1.2577, lat: 51.7520, height: 500 },
    color: '#9D4EDD', 
    path: '/courses', 
    description: 'World-renowned education hub'
  },
  { 
    id: 'jobs', 
    name: 'Jobs Hub', 
    city: 'San Francisco, USA',
    coords: { lon: -122.4194, lat: 37.7749, height: 500 },
    color: '#FF003C', 
    path: '/jobs', 
    description: 'Tech & innovation capital'
  },
  { 
    id: 'governance', 
    name: 'DAO Hall', 
    city: 'Zug, Switzerland',
    coords: { lon: 8.5156, lat: 47.1724, height: 500 },
    color: '#40C4FF', 
    path: '/voting', 
    description: 'Crypto Valley governance'
  },
  { 
    id: 'marketplace', 
    name: 'Marketplace', 
    city: 'Dubai, UAE',
    coords: { lon: 55.2708, lat: 25.2048, height: 500 },
    color: '#00FF88', 
    path: '/marketplace', 
    description: 'Global trade center'
  },
  { 
    id: 'social', 
    name: 'Social Plaza', 
    city: 'Tokyo, Japan',
    coords: { lon: 139.6917, lat: 35.6895, height: 500 },
    color: '#00F0FF', 
    path: '/social', 
    description: 'Cultural connection hub'
  },
  { 
    id: 'treasury', 
    name: 'Treasury', 
    city: 'Singapore',
    coords: { lon: 103.8198, lat: 1.3521, height: 500 },
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
    return { supported: false, error: e.message };
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
            The 3D Earth view requires WebGL which is not available in your browser.
            Please use Chrome, Firefox, or the latest Edge.
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

// Loading screen
const LoadingScreen = ({ message }) => (
  <div className="min-h-screen flex items-center justify-center bg-black" data-testid="cesium-loading">
    <div className="text-center">
      <div className="relative w-24 h-24 mx-auto mb-6">
        <Globe className="w-24 h-24 text-neon-cyan animate-pulse" />
        <div className="absolute inset-0 border-4 border-neon-cyan/30 border-t-neon-cyan rounded-full animate-spin" />
      </div>
      <p className="text-neon-cyan font-mono text-lg">{message || 'Loading 3D Earth...'}</p>
      <p className="text-white/40 text-sm mt-2">Powered by OpenStreetMap & Cesium</p>
    </div>
  </div>
);

// Main Cesium 3D Page
const Metaverse3DPage = () => {
  const navigate = useNavigate();
  const cesiumContainerRef = useRef(null);
  const viewerRef = useRef(null);
  
  const [isLoading, setIsLoading] = useState(true);
  const [loadingMessage, setLoadingMessage] = useState('Initializing...');
  const [error, setError] = useState(null);
  const [selectedZone, setSelectedZone] = useState(null);
  const [showLayers, setShowLayers] = useState(false);
  const [showInfo, setShowInfo] = useState(true);
  const [layers, setLayers] = useState({
    osmBuildings: true,
    terrain: true,
    osmImagery: true,
  });
  const [searchQuery, setSearchQuery] = useState('');
  const [webglSupport, setWebglSupport] = useState({ supported: true }); // Default to true

  // Check WebGL support on mount
  useEffect(() => {
    const support = checkWebGLSupport();
    setWebglSupport(support);
    if (!support.supported) {
      setIsLoading(false);
    }
  }, []);

  // Initialize Cesium viewer
  useEffect(() => {
    if (!cesiumContainerRef.current) return;
    if (viewerRef.current) return; // Already initialized

    let viewer = null;

    const initViewer = async () => {
      try {
        setLoadingMessage('Creating 3D globe...');
        console.log('Initializing Cesium viewer...');
        
        // Create the viewer
        viewer = new Viewer(cesiumContainerRef.current, {
          animation: false,
          baseLayerPicker: false,
          fullscreenButton: false,
          vrButton: false,
          geocoder: false,
          homeButton: false,
          infoBox: false,
          sceneModePicker: false,
          selectionIndicator: true,
          timeline: false,
          navigationHelpButton: false,
          creditContainer: document.createElement('div'),
        });

        viewerRef.current = viewer;
        console.log('Viewer created successfully');

        // Set dark background
        viewer.scene.backgroundColor = Color.fromCssColorString('#000011');
        viewer.scene.globe.baseColor = Color.fromCssColorString('#0a0a1a');
        viewer.scene.globe.enableLighting = false;

        setLoadingMessage('Loading OpenStreetMap...');
        console.log('Adding OSM imagery...');
        
        // Add OpenStreetMap imagery
        viewer.imageryLayers.removeAll();
        const osmImagery = new OpenStreetMapImageryProvider({
          url: 'https://tile.openstreetmap.org/'
        });
        viewer.imageryLayers.addImageryProvider(osmImagery);

        setLoadingMessage('Loading 3D buildings...');
        console.log('Adding OSM buildings...');
        
        // Add OSM Buildings 3D tileset
        try {
          const osmBuildingsTileset = await createOsmBuildingsAsync();
          viewer.scene.primitives.add(osmBuildingsTileset);
          console.log('OSM buildings added');
        } catch (e) {
          console.warn('OSM Buildings not loaded:', e.message);
        }

        setLoadingMessage('Adding REALUM zones...');
        console.log('Adding zone markers...');

        // Add REALUM zone markers
        if (viewer && viewer.entities) {
          REALUM_ZONES.forEach(zone => {
            viewer.entities.add({
              name: zone.name,
              position: Cartesian3.fromDegrees(
                zone.coords.lon, 
                zone.coords.lat, 
                zone.coords.height
              ),
              point: {
                pixelSize: 20,
                color: Color.fromCssColorString(zone.color),
                outlineColor: Color.WHITE,
                outlineWidth: 3,
                heightReference: HeightReference.RELATIVE_TO_GROUND,
            },
            label: {
              text: zone.name,
              font: '16px sans-serif',
              fillColor: Color.fromCssColorString(zone.color),
              outlineColor: Color.BLACK,
              outlineWidth: 2,
              style: LabelStyle.FILL_AND_OUTLINE,
              verticalOrigin: VerticalOrigin.BOTTOM,
              pixelOffset: new Cartesian2(0, -25),
            },
            properties: {
              zoneId: zone.id,
              zonePath: zone.path,
              zoneData: zone,
            }
          });
        });
        }

        // Click handler for zones
        if (viewer && viewer.screenSpaceEventHandler) {
          viewer.screenSpaceEventHandler.setInputAction((click) => {
            const pickedObject = viewer.scene.pick(click.position);
            if (defined(pickedObject) && pickedObject.id) {
              const entity = pickedObject.id;
              if (entity.properties && entity.properties.zoneData) {
                const zoneData = entity.properties.zoneData.getValue();
                setSelectedZone(zoneData);
              }
            } else {
              setSelectedZone(null);
            }
          }, ScreenSpaceEventType.LEFT_CLICK);
        }

        // Set initial camera position (overview of Earth)
        viewer.camera.setView({
          destination: Cartesian3.fromDegrees(10, 20, 25000000),
        });

        setIsLoading(false);
        setLoadingMessage('');

      } catch (err) {
        console.error('Cesium Error:', err);
        setError(err.message);
        setIsLoading(false);
      }
    };

    initViewer();

    // Cleanup
    return () => {
      if (viewerRef.current && !viewerRef.current.isDestroyed()) {
        viewerRef.current.destroy();
        viewerRef.current = null;
      }
    };
  }, []); // Remove webglSupport dependency

  // Fly to zone
  const flyToZone = useCallback((zone) => {
    if (!viewerRef.current) return;
    
    setSelectedZone(zone);
    viewerRef.current.camera.flyTo({
      destination: Cartesian3.fromDegrees(
        zone.coords.lon,
        zone.coords.lat,
        zone.coords.height + 5000
      ),
      orientation: {
        heading: CesiumMath.toRadians(0),
        pitch: CesiumMath.toRadians(-35),
        roll: 0,
      },
      duration: 2,
    });
  }, []);

  // Camera controls
  const zoomIn = useCallback(() => {
    if (!viewerRef.current) return;
    const camera = viewerRef.current.camera;
    camera.zoomIn(camera.positionCartographic.height * 0.3);
  }, []);

  const zoomOut = useCallback(() => {
    if (!viewerRef.current) return;
    const camera = viewerRef.current.camera;
    camera.zoomOut(camera.positionCartographic.height * 0.3);
  }, []);

  const resetView = useCallback(() => {
    if (!viewerRef.current) return;
    viewerRef.current.camera.flyTo({
      destination: Cartesian3.fromDegrees(10, 20, 25000000),
      duration: 2,
    });
    setSelectedZone(null);
  }, []);

  // Toggle layers
  const toggleLayer = useCallback((layerName) => {
    if (!viewerRef.current) return;

    setLayers(prev => {
      const newState = { ...prev, [layerName]: !prev[layerName] };

      if (layerName === 'osmBuildings') {
        const primitives = viewerRef.current.scene.primitives;
        for (let i = 0; i < primitives.length; i++) {
          const p = primitives.get(i);
          if (p.asset && p.asset.id === 96188) {
            p.show = newState.osmBuildings;
          }
        }
      } else if (layerName === 'terrain') {
        viewerRef.current.scene.globe.show = newState.terrain;
      } else if (layerName === 'osmImagery') {
        if (viewerRef.current.imageryLayers.length > 0) {
          viewerRef.current.imageryLayers.get(0).show = newState.osmImagery;
        }
      }

      return newState;
    });
  }, []);

  // Search handler
  const handleSearch = useCallback(async (e) => {
    e.preventDefault();
    if (!searchQuery.trim() || !viewerRef.current) return;

    try {
      // Use OpenStreetMap Nominatim for geocoding
      const response = await fetch(
        `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(searchQuery)}`
      );
      const data = await response.json();
      
      if (data && data.length > 0) {
        viewerRef.current.camera.flyTo({
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

  // Show WebGL error if not supported
  if (webglSupport && !webglSupport.supported) {
    return <BrowserCompatibilityError />;
  }

  // Show error
  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-black p-4">
        <CyberCard className="max-w-lg p-8 bg-black/90 border-red-500/50">
          <div className="text-center">
            <AlertTriangle className="w-16 h-16 text-red-500 mx-auto mb-4" />
            <h1 className="font-orbitron text-xl font-bold text-red-500 mb-2">
              Failed to Load 3D Earth
            </h1>
            <p className="text-white/70 mb-4 text-sm">{error}</p>
            <CyberButton onClick={() => window.location.reload()}>
              Try Again
            </CyberButton>
          </div>
        </CyberCard>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-black relative" data-testid="metaverse-3d-cesium-page">
      {/* Cesium Container - ALWAYS RENDER so ref is available */}
      <div 
        ref={cesiumContainerRef} 
        className="absolute inset-0 pt-16"
        style={{ background: '#000011' }}
      />

      {/* Loading Overlay */}
      {isLoading && (
        <div className="absolute inset-0 z-50 flex items-center justify-center bg-black/90">
          <div className="text-center">
            <div className="relative w-24 h-24 mx-auto mb-6">
              <Globe className="w-24 h-24 text-neon-cyan animate-pulse" />
              <div className="absolute inset-0 border-4 border-neon-cyan/30 border-t-neon-cyan rounded-full animate-spin" />
            </div>
            <p className="text-neon-cyan font-mono text-lg">{loadingMessage || 'Loading 3D Earth...'}</p>
            <p className="text-white/40 text-sm mt-2">Powered by OpenStreetMap & Cesium</p>
          </div>
        </div>
      )}

      {/* UI Overlay */}
      {!isLoading && (
      <div className="absolute inset-0 pointer-events-none pt-16">
        {/* Top controls */}
        <div className="absolute top-20 left-4 right-4 flex justify-between items-start pointer-events-auto">
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
            onClick={zoomIn}
            className="p-2 bg-black/80 border border-white/30 hover:border-neon-cyan transition-colors"
            title="Zoom In"
          >
            <ZoomIn className="w-5 h-5 text-white" />
          </button>
          <button
            onClick={zoomOut}
            className="p-2 bg-black/80 border border-white/30 hover:border-neon-cyan transition-colors"
            title="Zoom Out"
          >
            <ZoomOut className="w-5 h-5 text-white" />
          </button>
          <button
            onClick={resetView}
            className="p-2 bg-black/80 border border-white/30 hover:border-neon-cyan transition-colors"
            title="Reset View"
          >
            <RotateCcw className="w-5 h-5 text-white" />
          </button>
        </div>

        {/* Layers panel */}
        <AnimatePresence>
          {showLayers && (
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              className="absolute top-36 left-4 w-64 pointer-events-auto"
            >
              <CyberCard className="p-4 bg-black/95">
                <h3 className="font-orbitron font-bold text-neon-cyan mb-3 flex items-center gap-2">
                  <Layers className="w-4 h-4" />
                  MAP LAYERS
                </h3>
                <div className="space-y-2">
                  <label className="flex items-center gap-3 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={layers.osmImagery}
                      onChange={() => toggleLayer('osmImagery')}
                      className="w-4 h-4 accent-neon-cyan"
                    />
                    <Globe className="w-4 h-4 text-white/60" />
                    <span className="text-sm text-white/80">OpenStreetMap</span>
                  </label>
                  <label className="flex items-center gap-3 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={layers.osmBuildings}
                      onChange={() => toggleLayer('osmBuildings')}
                      className="w-4 h-4 accent-neon-cyan"
                    />
                    <Building2 className="w-4 h-4 text-white/60" />
                    <span className="text-sm text-white/80">3D Buildings</span>
                  </label>
                  <label className="flex items-center gap-3 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={layers.terrain}
                      onChange={() => toggleLayer('terrain')}
                      className="w-4 h-4 accent-neon-cyan"
                    />
                    <Mountain className="w-4 h-4 text-white/60" />
                    <span className="text-sm text-white/80">Globe</span>
                  </label>
                </div>
              </CyberCard>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Info panel */}
        <AnimatePresence>
          {showInfo && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 20 }}
              className="absolute top-36 right-4 w-72 pointer-events-auto"
            >
              <CyberCard className="p-4 bg-black/95">
                <h3 className="font-orbitron font-bold text-neon-cyan mb-2">REALUM 3D EARTH</h3>
                <p className="text-xs text-white/60 mb-3">
                  Explore the world with real OpenStreetMap data and 3D buildings.
                  REALUM zones are marked at key global locations.
                </p>
                <div className="text-xs text-white/40 space-y-1">
                  <p>• Drag to rotate globe</p>
                  <p>• Scroll to zoom</p>
                  <p>• Click markers for zones</p>
                  <p>• Search any location</p>
                </div>
              </CyberCard>
            </motion.div>
          )}
        </AnimatePresence>

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
