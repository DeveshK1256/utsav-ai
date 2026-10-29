"use client";

import React, {
  createContext,
  useContext,
  useEffect,
  useSyncExternalStore,
} from "react";

type Theme = "light" | "dark";

interface ThemeContextType {
  theme: Theme;
  toggleTheme: () => void;
  setTheme: (theme: Theme) => void;
}

const ThemeContext = createContext<ThemeContextType>({
  theme: "light",
  toggleTheme: () => {},
  setTheme: () => {},
});

function applyThemeClass(t: Theme) {
  if (typeof document === "undefined") return;
  const root = document.documentElement;
  if (t === "dark") {
    root.classList.add("dark");
  } else {
    root.classList.remove("dark");
  }
}

function subscribeTheme(callback: () => void) {
  if (typeof window === "undefined") return () => {};
  const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
  const handleSystemChange = () => {
    if (!localStorage.getItem("utsav-theme")) {
      callback();
    }
  };
  mediaQuery.addEventListener("change", handleSystemChange);
  window.addEventListener("utsav_theme_change", callback);
  window.addEventListener("storage", callback);
  return () => {
    mediaQuery.removeEventListener("change", handleSystemChange);
    window.removeEventListener("utsav_theme_change", callback);
    window.removeEventListener("storage", callback);
  };
}

function getThemeSnapshot(): Theme {
  if (typeof window === "undefined") return "light";
  try {
    const savedTheme = localStorage.getItem("utsav-theme");
    if (savedTheme === "dark" || savedTheme === "light") {
      return savedTheme;
    }
    const prefersDark = window.matchMedia(
      "(prefers-color-scheme: dark)",
    ).matches;
    return prefersDark ? "dark" : "light";
  } catch {
    return "light";
  }
}

function getServerSnapshot(): Theme {
  return "light";
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const theme: Theme = useSyncExternalStore<Theme>(
    subscribeTheme,
    getThemeSnapshot,
    getServerSnapshot,
  );

  useEffect(() => {
    applyThemeClass(theme);
  }, [theme]);

  const setTheme = (nextTheme: Theme) => {
    try {
      localStorage.setItem("utsav-theme", nextTheme);
      window.dispatchEvent(new Event("utsav_theme_change"));
    } catch {
      // storage quota or private mode
    }
    applyThemeClass(nextTheme);
  };

  const toggleTheme = () => {
    const nextTheme: Theme = theme === "dark" ? "light" : "dark";
    setTheme(nextTheme);
  };

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  return useContext(ThemeContext);
}
