'use client';
import React from 'react';

const base = {
  fill: 'none',
  stroke: 'currentColor',
  strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
};

export function TulsiLeaf({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 64 64" aria-hidden="true" focusable="false">
      <path d="M32 4 C 57 15, 58 46, 32 61 C 6 46, 7 15, 32 4 Z" fill="currentColor" opacity="0.85" />
      <path d="M32 11 C 33 25, 33 42, 31 55" {...base} strokeWidth="2" opacity="0.5" />
      <path d="M32 14 C 26 20, 26 30, 31 33 M32 24 C 38 29, 38 40, 32 44" {...base} strokeWidth="1.5" opacity="0.55" />
    </svg>
  );
}

const SPRIG_LEAVES: Array<[number, number, number, number]> = [
  [30, 20, 14, 0.9],
  [27, 31, -22, 0.85],
  [32, 42, 18, 0.9],
  [28, 52, -18, 0.8],
  [37, 62, 10, 0.8],
];

export function HerbSprig({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 64 64" fill="none" aria-hidden="true" focusable="false">
      <path d="M32 62 C 31 44, 34 30, 31 18 C 29 12, 31 8, 35 6" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
      {SPRIG_LEAVES.map(([x, y, rot, op], i) => (
        <path key={i} d="M0 0 C -11 3, -13 -9, -6 -13 C 1 -17, 7 -9, 0 0 Z" fill="currentColor" opacity={op}
          transform={`translate(${x} ${y}) rotate(${rot})`} />
      ))}
      <circle cx="35" cy="6" r="2" fill="currentColor" />
    </svg>
  );
}

const ROOT_FINGERS: Array<[number, number, number, number, number]> = [
  [30, 12, 10, 30, -14],
  [39, 8, 9, 32, 4],
  [45, 14, 10, 26, 16],
  [33, 6, 8, 24, 0],
];

export function TurmericRoot({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 64 64" aria-hidden="true" focusable="false">
      {ROOT_FINGERS.map(([x, y, w, h, rot], i) => (
        <rect key={i} x={x} y={y} width={w} height={h} rx={w / 2} fill="currentColor"
          transform={`rotate(${rot} ${x + w / 2} ${y + h / 2})`} opacity={0.9} />
      ))}
      <circle cx="38" cy="44" r="10" fill="currentColor" opacity="0.9" />
      <circle cx="36" cy="41" r="1.6" fill="#fff" opacity="0.35" />
    </svg>
  );
}

export function MortarPestle({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 64 64" fill="none" aria-hidden="true" focusable="false">
      <path d="M12 27 a20 20 0 0 0 40 0 Z" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
      <path d="M22 25 a10 10 0 0 0 20 0 Z" fill="currentColor" opacity="0.18" />
      <path d="M20 47 h24" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
      <path d="M44 8 L30 24" stroke="currentColor" strokeWidth="4.5" strokeLinecap="round" />
      <path d="M42 6 a2 2 0 1 0 0.01 0" fill="currentColor" />
    </svg>
  );
}

export function HerbGarland({ className }: { className?: string }) {
  const leaves: Array<[number, number, number, boolean]> = [
    [24, 38, -28, false],
    [34, 33, 30, true],
    [41, 27, -26, false],
    [49, 21, 26, true],
    [55, 14, -16, false],
  ];
  return (
    <svg className={className} viewBox="0 0 64 64" fill="none" aria-hidden="true" focusable="false">
      <path d="M6 58 C 18 48, 36 36, 58 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" opacity="0.9" />
      {leaves.map(([x, y, rot, flip], i) => (
        <path key={i} d="M0 0 C -12 4, -14 -9, -7 -14 C 0 -19, 8 -10, 0 0 Z"
          fill="currentColor" opacity={0.75}
          transform={`translate(${x} ${y}) rotate(${rot}) scale(${flip ? -1 : 1} 1)`} />
      ))}
      <circle cx="58" cy="12" r="2.2" fill="currentColor" />
    </svg>
  );
}

export function AyurvedaSeal({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 96 96" fill="none" aria-hidden="true" focusable="false">
      <circle cx="48" cy="48" r="44" stroke="currentColor" strokeWidth="2" />
      <circle cx="48" cy="48" r="35" stroke="currentColor" strokeWidth="1" opacity="0.55" strokeDasharray="3 3" />
      <path d="M48 22 C 62 30, 62 52, 48 62 C 34 52, 34 30, 48 22 Z" fill="currentColor" opacity="0.85" />
      <path d="M48 28 C 49 38, 49 50, 47 57" stroke="#fff" strokeWidth="1.4" strokeLinecap="round" opacity="0.5" />
      <text x="48" y="79" textAnchor="middle" fontSize="11" fill="currentColor" opacity="0.9" fontFamily="inherit">
        आयुर्वेद
      </text>
    </svg>
  );
}