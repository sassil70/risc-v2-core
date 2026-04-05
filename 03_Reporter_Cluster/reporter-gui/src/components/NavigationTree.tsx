'use client';

import React, { useState } from 'react';
import { Room } from '@/lib/api';

interface NavigationTreeProps {
    rooms: Room[];
    activeRoomId: string;
    onSelectRoom: (roomId: string) => void;
}

export function NavigationTree({ rooms, activeRoomId, onSelectRoom }: NavigationTreeProps) {
    // Expansion state for standard floors and special sections
    const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
        'floor_0': true,
        'floor_1': true,
        'services': true,
        'external': true
    });

    // Categorize Rooms
    const externalRooms = rooms.filter(r => r.type === 'external');
    const serviceRooms = rooms.filter(r => r.type === 'services');
    // "Standard" rooms are general, wet, dry, etc. EXCLUDING external/services
    const standardRooms = rooms.filter(r => r.type !== 'external' && r.type !== 'services');

    // Group standard rooms by floor
    const floors = standardRooms.reduce((acc, room) => {
        if (!acc[room.floor]) acc[room.floor] = [];
        acc[room.floor].push(room);
        return acc;
    }, {} as Record<number, Room[]>);

    const toggleSection = (key: string) => {
        setExpandedSections(prev => ({ ...prev, [key]: !prev[key] }));
    };

    const Section = ({ id, label, items, colorClass = "text-gray-400" }: { id: string, label: string, items: Room[], colorClass?: string }) => {
        if (!items || items.length === 0) return null;

        const isExpanded = expandedSections[id];

        return (
            <div className="mb-4">
                <div
                    className={`flex items-center cursor-pointer mb-2 font-bold uppercase text-xs tracking-wider transition-colors hover:text-white ${colorClass}`}
                    onClick={() => toggleSection(id)}
                >
                    <span className="mr-2 text-[10px]">{isExpanded ? '▼' : '▶'}</span>
                    {label}
                </div>

                {isExpanded && (
                    <div className="pl-3 ml-1 border-l border-gray-800 space-y-0.5">
                        {items.map(room => (
                            <div
                                key={room.id}
                                onClick={() => onSelectRoom(room.id)}
                                className={`
                    cursor-pointer px-3 py-1.5 rounded text-sm transition-all flex justify-between items-center group
                    ${activeRoomId === room.id
                                        ? 'bg-blue-900/40 text-blue-200 font-medium'
                                        : 'text-gray-500 hover:bg-gray-900 hover:text-gray-300'}
                `}
                            >
                                <span className="truncate pr-2 flex-1">{room.name}</span>

                                <div className="flex items-center gap-2">
                                    {/* Audio Count */}
                                    <span className="text-[10px] text-gray-600 group-hover:text-gray-500 font-mono">
                                        🎤 {room.audio_count || 0}
                                    </span>

                                    {/* Image Count */}
                                    <span className="text-[10px] text-gray-600 group-hover:text-gray-500 font-mono">
                                        📷 {room.images_count || room.inspection_count || 0}
                                    </span>

                                    {/* Status Dot */}
                                    <div className={`w-1.5 h-1.5 rounded-full ${getStatusColor(room.status)} opacity-60 group-hover:opacity-100`}></div>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        );
    };

    return (
        <div className="h-full flex flex-col p-4">
            <div className="mb-6 pl-1">
                <h2 className="text-white font-bold text-sm tracking-tight">Survey Plan</h2>
                <p className="text-[10px] text-gray-600 uppercase tracking-widest mt-1">Navigation V2.1</p>
            </div>

            <div className="flex-1 overflow-y-auto pr-2 custom-scrollbar">
                {/* 1. External Areas (Priority) */}
                <Section id="external" label="🏡 External Areas" items={externalRooms} colorClass="text-emerald-500" />

                {/* 2. Standard Floors */}
                {Object.keys(floors).sort().map(fKey => {
                    const fNum = parseInt(fKey);
                    return (
                        <Section
                            key={`floor_${fNum}`}
                            id={`floor_${fNum}`}
                            label={getFloorLabel(fNum)}
                            items={floors[fNum]}
                        />
                    );
                })}

                {/* 3. Services (MEP) */}
                <Section id="services" label="⚡ Services (MEP)" items={serviceRooms} colorClass="text-yellow-500" />
            </div>
        </div>
    );
}

function getFloorLabel(f: number): string {
    if (f === 0) return "Ground Floor";
    if (f === 1) return "First Floor";
    if (f === 2) return "Second Floor";
    if (f === 3) return "Third Floor";
    if (f === -1) return "Basement";
    return `Floor ${f}`;
}

function getStatusColor(status: string) {
    switch (status) {
        case 'completed': return 'bg-green-500';
        case 'in_progress': return 'bg-yellow-500';
        case 'red': return 'bg-red-500';
        default: return 'bg-gray-600';
    }
}
