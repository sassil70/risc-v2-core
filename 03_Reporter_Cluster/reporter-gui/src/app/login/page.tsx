
"use client";

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { ShieldCheck, Lock, Fingerprint, Loader2 } from 'lucide-react';
import { GlassContainer } from '@/components/ui/GlassContainer';
import { AuthService } from '@/services/auth.service';

export default function LoginPage() {
    const router = useRouter();
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');

    const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError(null);

        try {
            await AuthService.login(username, password);
            router.push('/properties'); // Redirect to Mission Select (Properties)
        } catch (err: any) {
            setError(err.message || "Failed to establish link.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <main className="min-h-screen w-full bg-slate-950 flex items-center justify-center p-4 relative overflow-hidden">
            {/* Background Ambient Effects */}
            <div className="absolute inset-0 bg-[url('https://images.unsplash.com/photo-1550751827-4bd374c3f58b?q=80&w=2670&auto=format&fit=crop')] bg-cover bg-center opacity-20 blur-sm scale-110 animate-pulse-slow"></div>
            <div className="absolute inset-0 bg-gradient-to-b from-slate-950/80 via-slate-950/90 to-slate-950 z-0"></div>

            {/* Content */}
            <div className="z-10 w-full max-w-md space-y-8">

                {/* Header / Logo */}
                <motion.div
                    initial={{ opacity: 0, y: -20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.8 }}
                    className="text-center space-y-2"
                >
                    <div className="inline-flex items-center justify-center p-4 rounded-full bg-cyan-500/10 border border-cyan-500/20 shadow-[0_0_30px_rgba(6,182,212,0.15)] mb-4">
                        <ShieldCheck className="w-12 h-12 text-cyan-400" />
                    </div>
                    <h1 className="text-4xl font-extrabold text-white tracking-widest font-sans">
                        RISC <span className="text-cyan-400">V2.0</span>
                    </h1>
                    <p className="text-xs text-cyan-500/80 font-mono tracking-[0.3em] uppercase">
                        Forensic Intelligence Unit
                    </p>
                </motion.div>

                {/* Login Form */}
                <GlassContainer className="border-t-cyan-500/30 border-b-cyan-500/5">
                    <form onSubmit={handleLogin} className="space-y-6">

                        {error && (
                            <div className="bg-red-500/10 border border-red-500/20 text-red-400 text-xs p-3 rounded-lg font-mono text-center">
                                ERROR: {error}
                            </div>
                        )}

                        <div className="space-y-2">
                            <label className="text-[10px] font-mono font-bold text-slate-400 tracking-widest uppercase">Operator ID</label>
                            <div className="relative group">
                                <Fingerprint className="absolute left-3 top-3.5 w-5 h-5 text-slate-500 group-focus-within:text-cyan-400 transition-colors" />
                                <input
                                    type="text"
                                    placeholder="Identity Signature"
                                    required
                                    value={username}
                                    onChange={(e) => setUsername(e.target.value)}
                                    className="w-full bg-slate-900/50 border border-slate-700/50 rounded-xl py-3 pl-10 pr-4 text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/50 transition-all font-mono text-sm"
                                />
                            </div>
                        </div>

                        <div className="space-y-2">
                            <label className="text-[10px] font-mono font-bold text-slate-400 tracking-widest uppercase">Access Key</label>
                            <div className="relative group">
                                <Lock className="absolute left-3 top-3.5 w-5 h-5 text-slate-500 group-focus-within:text-cyan-400 transition-colors" />
                                <input
                                    type="password"
                                    placeholder="Encrypted Token"
                                    required
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    className="w-full bg-slate-900/50 border border-slate-700/50 rounded-xl py-3 pl-10 pr-4 text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/50 transition-all font-mono text-sm"
                                />
                            </div>
                        </div>

                        <button
                            type="submit"
                            disabled={loading}
                            className="w-full py-3.5 bg-cyan-400 hover:bg-cyan-300 text-slate-950 font-bold rounded-xl shadow-[0_0_20px_rgba(6,182,212,0.3)] hover:shadow-[0_0_30px_rgba(6,182,212,0.5)] transition-all flex items-center justify-center gap-2 uppercase tracking-wide text-sm disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            {loading ? (
                                <>
                                    <Loader2 className="w-4 h-4 animate-spin" />
                                    Authenticating...
                                </>
                            ) : (
                                "Initiate Link"
                            )}
                        </button>

                    </form>
                </GlassContainer>

                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 1, duration: 1 }}
                    className="text-center"
                >
                    <p className="text-[9px] text-slate-600 font-mono tracking-wider">
                        SECURE CONNECTION :: ENCRYPTED [SHA-256]
                    </p>
                </motion.div>

            </div>
        </main>
    );
}
