import { api } from '@/lib/api';
import FloorPlanViewer from '@/components/FloorPlanViewer';
import Link from 'next/link';

// Layout for the Report Editor
export default async function ReportLayout({
    children,
    params,
}: {
    children: React.ReactNode;
    params: Promise<{ id: string }>;
}) {
    // We don't strictly *need* to fetch details here if the Page fetches them too, 
    // but we might want the header title. 
    // However, the Page logic now handles the full header.
    // Let's keep the layout minimal or move the header to the Page as well for total control?
    // The user's feedback suggests "Left bar is useless because everything is in the bar that follows".
    // "Everything is in the bar that follows" -> means the Page has the sidebar.
    // So we should remove *everything* from Layout except the wrapper?
    // The Page component I wrote has the "Survey Plan" sidebar AND the header.
    // So this Layout file causing a DOUBLE HEADER and DOUBLE SIDEBAR?
    // My Page component has: <div className="flex h-screen ..."> root.
    // If this layout *also* adds structure, that's bad.

    // Let's make this layout effectively a Fragment or simple wrapper.
    return (
        <>
            {children}
        </>
    );
}
