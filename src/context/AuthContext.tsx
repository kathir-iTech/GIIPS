import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../services/api';

interface User {
  user_id: string;
  full_name: string;
  email: string;
  role: 'Citizen' | 'Officer' | 'Executive';
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  login: (email: string, password: string) => Promise<void>;
  register: (data: RegisterData) => Promise<void>;
  logout: () => void;
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
  role: string;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider');
  return context;
};

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    try {
      const savedToken = localStorage.getItem('giips_token');
      const savedUser = localStorage.getItem('giips_user');
      if (savedToken && savedUser) {
        setToken(savedToken);
        setUser(JSON.parse(savedUser));
      }
    } catch {
      localStorage.removeItem('giips_token');
      localStorage.removeItem('giips_user');
    }
  }, []);

  useEffect(() => {
    if (user) {
      localStorage.setItem('giips_user', JSON.stringify(user));
    }
  }, [user]);

  const navigateBasedOnRole = (role: string) => {
    if (role === 'Citizen') navigate('/citizen');
    else if (role === 'Officer') navigate('/officer');
    else if (role === 'Executive') navigate('/executive');
    else navigate('/');
  };

  const login = async (email: string, password: string) => {
    setIsLoading(true);
    try {
      const response = await api.login(email, password);
      setToken(response.access_token);
      setUser({
        user_id: 'temp',
        full_name: email.split('@')[0],
        email,
        role: response.role
      });
      localStorage.setItem('giips_token', response.access_token);
      // Navigate after state is committed
      setTimeout(() => navigateBasedOnRole(response.role), 0);
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (data: RegisterData) => {
    setIsLoading(true);
    try {
      await api.register(data);
      navigate('/login');
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    setUser(null);
    setToken(null);
    localStorage.removeItem('giips_token');
    localStorage.removeItem('giips_user');
    navigate('/');
  };

  return (
    <AuthContext.Provider value={{ user, token, login, register, logout, isLoading, navigateBasedOnRole }}>
      {children}
    </AuthContext.Provider>
  );
};
