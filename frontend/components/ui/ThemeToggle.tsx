"use client";

import React, { useEffect, useState } from "react";
import { useTheme } from "./ThemeProvider";

interface ThemeToggleProps {
  className?: string;
  showLabel?: boolean;
}

export function ThemeToggle({
  className = "",
  showLabel = false,
}: ThemeToggleProps) {
  const { theme, toggleTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    // Render placeholder to avoid layout shift before mount
    return (
      <div
        className={`w-9 h-9 rounded-xl border border-stone-200 dark:border-stone-800 bg-stone-100/50 dark:bg-stone-900/50 ${className}`}
      />
    );
  }

  const isDark = theme === "dark";

  return (
    <button
      type="button"
      onClick={toggleTheme}
      aria-label={showLabel ? (isDark ? "Dark Mode" : "Light Mode") : (isDark ? "Switch to light mode" : "Switch to dark mode")}
      title={isDark ? "Switch to light mode" : "Switch to dark mode"}
      className={`group relative inline-flex items-center justify-center p-2 rounded-xl border transition-all duration-200 active:scale-95 focus:outline-none focus:ring-2 focus:ring-amber-500/30 ${
        isDark
          ? "bg-stone-900/90 hover:bg-stone-800 border-stone-700/80 text-amber-400 shadow-sm"
          : "bg-white hover:bg-stone-100 border-stone-300/80 text-stone-700 hover:text-stone-900 shadow-sm"
      } ${className}`}
    >

      {isDark ? (
        // Moon Icon with subtle star accent
        <svg
          className="w-4 h-4 transition-transform duration-300 group-hover:-rotate-12"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M21.752 15.002A9.718 9.718 0 0118 15.75c-5.385 0-9.75-4.365-9.75-9.75 0-1.33.266-2.597.748-3.752A9.753 9.753 0 003 11.25C3 16.635 7.365 21 12.75 21a9.753 9.753 0 009.002-5.998z"
          />
        </svg>
      ) : (
        // Sun Icon with rays
        <svg
          className="w-4 h-4 transition-transform duration-300 group-hover:rotate-45 text-amber-600"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M12 3v2.25m6.364.386l-1.591 1.591M21 12h-2.25m-.386 6.364l-1.591-1.591M12 18.75V21m-4.773-4.227l-1.591 1.591M5.25 12H3m4.227-4.773L5.636 5.636M15.75 12a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0z"
          />
        </svg>
      )}

      {showLabel && (
        <span className="ml-2 text-xs font-medium tracking-wide">
          {isDark ? "Dark Mode" : "Light Mode"}
        </span>
      )}
    </button>
  );
}
