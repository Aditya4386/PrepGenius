import React, { useState, useEffect } from 'react';
import { 
  fetchProfile, 
  saveProfile 
} from '../services/api';
import { 
  TARGET_ROLE_CATEGORIES, 
  COMPANY_TYPES 
} from '../utils/constants';
import SkillsManager from '../components/SkillsManager';
import EducationManager from '../components/EducationManager';
import { 
  Save, 
  CheckCircle, 
  AlertCircle, 
  Clock, 
  Calendar, 
  Briefcase, 
  Building2, 
  Target, 
  Sparkles,
  Info,
  Loader2,
  RefreshCw
} from 'lucide-react';

export default function ProfilePage() {
  // UI State Handlers
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);

  // Form State
  const [profile, setProfile] = useState({
    target_role: '',
    company_type: '',
    target_companies: [],
    career_goal: '',
    weekly_study_hours: 10.0,
    preparation_deadline: '',
    skills: [],
    education: [],
    is_profile_complete: false,
    student_id: '',
  });

  const [companyInput, setCompanyInput] = useState('');

  // Initial load: Fetch authenticated student profile
  useEffect(() => {
    loadProfile();
  }, []);

  const loadProfile = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchProfile();
      setProfile({
        target_role: data.target_role || '',
        company_type: data.company_type || '',
        target_companies: data.target_companies || [],
        career_goal: data.career_goal || '',
        weekly_study_hours: data.weekly_study_hours || 10.0,
        preparation_deadline: data.preparation_deadline || '',
        skills: data.skills || [],
        education: data.education || [],
        is_profile_complete: data.is_profile_complete || false,
        student_id: data.student_id || '',
      });
    } catch (err) {
      setError(err.message || 'Failed to load student profile');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setSuccessMessage(null);

    try {
      const payload = {
        target_role: profile.target_role || null,
        company_type: profile.company_type || null,
        target_companies: profile.target_companies,
        career_goal: profile.career_goal || null,
        weekly_study_hours: parseFloat(profile.weekly_study_hours) || 10.0,
        preparation_deadline: profile.preparation_deadline || null,
        skills: profile.skills,
        education: profile.education,
      };

      const updated = await saveProfile(payload);
      setProfile(prev => ({
        ...prev,
        ...updated,
        is_profile_complete: updated.is_profile_complete,
      }));
      setSuccessMessage('Student profile updated successfully in MySQL database!');
      setTimeout(() => setSuccessMessage(null), 5000);
    } catch (err) {
      setError(err.message || 'An error occurred while saving profile');
    } finally {
      setSaving(false);
    }
  };

  const handleAddCompany = (e) => {
    if (e) e.preventDefault();
    const clean = companyInput.trim();
    if (!clean) return;
    if (!profile.target_companies.includes(clean)) {
      setProfile(prev => ({
        ...prev,
        target_companies: [...prev.target_companies, clean],
      }));
    }
    setCompanyInput('');
  };

  const handleRemoveCompany = (companyName) => {
    setProfile(prev => ({
      ...prev,
      target_companies: prev.target_companies.filter(c => c !== companyName),
    }));
  };

  // 1. Loading Skeleton State
  if (loading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-24 bg-slate-900/60 rounded-2xl border border-slate-800"></div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="h-64 bg-slate-900/60 rounded-2xl border border-slate-800"></div>
          <div className="h-64 bg-slate-900/60 rounded-2xl border border-slate-800"></div>
        </div>
        <div className="h-48 bg-slate-900/60 rounded-2xl border border-slate-800"></div>
      </div>
    );
  }

  // 2. Error State with Retry
  if (error && !profile.student_id) {
    return (
      <div className="p-8 rounded-2xl bg-red-950/20 border border-red-500/30 text-center space-y-4">
        <AlertCircle className="h-10 w-10 text-red-400 mx-auto" />
        <h3 className="text-lg font-bold text-slate-100">Unable to Connect to Backend</h3>
        <p className="text-sm text-slate-400 max-w-md mx-auto">{error}</p>
        <button
          type="button"
          onClick={loadProfile}
          className="px-4 py-2 rounded-lg bg-red-600 hover:bg-red-500 text-white text-sm font-medium inline-flex items-center space-x-2 transition-all"
        >
          <RefreshCw className="h-4 w-4" />
          <span>Retry Connection</span>
        </button>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-8 pb-12">
      {/* Header Banner & Completion Status */}
      <div className="p-6 rounded-2xl bg-gradient-to-r from-slate-900 via-slate-900/90 to-blue-950/40 border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-xl">
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-2xl font-bold tracking-tight text-white">
              Student Career Profile
            </h1>
            <span className="text-[11px] font-semibold uppercase px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20">
              Single Source of Truth
            </span>
          </div>
        </div>

        {/* Readiness Badge */}
        <div className="shrink-0 flex items-center space-x-3">
          <div className="text-right">
            <span className="text-xs text-slate-400 block font-medium">Profile Status</span>
            <span className={`text-sm font-bold flex items-center space-x-1.5 ${
              profile.is_profile_complete ? 'text-emerald-400' : 'text-amber-400'
            }`}>
              {profile.is_profile_complete ? (
                <>
                  <CheckCircle className="h-4 w-4 inline" />
                  <span>Ready for AI Modules</span>
                </>
              ) : (
                <>
                  <Info className="h-4 w-4 inline" />
                  <span>Setup Incomplete</span>
                </>
              )}
            </span>
          </div>
          <button
            type="submit"
            id="btn-save-profile-top"
            disabled={saving}
            className="px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-medium text-sm flex items-center space-x-2 transition-all shadow-lg shadow-blue-600/30 disabled:opacity-50"
          >
            {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
            <span>{saving ? 'Saving...' : 'Save Profile'}</span>
          </button>
        </div>
      </div>

      {/* Notifications: Success or Validation Alerts */}
      {successMessage && (
        <div className="p-4 rounded-xl bg-emerald-950/40 border border-emerald-500/40 text-emerald-300 flex items-center space-x-3 text-sm animate-fadeIn">
          <CheckCircle className="h-5 w-5 text-emerald-400 shrink-0" />
          <span>{successMessage}</span>
        </div>
      )}

      {error && (
        <div className="p-4 rounded-xl bg-red-950/40 border border-red-500/40 text-red-300 flex items-center space-x-3 text-sm animate-fadeIn">
          <AlertCircle className="h-5 w-5 text-red-400 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* SECTION 1: Target Career Role & Company Focus */}
      <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-6">
        <div className="flex items-center space-x-2 pb-3 border-b border-slate-800/80">
          <Briefcase className="h-5 w-5 text-blue-400" />
          <h2 className="text-base font-bold text-slate-100">1. Target Career Role & Track</h2>
        </div>

        <div className="space-y-4">
          <div>
            <label htmlFor="select-target-role" className="block text-sm font-semibold text-slate-200 mb-1.5">
              Select Primary Target Role <span className="text-blue-400">*</span>
            </label>
            <select
              id="select-target-role"
              value={profile.target_role}
              onChange={(e) => setProfile(prev => ({ ...prev, target_role: e.target.value }))}
              className="w-full px-4 py-3 rounded-xl bg-slate-950 border border-slate-700/80 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500/40 focus:border-blue-500"
            >
              <option value="">-- Choose your primary role (36 roles available) --</option>
              {TARGET_ROLE_CATEGORIES.map((cat) => (
                <optgroup key={cat.category} label={cat.category} className="bg-slate-900 font-semibold text-slate-300">
                  {cat.roles.map((role) => (
                    <option key={role} value={role} className="bg-slate-950 text-slate-100 font-normal">
                      {role}
                    </option>
                  ))}
                </optgroup>
              ))}
            </select>
          </div>

          {/* Company Type Cards */}
          <div>
            <label className="block text-sm font-semibold text-slate-200 mb-2">
              Target Company Category <span className="text-blue-400">*</span>
            </label>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {COMPANY_TYPES.map((type) => {
                const isSelected = profile.company_type === type.id;
                return (
                  <div
                    key={type.id}
                    id={`company-type-${type.id}`}
                    onClick={() => setProfile(prev => ({ ...prev, company_type: type.id }))}
                    className={`p-4 rounded-xl border cursor-pointer transition-all flex items-center justify-between ${
                      isSelected
                        ? 'bg-blue-600/15 border-blue-500 shadow-md shadow-blue-500/10'
                        : 'bg-slate-950/60 border-slate-800 hover:border-slate-700'
                    }`}
                  >
                    <span className="font-bold text-sm text-slate-100">{type.label}</span>
                    <span className={`h-4 w-4 rounded-full border flex items-center justify-center shrink-0 ${
                      isSelected ? 'border-blue-400 bg-blue-500' : 'border-slate-600'
                    }`}>
                      {isSelected && <span className="h-1.5 w-1.5 rounded-full bg-white"></span>}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {/* SECTION 2: Study Horizon & Feasibility Constraints */}
      <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-6">
        <div className="flex items-center space-x-2 pb-3 border-b border-slate-800/80">
          <Clock className="h-5 w-5 text-indigo-400" />
          <h2 className="text-base font-bold text-slate-100">2. Study Horizon & Time Budget</h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Weekly Hours Slider */}
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <label htmlFor="input-weekly-hours" className="text-sm font-semibold text-slate-200">
                Weekly Study Commitment
              </label>
              <span className="text-xs font-mono font-bold px-2.5 py-1 rounded-md bg-indigo-500/15 text-indigo-300 border border-indigo-500/30">
                {profile.weekly_study_hours} hrs / week
              </span>
            </div>
            <input
              id="input-weekly-hours"
              type="range"
              min="1"
              max="60"
              step="1"
              value={profile.weekly_study_hours}
              onChange={(e) => setProfile(prev => ({ ...prev, weekly_study_hours: parseFloat(e.target.value) }))}
              className="w-full h-2 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-indigo-500"
            />
            <div className="flex justify-between text-[11px] text-slate-400">
              <span>1 hr (Light)</span>
              <span>15 hrs (Balanced)</span>
              <span>30 hrs (Intensive)</span>
              <span>60 hrs (Full-time)</span>
            </div>
          </div>

          {/* Preparation Deadline */}
          <div className="space-y-3">
            <label htmlFor="input-deadline" className="text-sm font-semibold text-slate-200 block">
              Placement / Target Deadline
            </label>
            <div className="relative">
              <input
                id="input-deadline"
                type="date"
                value={profile.preparation_deadline || ''}
                onChange={(e) => setProfile(prev => ({ ...prev, preparation_deadline: e.target.value }))}
                className="w-full px-4 py-2.5 rounded-xl bg-slate-950 border border-slate-700/80 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 focus:border-indigo-500"
              />
            </div>
          </div>
        </div>
      </div>

      {/* SECTION 3: Target Companies & Career Objective */}
      <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-6">
        <div className="flex items-center space-x-2 pb-3 border-b border-slate-800/80">
          <Building2 className="h-5 w-5 text-cyan-400" />
          <h2 className="text-base font-bold text-slate-100">3. Target Companies & Objective</h2>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-semibold text-slate-200 mb-1.5">
              Specific Target Companies (Optional)
            </label>
            <div className="flex gap-2 mb-2">
              <input
                id="input-target-company"
                type="text"
                value={companyInput}
                onChange={(e) => setCompanyInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleAddCompany(e)}
                placeholder="e.g. Google, Microsoft, Atlassian, Razorpay"
                className="flex-1 px-4 py-2 rounded-xl bg-slate-950 border border-slate-700/80 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500/40 focus:border-cyan-500"
              />
              <button
                type="button"
                onClick={handleAddCompany}
                className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-sm font-medium border border-slate-700 transition-all"
              >
                Add Company
              </button>
            </div>

            <div className="flex flex-wrap gap-1.5">
              {profile.target_companies.map((comp) => (
                <span
                  key={comp}
                  className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-medium bg-cyan-500/10 text-cyan-300 border border-cyan-500/30"
                >
                  <span>{comp}</span>
                  <button
                    type="button"
                    onClick={() => handleRemoveCompany(comp)}
                    className="hover:text-red-400"
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>
          </div>

          <div>
            <label htmlFor="textarea-career-goal" className="block text-sm font-semibold text-slate-200 mb-1.5">
              Career Goal / Target Statement
            </label>
            <textarea
              id="textarea-career-goal"
              rows={3}
              value={profile.career_goal || ''}
              onChange={(e) => setProfile(prev => ({ ...prev, career_goal: e.target.value }))}
              placeholder="e.g. Aiming to clear technical rounds for high-scale backend roles specializing in Python/Go, distributed databases, and cloud microservices."
              className="w-full px-4 py-2.5 rounded-xl bg-slate-950 border border-slate-700/80 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500/40 focus:border-cyan-500"
            />
          </div>
        </div>
      </div>

      {/* SECTION 4: Technical Skills Inventory */}
      <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-4">
        <div className="flex items-center space-x-2 pb-3 border-b border-slate-800/80">
          <Target className="h-5 w-5 text-emerald-400" />
          <h2 className="text-base font-bold text-slate-100">4. Skills Inventory & Proficiency Levels</h2>
        </div>
        <SkillsManager
          skills={profile.skills}
          onChange={(updatedSkills) => setProfile(prev => ({ ...prev, skills: updatedSkills }))}
        />
      </div>

      {/* SECTION 5: Academic Background */}
      <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-4">
        <div className="flex items-center space-x-2 pb-3 border-b border-slate-800/80">
          <Sparkles className="h-5 w-5 text-purple-400" />
          <h2 className="text-base font-bold text-slate-100">5. Education History</h2>
        </div>
        <EducationManager
          education={profile.education}
          onChange={(updatedEdu) => setProfile(prev => ({ ...prev, education: updatedEdu }))}
        />
      </div>

      {/* Bottom Save Action Bar */}
      <div className="flex justify-end items-center pt-4 border-t border-slate-800">
        <button
          type="submit"
          id="btn-save-profile-bottom"
          disabled={saving}
          className="px-6 py-3 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-medium text-sm flex items-center space-x-2 transition-all shadow-xl shadow-blue-600/30 disabled:opacity-50"
        >
          {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
          <span>{saving ? 'Saving Profile...' : 'Save Student Profile'}</span>
        </button>
      </div>
    </form>
  );
}
