import { api } from '@/lib/api';
import SessionList from '@/components/SessionList';

// Server Component (Async)
export default async function DashboardPage() {
    // Fetch Real Data from Brain Cluster
    // Note: Since we are in docker/local env, we use the internal URL or the public one mapped via rewrites?
    // In Server Components, we should usually hit the URL direct.
    // But our api.ts uses NEXT_PUBLIC_BRAIN_API_URL which is localhost:8001.
    // Next.js Server Component running on Node needs to reach localhost:8001.

    const sessions = await api.getSessions();

    return (
        <main className="min-h-screen bg-[#05080D] p-8 font-sans">
            <header className="mb-12 flex justify-between items-end border-b border-gray-800 pb-6">
                <div>
                    <h1 className="text-4xl font-bold text-white mb-2">
                        <span className="text-[#1E88E5]">RISC</span> Surveyor Dashboard
                    </h1>
                    <p className="text-gray-400">Manage, Analyze, and Print Forensic Reports</p>
                </div>
                <div className="text-right">
                    <div className="text-[#FFD700] font-mono text-sm">V2.1 DOCTORS PROTOCOL</div>
                    <div className="text-gray-500 text-xs">Connected to Brain Cluster (8001)</div>
                </div>
            </header>

            <section>
                <h2 className="text-2xl font-semibold text-white mb-6 flex items-center gap-2">
                    <span className="text-xl">📂</span> Active Sessions
                </h2>

                <SessionList sessions={sessions} />
            </section>
        </main>
    );
}
