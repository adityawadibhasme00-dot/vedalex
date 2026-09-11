'use client';
import React from 'react';

interface ReadinessGaugeProps {
  value: number;
  label?: string;
  size?: number;
}

function scoreColor(v: number): { color: string; text: string } {
  if (v <= 40) return { color: '#EF4444', text: 'Needs Attention' };
  if (v <= 70) return { color: '#F59E0B', text: 'Improving' };
  return { color: '#10B981', text: 'Patent Ready' };
}

export function ReadinessGauge({ value, label = 'Patent Readiness Score', size = 300 }: ReadinessGaugeProps) {
  const stroke = 20;
  const radius = (size - stroke) / 2 - 10;
  const cx = size / 2;
  const cyTop = 28 + radius; // center of the arc circle
  const w = size;
  const h = cyTop + radius + 12;

  // Arc spans 180° (from left to right), angles measured in degrees from 180..360
  const polar = (pct: number) => {
    const deg = 180 + 180 * pct; // 0% -> 180° (left), 100% -> 360° (right)
    const rad = (deg * Math.PI) / 180;
    return { x: cx + radius * Math.cos(rad), y: cyTop + radius * Math.sin(rad) };
  };

  const arcPath = (pct0: number, pct1: number) => {
    const s = polar(pct0);
    const e = polar(pct1);
    const large = pct1 - pct0 > 0.5 ? 1 : 0;
    return `M ${s.x.toFixed(2)} ${s.y.toFixed(2)} A ${radius} ${radius} 0 ${large} 1 ${e.x.toFixed(2)} ${e.y.toFixed(2)}`;
  };

  const frac = Math.max(0, Math.min(1, value / 100));
  const { color, text } = scoreColor(value);

  const bands: Array<[number, number, string]> = [
    [0, 0.4, '#EF4444'],
    [0.4, 0.7, '#F59E0B'],
    [0.7, 1, '#10B981'],
  ];
  const ticks = [0, 40, 70, 100];

  return (
    <div className="flex flex-col items-center" style={{ width: w }}>
      <div className="relative" style={{ width: w, height: h }}>
        <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} className="block">
          {/* band underlay */}
          {bands.map(([p0, p1, c], i) => (
            <path key={i} d={arcPath(p0, p1)} fill="none" stroke={c} strokeWidth={stroke} strokeLinecap="round" opacity={0.18} />
          ))}
          {/* gray baseline for the non-reached part */}
          <path d={arcPath(frac, 1)} fill="none" stroke="#e2e8f0" strokeWidth={stroke} strokeLinecap="round" opacity={0.5} />
          {/* value arc */}
          <path d={arcPath(0, frac)} fill="none" stroke={color} strokeWidth={stroke} strokeLinecap="round" />
          {/* ticks + labels */}
          {ticks.map((t) => {
            const p = polar(t / 100);
            const inner = polar(t / 100);
            const dx = inner.x + (inner.x - cx) * 0.12;
            return (
              <g key={t}>
                <line
                  x1={p.x} y1={p.y}
                  x2={p.x + (p.x - cx) * 0.12}
                  y2={p.y + (p.y - cyTop) * 0.12}
                  stroke="#94a3b8" strokeWidth={1.5} strokeLinecap="round"
                />
                <text x={dx} y={p.y + (p.y - cyTop) * 0.12 + (p.y > cyTop ? 18 : -6)} textAnchor="middle" fontSize={11} fill="#64748b" fontWeight={700}>
                  {t}
                </text>
              </g>
            );
          })}
        </svg>

        {/* center number */}
        <div className="absolute left-0 right-0" style={{ top: cyTop - 42 }}>
          <div className="text-center">
            <div className="text-6xl font-black font-display text-slate-900 leading-none">
              {Math.round(value)}<span className="text-3xl text-slate-400">%</span>
            </div>
            <div className="mt-1 text-sm font-bold" style={{ color }}>{text}</div>
            <div className="mt-0.5 text-[11px] text-slate-500">{label}</div>
          </div>
        </div>
      </div>
    </div>
  );
}