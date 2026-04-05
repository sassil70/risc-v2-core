
"use client";

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { FileText, Sparkles, Clock, ArrowRight, User, AlertCircle, Calendar } from 'lucide-react';
import { AuthService } from '@/services/auth.service';
import { motion } from 'framer-motion';

interface Session {
    id: string;
    title: string;
    status: string;
    created_at: string;
    date: string; // Helper for display
}

export default function ReportsPage() {
    const [sessions, setSessions] = useState<Session[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        async function fetchRecentSessions() {
            const user = AuthService.getUser();
            if (!user) {
                setError("Unauthorized. Please log in.");
                setLoading(false);
                return;
            }

            try {
                // Fetch all sessions (Backend orders by date DESC by default)
                const res = await fetch(`/api/surveyor/sessions?user_id=${user.id}`);
                if (!res.ok) throw new Error("Failed to fetch session history.");

                const data: any[] = await res.json();

                // Slice top 15 and map to interface
                const recent = data.slice(0, 15).map(item => ({
                    id: item.id,
                    title: item.title || "Untitled Inspection",
                    status: item.status || 'unknown',
                    created_at: item.created_at,
                    date: new Date(item.created_at).toLocaleDateString('en-GB', {
                        day: '2-digit', month: 'short', year: 'numeric'
                    })
                }));

                setSessions(recent);
            } catch (err) {
                console.error(err);
                setError("Could not load report history.");
            } finally {
                setLoading(false);
            }
        }

        fetchRecentSessions();
    }, []);

    const getStatusColor = (status: string) => {
        switch (status.toLowerCase()) {
            case 'completed': return 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10';
            case 'pending': return 'text-amber-400 border-amber-500/30 bg-amber-500/10';
            case 'draft': return 'text-blue-400 border-blue-500/30 bg-blue-500/10';
            default: return 'text-slate-400 border-slate-500/30 bg-slate-500/10';
        }
    };

    return (
        <div className="min-h-screen bg-slate-950 text-slate-50 font-sans">

            {/* Header */}
            <header className="bg-slate-900/50 border-b border-slate-800 sticky top-0 z-10 backdrop-blur-md">
                <div className="max-w-7xl mx-auto px-6 py-4 flex justify-between items-center">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-indigo-500/10 rounded-lg border border-indigo-500/20">
                            <FileText className="w-6 h-6 text-indigo-400" />
                        </div>
                        <div>
                            <h1 className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-indigo-400 to-cyan-400">
                                Report Generation Hub
                            </h1>
                            <p className="text-xs text-slate-500 font-mono">LATEST 15 INSPECTIONS</p>
                        </div>
                    </div>

                    <div className="flex items-center gap-3 text-sm text-slate-400">
                        <User className="w-4 h-4" />
                        <span className="hidden sm:inline">Surveyor Portal</span>
                    </div>
                </div>
            </header>

            <main className="max-w-7xl mx-auto px-6 py-8">

                {/* Error State */}
                {error && (
                    <div className="p-4 rounded-xl bg-red-900/20 border border-red-800 text-red-200 flex items-center gap-3 mb-8">
                        <AlertCircle className="w-5 h-5" />
                        {error}
                    </div>
                )}

                {/* Loading State */}
                {loading && (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 animate-pulse">
                        {[...Array(6)].map((_, i) => (
                            <div key={i} className="h-48 bg-slate-900 rounded-xl border border-slate-800" />
                        ))}
                    </div>
                )}

                {/* Empty State */}
                {!loading && sessions.length === 0 && !error && (
                    <div className="text-center py-20 border border-dashed border-slate-800 rounded-2xl">
                        <p className="text-slate-500">No inspection data found in records.</p>
                    </div>
                )}

                {/* Reports Grid */}
                {!loading && sessions.length > 0 && (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {sessions.map((session, idx) => (
                            <motion.div
                                key={session.id}
                                initial={{ opacity: 0, y: 15 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: idx * 0.05 }}
                            >
                                <Link href={`/report/${session.id}`} className="block group h-full">
                                    <div className="h-full bg-slate-900/40 border border-slate-800 hover:border-indigo-500/50 hover:bg-slate-900/80 rounded-xl p-6 transition-all duration-300 relative overflow-hidden flex flex-col">

                                        {/* Hover Gradient Effect */}
                                        <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />

                                        <div className="flex justify-between items-start mb-4 relative z-10">
                                            <div className={`px-2.5 py-1 rounded text-[10px] font-bold uppercase tracking-wider border ${getStatusColor(session.status)}`}>
                                                {session.status}
                                            </div>
                                            <span className="text-[10px] font-mono text-slate-500">{session.id.slice(0, 8)}...</span>
                                        </div>

                                        <h3 className="text-lg font-bold text-slate-100 mb-2 group-hover:text-indigo-300 transition-colors line-clamp-2 relative z-10">
                                            {session.title}
                                        </h3>

                                        <div className="mt-auto space-y-4 relative z-10 pt-4 border-t border-slate-800/50">
                                            <div className="flex items-center gap-2 text-xs text-slate-400">
                                                <Calendar className="w-3 h-3" />
                                                <span>{session.date}</span>
                                                <span className="text-slate-600">•</span>
                                                <Clock className="w-3 h-3" />
                                                <span>{new Date(session.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                                            </div>

                                            <div className="flex items-center justify-between text-xs font-bold text-indigo-400 group-hover:translate-x-1 transition-transform">
                                                <span>GENERATE REPORT</span>
                                                <ArrowRight className="w-4 h-4" />
                                            </div>
                                        </div>
                                    </div>
                                </Link>
                            </motion.div>
                        ))}
                    </div>
                )}
            </main>
        </div>
    );
}
