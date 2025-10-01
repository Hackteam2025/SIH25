import React, { useRef, useEffect, useState } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Sphere, Text } from '@react-three/drei';
import * as THREE from 'three';
import { motion } from 'framer-motion';
import { FloatingCard } from '../ocean/FloatingCard';
import { OceanButton } from '../design-system/Button';
import { Globe, MapPin, Zap } from 'lucide-react';

interface FloatPosition {
  id: string;
  lat: number;
  lon: number;
  temperature: number;
  depth: number;
  isActive: boolean;
}

interface OceanGlobeProps {
  floats?: FloatPosition[];
  onFloatClick?: (float: FloatPosition) => void;
  autoRotate?: boolean;
}

const Earth: React.FC<{ floats: FloatPosition[] }> = ({ floats }) => {
  const meshRef = useRef<THREE.Mesh>(null);
  const [texture, setTexture] = useState<THREE.Texture | null>(null);

  useEffect(() => {
    // Create procedural earth texture since we might not have the image
    const canvas = document.createElement('canvas');
    canvas.width = canvas.height = 512;
    const ctx = canvas.getContext('2d')!;

    // Create ocean gradient
    const gradient = ctx.createLinearGradient(0, 0, 0, 512);
    gradient.addColorStop(0, '#001F3F');
    gradient.addColorStop(0.3, '#003D7A');
    gradient.addColorStop(0.6, '#0074D9');
    gradient.addColorStop(1, '#4ECDC4');

    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, 512, 512);

    // Add some continents (simplified)
    ctx.fillStyle = '#2D5A27';
    // North America
    ctx.fillRect(100, 150, 120, 80);
    // Europe/Africa
    ctx.fillRect(250, 120, 60, 120);
    // Asia
    ctx.fillRect(320, 100, 100, 100);
    // Australia
    ctx.fillRect(380, 250, 40, 30);

    // Add some noise for texture
    for (let i = 0; i < 1000; i++) {
      ctx.fillStyle = `rgba(255, 255, 255, ${Math.random() * 0.1})`;
      ctx.fillRect(Math.random() * 512, Math.random() * 512, 2, 2);
    }

    const earthTexture = new THREE.CanvasTexture(canvas);
    setTexture(earthTexture);
  }, []);

  useFrame((state, delta) => {
    if (meshRef.current) {
      meshRef.current.rotation.y += delta * 0.1;
    }
  });

  // Convert lat/lon to 3D coordinates
  const latLonToVector3 = (lat: number, lon: number, radius: number = 1.01) => {
    const phi = (90 - lat) * (Math.PI / 180);
    const theta = (lon + 180) * (Math.PI / 180);

    const x = radius * Math.sin(phi) * Math.cos(theta);
    const y = radius * Math.cos(phi);
    const z = radius * Math.sin(phi) * Math.sin(theta);

    return new THREE.Vector3(x, y, z);
  };

  return (
    <>
      {/* Earth Sphere */}
      <Sphere ref={meshRef} args={[1, 64, 64]}>
        <meshLambertMaterial
          map={texture}
          transparent
          opacity={0.9}
        />
      </Sphere>

      {/* ARGO Float Markers */}
      {floats.map((float) => {
        const position = latLonToVector3(float.lat, float.lon);
        return (
          <group key={float.id} position={[position.x, position.y, position.z]}>
            {/* Float Marker */}
            <Sphere args={[0.015, 8, 8]}>
              <meshBasicMaterial
                color={float.isActive ? '#FF6B6B' : '#4ECDC4'}
                emissive={float.isActive ? '#FF6B6B' : '#4ECDC4'}
                emissiveIntensity={0.5}
              />
            </Sphere>

            {/* Data Beam */}
            {float.isActive && (
              <mesh rotation={[0, 0, 0]}>
                <cylinderGeometry args={[0.003, 0.003, 0.3, 8]} />
                <meshBasicMaterial
                  color="#4ECDC4"
                  transparent
                  opacity={0.6}
                />
              </mesh>
            )}

            {/* Pulse effect for active floats */}
            {float.isActive && (
              <Sphere args={[0.025, 8, 8]}>
                <meshBasicMaterial
                  color="#FF6B6B"
                  transparent
                  opacity={0.3}
                />
              </Sphere>
            )}
          </group>
        );
      })}

      {/* Atmosphere Glow */}
      <Sphere args={[1.05, 32, 32]}>
        <meshBasicMaterial
          color="#4ECDC4"
          transparent
          opacity={0.1}
          side={THREE.BackSide}
        />
      </Sphere>

      {/* Ambient ocean particles */}
      {Array.from({ length: 50 }).map((_, i) => (
        <mesh
          key={i}
          position={[
            (Math.random() - 0.5) * 4,
            (Math.random() - 0.5) * 4,
            (Math.random() - 0.5) * 4
          ]}
        >
          <sphereGeometry args={[0.002, 4, 4]} />
          <meshBasicMaterial
            color="#4ECDC4"
            transparent
            opacity={Math.random() * 0.5}
          />
        </mesh>
      ))}
    </>
  );
};

export const OceanGlobe: React.FC<OceanGlobeProps> = ({
  floats = [],
  onFloatClick,
  autoRotate = true
}) => {
  const [selectedFloat, setSelectedFloat] = useState<FloatPosition | null>(null);
  const [viewMode, setViewMode] = useState<'globe' | 'data'>('globe');

  // Sample ARGO float data
  const sampleFloats: FloatPosition[] = [
    { id: '1', lat: 35.5, lon: -20.3, temperature: 18.5, depth: 1200, isActive: true },
    { id: '2', lat: -10.2, lon: 45.8, temperature: 25.2, depth: 800, isActive: false },
    { id: '3', lat: 55.1, lon: -145.7, temperature: 8.3, depth: 1500, isActive: true },
    { id: '4', lat: -45.3, lon: 78.9, temperature: 4.1, depth: 2000, isActive: false },
    { id: '5', lat: 0.5, lon: -90.2, temperature: 26.8, depth: 600, isActive: true },
    { id: '6', lat: 60.1, lon: 10.5, temperature: 12.3, depth: 1800, isActive: false },
    { id: '7', lat: -30.8, lon: 150.2, temperature: 22.1, depth: 900, isActive: true },
    { id: '8', lat: 25.4, lon: -80.1, temperature: 24.7, depth: 750, isActive: false },
  ];

  const displayFloats = floats.length > 0 ? floats : sampleFloats;

  return (
    <div className="w-full h-[600px] relative">
      <FloatingCard className="h-full">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="ocean-heading text-xl font-bold">Global ARGO Network</h3>
            <p className="text-sm text-ocean-blue/70">
              {displayFloats.length} active floats • Real-time ocean data
            </p>
          </div>

          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1 px-3 py-1 bg-white/10 rounded-wave">
              <div className="w-2 h-2 bg-seafoam-green rounded-full animate-pulse" />
              <span className="text-xs text-ocean-blue">Live</span>
            </div>

            <OceanButton
              size="sm"
              variant={viewMode === 'globe' ? 'primary' : 'secondary'}
              onClick={() => setViewMode('globe')}
              leftIcon={<Globe className="w-4 h-4" />}
            >
              Globe
            </OceanButton>

            <OceanButton
              size="sm"
              variant={viewMode === 'data' ? 'primary' : 'secondary'}
              onClick={() => setViewMode('data')}
              leftIcon={<Zap className="w-4 h-4" />}
            >
              Data
            </OceanButton>
          </div>
        </div>

        {viewMode === 'globe' ? (
          <>
            {/* 3D Globe */}
            <div className="h-[400px] rounded-wave overflow-hidden bg-gradient-to-b from-abyss-black to-midnight-blue">
              <Canvas camera={{ position: [0, 0, 2.5], fov: 60 }}>
                <ambientLight intensity={0.6} />
                <pointLight position={[10, 10, 10]} />
                <pointLight position={[-10, -10, -10]} intensity={0.3} />
                <Earth floats={displayFloats} />
                <OrbitControls
                  enableZoom={true}
                  enablePan={false}
                  autoRotate={autoRotate}
                  autoRotateSpeed={0.5}
                  minDistance={1.5}
                  maxDistance={5}
                />
              </Canvas>
            </div>

            {/* Globe Controls */}
            <div className="mt-4 flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 bg-seafoam-green rounded-full" />
                  <span className="text-sm text-ocean-blue">Active Floats</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 bg-coral-pink rounded-full" />
                  <span className="text-sm text-ocean-blue">Transmitting</span>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <MapPin className="w-4 h-4 text-ocean-blue" />
                <span className="text-sm text-ocean-blue">
                  {displayFloats.filter(f => f.isActive).length} active
                </span>
              </div>
            </div>
          </>
        ) : (
          /* Data View */
          <div className="h-[400px] overflow-y-auto space-y-3 custom-scrollbar">
            {displayFloats.map((float) => (
              <motion.div
                key={float.id}
                whileHover={{ scale: 1.02 }}
                className="glass-surface p-4 rounded-wave cursor-pointer"
                onClick={() => {
                  setSelectedFloat(float);
                  onFloatClick?.(float);
                }}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <div className={`w-3 h-3 rounded-full ${
                        float.isActive ? 'bg-coral-pink animate-pulse' : 'bg-seafoam-green'
                      }`} />
                      <span className="font-medium text-ocean-blue">
                        Float {float.id}
                      </span>
                      {float.isActive && (
                        <span className="text-xs bg-coral-pink/20 text-coral-pink px-2 py-1 rounded-wave">
                          Transmitting
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-ocean-blue/70 mt-1">
                      {float.lat.toFixed(2)}°N, {Math.abs(float.lon).toFixed(2)}°{float.lon >= 0 ? 'E' : 'W'}
                    </p>
                  </div>

                  <div className="text-right">
                    <p className="text-lg font-bold text-ocean-blue">
                      {float.temperature.toFixed(1)}°C
                    </p>
                    <p className="text-sm text-ocean-blue/70">
                      {float.depth}m depth
                    </p>
                  </div>
                </div>

                {/* Additional data on hover/select */}
                {selectedFloat?.id === float.id && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    className="mt-3 pt-3 border-t border-white/10"
                  >
                    <div className="grid grid-cols-3 gap-3 text-sm">
                      <div>
                        <p className="text-ocean-blue/70">Status</p>
                        <p className="font-medium text-ocean-blue">
                          {float.isActive ? 'Active' : 'Standby'}
                        </p>
                      </div>
                      <div>
                        <p className="text-ocean-blue/70">Last Update</p>
                        <p className="font-medium text-ocean-blue">2 hrs ago</p>
                      </div>
                      <div>
                        <p className="text-ocean-blue/70">Data Points</p>
                        <p className="font-medium text-ocean-blue">1,247</p>
                      </div>
                    </div>
                  </motion.div>
                )}
              </motion.div>
            ))}
          </div>
        )}
      </FloatingCard>
    </div>
  );
};