"use client";

import React, { createContext, useContext, useEffect, useRef, useState } from "react";

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
  loginAs: (role: "CUSTOMER" | "STAFF", customData?: Partial<AuthUser>) => Promise<boolean>;
  logout: () => void;
  switchRole: (role: UserRole) => void;
  isReady: boolean;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  role: "GUEST",
  loginAs: async () => false,
  logout: () => {},
  switchRole: () => {},
  isReady: false,
});

const STORAGE_KEY = "vf_serviceflow_auth";

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isReady, setIsReady] = useState(false);
  const loginGeneration = useRef(0);

  useEffect(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        const tokenKey = parsed.role === "STAFF" ? "vf_staff_token" : "vf_customer_token";
        if (["CUSTOMER", "STAFF"].includes(parsed.role) && localStorage.getItem(tokenKey)) {
          setUser(parsed);
        } else {
          localStorage.removeItem(STORAGE_KEY);
        }
      }
    } catch {
      // Fallback
    } finally {
      setIsReady(true);
    }
  }, []);

  const loginAs = async (role: "CUSTOMER" | "STAFF", customData?: Partial<AuthUser>): Promise<boolean> => {
    const generation = ++loginGeneration.current;
    const base = DEMO_PROFILES[role];
    const newUser: AuthUser = {
      ...base,
      ...customData,
      role,
    };
    try {
      const username = role === "STAFF" ? "staff@vinfast.vn" : "customer@vinfast.vn";
      const password = role === "STAFF" ? "staff123" : "customer123";
      const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const response = await fetch(`${baseUrl}/api/v1/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      if (!response.ok) return false;
      const json = await response.json();
      if (!json?.data?.token || generation !== loginGeneration.current) return false;
      localStorage.setItem(role === "STAFF" ? "vf_staff_token" : "vf_customer_token", json.data.token);
      localStorage.removeItem(role === "STAFF" ? "vf_customer_token" : "vf_staff_token");
      localStorage.setItem(STORAGE_KEY, JSON.stringify(newUser));
      setUser(newUser);
      return true;
    } catch {
      return false;
    }
  };

  const logout = () => {
    loginGeneration.current++;
    setUser(null);
    try {
      localStorage.removeItem(STORAGE_KEY);
      localStorage.removeItem("vf_staff_token");
      localStorage.removeItem("vf_customer_token");
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
