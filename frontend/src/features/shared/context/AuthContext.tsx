"use client";

import React, { createContext, useContext, useEffect, useRef, useState } from "react";

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
  isDemo?: boolean;
}

interface ApiUser {
  id: string;
  username: string;
  role: AuthenticatedRole;
  full_name?: string | null;
  phone?: string | null;
  vehicle_model?: string | null;
  mock_customer_id?: string | null;
  is_demo?: boolean | null;
}

interface AuthResponse {
  success: boolean;
  data: { token: string; user?: ApiUser };
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
  updateProfile: (payload: UpdateProfilePayload) => Promise<AuthUser>;
  logout: () => void;
  isReady: boolean;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  role: "GUEST",
  login: async () => { throw new Error("AuthProvider is not mounted"); },
  registerCustomer: async () => { throw new Error("AuthProvider is not mounted"); },
  updateProfile: async () => { throw new Error("AuthProvider is not mounted"); },
  logout: () => { },
  isReady: false,
});

const STORAGE_KEY = "vf_serviceflow_auth";
const TOKEN_KEY = "vf_access_token";
const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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
    isDemo: Boolean(user.is_demo),
  };
}

function clearLegacyTokens() {
  localStorage.removeItem("vf_customer_token");
  localStorage.removeItem("vf_staff_token");
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isReady, setIsReady] = useState(false);
  const loginGeneration = useRef(0);

  const getActiveGuestSessionId = (): string | null => {
    if (typeof window === "undefined") return null;
    try {
      return localStorage.getItem("vf_guest_id") || localStorage.getItem("vf_chat_session:guest");
    } catch {
      return null;
    }
  };

  const clearGuestSessionOnClient = () => {
    if (typeof window === "undefined") return;
    try {
      localStorage.removeItem("vf_guest_id");
      localStorage.removeItem("vf_chat_session:guest");
      localStorage.removeItem("vf_chat_case:guest");
    } catch {}
  };

  const acceptAuthResponse = (
    response: { data: { token: string; user?: ApiUser } },
    localProfile: Partial<AuthUser> = {},
  ) => {
    if (!response.data.user) {
      throw new Error("Phản hồi xác thực không hợp lệ từ máy chủ.");
    }
    const authUser: AuthUser = mapApiUser(response.data.user, localProfile);

    localStorage.setItem(TOKEN_KEY, response.data.token);
    const tokenKey = authUser.role === "STAFF" ? "vf_staff_token" : "vf_customer_token";
    localStorage.setItem(tokenKey, response.data.token);
    // Xóa token role đối diện để tránh xung đột quyền
    localStorage.removeItem(authUser.role === "STAFF" ? "vf_customer_token" : "vf_staff_token");
    localStorage.setItem(STORAGE_KEY, JSON.stringify(authUser));
    clearGuestSessionOnClient();
    setUser(authUser);
    return authUser;
  };

  const requestLogin = async (username: string, password: string): Promise<AuthResponse> => {
    const guestSessionId = getActiveGuestSessionId();
    const response = await fetch(`${BASE_URL}/api/v1/auth/login`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(guestSessionId ? { "X-Session-Id": guestSessionId } : {}),
      },
      body: JSON.stringify({
        username: username.trim(),
        password,
        guest_session_id: guestSessionId || undefined,
      }),
    });
    const json = await response.json().catch(() => null);
    if (!response.ok || !json?.data?.token) {
      throw new Error(json?.detail || json?.error || "Tên đăng nhập hoặc mật khẩu không chính xác.");
    }
    return json as AuthResponse;
  };

  const login = async (username: string, password: string) => {
    const generation = ++loginGeneration.current;
    const json = await requestLogin(username, password);
    if (generation !== loginGeneration.current) {
      throw new Error("Phiên đăng nhập đã bị hủy.");
    }
    if (!json.data.user) {
      throw new Error("Phản hồi đăng nhập không hợp lệ từ máy chủ.");
    }
    localStorage.setItem("vf_last_username", username.trim());
    return acceptAuthResponse(json, savedProfile());
  };

  const registerCustomer: AuthContextType["registerCustomer"] = async (username, password, profile) => {
    const generation = ++loginGeneration.current;
    const guestSessionId = getActiveGuestSessionId();
    const response = await fetch(`${BASE_URL}/api/v1/auth/register`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(guestSessionId ? { "X-Session-Id": guestSessionId } : {}),
      },
      body: JSON.stringify({
        username: username.trim(),
        password,
        full_name: profile?.name?.trim() || null,
        phone: profile?.phone?.trim() || username.trim(),
        vehicle_model: profile?.vehicleModel || null,
        guest_session_id: guestSessionId || undefined,
      }),
    });
    const json = await response.json().catch(() => null);
    if (generation !== loginGeneration.current) {
      throw new Error("Phiên đăng nhập đã bị hủy.");
    }
    if (!response.ok || !json?.data?.token || !json?.data?.user) {
      throw new Error(json?.detail || json?.error || "Không thể tạo tài khoản. Vui lòng thử lại.");
    }
    localStorage.setItem("vf_last_username", username.trim());
    return acceptAuthResponse(json, profile);
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
    loginGeneration.current++;
    setUser(null);
    try {
      localStorage.removeItem(STORAGE_KEY);
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem("vf_staff_token");
      localStorage.removeItem("vf_customer_token");
      localStorage.removeItem("vf_chat_session:guest");
      localStorage.removeItem("vf_chat_case:guest");
      localStorage.removeItem("vf_guest_id");
      const freshGuestId =
        typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
          ? `sess_vf_${crypto.randomUUID()}`
          : `sess_vf_${Math.random().toString(36).slice(2)}_${Date.now()}`;
      localStorage.setItem("vf_chat_session:guest", freshGuestId);
    } catch { }
  };

  useEffect(() => {
    let cancelled = false;
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      const customerToken = localStorage.getItem("vf_customer_token");
      const staffToken = localStorage.getItem("vf_staff_token");
      const accessToken = localStorage.getItem(TOKEN_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        const token = parsed.role === "STAFF" ? (staffToken || accessToken) : (customerToken || accessToken);
        if (["CUSTOMER", "STAFF"].includes(parsed.role) && token) {
          setUser(parsed);
        } else {
          localStorage.removeItem(STORAGE_KEY);
        }
      }
    } catch {
      localStorage.removeItem(STORAGE_KEY);
    } finally {
      setIsReady(true);
    }

    const token = localStorage.getItem(TOKEN_KEY) || localStorage.getItem("vf_customer_token") || localStorage.getItem("vf_staff_token");
    if (!token) return;

    fetch(`${BASE_URL}/api/v1/auth/me`, { headers: { Authorization: `Bearer ${token}` } })
      .then(async (response) => {
        if (response.status === 401 || response.status === 403) {
          if (!cancelled) logout();
          return null;
        }
        if (!response.ok) throw new Error("Server error");
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
        // offline fallback: giữ phiên đăng nhập tạm thời khi lỗi kết nối mạng
      });

    return () => { cancelled = true; };
  }, []);

  const role: UserRole = user?.role || "GUEST";

  return (
    <AuthContext.Provider value={{ user, role, login, registerCustomer, updateProfile, logout, isReady }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
