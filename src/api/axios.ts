// API configuration and axios instance
import axios from 'axios';

// Base URL from environment variable (required)
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL;
if (!API_BASE_URL) {
    console.error('NEXT_PUBLIC_API_URL environment variable is not set!');
}

// Create axios instance
export const apiClient = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
    withCredentials: true, // Important for session cookies
});

// Request interceptor
apiClient.interceptors.request.use(
    async (config) => {
        // Add any auth tokens if needed
        const token = localStorage.getItem('access_token');
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        
        // Add Clerk user ID if available (for client-side requests)
        if (typeof window !== 'undefined') {
            try {
                // Dynamically import useUser to avoid SSR issues
                const { useUser } = await import('@clerk/nextjs');
                // Note: We can't use hooks here, so we'll get it from a different approach
                // We'll handle this in the hooks themselves
            } catch (e) {
                // Ignore if Clerk is not available
            }
        }
        
        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
);

// Response interceptor
apiClient.interceptors.response.use(
    (response) => response,
    (error) => {
        // Handle network errors (no response) - don't reject for email-accounts endpoint
        if (!error.response && error.config?.url?.includes('/api/email-accounts')) {
            console.warn('Network error for email-accounts, returning empty response');
            // Return a mock response with empty accounts
            return Promise.resolve({
                data: { accounts: [] },
                status: 200,
                statusText: 'OK',
                headers: {},
                config: error.config,
            });
        }
        
        if (error.response?.status === 401) {
            // Redirect to login if unauthorized, but only if not already on login or home page
            if (typeof window !== 'undefined') {
                const currentPath = window.location.pathname;
                // Don't redirect if already on login, home, or if it's a public route
                if (currentPath !== '/login' && currentPath !== '/' && !currentPath.startsWith('/api/')) {
                    window.location.href = '/login';
                }
            }
        }
        return Promise.reject(error);
    }
);

export default apiClient;
