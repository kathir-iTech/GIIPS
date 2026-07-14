import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../services/api';

import type { UserRole } from '../types';

interface User {
  user_id: string;
  full_name: string;
  email: string;
  role: UserRole;
  ward?: string;
  district?: string;
}

interface AuthContextType {
  user: User | null;
  login: (email: string, password: string) => Promise<void>;
  register: (data: RegisterData) => Promise<void>;
  logout: () => Promise<void>;
  isLoading: boolean;
  navigateBasedOnRole: (role: string) => void;
}

interface RegisterData {
  full_name: string;
  email: string;
  password: string;
  phone?: string;
  district?: string;
  ward?: string;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider');
  return context;
};

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    api.getMe()
      .then(data => {
        setUser({
          user_id: data.user_id,
          full_name: data.full_name,
          email: data.email,
          role: data.role,
          ward: data.ward,
          district: data.district,
        });
      })
      .catch(() => {
        setUser(null);
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, []);

  const navigateBasedOnRole = (role: string) => {
    if (role === 'Citizen') navigate('/citizen');
    else if (role === 'Officer') navigate('/officer');
    else if (role === 'Executive') navigate('/executive');
    else if (role === 'Councillor' || role === 'Commissioner') navigate('/local-authority');
    else if (role === 'MLA' || role === 'Collector') navigate('/oversight');
    else navigate('/');
  };

  const login = async (email: string, password: string) => {
    setIsLoading(true);
    try {
      const response = await api.login(email, password);
      let userData: User = {
        user_id: response.user_id || email,
        full_name: response.full_name || email.split('@')[0],
        email,
        role: response.role
      };
      setUser(userData);
      setTimeout(() => navigateBasedOnRole(response.role), 0);
    } catch (err: any) {
      throw new Error(err.message || 'Login failed');
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (data: RegisterData) => {
    setIsLoading(true);
    try {
      await api.register(data);
    } catch (err: any) {
      throw new Error(err.message || 'Registration failed');
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    try {
      await api.logout();
    } catch {
      // clear client state regardless
    }
    setUser(null);
    navigate('/');
  };

  return (
    <AuthContext.Provider value={{ user, login, register, logout, isLoading, navigateBasedOnRole }}>
      {children}
    </AuthContext.Provider>
  );
};