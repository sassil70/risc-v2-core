
import Link from 'next/link';
import { ArrowRight, ShieldCheck, Activity, FileText } from 'lucide-react';

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-between p-24 bg-slate-950 text-slate-50">
      <div className="z-10 max-w-5xl w-full items-center justify-between font-mono text-sm lg:flex">
        <p className="fixed left-0 top-0 flex w-full justify-center border-b border-slate-800 bg-gradient-to-b from-slate-900 pb-6 pt-8 backdrop-blur-2xl lg:static lg:w-auto lg:rounded-xl lg:border lg:bg-slate-900/50 lg:p-4">
          <ShieldCheck className="mr-2 h-4 w-4 text-emerald-400" />
          Neural Shadow Active
          <span className="ml-2 text-xs text-slate-500">v2.0.0</span>
        </p>
        <div className="fixed bottom-0 left-0 flex h-48 w-full items-end justify-center bg-gradient-to-t from-slate-950 via-slate-950 lg:static lg:h-auto lg:w-auto lg:bg-none">
          <div className="flex items-center gap-2">
            <Activity className="h-4 w-4 text-blue-400 animate-pulse" />
            <span className="text-blue-400">System Nominal</span>
          </div>
        </div>
      </div>

      <div className="relative flex place-items-center before:absolute before:h-[300px] before:w-[480px] before:-translate-x-1/2 before:rounded-full before:bg-gradient-to-br before:from-blue-500 before:to-transparent before:opacity-10 before:blur-2xl before:content-[''] after:absolute after:-z-20 after:h-[180px] after:w-[240px] after:translate-x-1/3 after:bg-gradient-to-t after:from-emerald-500 after:to-transparent after:opacity-10 after:blur-2xl after:content-['']">
        <h1 className="text-6xl font-bold tracking-tighter bg-clip-text text-transparent bg-gradient-to-r from-blue-200 to-emerald-200">
          RISC V2 Reporter
        </h1>
      </div>

      <div className="mb-32 grid text-center lg:max-w-5xl lg:w-full lg:mb-0 lg:grid-cols-3 lg:text-left gap-4">

        <Link
          href="/reports"
          className="group rounded-lg border border-transparent px-5 py-4 transition-colors hover:border-slate-700 hover:bg-slate-900/50"
        >
          <h2 className={`mb-3 text-2xl font-semibold flex items-center gap-2`}>
            Reports
            <FileText className="h-5 w-5 text-slate-400 group-hover:text-blue-400 transition-colors" />
          </h2>
          <p className={`m-0 max-w-[30ch] text-sm opacity-50`}>
            Generate forensic-grade reports using Gemini 2.5 Intelligence.
          </p>
        </Link>

        {/* Other modules placeholders */}
        <div className="group rounded-lg border border-transparent px-5 py-4 transition-colors hover:border-slate-700 hover:bg-slate-900/50 opacity-50 cursor-not-allowed">
          <h2 className={`mb-3 text-2xl font-semibold`}>
            Analytics
          </h2>
          <p className={`m-0 max-w-[30ch] text-sm opacity-50`}>
            Deep dive into session metrics and surveyor performance (Coming Soon).
          </p>
        </div>

        <div className="group rounded-lg border border-transparent px-5 py-4 transition-colors hover:border-slate-700 hover:bg-slate-900/50 opacity-50 cursor-not-allowed">
          <h2 className={`mb-3 text-2xl font-semibold`}>
            Settings
          </h2>
          <p className={`m-0 max-w-[30ch] text-sm opacity-50`}>
            Configure API keys and RICS compliance templates.
          </p>
        </div>

      </div>
    </main>
  );
}
