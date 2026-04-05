
"use client";

import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Check, Trash2, Maximize2, Loader2, Image as ImageIcon } from 'lucide-react';

interface MediaManagerProps {
    isOpen: boolean;
    onClose: () => void;
    sessionId: string;
    roomName: string;
    roomId?: string; // Optional if roomName is unique, but ID is safer
}

export const MediaManager: React.FC<MediaManagerProps> = ({ isOpen, onClose, sessionId, roomName, roomId }) => {
    const [images, setImages] = useState<string[]>([]);
    const [loading, setLoading] = useState(true);

    // Use Room Name as ID if ID is missing (Legacy Support)
    const effectiveRoomId = roomId || roomName;

    useEffect(() => {
        if (!isOpen || !sessionId || !effectiveRoomId) return;

        async function fetchImages() {
            setLoading(true);
            try {
                // The room folder name on disk usually matches the ID
                // But sometimes it might be the Name. Let's try ID first.
                const res = await fetch(`/api/sessions/${sessionId}/rooms/${effectiveRoomId}/images`);
                if (res.ok) {
                    const data = await res.json();
                    setImages(data.images || []);
                }
            } catch (error) {
                console.error("Failed to load evidence", error);
            } finally {
                setLoading(false);
            }
        }

        fetchImages();
    }, [isOpen, sessionId, effectiveRoomId]);

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
            <div className="absolute inset-0 bg-black/80 backdrop-blur-sm" onClick={onClose} />

            <motion.div
                initial={{ scale: 0.9, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.9, opacity: 0 }}
                className="bg-slate-900 border border-slate-700 w-full max-w-3xl rounded-2xl shadow-2xl relative z-10 overflow-hidden flex flex-col max-h-[85vh]"
            >
                {/* Header */}
                <div className="p-6 border-b border-slate-800 flex justify-between items-center bg-slate-950/50">
                    <div>
                        <h2 className="text-xl font-bold text-white">{roomName}</h2>
                        <p className="text-xs text-slate-400 font-mono mt-1">
                            {loading ? "Scanning Evidence Locker..." : `Found ${images.length} Evidence Capabilities`}
                        </p>
                    </div>
                    <button onClick={onClose} className="p-2 hover:bg-white/10 rounded-full transition-colors">
                        <X className="w-6 h-6 text-slate-400" />
                    </button>
                </div>

                {/* Grid */}
                <div className="p-6 overflow-y-auto min-h-[300px]">

                    {loading ? (
                        <div className="h-full flex flex-col items-center justify-center text-slate-500 gap-4">
                            <Loader2 className="w-10 h-10 animate-spin text-cyan-500" />
                            <p>Decryption in progress...</p>
                        </div>
                    ) : images.length > 0 ? (
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                            {images.map((imgUrl, idx) => (
                                <div key={idx} className="group relative aspect-square rounded-lg overflow-hidden bg-slate-800 border border-slate-700 hover:border-cyan-500 transition-all cursor-pointer">
                                    {/* Use Proxied Storage URL */}
                                    <img
                                        src={imgUrl}
                                        alt={`Evidence ${idx}`}
                                        className="w-full h-full object-cover"
                                        onError={(e) => {
                                            (e.target as HTMLImageElement).src = '/placeholder_error.png'; // Fallback
                                        }}
                                    />

                                    {/* Overlay Controls */}
                                    <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex flex-col items-center justify-center gap-3">
                                        <button className="px-3 py-1.5 bg-emerald-500/20 text-emerald-400 border border-emerald-500/50 rounded-full text-xs font-bold flex items-center gap-2 hover:bg-emerald-500 hover:text-white transition-colors">
                                            <Check className="w-3 h-3" /> INCLUDE
                                        </button>
                                        <button className="px-3 py-1.5 bg-red-500/20 text-red-400 border border-red-500/50 rounded-full text-xs font-bold flex items-center gap-2 hover:bg-red-500 hover:text-white transition-colors">
                                            <Trash2 className="w-3 h-3" /> IGNORE
                                        </button>
                                        <button
                                            onClick={() => window.open(imgUrl, '_blank')}
                                            className="p-1.5 bg-white/10 rounded-full text-white hover:bg-white/20 absolute top-2 right-2"
                                        >
                                            <Maximize2 className="w-3 h-3" />
                                        </button>
                                    </div>

                                    {/* Status Badge (Default Included) */}
                                    <div className="absolute top-2 left-2 w-2 h-2 rounded-full bg-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.5)]"></div>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <div className="h-full flex flex-col items-center justify-center text-slate-500 gap-4 border-2 border-dashed border-slate-800 rounded-xl p-10">
                            <ImageIcon className="w-12 h-12 opacity-20" />
                            <p>No visual evidence found for this zone.</p>
                        </div>
                    )}

                </div>

                {/* Footer */}
                <div className="p-4 border-t border-slate-800 bg-slate-950/30 flex justify-end gap-3">
                    <button onClick={onClose} className="px-6 py-2.5 rounded-lg text-sm font-semibold text-slate-300 hover:bg-white/5 transition-colors">
                        Cancel
                    </button>
                    <button onClick={onClose} className="px-6 py-2.5 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-black text-sm font-bold shadow-lg shadow-cyan-500/20 transition-all">
                        Save Changes
                    </button>
                </div>

            </motion.div>
        </div>
    );
};
