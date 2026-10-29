"use client";

import React, { useRef, useState, useEffect } from "react";

interface Interactive3DCardProps {
  children: React.ReactNode;
  className?: string;
  maxTilt?: number;
  perspective?: number;
  elevationZ?: number;
}

export function Interactive3DCard({
  children,
  className = "",
  maxTilt = 12,
  perspective = 1000,
  elevationZ = 20,
}: Interactive3DCardProps) {
  const cardRef = useRef<HTMLDivElement>(null);
  const [transformStyle, setTransformStyle] = useState<string>("");
  const [reducedMotion, setReducedMotion] = useState(false);

  useEffect(() => {
    // Check system preference
    const mediaQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReducedMotion(
      mediaQuery.matches ||
        document.documentElement.classList.contains("reduced-motion"),
    );

    const handler = (e: MediaQueryListEvent) => {
      setReducedMotion(
        e.matches ||
          document.documentElement.classList.contains("reduced-motion"),
      );
    };
    mediaQuery.addEventListener("change", handler);
    return () => mediaQuery.removeEventListener("change", handler);
  }, []);

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (reducedMotion || !cardRef.current) return;
    const rect = cardRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const centerX = rect.width / 2;
    const centerY = rect.height / 2;

    const rotateX = ((y - centerY) / centerY) * -maxTilt;
    const rotateY = ((x - centerX) / centerX) * maxTilt;

    setTransformStyle(
      `perspective(${perspective}px) rotateX(${rotateX.toFixed(2)}deg) rotateY(${rotateY.toFixed(2)}deg) translateZ(${elevationZ}px)`,
    );
  };

  const handleMouseLeave = () => {
    if (reducedMotion) return;
    setTransformStyle(
      `perspective(${perspective}px) rotateX(0deg) rotateY(0deg) translateZ(0px)`,
    );
  };

  return (
    <div
      ref={cardRef}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      className={`card-3d-tilt transition-transform duration-200 ease-out preserve-3d will-change-transform ${className}`}
      style={{
        transform: reducedMotion
          ? "none"
          : transformStyle || `perspective(${perspective}px)`,
      }}
    >
      {children}
    </div>
  );
}
