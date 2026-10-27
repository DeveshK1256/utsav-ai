'use client';

import React, { useEffect, useState } from 'react';

interface WakingUpNoticeProps {
  isLoading: boolean;
  timeoutMs?: number;
  className?: string;
}

export function WakingUpNotice({ isLoading, timeoutMs = 3500, className = '' }: WakingUpNoticeProps) {
  const [show, setShow] = useState(false);

  useEffect(() => {
    let timer: NodeJS.Timeout | null = null;
    if (isLoading) {
      timer = setTimeout(() => {
        setShow(true);
      }, timeoutMs);
    } else {
      setShow(false);
    }
    return () => {
      if (timer) clearTimeout(timer);
    };
  }, [isLoading, timeoutMs]);

  if (!show || !isLoading) return null;

  return (
    <div
      role="status"
      aria-live="polite"
      className={`p-3 sm:p-4 rounded-xl bg-amber-50 dark:bg-amber-950/70 border border-amber-300 dark:border-amber-700/80 text-amber-900 dark:text-amber-200 text-xs sm:text-sm animate-pulse transition-all ${className}`}
    >
      <div className="flex items-center justify-center gap-2 font-medium text-center">
        <span>🌅</span>
        <span>Utsav is waking up — this can take up to a minute on our free hosting tier, thanks for your patience!</span>
      </div>
    </div>
  );
}
