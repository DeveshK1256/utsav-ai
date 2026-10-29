"use client";

import React, { useRef, useState } from "react";
import { useReducedMotion } from "@/lib/useReducedMotion";

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
  const reducedMotion = useReducedMotion();

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
