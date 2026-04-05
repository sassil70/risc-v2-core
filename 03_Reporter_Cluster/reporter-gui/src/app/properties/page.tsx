"use client";

import Link from 'next/link';
import { motion } from 'framer-motion';
import { Building2, MapPin, Calendar, ArrowRight, Activity, Search } from 'lucide-react';
import { GlassContainer } from '@/components/ui/GlassContainer';
import { useEffect, useState } from 'react';
import { AuthService } from '@/services/auth.service';

interface Session {
    id: string;
    title: string;
    status: string;
    created_at: string;
    project_id?: string;
}

export default function PropertiesPage() {
    const [sessions, setSessions] = useState<Session[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        async function fetchSessions() {
            const user = AuthService.getUser();
            if (!user) return;

            try {
                const res = await fetch(`/api/surveyor/sessions?user_id=${user.id}`);
                if (res.ok) {
                    const data = await res.json();
                    setSessions(data);
                }
            } catch (error) {
                console.error("Failed to fetch sessions", error);
            } finally {
                setLoading(false);
            }
        }
        fetchSessions();
    }, []);

    // Helper to get consistent random image based on ID (so it doesn't flicker)
    const getPlaceholderImage = (id: string) => {
        const lastChar = id.charCodeAt(id.length - 1);
        if (lastChar % 3 === 0) return 'https://images.unsplash.com/photo-1613490493576-7fde63acd811?q=80&w=2671&auto=format&fit=crop'; // Villa
        if (lastChar % 3 === 1) return 'https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?q=80&w=2670&auto=format&fit=crop'; // Apt
        return 'https://images.unsplash.com/photo-1512917774080-9991f1c4c750?q=80&w=2670&auto=format&fit=crop'; // Townhouse
    };

    return (
        <div className="min-h-screen bg-slate-950 text-slate-100 font-sans pb-20">

            {/* Navbar */}
            <header className="sticky top-0 z-50 backdrop-blur-md bg-slate-950/80 border-b border-white/5 px-6 py-4 flex justify-between items-center">
                <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded bg-cyan-500/10 flex items-center justify-center border border-cyan-500/20">
                        <Building2 className="w-4 h-4 text-cyan-400" />
                    </div>
                    <div>
                        <h1 className="text-lg font-bold tracking-tight text-white">Active Missions</h1>
                        <p className="text-[10px] text-slate-500 font-mono">RISC V2.0 // SURVEYOR PORTAL</p>
                    </div>
                </div>
                <div className="flex items-center gap-4">
                    <div className="hidden md:flex items-center px-3 py-1.5 bg-slate-900 rounded-full border border-white/5 text-xs text-slate-400">
                        <Activity className="w-3 h-3 mr-2 text-emerald-400 animate-pulse" />
                        System Operational
                    </div>
                    <div className="w-8 h-8 rounded-full bg-slate-800 border border-white/10 flex items-center justify-center">
                        <span className="text-xs font-bold text-slate-300">SA</span>
                    </div>
                </div>
            </header>

            {/* Main Content */}
            <main className="max-w-7xl mx-auto px-6 py-10 space-y-8">

                {/* Search Bar */}
                <div className="relative max-w-md">
                    <Search className="absolute left-4 top-3.5 w-5 h-5 text-slate-500" />
                    <input
                        type="text"
                        placeholder="Search by Reference ID or Address..."
                        className="w-full bg-slate-900 border border-slate-800 rounded-xl py-3 pl-12 pr-4 text-sm text-slate-200 focus:outline-none focus:border-cyan-500/30 transition-all placeholder:text-slate-600"
                    />
                </div>

                {/* Loading State */}
                {loading && (
                    <div className="text-center py-20 text-slate-500">
                        Loading missions from Neural Core...
                    </div>
                )}

                {/* Empty State */}
                {!loading && sessions.length === 0 && (
                    <div className="text-center py-20 text-slate-500">
                        No active missions found.
                    </div>
                )}

                {/* Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {sessions.map((prop, index) => (
                        <motion.div
                            key={prop.id}
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: index * 0.1 }}
                        >
                            <Link href={`/report/${prop.id}`}>
                                <GlassContainer className="h-full hover:border-cyan-500/30 hover:bg-white/10 transition-all cursor-pointer group">
                                    {/* Image Header */}
                                    <div className="h-40 -mx-6 -mt-6 mb-4 overflow-hidden relative">
                                        <img src={getPlaceholderImage(prop.id)} alt={prop.title} className="w-full h-full object-cover opacity-80 group-hover:opacity-100 group-hover:scale-105 transition-all duration-500" />
                                        <div className="absolute top-4 right-4 px-2 py-1 rounded bg-black/60 backdrop-blur-md text-[10px] font-bold tracking-wider uppercase border border-white/10">
                                            {prop.status || 'Pending'}
                                        </div>
                                    </div>

                                    {/* Content */}
                                    <div className="space-y-4">
                                        <div>
                                            <h3 className="text-xl font-bold text-white group-hover:text-cyan-400 transition-colors">{prop.title}</h3>
                                            <div className="flex items-center gap-2 text-slate-400 text-sm mt-1">
                                                <MapPin className="w-3 h-3" />
                                                {prop.id} (Real Data)
                                            </div>
                                        </div>

                                        <div className="flex items-center justify-between text-xs text-slate-500 border-t border-white/5 pt-4">
                                            <div className="flex items-center gap-2">
                                                <Calendar className="w-3 h-3" />
                                                {new Date(prop.created_at).toLocaleDateString()}
                                            </div>
                                            <div className="flex items-center gap-1 font-mono text-cyan-500/80 group-hover:translate-x-1 transition-transform">
                                                OPEN REPORT <ArrowRight className="w-3 h-3" />
                                            </div>
                                        </div>
                                    </div>
                                </GlassContainer>
                            </Link>
                        </motion.div>
                    ))}
                </div>

            </main>
        </div>
    );
}
