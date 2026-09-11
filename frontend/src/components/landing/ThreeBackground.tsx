'use client';
import { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { useAccessibility } from '../../lib/AccessibilityContext';

export default function ThreeBackground() {
  const mountRef = useRef<HTMLDivElement>(null);
  const { reduceMotion } = useAccessibility();

  useEffect(() => {
    if (reduceMotion) return;
    if (!mountRef.current) return;

    const mount = mountRef.current;
    let width = mount.clientWidth || window.innerWidth;
    let height = mount.clientHeight || window.innerHeight;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(60, width / height, 0.1, 1000);
    camera.position.z = 9;

    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.6));
    mount.appendChild(renderer.domElement);

    const group = new THREE.Group();
    scene.add(group);

    const tube = new THREE.Mesh(
      new THREE.TorusKnotGeometry(1.7, 0.42, 160, 24),
      new THREE.MeshPhysicalMaterial({
        color: 0x8b5cf6,
        metalness: 0.35,
        roughness: 0.25,
        transparent: true,
        opacity: 0.28,
        wireframe: true,
        emissive: new THREE.Color(0x4f46e5),
        emissiveIntensity: 0.35,
      })
    );
    group.add(tube);

    const ring = new THREE.Mesh(
      new THREE.TorusGeometry(2.9, 0.02, 12, 90),
      new THREE.MeshBasicMaterial({ color: 0x34d399, transparent: true, opacity: 0.5 })
    );
    ring.rotation.x = Math.PI / 2.4;
    group.add(ring);

    const ring2 = new THREE.Mesh(
      new THREE.TorusGeometry(3.4, 0.012, 12, 90),
      new THREE.MeshBasicMaterial({ color: 0x22d3ee, transparent: true, opacity: 0.35 })
    );
    ring2.rotation.z = Math.PI / 3;
    group.add(ring2);

    const particleCount = 1300;
    const positions = new Float32Array(particleCount * 3);
    const colors = new Float32Array(particleCount * 3);
    const palette = [new THREE.Color(0x6366f1), new THREE.Color(0x22d3ee), new THREE.Color(0x34d399), new THREE.Color(0xa78bfa), new THREE.Color(0xf59e0b)];
    for (let i = 0; i < particleCount; i++) {
      positions[i * 3] = (Math.random() - 0.5) * 22;
      positions[i * 3 + 1] = (Math.random() - 0.5) * 22;
      positions[i * 3 + 2] = (Math.random() - 0.5) * 16;
      const c = palette[Math.floor(Math.random() * palette.length)];
      colors[i * 3] = c.r;
      colors[i * 3 + 1] = c.g;
      colors[i * 3 + 2] = c.b;
    }
    const particleGeo = new THREE.BufferGeometry();
    particleGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    particleGeo.setAttribute('color', new THREE.BufferAttribute(colors, 3));
    const particles = new THREE.Points(
      particleGeo,
      new THREE.PointsMaterial({ size: 0.045, vertexColors: true, transparent: true, opacity: 0.8, blending: THREE.AdditiveBlending })
    );
    scene.add(particles);

    const floats: Array<{ m: THREE.Mesh; a: number }> = [];
    const crystalGeo = new THREE.OctahedronGeometry(0.14);
    for (let i = 0; i < 26; i++) {
      const mat = new THREE.MeshBasicMaterial({
        color: palette[Math.floor(Math.random() * palette.length)],
        transparent: true,
        opacity: 0.7,
        wireframe: true,
      });
      const m = new THREE.Mesh(crystalGeo, mat);
      m.position.set((Math.random() - 0.5) * 18, (Math.random() - 0.5) * 12, (Math.random() - 0.5) * 10 - 2);
      scene.add(m);
      floats.push({ m, a: Math.random() * Math.PI * 2 });
    }

    const mouse = { x: 0, y: 0 };
    const onMouse = (e: MouseEvent) => {
      mouse.x = (e.clientX / window.innerWidth - 0.5) * 2;
      mouse.y = (e.clientY / window.innerHeight - 0.5) * 2;
    };
    window.addEventListener('mousemove', onMouse, { passive: true });

    const onResize = () => {
      width = mount.clientWidth || window.innerWidth;
      height = mount.clientHeight || window.innerHeight;
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
      renderer.setSize(width, height);
    };
    window.addEventListener('resize', onResize);

    let raf = 0;
    const clock = new THREE.Clock();
    const animate = () => {
      const t = clock.getElapsedTime();
      group.rotation.y = t * 0.12;
      group.rotation.x = Math.sin(t * 0.2) * 0.2;
      group.position.x += (mouse.x * 0.6 - group.position.x) * 0.04;
      group.position.y += (-mouse.y * 0.5 - group.position.y) * 0.04;

      particles.rotation.y = t * 0.02 + mouse.x * 0.05;
      particles.rotation.x = mouse.y * 0.05;

      for (const f of floats) {
        f.a += 0.008;
        f.m.position.y += Math.sin(f.a) * 0.004;
        f.m.rotation.x += 0.01;
        f.m.rotation.y += 0.015;
      }

      renderer.render(scene, camera);
      raf = requestAnimationFrame(animate);
    };
    animate();

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener('mousemove', onMouse);
      window.removeEventListener('resize', onResize);
      scene.traverse((obj) => {
        if (obj instanceof THREE.Mesh) {
          obj.geometry.dispose();
          if (Array.isArray(obj.material)) obj.material.forEach((m) => m.dispose());
          else obj.material.dispose();
        }
      });
      renderer.dispose();
      if (renderer.domElement.parentElement === mount) {
        mount.removeChild(renderer.domElement);
      }
    };
  }, [reduceMotion]);

  if (reduceMotion) return null;

  return (
    <div ref={mountRef} className="fixed inset-0 -z-10 pointer-events-none" aria-hidden="true" />
  );
}