
"use client";

import { useState, useEffect, use } from 'react';
import { getProject, addRoom, Project, Room } from '@/lib/api';
import Link from 'next/link';
import { ArrowLeft, Plus, Home, Box, CheckCircle } from 'lucide-react';

export default function ProjectDetails({ params }: { params: Promise<{ id: string }> }) {
    // Unwrap params using React.use()
    const { id } = use(params);

    const [project, setProject] = useState<Project | null>(null);
    const [loading, setLoading] = useState(true);

    // Room Form State
    const [showRoomModal, setShowRoomModal] = useState(false);
    const [roomName, setRoomName] = useState('');
    const [roomType, setRoomType] = useState('general');

    useEffect(() => {
        loadProject();
    }, [id]);

    async function loadProject() {
        if (!id) return;
        setLoading(true);
        const data = await getProject(id);
        setProject(data);
        setLoading(false);
    }

    async function handleAddRoom() {
        if (!project || !roomName) return;
        const newRooms = await addRoom(project.id, roomName, roomType);
        if (newRooms) {
            // Update local state to reflect new room list
            setProject({ ...project, rooms: newRooms });
            setShowRoomModal(false);
            setRoomName('');
        }
    }

    if (loading) return <div className="p-10 text-center">Loading Project Details...</div>;
    if (!project) return <div className="p-10 text-center text-red-500">Project Not Found</div>;

    return (
        <div className="p-8 max-w-7xl mx-auto">
            {/* 1. Header & Breadcrumbs */}
            <div className="mb-8">
                <Link href="/" className="inline-flex items-center text-gray-500 hover:text-blue-600 mb-4 transition">
                    <ArrowLeft size={16} className="mr-2" /> Back to Dashboard
                </Link>
                <div className="flex justify-between items-end">
                    <div>
                        <h1 className="text-4xl font-bold text-gray-900 mb-2">{project.reference_number}</h1>
                        <p className="text-xl text-gray-500">{project.client_name}</p>
                    </div>
                    <div className="flex gap-4">
                        <div className="text-right">
                            <span className="block text-sm text-gray-400">Created</span>
                            <span className="font-mono text-gray-700">{new Date(project.created_at!).toLocaleDateString()}</span>
                        </div>
                    </div>
                </div>
            </div>

            {/* 2. Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
                <div className="bg-blue-50 p-6 rounded-2xl border border-blue-100 flex items-center">
                    <div className="p-3 bg-blue-100 rounded-lg text-blue-600 mr-4"><Box size={24} /></div>
                    <div>
                        <div className="text-2xl font-bold text-blue-900">{project.rooms?.length || 0}</div>
                        <div className="text-blue-600 text-sm">Total Rooms</div>
                    </div>
                </div>
                <div className="bg-orange-50 p-6 rounded-2xl border border-orange-100 flex items-center">
                    <div className="p-3 bg-orange-100 rounded-lg text-orange-600 mr-4"><Home size={24} /></div>
                    <div>
                        <div className="text-2xl font-bold text-orange-900">
                            {project.rooms?.filter(r => r.status === 'pending').length || 0}
                        </div>
                        <div className="text-orange-600 text-sm">Pending Inspection</div>
                    </div>
                </div>
                <div className="bg-green-50 p-6 rounded-2xl border border-green-100 flex items-center">
                    <div className="p-3 bg-green-100 rounded-lg text-green-600 mr-4"><CheckCircle size={24} /></div>
                    <div>
                        <div className="text-2xl font-bold text-green-900">
                            {project.rooms?.filter(r => r.status === 'completed').length || 0}
                        </div>
                        <div className="text-green-600 text-sm">Completed</div>
                    </div>
                </div>
            </div>

            {/* 3. Room List & Actions */}
            <div className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden">
                <div className="p-6 border-b border-gray-100 flex justify-between items-center bg-gray-50/50">
                    <h2 className="text-xl font-bold text-gray-800">Inspection Scope (Rooms)</h2>
                    <button
                        onClick={() => setShowRoomModal(true)}
                        className="flex items-center gap-2 bg-black text-white px-4 py-2 rounded-lg hover:bg-gray-800 transition shadow-lg shadow-gray-200"
                    >
                        <Plus size={18} /> Add Room
                    </button>
                </div>

                {(!project.rooms || project.rooms.length === 0) ? (
                    <div className="p-12 text-center text-gray-400">
                        No rooms defined yet. Add a room to start scoping the project.
                    </div>
                ) : (
                    <div className="divide-y divide-gray-100">
                        {project.rooms.map((room) => (
                            <div key={room.id} className="p-4 hover:bg-gray-50 flex items-center justify-between transition group">
                                <div className="flex items-center gap-4">
                                    <div className={`w-2 h-2 rounded-full ${room.status === 'completed' ? 'bg-green-500' : 'bg-gray-300'}`} />
                                    <div>
                                        <div className="font-medium text-gray-900">{room.name}</div>
                                        <div className="text-xs text-gray-500 uppercase tracking-wider">{room.type.replace('_', ' ')}</div>
                                    </div>
                                </div>
                                <div className="text-sm text-gray-400 font-mono select-all">
                                    ID: {room.id}
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* Room Modal */}
            {showRoomModal && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 backdrop-blur-sm">
                    <div className="bg-white rounded-2xl p-8 w-full max-w-md shadow-2xl animate-in fade-in zoom-in duration-200">
                        <h2 className="text-2xl font-bold mb-6">Add New Room</h2>
                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Room Name</label>
                                <input
                                    autoFocus
                                    className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                                    placeholder="e.g. Master Bedroom, Kitchen"
                                    value={roomName}
                                    onChange={(e) => setRoomName(e.target.value)}
                                    onKeyDown={(e) => e.key === 'Enter' && handleAddRoom()}
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Room Type</label>
                                <select
                                    className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none bg-white"
                                    value={roomType}
                                    onChange={(e) => setRoomType(e.target.value)}
                                >
                                    <option value="general">General (Dry)</option>
                                    <option value="wet_room">Wet Room (Bath/WC)</option>
                                    <option value="kitchen">Kitchen</option>
                                    <option value="external">External / Garage</option>
                                    <option value="circulation">Circulation (Hall/Stairs)</option>
                                </select>
                            </div>
                        </div>
                        <div className="flex justify-end gap-3 mt-8">
                            <button
                                onClick={() => setShowRoomModal(false)}
                                className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleAddRoom}
                                disabled={!roomName}
                                className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
                            >
                                Add Room
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
