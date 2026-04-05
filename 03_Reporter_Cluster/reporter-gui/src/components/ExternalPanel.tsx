import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface ExternalPanelProps {
    roomId: string; // Typically 'external_front', 'external_rear'
    elementType: 'roof' | 'walls' | 'drainage' | 'grounds';
    onSave: (data: any) => void;
}

export function ExternalPanel({ roomId, elementType, onSave }: ExternalPanelProps) {
    return (
        <Card className="w-full bg-slate-900 border-slate-700 text-white">
            <CardHeader>
                <CardTitle className="flex items-center gap-2">
                    {getExtIcon(elementType)}
                    <span className="capitalize">{elementType} Inspection</span>
                </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
                {/* 1. Material Description */}
                <div className="space-y-2">
                    <label className="text-xs uppercase tracking-wider text-slate-400">Material / Construction</label>
                    <input
                        className="w-full bg-slate-800 border-none rounded p-2 text-sm text-white"
                        placeholder={getExtPlaceholder(elementType)}
                    />
                </div>

                {/* 2. RICS Condition Rating */}
                <div className="space-y-2">
                    <label className="text-xs uppercase tracking-wider text-slate-400">RICS Condition Rating</label>
                    <div className="flex gap-2">
                        <button className="flex-1 bg-green-900/50 hover:bg-green-800 py-2 rounded border border-green-700/50 text-xs">1 (Good)</button>
                        <button className="flex-1 bg-yellow-900/50 hover:bg-yellow-800 py-2 rounded border border-yellow-700/50 text-xs">2 (Fair)</button>
                        <button className="flex-1 bg-red-900/50 hover:bg-red-800 py-2 rounded border border-red-700/50 text-xs text-white font-bold">3 (Bad)</button>
                    </div>
                </div>

                {/* 3. Defects Wrapper */}
                <div className="space-y-2">
                    <label className="text-xs uppercase tracking-wider text-slate-400">Defect Analysis</label>
                    <textarea
                        className="w-full bg-slate-800 border-none rounded p-2 text-sm text-white h-32"
                        placeholder="Describe issues (e.g., slipped slates, spalled brickwork)..."
                    />
                </div>
            </CardContent>
        </Card>
    );
}

function getExtIcon(type: string) {
    switch (type) {
        case 'roof': return '🏠';
        case 'walls': return '🧱';
        case 'drainage': return '🕳️';
        case 'grounds': return '🌳';
        default: return '🏡';
    }
}

function getExtPlaceholder(type: string) {
    switch (type) {
        case 'roof': return 'e.g., Natural Welsh Slate, Clay Ridge Tiles';
        case 'walls': return 'e.g., Solid Brick (Flemish Bond), Pointed output';
        case 'drainage': return 'e.g., Cast iron gutters, PVC downpipes';
        default: return 'Describe construction...';
    }
}
