import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface ServicePanelProps {
    roomId: string;
    serviceType: 'electricity' | 'water' | 'heating' | 'gas';
    onSave: (data: any) => void;
}

export function ServicePanel({ roomId, serviceType, onSave }: ServicePanelProps) {
    return (
        <Card className="w-full bg-slate-900 border-slate-700 text-white">
            <CardHeader>
                <CardTitle className="flex items-center gap-2">
                    {getIcon(serviceType)}
                    <span className="capitalize">{serviceType} Systems</span>
                </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
                {/* 1. System Type */}
                <div className="space-y-2">
                    <label className="text-xs uppercase tracking-wider text-slate-400">System Type</label>
                    <input
                        className="w-full bg-slate-800 border-none rounded p-2 text-sm text-white"
                        placeholder={getPlaceholder(serviceType)}
                    />
                </div>

                {/* 2. Visual Condition */}
                <div className="space-y-2">
                    <label className="text-xs uppercase tracking-wider text-slate-400">Visual Condition</label>
                    <select className="w-full bg-slate-800 border-none rounded p-2 text-sm text-white">
                        <option>Good - Modern & Serviceable</option>
                        <option>Fair - Functional but aging</option>
                        <option>Poor - Requires attention/Upgrade</option>
                        <option>Dangerous - Immediate Isolation Required</option>
                    </select>
                </div>

                {/* 3. Defects */}
                <div className="space-y-2">
                    <label className="text-xs uppercase tracking-wider text-slate-400">Observed Defects</label>
                    <textarea
                        className="w-full bg-slate-800 border-none rounded p-2 text-sm text-white h-24"
                        placeholder="Describe defects (e.g., exposed wires, leaking joints)..."
                    />
                </div>
            </CardContent>
        </Card>
    );
}

function getIcon(type: string) {
    switch (type) {
        case 'electricity': return '⚡';
        case 'water': return '💧';
        case 'heating': return '🔥';
        case 'gas': return '⛽';
        default: return '🔧';
    }
}

function getPlaceholder(type: string) {
    switch (type) {
        case 'electricity': return 'e.g., Consumer Unit (17th Edition), PVC trunking';
        case 'water': return 'e.g., Mains stopcock location, copper/pvc pipes';
        case 'heating': return 'e.g., Combi Boiler (Worcester Bosch), Radiators';
        default: return 'Describe system...';
    }
}
