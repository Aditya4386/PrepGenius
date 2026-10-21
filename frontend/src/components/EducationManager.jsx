import React from 'react';
import { Plus, Trash2, GraduationCap } from 'lucide-react';

export default function EducationManager({ education = [], onChange }) {
  const handleAddEducation = () => {
    const newEntry = {
      institution: '',
      degree: '',
      year_of_completion: new Date().getFullYear(),
      cgpa: 8.0,
    };
    onChange([...education, newEntry]);
  };

  const handleUpdateEntry = (index, field, value) => {
    const updated = education.map((item, idx) => {
      if (idx === index) {
        return { ...item, [field]: value };
      }
      return item;
    });
    onChange(updated);
  };

  const handleRemoveEntry = (indexToRemove) => {
    const updated = education.filter((_, idx) => idx !== indexToRemove);
    onChange(updated);
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
          Education History ({education.length})
        </span>
        <button
          type="button"
          id="btn-add-education"
          onClick={handleAddEducation}
          className="text-xs text-blue-400 hover:text-blue-300 flex items-center space-x-1 font-medium bg-blue-500/10 hover:bg-blue-500/20 px-3 py-1.5 rounded-lg border border-blue-500/20 transition-all"
        >
          <Plus className="h-3.5 w-3.5" />
          <span>Add Degree / College</span>
        </button>
      </div>

      {education.length === 0 ? (
        <div className="p-6 rounded-xl border border-dashed border-slate-800 text-center bg-slate-900/30">
          <GraduationCap className="h-8 w-8 text-slate-400 mx-auto mb-2 opacity-50" />
          <p className="text-sm text-slate-400">No education records added yet.</p>
          <p className="text-xs text-slate-400 mt-0.5">Click &quot;Add Degree / College&quot; to specify your academic timeline.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {education.map((item, index) => (
            <div
              key={index}
              className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-3 relative group"
            >
              <div className="flex justify-between items-center pb-2 border-b border-slate-800/80">
                <span className="text-xs font-semibold text-slate-400">
                  Record #{index + 1}
                </span>
                <button
                  type="button"
                  onClick={() => handleRemoveEntry(index)}
                  className="text-slate-400 hover:text-red-400 p-1 rounded hover:bg-red-500/10 transition-colors"
                  title="Delete record"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Degree / Course Name
                  </label>
                  <input
                    type="text"
                    value={item.degree}
                    onChange={(e) => handleUpdateEntry(index, 'degree', e.target.value)}
                    placeholder="e.g. B.Tech Information Technology"
                    className="w-full px-3 py-2 rounded-lg bg-slate-950/80 border border-slate-700/80 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/40 focus:border-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Institution / University
                  </label>
                  <input
                    type="text"
                    value={item.institution}
                    onChange={(e) => handleUpdateEntry(index, 'institution', e.target.value)}
                    placeholder="e.g. Delhi Technological University"
                    className="w-full px-3 py-2 rounded-lg bg-slate-950/80 border border-slate-700/80 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/40 focus:border-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Graduation Year
                  </label>
                  <input
                    type="number"
                    min="1980"
                    max="2035"
                    value={item.year_of_completion || ''}
                    onChange={(e) => handleUpdateEntry(index, 'year_of_completion', parseInt(e.target.value) || null)}
                    placeholder="2026"
                    className="w-full px-3 py-2 rounded-lg bg-slate-950/80 border border-slate-700/80 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/40 focus:border-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    CGPA / Percentage (out of 10)
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    max="10"
                    value={item.cgpa || ''}
                    onChange={(e) => handleUpdateEntry(index, 'cgpa', parseFloat(e.target.value) || null)}
                    placeholder="8.75"
                    className="w-full px-3 py-2 rounded-lg bg-slate-950/80 border border-slate-700/80 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/40 focus:border-blue-500"
                  />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
