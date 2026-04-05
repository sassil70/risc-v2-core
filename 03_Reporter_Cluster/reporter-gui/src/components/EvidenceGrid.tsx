'use client';

import { useState, useEffect } from 'react';
import Image from 'next/image';
import { api } from '@/lib/api';

interface Props {
    sessionId: string;
    roomId: string; // Changed from roomName to match API usage
}

export default function EvidenceGrid({ sessionId, roomId, excludedItems, onToggle }: Props & { excludedItems: Set<string>, onToggle: (path: string) => void }) {
    const [images, setImages] = useState<string[]>([]);
    const [audio, setAudio] = useState<string[]>([]);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        if (!sessionId || !roomId) return;

        const fetchMedia = async () => {
            setLoading(true);
            try {
                const data = await api.getRoomImages(sessionId, roomId);
                setImages(data.images || []);
                setAudio(data.audio || []);
            } catch (error) {
                console.error("Error fetching evidence:", error);
                setImages([]);
                setAudio([]);
            } finally {
                setLoading(false);
            }
        };

        fetchMedia();
    }, [sessionId, roomId]);

    if (loading) return <div className="p-4 text-gray-500 text-xs animate-pulse">Scanning Secure Storage...</div>;

    if (images.length === 0 && audio.length === 0) {
        return (
            <div className="p-4 text-gray-600 text-xs flex flex-col items-center justify-center p-8 border border-dashed border-gray-800 rounded">
                <span>No Evidence Found</span>
                <span className="text-[10px] mt-1 text-gray-700">ID: {roomId}</span>
            </div>
        );
    }

    return (
        <div className="p-4 space-y-6">
            {audio.length > 0 && (
                <div>
                    <h4 className="text-xs font-bold text-yellow-500 mb-2 uppercase tracking-widest">Audio Notes 🎤</h4>
                    <div className="space-y-2">
                        {audio.map((aud, idx) => {
                            const isExcluded = excludedItems.has(aud);
                            const filename = aud.split('/').pop();
                            return (
                                <div key={idx} className={`bg-gray-800 rounded p-2 border ${isExcluded ? 'border-red-900 opacity-50' : 'border-gray-700 hover:border-yellow-500'} transition-all group relative`}>
                                    <div className="flex items-center justify-between mb-1">
                                        <span className="text-[10px] text-gray-300 font-mono truncate max-w-[150px]" title={filename}>
                                            {filename}
                                        </span>
                                        <button
                                            onClick={(e) => { e.stopPropagation(); onToggle(aud); }}
                                            className="text-[9px] text-gray-500 hover:text-red-500 uppercase font-bold"
                                        >
                                            {isExcluded ? 'Restore' : 'Exclude'}
                                        </button>
                                    </div>
                                    <audio controls className="w-full h-6 block" src={`http://localhost:8001${aud}`}></audio>
                                </div>
                            );
                        })}
                    </div>
                </div>
            )}

            {images.length > 0 && (
                <div>
                    <h4 className="text-xs font-bold text-blue-400 mb-2 uppercase tracking-widest">Visual Evidence 📷</h4>
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                        {images.map((img, idx) => {
                            const isExcluded = excludedItems.has(img);
                            return (
                                <div
                                    key={idx}
                                    onClick={() => window.open(`http://localhost:8001${img}`, '_blank')}
                                    className={`group relative aspect-square bg-gray-800 rounded overflow-hidden border transition-colors cursor-pointer ${isExcluded ? 'border-red-900 opacity-50 grayscale' : 'border-gray-700 hover:border-blue-500'}`}
                                >
                                    <img
                                        src={`http://localhost:8001${img}`}
                                        alt={`Evidence ${idx}`}
                                        className="w-full h-full object-cover"
                                        loading="lazy"
                                    />

                                    <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity flex flex-col justify-end p-2">
                                        <p className="text-[10px] text-gray-300 truncate mb-1">{img.split('/').pop()}</p>

                                        <button
                                            onClick={(e) => { e.stopPropagation(); onToggle(img); }}
                                            className={`text-[10px] px-2 py-1 rounded font-bold uppercase tracking-wider w-full ${isExcluded ? 'bg-red-600 text-white' : 'bg-gray-700 hover:bg-red-600 text-gray-300 hover:text-white'}`}
                                        >
                                            {isExcluded ? 'Restore' : 'Exclude'}
                                        </button>
                                    </div>

                                    {isExcluded && (
                                        <div className="absolute top-2 right-2 px-1.5 py-0.5 bg-red-600 text-white text-[9px] font-bold rounded uppercase">
                                            Excluded
                                        </div>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                </div>
            )}
        </div>
    );
}
