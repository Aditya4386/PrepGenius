import React, { useState } from 'react';
import { Plus, X, Award, CheckCircle2 } from 'lucide-react';
import { PROFICIENCY_LEVELS } from '../utils/constants';

const COMMON_SKILL_SUGGESTIONS = [
  'Python', 'Java', 'JavaScript', 'TypeScript', 'SQL', 'React', 'Node.js', 
  'FastAPI', 'Docker', 'AWS', 'Git', 'Data Structures', 'System Design'
];

export default function SkillsManager({ skills = [], onChange }) {
  const [skillName, setSkillName] = useState('');
  const [proficiency, setProficiency] = useState('intermediate');

  const handleAddSkill = (e) => {
    if (e) e.preventDefault();
    const cleanName = skillName.trim();
    if (!cleanName) return;

    // Check if skill already exists
    if (skills.some(s => s.name.toLowerCase() === cleanName.toLowerCase())) {
      return;
    }

    const updated = [...skills, { name: cleanName, level: proficiency }];
    onChange(updated);
    setSkillName('');
  };

  const handleRemoveSkill = (indexToRemove) => {
    const updated = skills.filter((_, idx) => idx !== indexToRemove);
    onChange(updated);
  };

  const handleQuickAdd = (suggestion) => {
    if (!skills.some(s => s.name.toLowerCase() === suggestion.toLowerCase())) {
      onChange([...skills, { name: suggestion, level: proficiency }]);
    }
  };

  return (
    <div className="space-y-4">
      {/* Input controls */}
      <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-3">
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="flex-1 relative">
            <input
              id="skill-name-input"
              type="text"
              value={skillName}
              onChange={(e) => setSkillName(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleAddSkill(e)}
              placeholder="e.g. FastAPI, MySQL, PyTorch, Kubernetes"
              className="w-full px-4 py-2.5 rounded-lg bg-slate-950/80 border border-slate-700/80 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/40 focus:border-blue-500 transition-all"
            />
          </div>

          {/* Proficiency selector */}
          <div className="flex items-center gap-1.5 p-1 rounded-lg bg-slate-950/80 border border-slate-800 shrink-0">
            {PROFICIENCY_LEVELS.map((level) => (
              <button
                key={level.id}
                type="button"
                id={`btn-proficiency-${level.id}`}
                onClick={() => setProficiency(level.id)}
                className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                  proficiency === level.id
                    ? `${level.color} border shadow-sm`
                    : 'text-slate-400 hover:text-slate-300'
                }`}
              >
                {level.label}
              </button>
            ))}
          </div>

          {/* Add button */}
          <button
            type="button"
            id="btn-add-skill"
            onClick={handleAddSkill}
            disabled={!skillName.trim()}
            className="px-4 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:hover:bg-blue-600 text-white text-sm font-medium flex items-center justify-center space-x-1.5 transition-all shadow-md shadow-blue-600/20 shrink-0"
          >
            <Plus className="h-4 w-4" />
            <span>Add Skill</span>
          </button>
        </div>

        {/* Quick Suggestion Pills */}
        <div className="flex items-center flex-wrap gap-1.5 pt-1">
          <span className="text-[11px] text-slate-400 mr-1 font-medium">Quick Suggestions:</span>
          {COMMON_SKILL_SUGGESTIONS.map((suggestion) => {
            const isAdded = skills.some(s => s.name.toLowerCase() === suggestion.toLowerCase());
            return (
              <button
                key={suggestion}
                type="button"
                disabled={isAdded}
                onClick={() => handleQuickAdd(suggestion)}
                className={`text-[11px] px-2 py-0.5 rounded-md transition-all ${
                  isAdded
                    ? 'bg-slate-800 text-slate-400 cursor-default'
                    : 'bg-slate-800/80 hover:bg-slate-700 text-slate-300 border border-slate-700/60'
                }`}
              >
                {suggestion} {isAdded && '✓'}
              </button>
            );
          })}
        </div>
      </div>

      {/* Render Current Skills List */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Registered Skills ({skills.length})
          </span>
          {skills.length > 0 && (
            <span className="text-xs text-slate-400">Click × to remove</span>
          )}
        </div>

        {skills.length === 0 ? (
          <div className="p-6 rounded-xl border border-dashed border-slate-800 text-center bg-slate-900/30">
            <Award className="h-8 w-8 text-slate-400 mx-auto mb-2 opacity-50" />
            <p className="text-sm text-slate-400">No skills added to your student profile yet.</p>
            <p className="text-xs text-slate-400 mt-0.5">Add skills above to calibrate your study roadmaps and interview questions.</p>
          </div>
        ) : (
          <div className="flex flex-wrap gap-2">
            {skills.map((item, index) => {
              const levelCfg = PROFICIENCY_LEVELS.find(l => l.id === item.level) || PROFICIENCY_LEVELS[1];
              return (
                <div
                  key={`${item.name}-${index}`}
                  className="flex items-center space-x-2 pl-3 pr-2 py-1.5 rounded-lg bg-slate-900 border border-slate-800 hover:border-slate-700 transition-all shadow-sm"
                >
                  <span className="text-sm font-medium text-slate-200">{item.name}</span>
                  <span className={`text-[10px] px-2 py-0.5 rounded border uppercase font-bold tracking-wider ${levelCfg.color}`}>
                    {levelCfg.label}
                  </span>
                  <button
                    type="button"
                    onClick={() => handleRemoveSkill(index)}
                    className="p-1 text-slate-400 hover:text-red-400 hover:bg-red-500/10 rounded transition-colors"
                    title="Remove skill"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
