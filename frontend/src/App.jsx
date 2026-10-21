import React, { useState } from 'react';
import { AuthProvider, useAuth } from './auth/AuthContext';
import DashboardLayout from './layouts/DashboardLayout';
import ProfilePage from './pages/ProfilePage';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import { Loader2 } from 'lucide-react';

function AppContent() {
  const { student, isAuthenticated, loading } = useAuth();
  const [authView, setAuthView] = useState('login'); // 'login' | 'register'

  // Loading Session State
  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center space-y-3">
        <Loader2 className="h-8 w-8 text-blue-500 animate-spin" />
        <p className="text-xs text-slate-400 font-medium">Verifying student session...</p>
      </div>
    );
  }

  // Access Control: Non-authenticated students must sign in or register first
  if (!isAuthenticated) {
    if (authView === 'register') {
      return <RegisterPage onNavigateToLogin={() => setAuthView('login')} />;
    }
    return <LoginPage onNavigateToRegister={() => setAuthView('register')} />;
  }

  // Authenticated Student: Full access to PrepGenius features
  return (
    <DashboardLayout 
      activeTab="profile" 
      studentId={student?.full_name || student?.email || 'Authenticated Student'}
    >
      <ProfilePage />
    </DashboardLayout>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}
