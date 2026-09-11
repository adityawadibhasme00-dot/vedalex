'use client';

import React, { useState, useRef } from 'react';

interface TiltCardProps {
  children: React.ReactNode;
  backContent?: React.ReactNode;
  className?: string;
  glowColor?: 'emerald' | 'gold' | 'cyan' | 'purple' | 'red';
  isFlippable?: boolean;
}

export default function TiltCard({
  children,
  backContent,
  className = '',
  glowColor = 'emerald',
  isFlippable = false
}: TiltCardProps) {
  const cardRef = useRef<HTMLDivElement>(null);
  const [rotateX, setRotateX] = useState(0);
  const [rotateY, setRotateY] = useState(0);
  const [glarePos, setGlarePos] = useState({ x: 50, y: 50, opacity: 0 });
  const [isFlipped, setIsFlipped] = useState(false);

  const glowStyles = {
    emerald: 'hover:border-emerald-500/50 hover:shadow-[0_0_30px_rgba(16,185,129,0.2)]',
    gold: 'hover:border-amber-500/50 hover:shadow-[0_0_30px_rgba(245,158,11,0.2)]',
    cyan: 'hover:border-cyan-500/50 hover:shadow-[0_0_30px_rgba(6,182,212,0.2)]',
    purple: 'hover:border-purple-500/50 hover:shadow-[0_0_30px_rgba(168,85,247,0.2)]',
    red: 'hover:border-red-500/50 hover:shadow-[0_0_30px_rgba(239,68,68,0.2)]'
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!cardRef.current) return;
    const rect = cardRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    const centerX = rect.width / 2;
    const centerY = rect.height / 2;

    const rX = ((y - centerY) / centerY) * -8;
    const rY = ((x - centerX) / centerX) * 8;

    setRotateX(rX);
    setRotateY(rY);
    setGlarePos({
      x: (x / rect.width) * 100,
      y: (y / rect.height) * 100,
      opacity: 0.25
    });
  };

  const handleMouseLeave = () => {
    setRotateX(0);
    setRotateY(0);
    setGlarePos({ x: 50, y: 50, opacity: 0 });
  };

  return (
    <div
      ref={cardRef}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      style={{
        perspective: '1000px'
      }}
      className="relative group transition-all duration-300 select-none"
    >
      <div
        style={{
          transform: `rotateX(${rotateX}deg) rotateY(${rotateY + (isFlipped ? 180 : 0)}deg)`,
          transformStyle: 'preserve-3d',
          transition: 'transform 0.15s ease-out'
        }}
        className={`glass-panel rounded-2xl border border-emerald-200 p-5 ${glowStyles[glowColor]} ${className} relative overflow-hidden`}
      >
        {/* Specular Glare Reflection */}
        <div
          style={{
            background: `radial-gradient(circle at ${glarePos.x}% ${glarePos.y}%, rgba(255,255,255,${glarePos.opacity}) 0%, transparent 60%)`,
            pointerEvents: 'none'
          }}
          className="absolute inset-0 z-20 transition-opacity duration-200"
        />

        {/* Card Content Front / Back */}
        <div className="relative z-10">
          {!isFlipped ? children : backContent || children}
        </div>

        {/* Flip button if enabled */}
        {isFlippable && backContent && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              setIsFlipped(!isFlipped);
            }}
            className="absolute top-3 right-3 z-30 px-2 py-0.5 text-[9px] font-bold rounded-full bg-emerald-50 hover:bg-emerald-100 text-slate-600 border border-emerald-200 transition"
          >
            {isFlipped ? 'Flip Front' : 'Inspect Stat'}
          </button>
        )}
      </div>
    </div>
  );
}
