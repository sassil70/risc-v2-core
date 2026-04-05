'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter, useSearchParams } from 'next/navigation';
import { api, SessionDetails } from '@/lib/api';
import { NavigationTree } from '@/components/NavigationTree';
import EvidenceGrid from '@/components/EvidenceGrid'; // Default export
import { ServicePanel } from '@/components/ServicePanel';
import { ExternalPanel } from '@/components/ExternalPanel';

export default function ReportPage() {
    const { id } = useParams() as { id: string };
    const searchParams = useSearchParams();
    const router = useRouter();

    const [sessionData, setSessionData] = useState<SessionDetails | null>(null);
    const [selectedRoomId, setSelectedRoomId] = useState<string | null>(null);

    // Derived State
    const rooms = sessionData?.floor_plan.rooms || [];
    const selectedRoom = rooms.find(r => r.id === selectedRoomId);

    const [error, setError] = useState<string | null>(null);

    // AI Generation State (Moved Up)
    const [isGenerating, setIsGenerating] = useState(false);
    const [observationText, setObservationText] = useState("");

    // Reset text when room changes (or load from DB if we had it)
    useEffect(() => {
        setObservationText(""); // Clear previous room's text
        // TODO: In V2.2, fetch existing text from DB here
    }, [selectedRoomId]);

    // Initial Load
    useEffect(() => {
        const fetchSession = async () => {
            try {
                const data = await api.getSessionDetails(id);
                setSessionData(data); // <--- This might fail if data is weird

                // Handle URL param or default
                const paramRoom = searchParams.get('room');
                if (paramRoom) {
                    setSelectedRoomId(paramRoom);
                } else if (data.floor_plan.rooms.length > 0) {
                    // Default to first room
                    handleSelectRoom(data.floor_plan.rooms[0].id);
                }
            } catch (e: any) {
                console.error("Failed to load session", e);
                setError(e.message || "Failed to load session data");
            }
        };
        fetchSession();
    }, [id, searchParams]);

    const handleSelectRoom = (roomId: string) => {
        setSelectedRoomId(roomId);
        // Update URL strictly for bookmarking, shallow routing
        const url = `/report/${id}?room=${roomId}`;
        router.replace(url, { scroll: false });
    };

    // Evidence Management
    const [excludedEvidence, setExcludedEvidence] = useState<Set<string>>(new Set());

    const handleToggleEvidence = (path: string) => {
        setExcludedEvidence(prev => {
            const next = new Set(prev);
            if (next.has(path)) next.delete(path);
            else next.add(path);
            return next;
        });
    };

    if (error) {
        return (
            <div className="flex items-center justify-center h-screen bg-black text-red-500 flex-col">
                <h1 className="text-xl font-bold mb-2">CRITICAL ERROR</h1>
                <p>{error}</p>
                <button onClick={() => window.location.reload()} className="mt-4 px-4 py-2 bg-gray-800 rounded text-white hover:bg-gray-700">Retry Connection</button>
            </div>
        );
    }

    if (!sessionData) {
        return (
            <div className="flex items-center justify-center h-screen bg-black text-white flex-col">
                <div className="animate-spin h-8 w-8 border-4 border-blue-500 rounded-full border-t-transparent mb-4"></div>
                <p className="text-xs uppercase tracking-widest animate-pulse">Establishing Secure Uplink...</p>
            </div>
        );
    }

    const handleGenerateAI = async () => {
        if (!selectedRoom) return;
        setIsGenerating(true);
        try {
            // Trigger AI Generation
            const res = await fetch(`http://localhost:8001/api/reports/${id}/generate_ai`, { method: 'POST' });
            if (!res.ok) throw new Error("AI Generation Failed");

            const data = await res.json();
            const report = data.report; // The full JSON report

            // Match logic: Try to find a section that matches the room name
            // exact match or fuzzy match logic needed?
            // For V2.1, let's look for exact name match in the report sections

            // Assuming report is a Dict or List. Based on prompt engine, it returns structured sections.
            // Let's assume the sections key matches room names for now? 
            // Or look for a key matching room.type?

            // Fallback: Dump the whole relevant section
            let relevantText = "";

            if (report.sections && Array.isArray(report.sections)) {
                const section = report.sections.find((s: any) => s.room_id === selectedRoom.id || s.title === selectedRoom.name);
                if (section) {
                    relevantText = JSON.stringify(section.content || section, null, 2);
                } else {
                    // Try finding by type
                    const typeMatch = report.sections.find((s: any) => s.type === selectedRoom.type);
                    if (typeMatch) relevantText = JSON.stringify(typeMatch, null, 2);
                }
            } else if (report.general_observation && selectedRoom.type === 'general') {
                relevantText = report.general_observation;
            } else {
                // Just dump the whole thing for the Surveyor to pick
                relevantText = JSON.stringify(report, null, 2);
            }

            setObservationText(relevantText);
            alert("✅ AI Analysis Injected into Editor!");

        } catch (e) {
            alert("❌ AI Failed: " + e);
        } finally {
            setIsGenerating(false);
        }
    };

    return (
        <div className="flex h-screen bg-black text-gray-200 overflow-hidden">
            {/* LEFT PANE: Navigation Tree */}
            <div className="w-[300px] border-r border-gray-800 bg-gray-950 overflow-y-auto shrink-0">
                <NavigationTree
                    rooms={rooms}
                    activeRoomId={selectedRoomId || ''}
                    onSelectRoom={handleSelectRoom}
                />
            </div>

            {/* CENTER PANE: Editor & Context */}
            <div className="flex-1 flex flex-col border-r border-gray-800 min-w-0">
                {/* Header */}
                <div className="h-16 border-b border-gray-800 flex items-center px-6 justify-between bg-gray-900/50">
                    <div>
                        <h1 className="text-lg font-bold text-white truncate max-w-md">
                            {selectedRoom ? selectedRoom.name : 'Select a Room'}
                        </h1>
                        <div className="text-xs text-blue-400 font-mono flex items-center gap-2">
                            <span>{selectedRoom?.type.toUpperCase()}</span>
                            <span className="text-gray-600">|</span>
                            <span className={selectedRoom?.status === 'completed' ? 'text-green-500' : 'text-yellow-500'}>
                                {selectedRoom?.status.toUpperCase()}
                            </span>
                        </div>
                    </div>

                    <div className="flex space-x-2">
                        <button
                            onClick={handleGenerateAI}
                            disabled={isGenerating}
                            className={`px-3 py-1.5 rounded text-xs font-bold uppercase tracking-wider transition-colors flex items-center gap-2 ${isGenerating ? 'bg-purple-900/50 text-purple-200 cursor-not-allowed' : 'bg-purple-600 hover:bg-purple-500 text-white'}`}
                        >
                            {isGenerating ? (
                                <>
                                    <span className="animate-spin">⚙️</span> Generating...
                                </>
                            ) : (
                                <>
                                    🔮 AI Analyze
                                </>
                            )}
                        </button>
                        <button className="bg-blue-700 hover:bg-blue-600 text-white px-3 py-1.5 rounded text-xs font-bold uppercase tracking-wider transition-colors">
                            Save Observations
                        </button>
                        <button
                            onClick={() => window.open(`http://localhost:8001/api/reports/${id}`, '_blank')}
                            className="border border-gray-600 hover:bg-gray-800 text-gray-300 px-3 py-1.5 rounded text-xs font-bold uppercase tracking-wider transition-colors"
                        >
                            Generate PDF
                        </button>
                    </div>
                </div>

                {/* Editor Area */}
                <div className="flex-1 p-6 overflow-y-auto bg-gray-950">
                    {selectedRoom ? (
                        <div className="max-w-3xl mx-auto space-y-6">
                            {/* Tips */}
                            <div className="p-4 bg-gray-900 rounded border border-gray-800">
                                <h3 className="text-xs font-bold text-gray-500 uppercase mb-2">Inspection Contexts</h3>
                                <div className="flex flex-wrap gap-2">
                                    {selectedRoom.contexts?.map(ctx => (
                                        <span key={ctx} className="px-2 py-1 bg-gray-800 rounded text-xs text-gray-300 border border-gray-700">
                                            {ctx}
                                        </span>
                                    ))}
                                </div>
                            </div>

                            {/* DYNAMIC EDITOR SWITCHER */}
                            {selectedRoom.type === 'external' ? (
                                // EXTERNAL PANEL
                                <ExternalPanel
                                    roomId={selectedRoom.id}
                                    elementType={(selectedRoom.name.toLowerCase().includes('roof') ? 'roof' : 'walls')}
                                    onSave={(d) => console.log('Saving External:', d)}
                                />
                            ) : selectedRoom.type === 'services' ? (
                                // SERVICE PANEL
                                <ServicePanel
                                    roomId={selectedRoom.id}
                                    serviceType={(selectedRoom.name.toLowerCase().includes('elect') ? 'electricity' : 'water')}
                                    onSave={(d) => console.log('Saving Service:', d)}
                                />
                            ) : (
                                // STANDARD ROOM EDITOR
                                <div className="space-y-2">
                                    <label className="text-xs uppercase font-bold text-gray-500">Forensic Observations</label>
                                    <textarea
                                        className="w-full h-96 bg-gray-900 border border-gray-700 rounded p-4 text-sm text-gray-200 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none resize-none leading-relaxed font-mono"
                                        placeholder="Typing forensic analysis..."
                                        value={observationText}
                                        onChange={(e) => setObservationText(e.target.value)}
                                    ></textarea>
                                </div>
                            )}

                        </div>
                    ) : (
                        <div className="flex h-full items-center justify-center text-gray-600">
                            Select a room to begin editing.
                        </div>
                    )}
                </div>
            </div>

            {/* RIGHT PANE: Evidence Gallery */}
            <div className="w-80 bg-gray-900 border-l border-gray-800 flex flex-col h-full shrink-0">
                <div className="h-16 border-b border-gray-800 flex items-center px-4 font-bold text-emerald-400 text-sm uppercase tracking-wider">
                    Evidence Locker 🔒
                </div>
                <div className="flex-1 overflow-y-auto p-4">
                    {selectedRoomId ? (
                        <EvidenceGrid
                            sessionId={id}
                            roomId={selectedRoomId}
                            excludedItems={excludedEvidence}
                            onToggle={handleToggleEvidence}
                        />
                    ) : (
                        <div className="text-center text-gray-600 mt-10 text-xs">No active locker</div>
                    )}
                </div>
            </div>
        </div>
    );
}
