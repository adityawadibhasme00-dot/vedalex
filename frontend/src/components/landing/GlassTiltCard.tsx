'use client';
import React, { useRef, useState } from 'react';

interface GlassTiltCardProps {
  children: React.ReactNode;
  className?: string;
  intensity?: number;
  glare?: boolean;
  glowColor?: string;
  depth?: boolean;
  clickable?: boolean;
  onClick?: () => void;
}

export default function GlassTiltCard({
  children,
  className = '',
  intensity = 8,
  glare = true,
  glowColor = 'rgba(16,185,129,0.2)',
  depth = true,
  clickable = false,
  onClick,
}: GlassTiltCardProps) {
  const ref = useRef<HTMLDivElement>(null);
  const [tilt, setTilt] = useState({ x: 0, y: 0 });
  const [springing, setSpringing] = useState(false);

  const onMove = (e: React.MouseEvent<HTMLDivElement>) => {
    const el = ref.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const px = (e.clientX - rect.left) / rect.width - 0.5;
    const py = (e.clientY - rect.top) / rect.height - 0.5;
    const rx = -py * intensity * (springing ? 0.6 : 1);
    const ry = px * intensity * (springing ? 0.6 : 1);
    el.style.transform = `perspective(900px) rotateX(${rx}deg) rotateY(${ry}deg) translateY(-4px)`;
    el.style.setProperty('--gx', `${(px + 0.5) * 100}%`);
    el.style.setProperty('--gy', `${(py + 0.5) * 100}%`);
    setTilt({ x: px, y: py });
  };

  const onLeave = () => {
    const el = ref.current;
    if (!el) return;
    setSpringing(true);
    el.style.transition = 'transform 0.5s cubic-bezier(0.34, 1.56, 0.64, 1)';
    el.style.transform = 'perspective(900px) rotateX(0deg) rotateY(0deg) translateY(0)';
    setTimeout(() => {
      if (el) el.style.transition = 'transform 0.2s ease';
      setSpringing(false);
    }, 500);
    setTilt({ x: 0, y: 0 });
  };

  const tx = tilt.x * -18;
  const ty = tilt.y * 18;

  return (
    <div
      ref={ref}
      onMouseMove={onMove}
      onMouseLeave={onLeave}
      onClick={clickable ? onClick : undefined}
      role={clickable ? 'button' : undefined}
      tabIndex={clickable ? 0 : undefined}
      onKeyDown={clickable ? (e) => { if (e.key === 'Enter' || e.key === ' ') onClick?.(); } : undefined}
      className={`group relative overflow-hidden rounded-3xl border border-emerald-200 bg-white backdrop-blur-xl transition-transform duration-200 will-change-transform ${clickable ? 'cursor-pointer' : ''} ${className}`}
      style={{ transformStyle: 'preserve-3d' }}
    >
      {/* Top-edge bright line */}
      <div className="absolute inset-0 rounded-3xl pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity duration-300"
        style={{ boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.9), inset 0 0 40px rgba(16,185,129,0.05)' }} />

      {/* Cursor-following radial glow */}
      <div
        className="absolute inset-0 opacity-0 transition-opacity duration-300 group-hover:opacity-100 pointer-events-none"
        style={{ background: `radial-gradient(circle at var(--gx,50%) var(--gy,50%), ${glowColor}, rgba(34,211,238,0.05) 45%, transparent 75%)` }}
      />

      {/* Moving glare streak */}
      {glare && (
        <div
          className="absolute -inset-x-full top-0 h-full w-full pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity duration-500"
          style={{
            background: 'linear-gradient(105deg, transparent 40%, rgba(255,255,255,0.28) 50%, transparent 60%)',
            transform: 'translateX(0)',
            animation: 'card-glare 1.6s ease-out both',
          }}
        />
      )}

      {/* Content with parallax depth layers */}
      <div
        className="relative z-10"
        style={depth ? { transform: `translateZ(30px) translate3d(${tx}px, ${ty}px, 0)` } : undefined}
      >
        {children}
      </div>

      {/* Depth reflection under the card */}
      <div
        className="absolute bottom-[-18px] left-[8%] right-[8%] h-8 rounded-full bg-emerald-900/10 blur-xl pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity duration-300"
        style={depth ? { transform: `translate3d(${tx * 0.4}px, ${ty * 0.4}px, 0)` } : undefined}
        aria-hidden="true"
      />
    </div>
  );
}