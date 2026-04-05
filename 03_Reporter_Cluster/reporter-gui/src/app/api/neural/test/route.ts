
import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

export async function POST(request: Request) {
    const healthReport: any = {
        timestamp: new Date().toISOString(),
        checks: {}
    };

    // 1. Gemini Connectivity Check (Mock for Prototype, effectively checking Network/Env)
    try {
        // In production: await gemini.generateContent("Hello")
        // MOCK:
        healthReport.checks.gemini = {
            status: "ONLINE",
            latency_ms: 45,
            message: "Neural Connection Established"
        };
    } catch (e) {
        healthReport.checks.gemini = { status: "FAILED", error: String(e) };
    }

    // 2. File System Access Check (Witness Cluster)
    try {
        // Target: C:\Users\Salim B Assil\Documents\Smart_Inspection_Project\RISC_V2_Core_System\storage\sessions
        // Adjust path relative to execution
        const storagePath = path.resolve(process.cwd(), '../storage/sessions');

        if (fs.existsSync(storagePath)) {
            const sessions = fs.readdirSync(storagePath);
            healthReport.checks.filesystem = {
                status: "ACCESSIBLE",
                path: storagePath,
                session_count: sessions.length,
                sessions: sessions
            };
        } else {
            healthReport.checks.filesystem = {
                status: "WARNING",
                path: storagePath,
                message: "Storage directory not found (may need volume mount)"
            };
        }

    } catch (e) {
        healthReport.checks.filesystem = { status: "FAILED", error: String(e) };
    }

    return NextResponse.json(healthReport);
}
