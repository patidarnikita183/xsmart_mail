// API hooks using React Query
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useUser } from '@clerk/nextjs';
import apiClient from './axios';

// Types
export interface UserProfile {
    displayName: string;
    email: string;
    id: string;
    jobTitle?: string;
    officeLocation?: string;
    userType: 'sender' | 'target';
}

export interface EmailAccount {
    id: string;
    email: string;
    provider: 'outlook' | 'gmail';
    status: 'active' | 'inactive' | 'error';
    is_primary: boolean;
    last_used: string;
    created_at: string;
}

export interface Campaign {
    campaign_id: string;
    subject: string;
    created_at: string;
    updated_at: string;
    total_recipients: number;
    total_mails: number;
    successfully_sent: number;
    bounced: number;
    opened: number;
    clicked: number;
    open_rate: number;
    bounce_rate: number;
    status: string;
}

export interface EmailTracking {
    tracking_id: string;
    campaign_id: string;
    sender_email: string;
    recipient_name: string;
    recipient_email: string;
    subject: string;
    sent_at: string;
    opens: number;
    clicks: number;
    replies: number;
    bounced: boolean;
    bounce_reason?: string;
    first_open?: string;
    first_click?: string;
    reply_date?: string;
    application_error?: boolean;
    error_date?: string;
    unsubscribe_date?: string;
    bounce_date?: string;
}

// Auth hooks
export function useUserProfile() {
    return useQuery<UserProfile>({
        queryKey: ['userProfile'],
        queryFn: async () => {
            const { data } = await apiClient.get('/get-user-profile');
            return data;
        },
        retry: false,
        refetchOnWindowFocus: false,
        refetchOnMount: false,
        staleTime: 5 * 60 * 1000,
    });
}

export function useLogout() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: async () => {
            await apiClient.get('/logout');
        },
        onSuccess: () => {
            queryClient.clear();
            window.location.href = '/login';
        },
    });
}

export function useLogin() {
    return useMutation({
        mutationFn: async (credentials: { username: string; password: string }) => {
            const { data } = await apiClient.post('/api/login', credentials);
            return data;
        },
    });
}

export function useRegister() {
    return useMutation({
        mutationFn: async (userData: {
            username: string;
            password: string;
            email: string;
            display_name?: string
        }) => {
            const { data } = await apiClient.post('/api/register', userData);
            return data;
        },
    });
}

// Email Accounts Hooks
export function useEmailAccounts() {
    const { user: clerkUser } = useUser();

    console.log('[useEmailAccounts] Clerk user ID:', clerkUser?.id);

    return useQuery<{ accounts: EmailAccount[] }>({
        queryKey: ['emailAccounts', clerkUser?.id],
        queryFn: async (): Promise<{ accounts: EmailAccount[] }> => {
            console.log('[useEmailAccounts] Fetching email accounts for user:', clerkUser?.id);
            try {
                // Don't make the request if user ID is not available
                if (!clerkUser?.id) {
                    console.warn('[useEmailAccounts] Clerk user ID not available, returning empty accounts');
                    return { accounts: [] };
                }

                const response = await apiClient.get('/api/email-accounts', {
                    timeout: 10000, // 10 second timeout
                    headers: {
                        'X-Clerk-User-Id': clerkUser.id
                    }
                });
                console.log('[useEmailAccounts] Response:', response.data);
                return response.data || { accounts: [] };
            } catch (error: any) {
                console.error('[useEmailAccounts] Error:', error);
                // Handle network errors gracefully
                const isNetworkError =
                    error.code === 'ERR_NETWORK' ||
                    error.message === 'Network Error' ||
                    error.message?.includes('Network Error') ||
                    !error.response;

                if (isNetworkError) {
                    console.warn('Network error for email-accounts - returning empty array');
                    return { accounts: [] };
                }

                // Return empty accounts on 401 (unauthorized) or 400 (missing header)
                if (error.response?.status === 401 || error.response?.status === 400) {
                    console.warn('Unauthorized or missing Clerk ID - returning empty accounts');
                    return { accounts: [] };
                }

                // For other errors, return empty accounts
                console.warn('Error fetching email accounts:', error.response?.status || error.message);
                return { accounts: [] };
            }
        },
        enabled: !!clerkUser?.id, // Only fetch when Clerk user is available
        retry: false, // Don't retry on network errors
        refetchOnWindowFocus: false,
        staleTime: 30 * 1000, // Consider data fresh for 30 seconds
        // Don't treat errors as errors - always return data
        throwOnError: false,
    });
}

export function useConnectOutlook() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: async () => {
            const API_URL = process.env.NEXT_PUBLIC_API_URL;
            if (!API_URL) {
                throw new Error('NEXT_PUBLIC_API_URL environment variable is not set');
            }

            // Get Clerk user ID from the auth context or localStorage
            // We need to get it dynamically since hooks can't be used here
            let clerkUserId: string | null = null;

            if (typeof window !== 'undefined') {
                // Try to get from localStorage (set by AuthContext)
                clerkUserId = localStorage.getItem('clerk_user_id');

                // If not in localStorage, try to get from Clerk directly
                if (!clerkUserId) {
                    try {
                        const { useUser } = await import('@clerk/nextjs');
                        // Note: We can't use hooks here, so we'll pass it as query param
                        // The frontend will need to pass it when calling this
                    } catch (e) {
                        // Ignore
                    }
                }
            }

            // Build URL with Clerk user ID if available
            const url = clerkUserId
                ? `${API_URL}/add-account?clerk_user_id=${encodeURIComponent(clerkUserId)}`
                : `${API_URL}/add-account`;

            // Use add-account endpoint for adding new accounts
            window.location.href = url;
        },
    });
}

export function useDisconnectAccount() {
    const queryClient = useQueryClient();
    const { user: clerkUser } = useUser();

    return useMutation({
        mutationFn: async (accountId: string) => {
            if (!clerkUser?.id) {
                throw new Error('Clerk user ID is required');
            }
            await apiClient.delete(`/api/email-accounts/${accountId}`, {
                headers: {
                    'X-Clerk-User-Id': clerkUser.id
                }
            });
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['emailAccounts'] });
        },
    });
}

export function useSetPrimaryAccount() {
    const queryClient = useQueryClient();
    const { user: clerkUser } = useUser();

    return useMutation({
        mutationFn: async (accountId: string) => {
            if (!clerkUser?.id) {
                throw new Error('Clerk user ID is required');
            }
            await apiClient.post(`/api/email-accounts/${accountId}/set-primary`, {}, {
                headers: {
                    'X-Clerk-User-Id': clerkUser.id
                }
            });
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['emailAccounts'] });
        },
    });
}

// Mailbox hooks
export function useEmailAccount(accountId: string) {
    return useQuery({
        queryKey: ['emailAccount', accountId],
        queryFn: async () => {
            const { data } = await apiClient.get(`/api/email-accounts/${accountId}`);
            return data.account;
        },
        enabled: !!accountId,
    });
}

export function useMailboxCampaigns(accountId: string) {
    return useQuery({
        queryKey: ['mailboxCampaigns', accountId],
        queryFn: async () => {
            const { data } = await apiClient.get(`/api/mailbox/${accountId}/campaigns`);
            return data.campaigns || [];
        },
        enabled: !!accountId,
    });
}

// Campaign hooks
export function useCampaigns(filters?: {
    status?: string;
    date_from?: string;
    date_to?: string;
    search?: string;
}) {
    const { user: clerkUser } = useUser();

    return useQuery({
        queryKey: ['campaigns', filters, clerkUser?.id],
        queryFn: async () => {
            const params = new URLSearchParams();
            if (filters?.status) params.append('status', filters.status);
            if (filters?.date_from) params.append('date_from', filters.date_from);
            if (filters?.date_to) params.append('date_to', filters.date_to);
            if (filters?.search) params.append('search', filters.search);

            const { data } = await apiClient.get(`/api/campaigns/user?${params.toString()}`, {
                headers: {
                    'X-Clerk-User-Id': clerkUser?.id || ''
                }
            });
            return data;
        },
        enabled: !!clerkUser?.id, // Only fetch when Clerk user is available
    });
}

export function useCampaign(campaignId: string) {
    return useQuery({
        queryKey: ['campaign', campaignId],
        queryFn: async () => {
            const { data } = await apiClient.get(`/api/campaign/${campaignId}`);
            return data;
        },
        enabled: !!campaignId,
    });
}

export function useCampaignAnalytics(campaignId: string) {
    return useQuery({
        queryKey: ['campaignAnalytics', campaignId],
        queryFn: async () => {
            const { data } = await apiClient.get(`/api/analytics/campaign/${campaignId}`);
            return data;
        },
        enabled: !!campaignId,
    });
}

export function useCreateCampaign() {
    const queryClient = useQueryClient();
    const { user: clerkUser } = useUser();

    return useMutation({
        mutationFn: async (campaignData: any) => {
            const { data } = await apiClient.post('/send-mail', campaignData, {
                headers: {
                    'X-Clerk-User-Id': clerkUser?.id || ''
                }
            });
            return data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['campaigns'] });
        },
    });
}

// Email tracking hooks
export function useEmailTracking(campaignId?: string) {
    return useQuery<EmailTracking[]>({
        queryKey: ['emailTracking', campaignId],
        queryFn: async () => {
            const url = campaignId
                ? `/get-email-tracking?campaign_id=${campaignId}`
                : '/get-email-tracking';
            const { data } = await apiClient.get(url);
            return data.tracking || [];
        },
    });
}

// Dashboard Analytics
export function useDashboardStats() {
    const { user: clerkUser } = useUser();

    return useQuery({
        queryKey: ['dashboardStats', clerkUser?.id],
        queryFn: async () => {
            const { data } = await apiClient.get('/api/analytics/dashboard', {
                headers: {
                    'X-Clerk-User-Id': clerkUser?.id || ''
                }
            });
            return data;
        },
        enabled: !!clerkUser?.id,
    });
}

// Registered users hooks
export function useRegisteredUsers() {
    return useQuery({
        queryKey: ['registeredUsers'],
        queryFn: async () => {
            const { data } = await apiClient.get('/get-registered-users');
            return data;
        },
    });
}

// Warmup hooks
export function useStartWarmup() {
    return useMutation({
        mutationFn: async (warmupData: any) => {
            const { data } = await apiClient.post('/start-warmup', warmupData);
            return data;
        },
    });
}

// Campaign logs hooks
export function useCampaignLogs() {
    return useQuery({
        queryKey: ['campaignLogs'],
        queryFn: async () => {
            const { data } = await apiClient.get('/get-campaign-logs');
            return data.logs || [];
        },
    });
}

// Analytics hooks
export function useAnalytics() {
    return useQuery({
        queryKey: ['analytics'],
        queryFn: async () => {
            const { data } = await apiClient.get('/api/analytics/overview');
            return data;
        },
    });
}

export function useCampaignStatus(campaignId: string, enabled: boolean = false) {
    return useQuery({
        queryKey: ['campaignStatus', campaignId],
        queryFn: async () => {
            const { data } = await apiClient.get(`/api/campaigns/${campaignId}/status`);
            return data;
        },
        enabled: !!campaignId && enabled,
        refetchInterval: (query) => {
            const data = query.state.data as any;
            // Poll every 5 seconds if active or scheduled
            if (data?.status === 'active' || data?.status === 'scheduled') {
                return 5000;
            }
            return false;
        },
    });
}
