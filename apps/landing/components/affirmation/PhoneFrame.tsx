import Image from 'next/image';
import React from 'react';

type Props = {
  src: string;
  alt: string;
  variant?: 'screen' | 'lockscreen';
  width?: number;
  className?: string;
  priority?: boolean;
  tilt?: 'left' | 'right' | 'none';
};

/**
 * Pure-CSS iPhone bezel that frames a screenshot.
 * Designed for our 1179×2556 Pro screenshots → ~9:19.5 aspect.
 */
export default function PhoneFrame({
  src,
  alt,
  variant = 'screen',
  width = 280,
  className = '',
  priority = false,
  tilt = 'none',
}: Props) {
  // Bezel scale derived from width.
  const radius = Math.round(width * 0.16);
  const innerRadius = Math.round(width * 0.135);
  const padding = Math.round(width * 0.018);
  const islandWidth = Math.round(width * 0.32);
  const islandHeight = Math.round(width * 0.085);
  const screenW = width - padding * 2;
  const screenH = Math.round(screenW * (2556 / 1179));

  const tiltClass =
    tilt === 'left' ? '-rotate-[3deg]' : tilt === 'right' ? 'rotate-[3deg]' : '';

  return (
    <div
      className={`relative inline-block ${tiltClass} ${className}`}
      style={{
        width,
        height: screenH + padding * 2,
        borderRadius: radius,
        background:
          'linear-gradient(160deg, #1d1d1f 0%, #0c0c0e 50%, #1d1d1f 100%)',
        padding,
        boxShadow:
          '0 30px 60px -20px rgba(20,20,30,0.45), 0 12px 24px -8px rgba(20,20,30,0.25), inset 0 0 0 1px rgba(255,255,255,0.05)',
      }}
    >
      <div
        className="relative overflow-hidden bg-cream"
        style={{ width: screenW, height: screenH, borderRadius: innerRadius }}
      >
        <Image
          src={src}
          alt={alt}
          fill
          sizes={`${width}px`}
          className="object-cover"
          priority={priority}
        />

        {/* Dynamic island */}
        <div
          aria-hidden
          className="absolute left-1/2 -translate-x-1/2"
          style={{
            top: Math.round(width * 0.022),
            width: islandWidth,
            height: islandHeight,
            borderRadius: islandHeight,
            background: '#0a0a0c',
            boxShadow: 'inset 0 0 0 1px rgba(255,255,255,0.04)',
          }}
        />

        {/* Lock-screen subtle glass overlay */}
        {variant === 'lockscreen' && (
          <div
            aria-hidden
            className="absolute inset-0"
            style={{
              background:
                'linear-gradient(180deg, rgba(0,0,0,0.0) 35%, rgba(0,0,0,0.18) 100%)',
            }}
          />
        )}
      </div>
    </div>
  );
}
