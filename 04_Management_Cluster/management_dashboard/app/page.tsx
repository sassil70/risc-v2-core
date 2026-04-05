
"use client";

import { useState, useEffect } from 'react';
import { getProjects, Project, createProject } from '@/lib/api';
import Link from 'next/link';
import { Plus, Folder, Calendar } from 'lucide-react';

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);

  // Modal State
  const [showModal, setShowModal] = useState(false);
  const [ref, setRef] = useState('');
  const [client, setClient] = useState('');

  useEffect(() => {
    loadProjects();
  }, []);

  async function loadProjects() {
    setLoading(true);
    const data = await getProjects();
    setProjects(data);
    setLoading(false);
  }

  async function handleCreate() {
    if (!ref) return;
    const newProject = await createProject(ref, client);
    if (newProject) {
      setProjects([newProject, ...projects]);
      setShowModal(false);
      setRef('');
      setClient('');
    }
  }

  return (
    <div className="p-8">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
          Project Dashboard
        </h1>
        <button
          onClick={() => setShowModal(true)}
          className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition"
        >
          <Plus size={20} /> New Project
        </button>
      </div>

      {loading ? (
        <div className="text-center py-20 text-gray-500">Loading Projects...</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {projects.map((p) => (
            <Link key={p.id} href={`/projects/${p.id}`} className="block group">
              <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm hover:shadow-md transition relative overflow-hidden">
                <div className="absolute top-0 left-0 w-1 h-full bg-blue-500 group-hover:bg-purple-500 transition-colors" />
                <div className="flex items-start justify-between mb-4">
                  <div className="p-3 bg-blue-50 rounded-lg text-blue-600 group-hover:bg-purple-50 group-hover:text-purple-600 transition">
                    <Folder size={24} />
                  </div>
                  <span className="text-xs font-mono bg-gray-100 text-gray-600 px-2 py-1 rounded">
                    {p.status || 'Active'}
                  </span>
                </div>
                <h3 className="text-xl font-bold text-gray-900 mb-1">{p.reference_number}</h3>
                <p className="text-gray-500 text-sm mb-4">{p.client_name || 'No Client Specified'}</p>
                <div className="flex items-center text-gray-400 text-xs">
                  <Calendar size={14} className="mr-1" />
                  {p.created_at ? new Date(p.created_at).toLocaleDateString() : 'Unknown Date'}
                </div>
              </div>
            </Link>
          ))}

          {projects.length === 0 && (
            <div className="col-span-full text-center py-20 text-gray-400 border-2 border-dashed border-gray-200 rounded-xl">
              No active projects found. Start by creating one.
            </div>
          )}
        </div>
      )}

      {/* Simple Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 backdrop-blur-sm">
          <div className="bg-white rounded-2xl p-8 w-full max-w-md shadow-2xl">
            <h2 className="text-2xl font-bold mb-6">Create New Project</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Project Reference</label>
                <input
                  autoFocus
                  className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                  placeholder="e.g. RICS-2024-001"
                  value={ref}
                  onChange={(e) => setRef(e.target.value)}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Client Name</label>
                <input
                  className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                  placeholder="e.g. John Doe"
                  value={client}
                  onChange={(e) => setClient(e.target.value)}
                />
              </div>
            </div>
            <div className="flex justify-end gap-3 mt-8">
              <button
                onClick={() => setShowModal(false)}
                className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={handleCreate}
                disabled={!ref}
                className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                Create Project
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
