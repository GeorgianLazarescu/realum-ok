import React, { useRef, useState, useEffect, Suspense } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { 
  OrbitControls, 
  PerspectiveCamera, 
  Environment,
  Text3D,
  Center,
  Float,
  Stars,
  Html,
  useTexture
} from '@react-three/drei';
import * as THREE from 'three';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { 
  Maximize2, Minimize2, Home, Users, Info, Volume2, VolumeX,
  GraduationCap, Briefcase, Vote, Wallet, ShoppingBag, Trophy
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { CyberCard, CyberButton } from '../components/common/CyberUI';

// Zone configurations
const ZONES = [
  { id: 'learning', name: 'Learning Zone', position: [-15, 0, -15], color: '#9D4EDD', icon: GraduationCap, path: '/courses', description: 'Courses & Education' },
  { id: 'jobs', name: 'Jobs Hub', position: [15, 0, -15], color: '#FF003C', icon: Briefcase, path: '/jobs', description: 'Find Work & Bounties' },
  { id: 'governance', name: 'DAO Hall', position: [-15, 0, 15], color: '#40C4FF', icon: Vote, path: '/voting', description: 'Vote on Proposals' },
  { id: 'marketplace', name: 'Marketplace', position: [15, 0, 15], color: '#00FF88', icon: ShoppingBag, path: '/marketplace', description: 'Trade Resources' },
  { id: 'social', name: 'Social Plaza', position: [0, 0, 0], color: '#00F0FF', icon: Users, path: '/social', description: 'Connect with Others' },
  { id: 'treasury', name: 'Treasury', position: [0, 0, -20], color: '#FFD700', icon: Wallet, path: '/wallet', description: 'Manage Tokens' },
];

// Glowing ground plane
function GroundPlane() {
  const meshRef = useRef();
  
  useFrame((state) => {
    if (meshRef.current) {
      meshRef.current.material.emissiveIntensity = 0.1 + Math.sin(state.clock.elapsedTime * 0.5) * 0.05;
    }
  });

  return (
    <mesh ref={meshRef} rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.1, 0]} receiveShadow>
      <planeGeometry args={[100, 100, 50, 50]} />
      <meshStandardMaterial 
        color="#0a0a0a"
        emissive="#00F0FF"
        emissiveIntensity={0.1}
        metalness={0.8}
        roughness={0.2}
        wireframe={false}
      />
    </mesh>
  );
}

// Grid lines on ground
function GridLines() {
  return (
    <gridHelper 
      args={[100, 50, '#00F0FF', '#1a1a2e']} 
      position={[0, 0.01, 0]}
    />
  );
}

// Zone Building Component
function ZoneBuilding({ zone, onSelect, isSelected }) {
  const meshRef = useRef();
  const [hovered, setHovered] = useState(false);
  
  useFrame((state) => {
    if (meshRef.current) {
      // Floating animation
      meshRef.current.position.y = 2 + Math.sin(state.clock.elapsedTime * 0.5 + zone.position[0]) * 0.3;
      
      // Rotation when hovered
      if (hovered) {
        meshRef.current.rotation.y += 0.01;
      }
    }
  });

  const Icon = zone.icon;

  return (
    <group position={zone.position}>
      {/* Base platform */}
      <mesh position={[0, 0.1, 0]} receiveShadow>
        <cylinderGeometry args={[5, 6, 0.3, 6]} />
        <meshStandardMaterial 
          color={zone.color}
          emissive={zone.color}
          emissiveIntensity={hovered ? 0.5 : 0.2}
          metalness={0.9}
          roughness={0.1}
        />
      </mesh>
      
      {/* Main building */}
      <mesh 
        ref={meshRef}
        position={[0, 2, 0]}
        castShadow
        onPointerOver={() => setHovered(true)}
        onPointerOut={() => setHovered(false)}
        onClick={() => onSelect(zone)}
      >
        <boxGeometry args={[4, 4, 4]} />
        <meshStandardMaterial 
          color={hovered ? '#ffffff' : zone.color}
          emissive={zone.color}
          emissiveIntensity={hovered ? 0.8 : 0.3}
          metalness={0.7}
          roughness={0.2}
          transparent
          opacity={0.9}
        />
      </mesh>
      
      {/* Glowing ring */}
      <mesh position={[0, 0.2, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <ringGeometry args={[5.5, 6, 32]} />
        <meshBasicMaterial 
          color={zone.color}
          transparent
          opacity={hovered ? 0.8 : 0.4}
        />
      </mesh>
      
      {/* Zone label */}
      <Html position={[0, 6, 0]} center distanceFactor={15}>
        <div 
          className={`px-3 py-1 whitespace-nowrap text-sm font-mono border transition-all cursor-pointer ${
            hovered ? 'bg-black/90 border-white scale-110' : 'bg-black/70 border-white/30'
          }`}
          style={{ color: zone.color }}
        >
          {zone.name}
        </div>
      </Html>
      
      {/* Vertical beam */}
      {hovered && (
        <mesh position={[0, 10, 0]}>
          <cylinderGeometry args={[0.1, 0.1, 20, 8]} />
          <meshBasicMaterial color={zone.color} transparent opacity={0.5} />
        </mesh>
      )}
    </group>
  );
}

// Avatar component for user presence
function Avatar({ position, username, isCurrentUser }) {
  const meshRef = useRef();
  
  useFrame((state) => {
    if (meshRef.current) {
      meshRef.current.position.y = 1 + Math.sin(state.clock.elapsedTime * 2) * 0.1;
    }
  });

  return (
    <group position={position}>
      <mesh ref={meshRef} castShadow>
        <capsuleGeometry args={[0.3, 0.8, 4, 8]} />
        <meshStandardMaterial 
          color={isCurrentUser ? '#00F0FF' : '#9D4EDD'}
          emissive={isCurrentUser ? '#00F0FF' : '#9D4EDD'}
          emissiveIntensity={0.3}
        />
      </mesh>
      <Html position={[0, 2, 0]} center>
        <div className="px-2 py-0.5 bg-black/80 border border-white/30 text-xs whitespace-nowrap">
          {username}
        </div>
      </Html>
    </group>
  );
}

// Central tower
function CentralTower() {
  const meshRef = useRef();
  
  useFrame((state) => {
    if (meshRef.current) {
      meshRef.current.rotation.y += 0.002;
    }
  });

  return (
    <group position={[0, 0, 0]}>
      {/* Base */}
      <mesh position={[0, 0.5, 0]}>
        <cylinderGeometry args={[3, 4, 1, 8]} />
        <meshStandardMaterial color="#1a1a2e" metalness={0.9} roughness={0.1} />
      </mesh>
      
      {/* Tower */}
      <mesh ref={meshRef} position={[0, 5, 0]}>
        <octahedronGeometry args={[2, 0]} />
        <meshStandardMaterial 
          color="#00F0FF"
          emissive="#00F0FF"
          emissiveIntensity={0.5}
          metalness={0.8}
          roughness={0.1}
          transparent
          opacity={0.8}
        />
      </mesh>
      
      {/* Ring */}
      <mesh position={[0, 5, 0]} rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry args={[3, 0.1, 8, 32]} />
        <meshBasicMaterial color="#00F0FF" />
      </mesh>
    </group>
  );
}

// Scene component
function Scene({ onZoneSelect, selectedZone }) {
  return (
    <>
      <ambientLight intensity={0.2} />
      <pointLight position={[0, 20, 0]} intensity={1} color="#00F0FF" />
      <pointLight position={[-20, 10, -20]} intensity={0.5} color="#9D4EDD" />
      <pointLight position={[20, 10, 20]} intensity={0.5} color="#00FF88" />
      
      <Stars radius={100} depth={50} count={2000} factor={4} saturation={0} fade speed={1} />
      
      <GroundPlane />
      <GridLines />
      <CentralTower />
      
      {ZONES.map(zone => (
        <ZoneBuilding 
          key={zone.id} 
          zone={zone} 
          onSelect={onZoneSelect}
          isSelected={selectedZone?.id === zone.id}
        />
      ))}
      
      <fog attach="fog" args={['#000000', 30, 100]} />
    </>
  );
}

// Main 3D Metaverse Page
const Metaverse3DPage = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [selectedZone, setSelectedZone] = useState(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [showInfo, setShowInfo] = useState(true);
  const [soundEnabled, setSoundEnabled] = useState(false);
  const containerRef = useRef();

  const handleZoneSelect = (zone) => {
    setSelectedZone(zone);
  };

  const handleEnterZone = () => {
    if (selectedZone) {
      navigate(selectedZone.path);
    }
  };

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      containerRef.current?.requestFullscreen();
      setIsFullscreen(true);
    } else {
      document.exitFullscreen();
      setIsFullscreen(false);
    }
  };

  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
    };
    document.addEventListener('fullscreenchange', handleFullscreenChange);
    return () => document.removeEventListener('fullscreenchange', handleFullscreenChange);
  }, []);

  return (
    <div 
      ref={containerRef}
      className="min-h-screen pt-16 lg:pt-0 bg-black relative"
      data-testid="metaverse-3d-page"
    >
      {/* 3D Canvas */}
      <div className="absolute inset-0 lg:pt-16">
        <Canvas shadows dpr={[1, 2]}>
          <PerspectiveCamera makeDefault position={[30, 25, 30]} fov={50} />
          <OrbitControls 
            enablePan={true}
            enableZoom={true}
            enableRotate={true}
            minDistance={10}
            maxDistance={80}
            maxPolarAngle={Math.PI / 2.2}
            target={[0, 0, 0]}
          />
          <Suspense fallback={null}>
            <Scene 
              onZoneSelect={handleZoneSelect} 
              selectedZone={selectedZone}
            />
          </Suspense>
        </Canvas>
      </div>

      {/* UI Overlay */}
      <div className="absolute inset-0 pointer-events-none">
        {/* Top bar */}
        <div className="absolute top-16 lg:top-20 left-0 right-0 px-4 flex justify-between items-start pointer-events-auto">
          <motion.div 
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            className="flex gap-2"
          >
            <button
              onClick={() => navigate('/metaverse')}
              className="p-2 bg-black/80 border border-white/20 hover:border-neon-cyan transition-colors"
              title="2D Map"
            >
              <Home className="w-5 h-5" />
            </button>
            <button
              onClick={toggleFullscreen}
              className="p-2 bg-black/80 border border-white/20 hover:border-neon-cyan transition-colors"
            >
              {isFullscreen ? <Minimize2 className="w-5 h-5" /> : <Maximize2 className="w-5 h-5" />}
            </button>
            <button
              onClick={() => setSoundEnabled(!soundEnabled)}
              className="p-2 bg-black/80 border border-white/20 hover:border-neon-cyan transition-colors"
            >
              {soundEnabled ? <Volume2 className="w-5 h-5" /> : <VolumeX className="w-5 h-5" />}
            </button>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
          >
            <button
              onClick={() => setShowInfo(!showInfo)}
              className="p-2 bg-black/80 border border-white/20 hover:border-neon-cyan transition-colors"
            >
              <Info className="w-5 h-5" />
            </button>
          </motion.div>
        </div>

        {/* Info panel */}
        {showInfo && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="absolute top-32 lg:top-36 right-4 w-64 pointer-events-auto"
          >
            <CyberCard className="p-4 bg-black/90">
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

        {/* Selected zone panel */}
        {selectedZone && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="absolute bottom-24 lg:bottom-8 left-4 right-4 lg:left-auto lg:right-4 lg:w-80 pointer-events-auto"
          >
            <CyberCard className="p-4 bg-black/90" style={{ borderColor: selectedZone.color }}>
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
                style={{ borderColor: selectedZone.color, color: selectedZone.color }}
              >
                Enter Zone
              </CyberButton>
            </CyberCard>
          </motion.div>
        )}

        {/* Zone legend */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          className="absolute bottom-24 lg:bottom-8 left-4 hidden lg:block pointer-events-auto"
        >
          <CyberCard className="p-3 bg-black/90">
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
