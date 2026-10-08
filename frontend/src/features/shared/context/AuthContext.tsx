"use client";

import React, { createContext, useContext, useEffect, useState } from "react";

export type UserRole = "GUEST" | "CUSTOMER" | "STAFF";
export type AuthenticatedRole = Exclude<UserRole, "GUEST">;

export interface AuthUser {
  id: string;
  name: string;
  role: AuthenticatedRole;
  email: string;
  phone?: string;
  vehicleModel?: string;
  mockCustomerId?: string;
  avatar?: string;
}

interface ApiUser {
  id: string;
  username: string;
  role: AuthenticatedRole;
  full_name?: string | null;
  phone?: string | null;
  vehicle_model?: string | null;
  mock_customer_id?: string | null;
}

interface AuthResponse {
  success: boolean;
  data: { token: string; user: ApiUser };
  error?: string | null;
}

interface UserResponse {
  success: boolean;
  data: ApiUser;
}

export interface UpdateProfilePayload {
  name?: string;
  phone?: string;
  vehicleModel?: string;
}

interface AuthContextType {
  user: AuthUser | null;
  role: UserRole;
  login: (username: string, password: string) => Promise<AuthUser>;
  registerCustomer: (username: string, password: string, profile?: Pick<AuthUser, "name" | "vehicleModel" | "phone">) => Promise<AuthUser>;
  loginDemo: (role: "CUSTOMER" | "STAFF") => Promise<AuthUser>;
  updateProfile: (payload: UpdateProfilePayload) => Promise<AuthUser>;
  logout: () => void;
  isReady: boolean;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  role: "GUEST",
  login: async () => { throw new Error("AuthProvider is not mounted"); },
  registerCustomer: async () => { throw new Error("AuthProvider is not mounted"); },
  loginDemo: async () => { throw new Error("AuthProvider is not mounted"); },
  updateProfile: async () => { throw new Error("AuthProvider is not mounted"); },
  logout: () => { },
  isReady: false,
});

const STORAGE_KEY = "vf_serviceflow_auth";
const TOKEN_KEY = "vf_access_token";
const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const DEMO_CREDENTIALS: Record<"CUSTOMER" | "STAFF", { username: string; password: string }> = {
  CUSTOMER: { username: "customer@vinfast.vn", password: "customer123" },
  STAFF: { username: "staff@vinfast.vn", password: "staff123" },
};

function savedProfile(): Partial<AuthUser> {
  try {
    const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) || "null");
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch {
    return {};
  }
}

function mapApiUser(user: ApiUser, profile: Partial<AuthUser> = {}): AuthUser {
  const localProfile = profile.id && profile.id !== user.id ? {} : profile;
  const fallbackName = user.username.includes("@") ? "Chủ xe VinFast" : user.username;
  const name =
    user.full_name ||
    (localProfile.name && !localProfile.name.startsWith("CUST_MOCK") ? localProfile.name : null) ||
    fallbackName;
  const vehicleModel = user.vehicle_model || localProfile.vehicleModel || "VF8";
  const phone =
    user.phone && user.phone !== "customer" && !user.phone.startsWith("customer")
      ? user.phone
      : localProfile.phone && localProfile.phone !== "customer"
        ? localProfile.phone
        : undefined;
  return {
    id: user.id,
    role: user.role,
    name,
    email: user.username,
    phone: phone || undefined,
    vehicleModel: vehicleModel || undefined,
    mockCustomerId: user.mock_customer_id || undefined,
    avatar: localProfile.avatar,
  };
}

function clearLegacyTokens() {
  localStorage.removeItem("vf_customer_token");
  localStorage.removeItem("vf_staff_token");
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isReady, setIsReady] = useState(false);

  const acceptAuthResponse = (response: AuthResponse, localProfile: Partial<AuthUser> = {}) => {
    const authUser = mapApiUser(response.data.user, localProfile);
    localStorage.setItem(TOKEN_KEY, response.data.token);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(authUser));
    clearLegacyTokens();
    setUser(authUser);
    return authUser;
  };

  const login = async (username: string, password: string) => {
    const response = await fetch(`${BASE_URL}/api/v1/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: username.trim(), password }),
    });
    const json = await response.json().catch(() => null);
    if (!response.ok || !json?.data?.token || !json?.data?.user) {
      throw new Error(json?.detail || json?.error || "Tên đăng nhập hoặc mật khẩu không chính xác.");
    }
    localStorage.setItem("vf_last_username", username.trim());
    return acceptAuthResponse(json as AuthResponse, savedProfile());
  };

  const registerCustomer: AuthContextType["registerCustomer"] = async (username, password, profile) => {
    const response = await fetch(`${BASE_URL}/api/v1/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        username: username.trim(),
        password,
        full_name: profile?.name?.trim() || null,
        phone: profile?.phone?.trim() || username.trim(),
        vehicle_model: profile?.vehicleModel || null,
      }),
    });
    const json = await response.json().catch(() => null);
    if (!response.ok || !json?.data?.token || !json?.data?.user) {
      throw new Error(json?.detail || json?.error || "Không thể tạo tài khoản. Vui lòng thử lại.");
    }
    localStorage.setItem("vf_last_username", username.trim());
    return acceptAuthResponse(json as AuthResponse, profile);
  };

  const loginDemo = async (role: "CUSTOMER" | "STAFF") => {
    const credentials = DEMO_CREDENTIALS[role];
    const authUser = await login(credentials.username, credentials.password);
    if (authUser.role !== role) {
      logout();
      throw new Error("Demo account has the wrong role. Check the local seed data.");
    }
    return authUser;
  };

  const updateProfile = async (payload: UpdateProfilePayload) => {
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) throw new Error("Chưa đăng nhập.");

    const response = await fetch(`${BASE_URL}/api/v1/auth/me`, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        full_name: payload.name !== undefined ? payload.name.trim() || null : undefined,
        phone: payload.phone !== undefined ? payload.phone.trim() || null : undefined,
        vehicle_model: payload.vehicleModel !== undefined ? payload.vehicleModel.trim() || null : undefined,
      }),
    });

    const json = await response.json().catch(() => null);
    if (!response.ok || !json?.data) {
      throw new Error(json?.detail || json?.error || "Không thể cập nhật thông tin cá nhân.");
    }

    const updated = mapApiUser(json.data, {
      ...user,
      name: payload.name ?? user?.name,
      phone: payload.phone ?? user?.phone,
      vehicleModel: payload.vehicleModel ?? user?.vehicleModel,
    });
    localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
    setUser(updated);
    return updated;
  };

  const logout = () => {
    setUser(null);
    localStorage.removeItem(STORAGE_KEY);
    localStorage.removeItem(TOKEN_KEY);
    clearLegacyTokens();
  };

  useEffect(() => {
    let cancelled = false;
    const token = localStorage.getItem(TOKEN_KEY);
    clearLegacyTokens();
    if (!token) {
      localStorage.removeItem(STORAGE_KEY);
      setIsReady(true);
      return () => { cancelled = true; };
    }

    fetch(`${BASE_URL}/api/v1/auth/me`, { headers: { Authorization: `Bearer ${token}` } })
      .then(async (response) => {
        if (!response.ok) throw new Error("Session expired");
        return response.json() as Promise<UserResponse>;
      })
      .then((json) => {
        if (!cancelled && json?.data) {
          const authUser = mapApiUser(json.data, savedProfile());
          localStorage.setItem(STORAGE_KEY, JSON.stringify(authUser));
          setUser(authUser);
        }
      })
      .catch(() => {
        if (!cancelled) {
          localStorage.removeItem(TOKEN_KEY);
          localStorage.removeItem(STORAGE_KEY);
          setUser(null);
        }
      })
      .finally(() => {
        if (!cancelled) setIsReady(true);
      });

    return () => { cancelled = true; };
  }, []);

  const role: UserRole = user?.role || "GUEST";

  return (
    <AuthContext.Provider value={{ user, role, login, registerCustomer, loginDemo, updateProfile, logout, isReady }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
