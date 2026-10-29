"use client";

import React, { useSyncExternalStore } from "react";
import { Globe } from "lucide-react";

const SUPPORTED_LANGUAGES = [
  { code: "en", label: "English", native: "EN" },
  { code: "hi", label: "हिन्दी", native: "हिन्दी" },
  { code: "mr", label: "मराठी", native: "मराठी" },
];

const subscribeLang = (callback: () => void) => {
  if (typeof window === "undefined") return () => {};
  window.addEventListener("utsav_locale_change", callback);
  window.addEventListener("storage", callback);
  return () => {
    window.removeEventListener("utsav_locale_change", callback);
    window.removeEventListener("storage", callback);
  };
};

const getLangSnapshot = (): string => {
  if (typeof window === "undefined") return "en";
  try {
    const saved = localStorage.getItem("utsav_locale");
    if (saved && ["en", "hi", "mr"].includes(saved)) return saved;
  } catch {
    // storage quota or private mode
  }
  return "en";
};

export function LanguageSelector() {
  const currentLang = useSyncExternalStore(
    subscribeLang,
    getLangSnapshot,
    () => "en",
  );

  const handleLangChange = (code: string) => {
    document.documentElement.lang = code;
    try {
      localStorage.setItem("utsav_locale", code);
      window.dispatchEvent(new Event("utsav_locale_change"));
    } catch {
      // storage quota or private mode
    }
  };

  return (
    <div className="relative inline-flex items-center">
      <label htmlFor="utsav-lang-select" className="sr-only">
        Select Language
      </label>
      <div className="relative inline-flex items-center">
        <Globe
          className="w-3.5 h-3.5 absolute left-2.5 pointer-events-none text-stone-500 dark:text-stone-400"
          aria-hidden="true"
        />
        <select
          id="utsav-lang-select"
          aria-label="Language"
          value={currentLang}
          onChange={(e) => handleLangChange(e.target.value)}
          className="appearance-none pl-7 pr-6 py-1 rounded-full text-xs font-medium border border-stone-300/80 dark:border-stone-700 bg-stone-100/90 dark:bg-stone-900/90 text-stone-700 dark:text-stone-300 hover:text-stone-950 dark:hover:text-white transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-500 cursor-pointer shadow-xs"
        >
          {SUPPORTED_LANGUAGES.map((l) => (
            <option
              key={l.code}
              value={l.code}
              className="bg-white dark:bg-stone-900 text-stone-900 dark:text-stone-100"
            >
              {l.native}
            </option>
          ))}
        </select>
        <span className="pointer-events-none absolute right-2 text-[10px] text-stone-500">
          ▼
        </span>
      </div>
    </div>
  );
}
