'use client';

import React, { useEffect, useRef } from 'react';
import { useAccessibility } from '../lib/AccessibilityContext';

interface LeafSpec {
  layer: number;
  x: number;
  y: number;
  baseX: number;
  len: number;
  halfW: number;
  rot: number;
  rotSway: number;
  speed: number;
  sway: number;
  swayAmp: number;
  phase: number;
  parity: number;
  tumble: number;
  stemBend: number;
  stroke: string;
  fillTop: string;
  fillBottom: string;
}

interface Palette {
  stroke: string;
  fillTop: string;
  fillBottom: string;
}

const FRESH_GREENS: Palette[] = [
  { stroke: '#047857', fillTop: '#6ee7b7', fillBottom: '#10b981' },
  { stroke: '#065f46', fillTop: '#5eead4', fillBottom: '#14b8a6' },
  { stroke: '#14532d', fillTop: '#86efac', fillBottom: '#22c55e' },
  { stroke: '#166534', fillTop: '#a7f3d0', fillBottom: '#34d399' },
];

const AUTUMN: Palette[] = [
  { stroke: '#854d0e', fillTop: '#fde68a', fillBottom: '#f59e0b' },
  { stroke: '#92400e', fillTop: '#fdba74', fillBottom: '#ea580c' },
  { stroke: '#7c2d12', fillTop: '#fecaca', fillBottom: '#dc2626' },
];

const LAYERS = [
  { len: 20, halfW: 6.5, speed: 16, amp: 8, count: 8, scroll: 0.2, alpha: 0.8 },
  { len: 30, halfW: 10, speed: 44, amp: 16, count: 5, scroll: 0.55, alpha: 0.95 },
  { len: 48, halfW: 16, speed: 80, amp: 28, count: 2, scroll: 1.0, alpha: 1 },
];

function pickPalette(): Palette {
  const pool =
    Math.random() < 0.24 ? AUTUMN : FRESH_GREENS;
  return pool[Math.floor(Math.random() * pool.length)];
}

export default function LeafRain({ density = 1 }: { density?: number }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const { reduceMotion } = useAccessibility();

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let raf = 0;
    let leaves: LeafSpec[] = [];
    let W = 0;
    let H = 0;
    let scrollY = 0;
    let last = performance.now();

    const spawn = (layer: number, fromTop: boolean): LeafSpec => {
      const cfg = LAYERS[layer];
      const x = Math.random() * W;
      const rot = -70 + Math.random() * 140;
      const len = cfg.len * (0.75 + Math.random() * 0.5) * density;
      const pal = pickPalette();
      return {
        layer,
        x,
        y: fromTop ? -60 - Math.random() * 80 : Math.random() * H,
        baseX: x,
        len,
        halfW: cfg.halfW * (len / cfg.len) * density,
        rot,
        rotSway: 0.5 + Math.random() * 1.4,
        speed: cfg.speed * (0.75 + Math.random() * 0.6),
        sway: 0.4 + Math.random() * 0.6,
        swayAmp: cfg.amp * (0.6 + Math.random() * 0.8),
        phase: Math.random() * Math.PI * 2,
        parity: Math.random() > 0.5 ? 1 : -1,
        tumble: 0.6 + Math.random() * 1.6,
        stemBend: -3 + Math.random() * 6,
        stroke: pal.stroke,
        fillTop: pal.fillTop,
        fillBottom: pal.fillBottom,
      };
    };

    const drawLeaf = (
      leaf: LeafSpec,
      rot: number,
      widthFactor: number
    ) => {
      const len = leaf.len;
      const hw = leaf.halfW;
      const tip = -len;
      const w = hw * (0.22 + 0.78 * widthFactor);

      ctx.save();
      ctx.translate(leaf.x, leaf.y);
      ctx.rotate((rot * Math.PI) / 180);

      // Petiole (stem)
      ctx.beginPath();
      ctx.moveTo(0, len * 0.2);
      ctx.quadraticCurveTo(leaf.stemBend * 0.6, len * 0.1, leaf.stemBend, 0);
      ctx.strokeStyle = leaf.stroke;
      ctx.lineWidth = Math.max(0.9, len * 0.03);
      ctx.lineCap = 'round';
      ctx.stroke();

      const grad = ctx.createLinearGradient(0, tip, 0, 0);
      grad.addColorStop(0, leaf.fillTop);
      grad.addColorStop(0.62, leaf.fillBottom);
      grad.addColorStop(1, leaf.fillBottom);

      // Leaf blade — ovate with pointed tip (tulsi/neem shape)
      ctx.beginPath();
      ctx.moveTo(0, tip);
      ctx.bezierCurveTo(
        w * 1.65, tip + len * 0.2,
        w * 1.4, tip + len * 0.58,
        w * 0.26, tip + len * 0.93
      );
      ctx.quadraticCurveTo(0, tip + len * 0.97, -w * 0.26, tip + len * 0.93);
      ctx.bezierCurveTo(
        -w * 1.4, tip + len * 0.58,
        -w * 1.65, tip + len * 0.2,
        0, tip
      );
      ctx.closePath();
      ctx.fillStyle = grad;
      ctx.fill();
      ctx.strokeStyle = leaf.stroke;
      ctx.lineWidth = 1;
      ctx.globalAlpha *= 0.9;
      ctx.stroke();
      ctx.globalAlpha /= 0.9;

      // Serration along the blade edges
      ctx.beginPath();
      ctx.strokeStyle = leaf.stroke;
      ctx.lineWidth = Math.max(0.5, len * 0.018);
      for (let s = 1; s <= 6; s++) {
        const k = s / 7;
        const sy = tip + len * (0.08 + k * 0.8);
        const out = w * (1.2 - 0.9 * k);
        ctx.moveTo(-out * 0.55, sy);
        ctx.lineTo(-out, sy - len * 0.012);
        ctx.moveTo(out * 0.55, sy + len * 0.018);
        ctx.lineTo(out, sy + len * 0.006);
      }
      ctx.stroke();

      // Main vein
      ctx.beginPath();
      ctx.moveTo(0, tip + len * 0.06);
      ctx.quadraticCurveTo(
        leaf.stemBend * 0.7, tip + len * 0.5,
        leaf.stemBend, tip + len * 0.88
      );
      ctx.strokeStyle = leaf.stroke;
      ctx.lineWidth = Math.max(0.55, len * 0.02);
      ctx.lineCap = 'round';
      ctx.stroke();

      // Lateral veins
      const n = 4;
      for (let i = 0; i < n; i++) {
        const k = (i + 1) / (n + 1);
        const y = tip + len * (0.16 + k * 0.74);
        const reach = w * (1.1 - 0.65 * k);
        ctx.lineWidth = Math.max(0.4, len * 0.014);
        ctx.strokeStyle = leaf.stroke;
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.quadraticCurveTo(reach * 0.45, y - len * 0.05, reach, y + len * 0.045);
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.quadraticCurveTo(-reach * 0.45, y - len * 0.05, -reach, y + len * 0.045);
        ctx.stroke();
      }

      ctx.restore();
    };

    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      W = window.innerWidth;
      H = window.innerHeight;
      canvas.width = W * dpr;
      canvas.height = H * dpr;
      canvas.style.width = `${W}px`;
      canvas.style.height = `${H}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      leaves = [];
      LAYERS.forEach((cfg, layer) => {
        const count = Math.round(cfg.count * density);
        for (let i = 0; i < count; i++) leaves.push(spawn(layer, false));
      });
    };

    const onScroll = () => { scrollY = window.scrollY; };

    const draw = () => {
      const now = performance.now();
      const dt = Math.min((now - last) / 1000, 0.05);
      last = now;
      const t = now / 1000;

      ctx.clearRect(0, 0, W, H);

      for (const leaf of leaves) {
        const cfg = LAYERS[leaf.layer];
        const offsetY = scrollY * cfg.scroll;
        const y = ((leaf.y + offsetY + leaf.speed * t) % (H + 140)) - 70;
        const xx = leaf.baseX + Math.sin(t * leaf.sway + leaf.phase) * leaf.swayAmp * leaf.parity;
        const rot = leaf.rot + Math.sin(t * leaf.rotSway + leaf.phase) * 28 * leaf.parity;

        // 3D tumble around the long axis — leaf narrows as it turns edge-on
        const tumble = leaf.tumble * t * leaf.parity + leaf.phase;
        const widthFactor = Math.abs(Math.cos(tumble));

        ctx.save();
        ctx.globalAlpha = cfg.alpha * (0.4 + 0.6 * widthFactor);

        if (leaf.layer === 2) {
          ctx.fillStyle = 'rgba(2,44,34,0.10)';
          ctx.beginPath();
          ctx.ellipse(xx + 4, y + 5, leaf.len * 0.42, leaf.len * 0.2, rot * (Math.PI / 180) * 0.3, 0, Math.PI * 2);
          ctx.fill();
        }

        if (leaf.layer === 0) {
          const prev = ctx.filter;
          ctx.filter = 'blur(0.7px)';
          drawLeaf({ ...leaf, x: xx, y }, rot, widthFactor);
          ctx.filter = prev;
        } else {
          drawLeaf({ ...leaf, x: xx, y }, rot, widthFactor);
        }
        ctx.restore();
      }

      raf = requestAnimationFrame(draw);
    };

    const drawStatic = () => {
      ctx.clearRect(0, 0, W, H);
      LAYERS.forEach((cfg, layer) => {
        const count = Math.round(cfg.count * density);
        for (let i = 0; i < count; i++) {
          const leaf = spawn(layer, false);
          ctx.globalAlpha = cfg.alpha;
          drawLeaf(leaf, leaf.rot, 1);
        }
      });
    };

    resize();
    window.addEventListener('resize', resize);
    window.addEventListener('scroll', onScroll, { passive: true });

    if (reduceMotion) {
      drawStatic();
    } else {
      raf = requestAnimationFrame(draw);
    }

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener('resize', resize);
      window.removeEventListener('scroll', onScroll);
    };
  }, [reduceMotion, density]);

  return <canvas ref={canvasRef} className="fixed inset-0 z-0 pointer-events-none" aria-hidden="true" />;
}