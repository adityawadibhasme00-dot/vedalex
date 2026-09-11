'use client';

import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';

export default function ThreeBackground() {
  const mountRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!mountRef.current) return;

    // 1. Scene, Camera, Renderer
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(
      60,
      window.innerWidth / window.innerHeight,
      0.1,
      1000
    );
    camera.position.z = 30;

    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    mountRef.current.appendChild(renderer.domElement);

    // 2. DNA Double Helix Particles
    const dnaGroup = new THREE.Group();
    const particleCount = 180;
    const helixRadius = 4;
    const helixLength = 40;

    const geometry = new THREE.SphereGeometry(0.12, 8, 8);
    const goldMaterial = new THREE.MeshBasicMaterial({ color: 0xf59e0b });
    const emeraldMaterial = new THREE.MeshBasicMaterial({ color: 0x10b981 });
    const cyanMaterial = new THREE.MeshBasicMaterial({ color: 0x06b6d4 });

    for (let i = 0; i < particleCount; i++) {
      const t = (i / particleCount) * Math.PI * 8;
      const y = (i / particleCount) * helixLength - helixLength / 2;

      // Strand 1
      const x1 = Math.cos(t) * helixRadius;
      const z1 = Math.sin(t) * helixRadius;
      const sphere1 = new THREE.Mesh(geometry, i % 2 === 0 ? goldMaterial : emeraldMaterial);
      sphere1.position.set(x1, y, z1);
      dnaGroup.add(sphere1);

      // Strand 2 (Opposite Phase)
      const x2 = Math.cos(t + Math.PI) * helixRadius;
      const z2 = Math.sin(t + Math.PI) * helixRadius;
      const sphere2 = new THREE.Mesh(geometry, i % 2 === 0 ? cyanMaterial : emeraldMaterial);
      sphere2.position.set(x2, y, z2);
      dnaGroup.add(sphere2);

      // Connecting rungs every 6 particles
      if (i % 6 === 0) {
        const rungPoints = [
          new THREE.Vector3(x1, y, z1),
          new THREE.Vector3(x2, y, z2)
        ];
        const rungGeo = new THREE.BufferGeometry().setFromPoints(rungPoints);
        const rungMat = new THREE.LineBasicMaterial({
          color: 0x10b981,
          transparent: true,
          opacity: 0.3
        });
        const rung = new THREE.Line(rungGeo, rungMat);
        dnaGroup.add(rung);
      }
    }

    dnaGroup.position.set(18, 0, -5);
    dnaGroup.rotation.z = Math.PI / 6;
    scene.add(dnaGroup);

    // 3. Floating Ambient Stardust Particles
    const starCount = 350;
    const starGeo = new THREE.BufferGeometry();
    const starPositions = new Float32Array(starCount * 3);
    const starColors = new Float32Array(starCount * 3);

    const c1 = new THREE.Color(0x10b981);
    const c2 = new THREE.Color(0xf59e0b);
    const c3 = new THREE.Color(0x38bdf8);

    for (let i = 0; i < starCount; i++) {
      starPositions[i * 3] = (Math.random() - 0.5) * 80;
      starPositions[i * 3 + 1] = (Math.random() - 0.5) * 60;
      starPositions[i * 3 + 2] = (Math.random() - 0.5) * 50;

      const mixedColor = c1.clone().lerp(Math.random() > 0.5 ? c2 : c3, Math.random());
      starColors[i * 3] = mixedColor.r;
      starColors[i * 3 + 1] = mixedColor.g;
      starColors[i * 3 + 2] = mixedColor.b;
    }

    starGeo.setAttribute('position', new THREE.BufferAttribute(starPositions, 3));
    starGeo.setAttribute('color', new THREE.BufferAttribute(starColors, 3));

    const starMat = new THREE.PointsMaterial({
      size: 0.22,
      vertexColors: true,
      transparent: true,
      opacity: 0.65
    });

    const starField = new THREE.Points(starGeo, starMat);
    scene.add(starField);

    // 4. Mouse Interactivity / Parallax
    let mouseX = 0;
    let mouseY = 0;
    const handleMouseMove = (e: MouseEvent) => {
      mouseX = (e.clientX / window.innerWidth - 0.5) * 2;
      mouseY = -(e.clientY / window.innerHeight - 0.5) * 2;
    };
    window.addEventListener('mousemove', handleMouseMove);

    // 5. Window Resize Handler
    const handleResize = () => {
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
    };
    window.addEventListener('resize', handleResize);

    // 6. Animation Loop (60 FPS)
    let animationId: number;
    const clock = new THREE.Clock();

    const animate = () => {
      animationId = requestAnimationFrame(animate);
      const delta = clock.getDelta();

      // Rotate DNA
      dnaGroup.rotation.y += delta * 0.4;
      starField.rotation.y += delta * 0.05;
      starField.rotation.x += delta * 0.02;

      // Parallax smooth interpolation
      camera.position.x += (mouseX * 3 - camera.position.x) * 0.03;
      camera.position.y += (mouseY * 2 - camera.position.y) * 0.03;
      camera.lookAt(scene.position);

      renderer.render(scene, camera);
    };

    animate();

    return () => {
      cancelAnimationFrame(animationId);
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('resize', handleResize);
      if (mountRef.current && renderer.domElement) {
        mountRef.current.removeChild(renderer.domElement);
      }
      renderer.dispose();
    };
  }, []);

  return (
    <div
      ref={mountRef}
      className="fixed inset-0 pointer-events-none z-0 overflow-hidden"
      aria-hidden="true"
    />
  );
}
