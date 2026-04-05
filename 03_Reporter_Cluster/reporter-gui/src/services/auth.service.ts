export interface User {
    id: string;
    username: string;
    full_name: string;
    role: string;
}

export interface AuthResponse {
    access_token: string;
    token_type: string;
    user: User;
}

const TOKEN_KEY = 'risc_v2_token';
const USER_KEY = 'risc_v2_user';

export const AuthService = {
    async login(username: string, password: string): Promise<User> {
        const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ username, password }),
        });

        if (!response.ok) {
            // Try to get error message from body
            let errorMessage = 'Authentication Failed';
            try {
                const errorData = await response.json();
                errorMessage = errorData.detail || errorMessage;
            } catch (e) {
                // Ignore json parse error
            }
            throw new Error(errorMessage);
        }

        const data: AuthResponse = await response.json();

        // Save Session
        if (typeof window !== 'undefined') {
            localStorage.setItem(TOKEN_KEY, data.access_token);
            localStorage.setItem(USER_KEY, JSON.stringify(data.user));
            // Also set cookie if needed for server components, but client-side is mostly fine for this dashboard
            document.cookie = `token=${data.access_token}; path=/; max-age=86400; SameSite=Strict`;
        }

        return data.user;
    },

    logout() {
        if (typeof window !== 'undefined') {
            localStorage.removeItem(TOKEN_KEY);
            localStorage.removeItem(USER_KEY);
            document.cookie = 'token=; path=/; expires=Thu, 01 Jan 1970 00:00:01 GMT;';
            window.location.href = '/login';
        }
    },

    getToken(): string | null {
        if (typeof window !== 'undefined') {
            return localStorage.getItem(TOKEN_KEY);
        }
        return null;
    },

    getUser(): User | null {
        if (typeof window !== 'undefined') {
            const userStr = localStorage.getItem(USER_KEY);
            if (userStr) {
                try {
                    return JSON.parse(userStr);
                } catch (e) {
                    return null;
                }
            }
        }
        return null;
    },

    isAuthenticated(): boolean {
        return !!this.getToken();
    }
};
