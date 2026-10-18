"use client";

import { createContext, useContext, useEffect, useState } from "react";
export type Theme = "light" | "dark";
const ThemeContext = createContext<{theme: Theme; setTheme: (value: Theme) => void}>({theme:"light",setTheme:()=>{}});
export function ThemeProvider({children}: {children: React.ReactNode}) {
  const [theme, updateTheme] = useState<Theme>("light");
  useEffect(()=>{updateTheme(document.documentElement.dataset.theme === "dark" ? "dark" : "light");},[]);
  function setTheme(value: Theme) {
    document.documentElement.dataset.theme = value;
    updateTheme(value);
    try { localStorage.setItem("vf_theme", value); } catch { /* Preference still applies for this page. */ }
  }
  return <ThemeContext.Provider value={{theme,setTheme}}>{children}</ThemeContext.Provider>;
}
export const useTheme = () => useContext(ThemeContext);
