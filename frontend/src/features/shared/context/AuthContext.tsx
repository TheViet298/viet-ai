"use client";

import React, { createContext, useContext, useEffect, useState } from "react";

export type UserRole = "GUEST" | "CUSTOMER" | "STAFF";

export interface AuthUser {
  id: string;
  name: string;
  role: UserRole;
  email: string;
  vehicleModel?: string;
  avatar?: string;
}

export const DEMO_PROFILES: Record<"CUSTOMER" | "STAFF", AuthUser> = {
  CUSTOMER: {
    id: "CUST_MOCK_01",
    name: "Nguyễn Văn An",
    role: "CUSTOMER",
    email: "an.nguyen@vinfast.customer",
    vehicleModel: "VF8",
  },
  STAFF: {
    id: "STAFF_01",
    name: "Lê Hoàng Quân (KTV)",
    role: "STAFF",
    email: "quan.lh@vinfast.vn",
  },
};

interface AuthContextType {
  user: AuthUser | null;
  role: UserRole;
  loginAs: (role: "CUSTOMER" | "STAFF", customData?: Partial<AuthUser>) => void;
  logout: () => void;
  switchRole: (role: UserRole) => void;
  isReady: boolean;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  role: "GUEST",
  loginAs: () => {},
  logout: () => {},
  switchRole: () => {},
  isReady: false,
});

const STORAGE_KEY = "vf_serviceflow_auth";

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        setUser(parsed);
      }
    } catch {
      // Fallback
    } finally {
      setIsReady(true);
    }
  }, []);

  const loginAs = (role: "CUSTOMER" | "STAFF", customData?: Partial<AuthUser>) => {
    const base = DEMO_PROFILES[role];
    const newUser: AuthUser = {
      ...base,
      ...customData,
      role,
    };
    setUser(newUser);
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(newUser));
    } catch {}
  };

  const logout = () => {
    setUser(null);
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch {}
  };

  const switchRole = (newRole: UserRole) => {
    if (newRole === "GUEST") {
      logout();
    } else {
      loginAs(newRole);
    }
  };

  const role: UserRole = user?.role || "GUEST";

  return (
    <AuthContext.Provider
      value={{
        user,
        role,
        loginAs,
        logout,
        switchRole,
        isReady,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
