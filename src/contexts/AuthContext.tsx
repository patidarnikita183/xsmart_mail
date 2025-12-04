"use client";

import React, { createContext, useContext, useEffect, useState } from 'react';
import { useUser, useClerk } from '@clerk/nextjs';
import { useRouter } from 'next/navigation';
import apiClient from '@/api/axios';

interface User {
    displayName: string;
    email: string;
    id: string;
    jobTitle?: string;
    officeLocation?: string;
    userType: 'sender' | 'target';
    clerkUserId?: string;
}

interface AuthContextType {
    user: User | null;
    isLoading: boolean;
    isAuthenticated: boolean;
    clerkUserId: string | null;
    logout: () => void;
    syncClerkUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
    const router = useRouter();
    const { user: clerkUser, isLoaded: clerkLoaded } = useUser();
    const { signOut } = useClerk();
    const [user, setUser] = useState<User | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [isAuthenticated, setIsAuthenticated] = useState(false);

    // Sync Clerk user with backend (non-blocking)
    const syncClerkUser = async () => {
        if (!clerkUser) return;
        
        // Set user immediately from Clerk (don't wait for backend sync)
        setUser({
            displayName: clerkUser.fullName || clerkUser.firstName || '',
            email: clerkUser.primaryEmailAddress?.emailAddress || '',
            id: clerkUser.id,
            clerkUserId: clerkUser.id,
            userType: 'sender',
        });
        setIsAuthenticated(true);
        
        // Store Clerk user ID in localStorage for use in OAuth flow
        if (typeof window !== 'undefined') {
            localStorage.setItem('clerk_user_id', clerkUser.id);
        }
        
        // Try to sync with backend in the background (non-blocking)
        try {
            const response = await apiClient.post('/api/sync-clerk-user', {
                clerk_user_id: clerkUser.id,
                email: clerkUser.primaryEmailAddress?.emailAddress || '',
                display_name: clerkUser.fullName || clerkUser.firstName || '',
            }, {
                timeout: 5000, // 5 second timeout
            });
            
            if (response.data.success && response.data.user_id) {
                // Update user ID if backend returned one
                setUser(prev => prev ? {
                    ...prev,
                    id: response.data.user_id || prev.id,
                } : null);
            }
        } catch (error: any) {
            // Silently fail - user is already authenticated via Clerk
            // Only log if it's not a network error (backend might not be running)
            if (error.code !== 'ERR_NETWORK' && error.code !== 'ECONNABORTED') {
                console.warn('Failed to sync Clerk user with backend:', error.message);
            }
            // User is still authenticated, just backend sync failed
        }
    };

    useEffect(() => {
        if (clerkLoaded) {
            if (clerkUser) {
                syncClerkUser();
            } else {
                setUser(null);
                setIsAuthenticated(false);
            }
            setIsLoading(false);
        }
    }, [clerkUser, clerkLoaded]);

    const logout = async () => {
        try {
            // Sign out from Clerk
            await signOut();
        } catch (error) {
            console.error('Error signing out from Clerk:', error);
        } finally {
            // Clear local state
            setUser(null);
            setIsAuthenticated(false);
            // Redirect to home page
            router.push('/');
        }
    };

    return (
        <AuthContext.Provider value={{ 
            user, 
            isLoading, 
            isAuthenticated, 
            clerkUserId: clerkUser?.id || null,
            logout,
            syncClerkUser
        }}>
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    const context = useContext(AuthContext);
    if (context === undefined) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
}
