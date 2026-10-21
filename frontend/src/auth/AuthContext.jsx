import React, { createContext, useContext, useState, useEffect } from 'react';
import { 
  getStoredStudent, 
  saveAuthSession, 
  clearAuthSession, 
  apiLogin, 
  apiRegister, 
  apiGetMe 
} from '../services/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [student, setStudent] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check local token on mount
    const stored = getStoredStudent();
    const token = localStorage.getItem('prepgenius_auth_token');

    if (token && stored) {
      setStudent(stored);
      // Validate session with backend in background
      apiGetMe()
        .then((fresh) => {
          setStudent(fresh);
          localStorage.setItem('prepgenius_student', JSON.stringify(fresh));
        })
        .catch(() => {
          // Token is invalid/expired
          clearAuthSession();
          setStudent(null);
        })
        .finally(() => {
          setLoading(false);
        });
    } else {
      setLoading(false);
    }
  }, []);

  const login = async (email, password) => {
    const data = await apiLogin({ email, password });
    setStudent(data.student);
    return data.student;
  };

  const register = async (fullName, email, password) => {
    const data = await apiRegister({ fullName, email, password });
    setStudent(data.student);
    return data.student;
  };

  const logout = () => {
    clearAuthSession();
    setStudent(null);
  };

  const value = {
    student,
    isAuthenticated: !!student,
    loading,
    login,
    register,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
