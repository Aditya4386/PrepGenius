import React from 'react';
import { 
  UserCheck, 
  MapPin, 
  FileText, 
  Mic, 
  HelpCircle, 
  LayoutDashboard, 
  Sparkles,
  ShieldCheck,
  GraduationCap,
  LogOut
} from 'lucide-react';
import { useAuth } from '../auth/AuthContext';

export default function DashboardLayout({ children, activeTab = 'profile', studentId = 'Student' }) {
  const { student, logout } = useAuth();
  const navItems = [
    { id: 'profile', label: 'Student Profile', icon: UserCheck, active: true, badge: 'Module 1 Active' },
    { id: 'roadmap', label: 'Study Roadmap', icon: MapPin, disabled: true, badge: 'Module 2' },
    { id: 'resume', label: 'Resume Analyzer', icon: FileText, disabled: true, badge: 'Module 3' },
    { id: 'learning', label: 'Learning Assistant', icon: HelpCircle, disabled: true, badge: 'Module 4' },
    { id: 'interview', label: 'Mock Interview', icon: Mic, disabled: true, badge: 'Module 5' },
  ];

  return (
    <div className="min-h-screen flex bg-slate-950 text-slate-100">
      {/* Sidebar Navigation */}
      <aside className="w-72 bg-slate-900/80 border-r border-slate-800/80 flex flex-col backdrop-blur-xl shrink-0">
        {/* Brand Header */}
        <div className="p-6 border-b border-slate-800/60 flex items-center space-x-3">
          <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-blue-600 via-indigo-600 to-cyan-400 flex items-center justify-center shadow-lg shadow-blue-500/20">
            <GraduationCap className="h-6 w-6 text-white" />
          </div>
          <div>
            <span className="font-bold text-lg tracking-tight bg-gradient-to-r from-white via-slate-200 to-blue-300 bg-clip-text text-transparent">
              PrepGenius
            </span>
            <p className="text-xs text-slate-400">Career Readiness Platform</p>
          </div>
        </div>

        {/* Navigation Links */}
        <nav className="flex-1 p-4 space-y-1.5">
          <div className="px-3 py-2 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
            Core Modules
          </div>
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <div
                key={item.id}
                id={`nav-item-${item.id}`}
                className={`flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
                  item.active
                    ? 'bg-blue-600/15 text-blue-400 border border-blue-500/30 shadow-sm'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50 cursor-not-allowed opacity-60'
                }`}
              >
                <div className="flex items-center space-x-3">
                  <Icon className={`h-4 w-4 ${item.active ? 'text-blue-400' : 'text-slate-400'}`} />
                  <span>{item.label}</span>
                </div>
                <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${
                  item.active 
                    ? 'bg-blue-500/20 text-blue-300 border border-blue-400/30' 
                    : 'bg-slate-800 text-slate-400'
                }`}>
                  {item.badge}
                </span>
              </div>
            );
          })}
        </nav>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-y-auto">
        {/* Top Navbar */}
        <header className="h-16 border-b border-slate-800/80 bg-slate-900/40 backdrop-blur-md px-8 flex items-center justify-between shrink-0">
          <div className="flex items-center space-x-2">
            <span className="text-xs font-semibold px-2.5 py-1 rounded-md bg-blue-500/10 text-blue-400 border border-blue-500/20">
              Module 1: Shared Student Profile
            </span>
          </div>

          {/* User Status, Profile & Logout */}
          <div className="flex items-center space-x-4">
            <div className="text-right">
              <p className="text-xs font-semibold text-slate-100">
                {student?.full_name || student?.email || studentId}
              </p>
              <p className="text-[10px] text-slate-400 font-mono">
                {student?.email || 'Logged In Student'}
              </p>
            </div>

            <div className="h-9 w-9 rounded-full bg-gradient-to-tr from-blue-500 to-indigo-600 flex items-center justify-center font-bold text-xs text-white shadow-md border border-white/10">
              {student?.full_name
                ? student.full_name.substring(0, 2).toUpperCase()
                : (studentId ? studentId.substring(0, 2).toUpperCase() : 'ST')}
            </div>

            {/* Logout Button */}
            <button
              type="button"
              id="btn-logout"
              onClick={logout}
              title="Sign Out"
              className="p-2 rounded-lg bg-slate-800/80 hover:bg-red-500/15 text-slate-400 hover:text-red-400 border border-slate-700/60 hover:border-red-500/30 transition-all flex items-center space-x-1.5 text-xs font-medium"
            >
              <LogOut className="h-4 w-4" />
              <span className="hidden sm:inline">Sign Out</span>
            </button>
          </div>
        </header>

        {/* Page View Body */}
        <main className="flex-1 p-8 max-w-6xl mx-auto w-full">
          {children}
        </main>
      </div>
    </div>
  );
}
