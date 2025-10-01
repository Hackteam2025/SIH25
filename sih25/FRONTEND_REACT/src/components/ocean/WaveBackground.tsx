import React, { useEffect, useRef } from 'react';
import { motion } from 'framer-motion';

interface WaveBackgroundProps {
  intensity?: 'calm' | 'moderate' | 'stormy';
  showBubbles?: boolean;
}

export const WaveBackground: React.FC<WaveBackgroundProps> = ({
  intensity = 'moderate',
  showBubbles = true
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Set canvas size
    const resizeCanvas = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };

    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);

    // Wave animation parameters based on intensity
    const intensityMap = {
      calm: { amplitude: 15, speed: 0.005 },
      moderate: { amplitude: 25, speed: 0.01 },
      stormy: { amplitude: 40, speed: 0.02 }
    };

    const settings = intensityMap[intensity];

    const waves = [
      { amplitude: settings.amplitude, frequency: 0.01, speed: settings.speed, offset: 0 },
      { amplitude: settings.amplitude * 0.75, frequency: 0.015, speed: settings.speed * 0.8, offset: Math.PI },
      { amplitude: settings.amplitude * 0.5, frequency: 0.02, speed: settings.speed * 1.2, offset: Math.PI / 2 }
    ];

    let animationId: number;
    let time = 0;

    const drawWaves = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      // Ocean gradient background
      const gradient = ctx.createLinearGradient(0, 0, 0, canvas.height);
      gradient.addColorStop(0, 'rgba(0, 31, 63, 0.1)');
      gradient.addColorStop(0.3, 'rgba(0, 61, 122, 0.08)');
      gradient.addColorStop(0.6, 'rgba(0, 116, 217, 0.05)');
      gradient.addColorStop(1, 'rgba(78, 205, 196, 0.1)');

      ctx.fillStyle = gradient;
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      // Draw waves
      waves.forEach((wave, index) => {
        ctx.beginPath();
        ctx.moveTo(0, canvas.height / 2);

        for (let x = 0; x <= canvas.width; x += 5) {
          const y = canvas.height / 2 +
            Math.sin(x * wave.frequency + time * wave.speed + wave.offset) * wave.amplitude;
          ctx.lineTo(x, y);
        }

        ctx.lineTo(canvas.width, canvas.height);
        ctx.lineTo(0, canvas.height);
        ctx.closePath();

        const waveGradient = ctx.createLinearGradient(0, 0, 0, canvas.height);
        waveGradient.addColorStop(0, `rgba(78, 205, 196, ${0.1 - index * 0.02})`);
        waveGradient.addColorStop(0.5, `rgba(0, 116, 217, ${0.08 - index * 0.015})`);
        waveGradient.addColorStop(1, `rgba(0, 61, 122, ${0.05 - index * 0.01})`);

        ctx.fillStyle = waveGradient;
        ctx.fill();
      });

      time += 1;
      animationId = requestAnimationFrame(drawWaves);
    };

    drawWaves();

    return () => {
      window.removeEventListener('resize', resizeCanvas);
      cancelAnimationFrame(animationId);
    };
  }, [intensity]);

  return (
    <>
      <canvas
        ref={canvasRef}
        className="fixed inset-0 -z-10 pointer-events-none"
        style={{
          background: 'linear-gradient(135deg, #001F3F 0%, #003D7A 50%, #0074D9 100%)'
        }}
      />

      {showBubbles && (
        <div className="fixed inset-0 -z-5 pointer-events-none overflow-hidden">
          {Array.from({ length: 20 }).map((_, i) => (
            <motion.div
              key={i}
              className="absolute w-2 h-2 bg-white/20 rounded-full"
              initial={{
                x: Math.random() * (typeof window !== 'undefined' ? window.innerWidth : 1920),
                y: typeof window !== 'undefined' ? window.innerHeight + 50 : 1080,
                scale: 0
              }}
              animate={{
                y: -50,
                scale: [0, 1, 1, 0],
                x: Math.random() * (typeof window !== 'undefined' ? window.innerWidth : 1920)
              }}
              transition={{
                duration: 8 + Math.random() * 4,
                repeat: Infinity,
                delay: Math.random() * 5,
                ease: "linear"
              }}
            />
          ))}
        </div>
      )}
    </>
  );
};