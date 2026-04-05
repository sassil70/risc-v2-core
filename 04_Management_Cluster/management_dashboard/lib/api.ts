
const API_BASE_URL = 'http://127.0.0.1:8001/api';

export interface Project {
    id: string;
    reference_number: string;
    client_name?: string;
    rooms?: Room[];
    status: 'active' | 'completed' | 'archived';
    created_at?: string;
}

export interface Room {
    id: string;
    name: string;
    type: string;
    status: 'pending' | 'in_progress' | 'completed';
}

export async function getProjects(): Promise<Project[]> {
    try {
        const res = await fetch(`${API_BASE_URL}/projects`, { cache: 'no-store' });
        if (!res.ok) return [];
        return res.json();
    } catch (e) {
        console.error("Failed to fetch projects", e);
        return [];
    }
}

export async function createProject(reference: string, client: string): Promise<Project | null> {
    try {
        const res = await fetch(`${API_BASE_URL}/projects`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ reference_number: reference, client_name: client })
        });
        if (!res.ok) return null;
        return res.json();
    } catch (e) {
        console.error("Failed to create project", e);
        return null;
    }
}

export async function getProject(id: string): Promise<Project | null> {
    try {
        const res = await fetch(`${API_BASE_URL}/projects`, { cache: 'no-store' });
        if (!res.ok) return null;
        const projects: Project[] = await res.json();
        return projects.find(p => p.id === id) || null;
    } catch (e) {
        console.error("Failed to fetch project", e);
        return null;
    }
}

export async function addRoom(projectId: string, name: string, type: string): Promise<Room[]> {
    try {
        const res = await fetch(`${API_BASE_URL}/projects/${projectId}/rooms`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, type })
        });
        if (!res.ok) return [];
        return res.json();
    } catch (e) {
        console.error("Failed to add room", e);
        return [];
    }
}
