'use client';

import Link from 'next/link';
import { Session } from '@/lib/api';

export default function SessionList({ sessions }: { sessions: Session[] }) {
    if (!sessions || sessions.length === 0) {
        return (
            <div className="text-center p-10 text-white/50">
                <h2 className="text-xl">No Sessions Found</h2>
                <p>Start a new inspection from the Mobile App (Witness Cluster).</p>
            </div>
        );
    }

    return (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {sessions.map((session) => (
                <Link
                    key={session.id}
                    href={`/report/${session.id}`}
                    className="group relative block p-6 bg-[#0B1019] border border-gray-800 rounded-xl hover:border-[#1E88E5] transition-all duration-300"
                >
                    {/* Status Indicator */}
                    <div className={`absolute top-4 right-4 w-3 h-3 rounded-full ${session.status === 'completed' ? 'bg-green-500 shadow-[0_0_10px_#22c55e]' :
                            session.status === 'in_progress' ? 'bg-orange-500' : 'bg-red-500'
                        }`} />

                    <h3 className="text-xl font-bold text-white mb-2 group-hover:text-[#1E88E5] transition-colors">
                        {session.address || `Session ${session.id.slice(0, 8)}...`}
                    </h3>

                    <div className="space-y-1 text-sm text-gray-400">
                        <p>📅 {new Date(session.started_at || Date.now()).toLocaleDateString()}</p>
                        <p>🚪 {session.room_count || 0} Rooms Detected</p>
                        <p className="font-mono text-xs text-gray-600 mt-4">{session.id}</p>
                    </div>

                    {/* Hover Effect: Glow */}
                    <div className="absolute inset-0 bg-[#1E88E5]/5 opacity-0 group-hover:opacity-100 transition-opacity rounded-xl" />
                </Link>
            ))}
        </div>
    );
}
