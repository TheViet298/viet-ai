"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Zap, MessageSquare, ShieldCheck, Cpu } from "lucide-react";

export function Navbar() {
  const pathname = usePathname();

  const navItems = [
    {
      name: "Trợ lý Trực tuyến (Customer Chat)",
      href: "/chat",
      icon: MessageSquare,
      badge: "SCR-01 & 02",
    },
    {
      name: "Bàn Điều Phối Dịch Vụ (Staff Console)",
      href: "/console",
      icon: ShieldCheck,
      badge: "SCR-04 HITL",
    },
  ];

  return (
    <header className="sticky top-0 z-50 w-full border-b border-blue-900/20 bg-slate-900 text-white shadow-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center space-x-3">
            <Link href="/" className="flex items-center space-x-2 group">
              <div className="w-9 h-9 rounded-lg bg-blue-600 flex items-center justify-center text-white shadow-lg shadow-blue-500/30 group-hover:bg-blue-500 transition-colors">
                <Zap className="w-5 h-5" />
              </div>
              <div>
                <div className="font-bold text-base tracking-wide flex items-center gap-1.5">
                  VINFAST <span className="text-blue-400 font-medium">ServiceFlow AI</span>
                </div>
                <div className="text-[10px] text-slate-400 tracking-wider font-mono">
                  TEAM VFO2O-18 • COHORT 4
                </div>
              </div>
            </Link>
          </div>

          <nav className="flex items-center space-x-1 sm:space-x-3">
            {navItems.map((item) => {
              const isActive = pathname.startsWith(item.href);
              const Icon = item.icon;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-sm font-medium transition-all ${
                    isActive
                      ? "bg-blue-600 text-white shadow-sm"
                      : "text-slate-300 hover:bg-slate-800 hover:text-white"
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  <span>{item.name}</span>
                </Link>
              );
            })}

            <div className="hidden md:flex items-center pl-3 border-l border-slate-700 text-xs text-emerald-400 gap-1.5 font-mono">
              <Cpu className="w-3.5 h-3.5" />
              <span>FastAPI + LangGraph</span>
            </div>
          </nav>
        </div>
      </div>
    </header>
  );
}
