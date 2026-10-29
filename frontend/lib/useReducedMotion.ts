"use client";

import { useSyncExternalStore } from "react";

function subscribe(callback: () => void) {
  if (typeof window === "undefined") return () => {};

  const mediaQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
  const handleMediaChange = () => callback();
  mediaQuery.addEventListener("change", handleMediaChange);

  const observer = new MutationObserver(() => {
    callback();
  });
  observer.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ["class"],
  });

  const handleStorage = (e: StorageEvent) => {
    if (e.key === "utsav_reduced_motion") {
      callback();
    }
  };
  window.addEventListener("storage", handleStorage);

  return () => {
    mediaQuery.removeEventListener("change", handleMediaChange);
    observer.disconnect();
    window.removeEventListener("storage", handleStorage);
  };
}

function getSnapshot(): boolean {
  if (typeof window === "undefined") return false;
  const saved = localStorage.getItem("utsav_reduced_motion");
  if (saved !== null) {
    return saved === "true";
  }
  return (
    window.matchMedia("(prefers-reduced-motion: reduce)").matches ||
    document.documentElement.classList.contains("reduced-motion")
  );
}

function getServerSnapshot(): boolean {
  return false;
}

export function useReducedMotion(): boolean {
  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
}
