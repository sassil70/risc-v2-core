import { notFound } from 'next/navigation';

const BRAIN_API_URL = process.env.NEXT_PUBLIC_BRAIN_API_URL || 'http://127.0.0.1:8000';

// Types matching the Backend Response
export interface Session {
    id: string;
    project_id?: string;
    started_at: string;
    status: string;
    // Extracted from session_init.json logic if available in listing
    address?: string;
    room_count?: number;
}

export interface Room {
    id: string;
    name: string;
    type: string;
    floor: number;
    status: 'pending' | 'in_progress' | 'completed' | 'red';
    completeness: number;
    inspection_count: number;
    images_count?: number; // New V2.1
    audio_count?: number; // New V2.1
    contexts?: string[]; // New V2.1
}

// Simplified Interface - The Session IS the Details
export interface SessionDetails {
    id: string;
    status: string;
    address: {
        postcode: string;
        street: string;
        city: string;
        full_address: string;
    };
    property_type: string;
    floor_plan: {
        rooms: Room[];
    };
    created_at?: string;
}

export const api = {
    /**
     * Lists all sessions. 
     * Uses the Hybrid DB/Disk logic from Backend.
     */
    getSessions: async (): Promise<Session[]> => {
        try {
            const res = await fetch(`${BRAIN_API_URL}/api/sessions`);
            if (!res.ok) {
                console.error("Failed to fetch sessions");
                return [];
            }
            return await res.json();
        } catch (e) {
            console.error("API Error (getSessions):", e);
            return [];
        }
    },

    /**
     * Gets the full session object directly.
     * Endpoint: /api/sessions/{id}
     */
    getSessionDetails: async (sessionId: string): Promise<SessionDetails> => {
        try {
            // Updated to use the standard REST endpoint, not the Status check
            const res = await fetch(`${BRAIN_API_URL}/api/sessions/${sessionId}`, {
                cache: 'no-store'
            });

            if (!res.ok) {
                if (res.status === 404) notFound();
                throw new Error("Failed to fetch session details");
            }
            return await res.json();
        } catch (e) {
            console.error("API Error (getSessionDetails):", e);
            throw e;
        }
    },

    /**
     * Helper to construct the Image URL for a specific evidence file.
     * Since we use a Static Mount at /storage, we just construct the path.
     */
    getEvidenceUrl: (sessionId: string, roomId: string, filename: string) => {
        return `${BRAIN_API_URL}/storage/sessions/${sessionId}/${roomId}/${filename}`;
    },

    /**
     * Lists all images in a room.
     * Endpoint: /api/sessions/{session_id}/rooms/{room_id}/images
     */
    getRoomImages: async (sessionId: string, roomId: string): Promise<{ images: string[], audio: string[] }> => {
        try {
            const res = await fetch(`${BRAIN_API_URL}/api/sessions/${sessionId}/rooms/${roomId}/images`);
            if (!res.ok) {
                console.error("Failed to fetch room media");
                return { images: [], audio: [] };
            }
            return await res.json();
        } catch (e) {
            console.error("API Error (getRoomImages):", e);
            return { images: [], audio: [] };
        }
    }
};
