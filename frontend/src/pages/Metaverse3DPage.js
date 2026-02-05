import React, { useRef, useState, Suspense, useEffect } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Stars, Html } from '@react-three/drei';
import * as THREE from 'three';
import { motion, AnimatePresence } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { 
  Maximize2, Minimize2, Home, Info, AlertTriangle, Chrome, Monitor,
  GraduationCap, Briefcase, Vote, Wallet, ShoppingBag, Users
} from 'lucide-react';
import { CyberCard, CyberButton } from '../components/common/CyberUI';

// WebGL2 compatibility check
const checkWebGLSupport = () => {
  try {
    const canvas = document.createElement('canvas');
    const gl = canvas.getContext('webgl2') || canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
    if (!gl) return { supported: false, version: null };
    
    const isWebGL2 = gl instanceof WebGL2RenderingContext;
    return { 
      supported: true, 
      version: isWebGL2 ? 2 : 1,
      renderer: gl.getParameter(gl.RENDERER),
      vendor: gl.getParameter(gl.VENDOR)
    };
  } catch (e) {
    return { supported: false, version: null, error: e.message };
  }
};

// Browser compatibility error component
const BrowserCompatibilityError = ({ webglInfo }) => {
  const navigate = useNavigate();
  
  return (
    <div 
      className="min-h-screen bg-gradient-to-b from-gray-900 via-black to-gray-900 flex items-center justify-center p-4"
      data-testid="webgl-error-page"
    >
      <div className="max-w-lg w-full">
        <CyberCard className="p-8 bg-black/90 border-red-500/50">
          <div className="text-center">
            {/* Warning Icon */}
            <div className="w-20 h-20 mx-auto mb-6 rounded-full bg-red-500/20 flex items-center justify-center border-2 border-red-500/50">
              <AlertTriangle className="w-10 h-10 text-red-500" />
            </div>
            
            {/* Title */}
            <h1 className="font-orbitron text-2xl font-bold text-red-500 mb-2">
              Browser Not Supported
            </h1>
            
            {/* Message */}
            <p className="text-white/70 mb-6">
              The 3D Metaverse requires <span className="text-neon-cyan font-semibold">WebGL2</span> technology 
              which is not available in your current browser.
            </p>
            
            {/* Technical Details */}
            <div className="bg-gray-900/50 rounded-lg p-4 mb-6 text-left">
              <p className="text-xs font-mono text-white/40 mb-2">DIAGNOSTIC INFO:</p>
              <div className="text-xs text-white/60 space-y-1">
                <p>• WebGL Support: <span className={webglInfo?.supported ? 'text-yellow-500' : 'text-red-500'}>
                  {webglInfo?.supported ? `Version ${webglInfo.version} (needs v2)` : 'Not Available'}
                </span></p>
                <p>• Browser: <span className="text-white/40">{navigator.userAgent.split(' ').slice(-2).join(' ')}</span></p>
              </div>
            </div>
            
            {/* Recommended Browsers */}
            <div className="mb-6">
              <p className="text-sm text-white/60 mb-3">Please use a modern browser:</p>
              <div className="flex justify-center gap-4">
                <a 
                  href="https://www.google.com/chrome/" 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="flex flex-col items-center gap-2 p-3 bg-white/5 hover:bg-white/10 rounded-lg transition-colors group"
                >
                  <Chrome className="w-8 h-8 text-white/60 group-hover:text-neon-cyan transition-colors" />
                  <span className="text-xs text-white/60 group-hover:text-white transition-colors">Chrome</span>
                </a>
                <a 
                  href="https://www.mozilla.org/firefox/" 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="flex flex-col items-center gap-2 p-3 bg-white/5 hover:bg-white/10 rounded-lg transition-colors group"
                >
                  <Monitor className="w-8 h-8 text-white/60 group-hover:text-orange-500 transition-colors" />
                  <span className="text-xs text-white/60 group-hover:text-white transition-colors">Firefox</span>
                </a>
                <a 
                  href="https://www.microsoft.com/edge" 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="flex flex-col items-center gap-2 p-3 bg-white/5 hover:bg-white/10 rounded-lg transition-colors group"
                >
                  <Monitor className="w-8 h-8 text-white/60 group-hover:text-blue-500 transition-colors" />
                  <span className="text-xs text-white/60 group-hover:text-white transition-colors">Edge</span>
                </a>
              </div>
            </div>
            
            {/* Actions */}
            <div className="flex gap-3 justify-center">
              <CyberButton 
                onClick={() => navigate('/metaverse')}
                className="px-6"
              >
                <Home className="w-4 h-4 mr-2" />
                Use 2D Map Instead
              </CyberButton>
            </div>
            
            <p className="text-xs text-white/30 mt-4">
              The 2D map offers similar navigation without requiring WebGL2.
            </p>
          </div>
        </CyberCard>
      </div>
    </div>
  );
};

// Zone configurations
const ZONES = [
  { id: 'learning', name: 'Learning Zone', position: [-12, 0, -12], color: '#9D4EDD', icon: GraduationCap, path: '/courses', description: 'Courses & Education' },
  { id: 'jobs', name: 'Jobs Hub', position: [12, 0, -12], color: '#FF003C', icon: Briefcase, path: '/jobs', description: 'Find Work & Bounties' },
  { id: 'governance', name: 'DAO Hall', position: [-12, 0, 12], color: '#40C4FF', icon: Vote, path: '/voting', description: 'Vote on Proposals' },
  { id: 'marketplace', name: 'Marketplace', position: [12, 0, 12], color: '#00FF88', icon: ShoppingBag, path: '/marketplace', description: 'Trade Resources' },
  { id: 'social', name: 'Social Plaza', position: [0, 0, 0], color: '#00F0FF', icon: Users, path: '/social', description: 'Connect with Others' },
  { id: 'treasury', name: 'Treasury', position: [0, 0, -18], color: '#FFD700', icon: Wallet, path: '/wallet', description: 'Manage Tokens' },
];

// Ground component
function Ground() {
  return (
    <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.5, 0]} receiveShadow>
      <planeGeometry args={[80, 80]} />
      <meshStandardMaterial color="#111122" />
    </mesh>
  );
}

// Grid helper
function Grid() {
  return (
    <gridHelper args={[80, 40, '#00F0FF', '#1a1a3e']} position={[0, -0.49, 0]} />
  );
}

// Zone Building
function ZoneBuilding({ zone, onSelect, isSelected }) {
  const groupRef = useRef();
  const [hovered, setHovered] = useState(false);
  
  useFrame((state) => {
    if (groupRef.current) {
      // Floating animation for the main cube
      const floatY = Math.sin(state.clock.elapsedTime + zone.position[0] * 0.1) * 0.3;
      groupRef.current.children[1].position.y = 3 + floatY;
      
      // Rotate when hovered
      if (hovered) {
        groupRef.current.children[1].rotation.y += 0.02;
      }
    }
  });

  return (
    <group ref={groupRef} position={zone.position}>
      {/* Base platform */}
      <mesh position={[0, 0, 0]} receiveShadow castShadow>
        <cylinderGeometry args={[4, 4.5, 0.5, 6]} />
        <meshStandardMaterial 
          color={zone.color}
          emissive={zone.color}
          emissiveIntensity={hovered ? 0.5 : 0.2}
          metalness={0.8}
          roughness={0.2}
        />
      </mesh>
      
      {/* Floating cube building */}
      <mesh 
        position={[0, 3, 0]}
        castShadow
        onPointerOver={(e) => { e.stopPropagation(); setHovered(true); }}
        onPointerOut={() => setHovered(false)}
        onClick={(e) => { e.stopPropagation(); onSelect(zone); }}
      >
        <boxGeometry args={[3, 3, 3]} />
        <meshStandardMaterial 
          color={hovered ? '#ffffff' : zone.color}
          emissive={zone.color}
          emissiveIntensity={hovered ? 0.8 : 0.4}
          metalness={0.6}
          roughness={0.3}
        />
      </mesh>
      
      {/* Glowing ring around base */}
      <mesh position={[0, 0.3, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <ringGeometry args={[4.2, 4.8, 32]} />
        <meshBasicMaterial 
          color={zone.color}
          transparent
          opacity={hovered ? 0.9 : 0.5}
          side={THREE.DoubleSide}
        />
      </mesh>

      {/* Label */}
      <Html position={[0, 6, 0]} center distanceFactor={20}>
        <div 
          className={`px-3 py-1.5 text-sm font-mono border whitespace-nowrap cursor-pointer transition-all ${
            hovered || isSelected ? 'bg-black border-white scale-110' : 'bg-black/80 border-white/40'
          }`}
          style={{ color: zone.color }}
          onClick={() => onSelect(zone)}
        >
          {zone.name}
        </div>
      </Html>
      
      {/* Beam when selected */}
      {isSelected && (
        <mesh position={[0, 8, 0]}>
          <cylinderGeometry args={[0.1, 0.1, 16, 8]} />
          <meshBasicMaterial color={zone.color} transparent opacity={0.6} />
        </mesh>
      )}
    </group>
  );
}

// Central tower
function CentralTower() {
  const towerRef = useRef();
  
  useFrame((state) => {
    if (towerRef.current) {
      towerRef.current.rotation.y += 0.005;
    }
  });

  return (
    <group position={[0, 0, 0]}>
      {/* Base */}
      <mesh position={[0, 0.5, 0]}>
        <cylinderGeometry args={[2, 2.5, 1, 8]} />
        <meshStandardMaterial color="#1a1a2e" metalness={0.9} roughness={0.1} />
      </mesh>
      
      {/* Rotating crystal */}
      <mesh ref={towerRef} position={[0, 4, 0]}>
        <octahedronGeometry args={[1.5, 0]} />
        <meshStandardMaterial 
          color="#00F0FF"
          emissive="#00F0FF"
          emissiveIntensity={0.6}
          metalness={0.7}
          roughness={0.2}
          transparent
          opacity={0.9}
        />
      </mesh>
      
      {/* Orbiting ring */}
      <mesh position={[0, 4, 0]} rotation={[Math.PI / 4, 0, 0]}>
        <torusGeometry args={[2.5, 0.08, 8, 32]} />
        <meshBasicMaterial color="#00F0FF" />
      </mesh>
    </group>
  );
}

// Scene with all 3D elements
function Scene({ onZoneSelect, selectedZone }) {
  return (
    <>
      {/* Lighting */}
      <ambientLight intensity={0.3} />
      <pointLight position={[0, 15, 0]} intensity={1.5} color="#00F0FF" />
      <pointLight position={[-15, 8, -15]} intensity={0.6} color="#9D4EDD" />
      <pointLight position={[15, 8, 15]} intensity={0.6} color="#00FF88" />
      <directionalLight position={[10, 20, 10]} intensity={0.5} castShadow />
      
      {/* Environment */}
      <Stars radius={100} depth={50} count={3000} factor={4} fade speed={0.5} />
      <fog attach="fog" args={['#000011', 25, 80]} />
      
      {/* Ground and grid */}
      <Ground />
      <Grid />
      
      {/* Central tower */}
      <CentralTower />
      
      {/* Zone buildings */}
      {ZONES.map(zone => (
        <ZoneBuilding 
          key={zone.id} 
          zone={zone} 
          onSelect={onZoneSelect}
          isSelected={selectedZone?.id === zone.id}
        />
      ))}
    </>
  );
}

// Loading fallback
function LoadingScreen() {
  return (
    <div className="absolute inset-0 flex items-center justify-center bg-black">
      <div className="text-center">
        <div className="w-16 h-16 border-4 border-neon-cyan/30 border-t-neon-cyan rounded-full animate-spin mx-auto mb-4" />
        <p className="text-neon-cyan font-mono">Loading 3D Metaverse...</p>
      </div>
    </div>
  );
}

// Main page component
const Metaverse3DPage = () => {
  const navigate = useNavigate();
  const [selectedZone, setSelectedZone] = useState(null);
  const [showInfo, setShowInfo] = useState(true);
  const [webglSupport, setWebglSupport] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const containerRef = useRef();

  // Check WebGL support on mount
  useEffect(() => {
    const checkSupport = () => {
      const result = checkWebGLSupport();
      setWebglSupport(result);
      setIsLoading(false);
    };
    
    // Small delay to ensure DOM is ready
    const timer = setTimeout(checkSupport, 100);
    return () => clearTimeout(timer);
  }, []);

  const handleZoneSelect = (zone) => {
    setSelectedZone(zone);
  };

  const handleEnterZone = () => {
    if (selectedZone) {
      navigate(selectedZone.path);
    }
  };

  // Show loading state
  if (isLoading) {
    return <LoadingScreen />;
  }

  // Show error if WebGL2 is not supported
  if (!webglSupport?.supported || webglSupport?.version < 2) {
    return <BrowserCompatibilityError webglInfo={webglSupport} />;
  }

  return (
    <div 
      ref={containerRef}
      className="min-h-screen bg-black relative"
      data-testid="metaverse-3d-page"
    >
      {/* 3D Canvas */}
      <div className="absolute inset-0 pt-16">
        <Suspense fallback={<LoadingScreen />}>
          <Canvas
            shadows
            camera={{ position: [25, 20, 25], fov: 50 }}
            gl={{ antialias: true, alpha: false }}
            onCreated={({ gl }) => {
              gl.setClearColor('#000011');
            }}
          >
            <OrbitControls 
              enablePan={true}
              enableZoom={true}
              enableRotate={true}
              minDistance={15}
              maxDistance={60}
              maxPolarAngle={Math.PI / 2.1}
              target={[0, 0, 0]}
            />
            <Scene 
              onZoneSelect={handleZoneSelect} 
              selectedZone={selectedZone}
            />
          </Canvas>
        </Suspense>
      </div>

      {/* UI Overlay */}
      <div className="absolute inset-0 pointer-events-none pt-16">
        {/* Top controls */}
        <div className="absolute top-20 left-4 right-4 flex justify-between items-start pointer-events-auto">
          <div className="flex gap-2">
            <button
              onClick={() => navigate('/metaverse')}
              className="p-2 bg-black/80 border border-white/30 hover:border-neon-cyan transition-colors"
              title="2D Map"
            >
              <Home className="w-5 h-5" />
            </button>
          </div>

          <button
            onClick={() => setShowInfo(!showInfo)}
            className="p-2 bg-black/80 border border-white/30 hover:border-neon-cyan transition-colors"
          >
            <Info className="w-5 h-5" />
          </button>
        </div>

        {/* Info panel */}
        <AnimatePresence>
          {showInfo && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 20 }}
              className="absolute top-32 right-4 w-64 pointer-events-auto"
            >
              <CyberCard className="p-4 bg-black/95">
                <h3 className="font-orbitron font-bold text-neon-cyan mb-2">REALUM 3D</h3>
                <p className="text-xs text-white/60 mb-3">
                  Explore the metaverse in 3D. Click on buildings to select zones.
                </p>
                <div className="text-xs text-white/40 space-y-1">
                  <p>• Drag to rotate view</p>
                  <p>• Scroll to zoom</p>
                  <p>• Click buildings to select</p>
                </div>
              </CyberCard>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Selected zone panel */}
        <AnimatePresence>
          {selectedZone && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 20 }}
              className="absolute bottom-24 lg:bottom-8 left-4 right-4 lg:left-auto lg:right-4 lg:w-80 pointer-events-auto"
            >
              <CyberCard className="p-4 bg-black/95" style={{ borderColor: selectedZone.color }}>
                <div className="flex items-center gap-3 mb-3">
                  <div 
                    className="w-12 h-12 flex items-center justify-center border"
                    style={{ borderColor: selectedZone.color, backgroundColor: `${selectedZone.color}20` }}
                  >
                    <selectedZone.icon className="w-6 h-6" style={{ color: selectedZone.color }} />
                  </div>
                  <div>
                    <h3 className="font-orbitron font-bold" style={{ color: selectedZone.color }}>
                      {selectedZone.name}
                    </h3>
                    <p className="text-xs text-white/60">{selectedZone.description}</p>
                  </div>
                </div>
                <CyberButton 
                  onClick={handleEnterZone}
                  className="w-full"
                >
                  Enter Zone
                </CyberButton>
              </CyberCard>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Zone legend */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          className="absolute bottom-24 lg:bottom-8 left-4 hidden lg:block pointer-events-auto"
        >
          <CyberCard className="p-3 bg-black/95">
            <h4 className="text-xs font-mono text-white/50 mb-2">ZONES</h4>
            <div className="space-y-1">
              {ZONES.map(zone => (
                <button
                  key={zone.id}
                  onClick={() => setSelectedZone(zone)}
                  className={`w-full flex items-center gap-2 px-2 py-1 text-xs transition-colors ${
                    selectedZone?.id === zone.id ? 'bg-white/10' : 'hover:bg-white/5'
                  }`}
                >
                  <div 
                    className="w-2 h-2 rounded-full"
                    style={{ backgroundColor: zone.color }}
                  />
                  <span style={{ color: selectedZone?.id === zone.id ? zone.color : 'white' }}>
                    {zone.name}
                  </span>
                </button>
              ))}
            </div>
          </CyberCard>
        </motion.div>
      </div>
    </div>
  );
};

export default Metaverse3DPage;
