'use client';

import { useState } from 'react';
import { Room } from '@/lib/api';
import Link from 'next/link';

interface Props {
    rooms: Room[];
    selectedRoomId?: string;
    sessionId: string;
}

export default function FloorPlanViewer({ rooms, selectedRoomId, sessionId }: Props) {
    // Group rooms by floor
    const floors = rooms.reduce((acc, room) => {
        const floorNum = room.floor;
        if (!acc[floorNum]) acc[floorNum] = [];
        acc[floorNum].push(room);
        return acc;
    }, {} as Record<number, Room[]>);

    const floorNumbers = Object.keys(floors).map(Number).sort();
    const [activeFloor, setActiveFloor] = useState(floorNumbers[0] || 0);

    return (
        <div className="flex flex-col h-full bg-[#111827] border-r border-gray-800 w-80">
            {/* Floor Tabs */}
            <div className="flex border-b border-gray-700">
                {floorNumbers.map((floor) => (
                    <button
                        key={floor}
                        onClick={() => setActiveFloor(floor)}
                        className={`flex-1 py-3 text-sm font-medium transition-colors ${activeFloor === floor
                                ? 'bg-[#1E88E5] text-white'
                                : 'text-gray-400 hover:text-white hover:bg-white/5'
                            }`}
                    >
                        Floor {floor}
                    </button>
                ))}
            </div>

            {/* Room List */}
            <div className="flex-1 overflow-y-auto p-4 space-y-2">
                {floors[activeFloor]?.map((room) => {
                    const isSelected = room.id === selectedRoomId; // Note: using unique key if IDs are duplicated?
                    // In V2 session_init.json, we saw duplicate IDs "1767789832252" for all rooms.
                    // This is a known issue from the Mobile App V2 experiment.
                    // For UI stability, we should use index or generate unique keys logic if IDs are shared.
                    // BUT, we should assume the backend will fix this or we use name+index as key.

                    return (
                        <Link
                            key={room.id + room.name} // Fallback key
                            href={`/report/${sessionId}?room=${encodeURIComponent(room.name)}`} // Using URL state for selection
                            className={`block p-3 rounded-lg border transition-all ${isSelected
                                    ? 'border-[#1E88E5] bg-[#1E88E5]/10 text-white'
                                    : 'border-transparent hover:bg-white/5 text-gray-300'
                                }`}
                        >
                            <div className="flex justify-between items-center mb-1">
                                <span className="font-semibold truncate">{room.name}</span>
                                {/* Status Dot */}
                                <div className={`w-2 h-2 rounded-full ${room.status === 'completed' ? 'bg-green-500' : 'bg-red-500'
                                    }`} />
                            </div>
                            <div className="text-xs text-gray-500 flex justify-between">
                                <span>{room.type}</span>
                                <span>{room.inspection_count} photos</span>
                            </div>
                        </Link>
                    );
                })}
            </div>
        </div>
    );
}
