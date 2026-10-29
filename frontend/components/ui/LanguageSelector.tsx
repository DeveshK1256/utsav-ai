"use client";

import React, { useState, useEffect } from "react";
import { Globe } from "lucide-react";

const SUPPORTED_LANGUAGES = [
  { code: "en", label: "English", native: "EN" },
  { code: "hi", label: "हिन्दी", native: "हिन्दी" },
  { code: "mr", label: "मराठी", native: "मराठी" },
];

export function LanguageSelector() {
  const [currentLang, setCurrentLang] = useState("en");

  useEffect(() => {
    try {
      const saved = localStorage.getItem("utsav_locale");
      if (saved && ["en", "hi", "mr"].includes(saved)) {
        setCurrentLang(saved);
        document.documentElement.lang = saved;
      } else {
        document.documentElement.lang = "en";
      }
    } catch {
      document.documentElement.lang = "en";
    }
  }, []);

  const handleLangChange = (code: string) => {
    setCurrentLang(code);
    document.documentElement.lang = code;
    try {
      localStorage.setItem("utsav_locale", code);
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
