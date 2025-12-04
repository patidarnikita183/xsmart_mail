"use client";

import { useEffect } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { useEmailAccounts, useConnectOutlook, useDisconnectAccount, useSetPrimaryAccount } from "@/api/hooks";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Mail, Plus, CheckCircle2, AlertCircle, Loader2 } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "sonner";
import { useQueryClient } from "@tanstack/react-query";

export default function EmailAccountsPage() {
    const searchParams = useSearchParams();
    const router = useRouter();
    const queryClient = useQueryClient();
    const { data, isLoading, error } = useEmailAccounts();
    const connectOutlook = useConnectOutlook();
    const disconnectAccount = useDisconnectAccount();
    const setPrimaryAccount = useSetPrimaryAccount();

    // Handle OAuth callback for adding accounts
    useEffect(() => {
        const accountAdded = searchParams.get('account_added');
        const tempToken = searchParams.get('token');

        if (accountAdded === 'success' && tempToken) {
            // Exchange token for session
            console.log('Exchanging token for session after adding account...', tempToken.substring(0, 20));
            fetch('/api/exchange-token', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include',
                body: JSON.stringify({ token: tempToken }),
            })
                .then(async (response) => {
                    if (!response.ok) {
                        const errorData = await response.json().catch(() => ({}));
                        throw new Error(errorData.error || `HTTP ${response.status}`);
                    }
                    return response.json();
                })
                .then((data) => {
                    console.log('Session established after adding account:', data);
                    toast.success("Account added successfully!", {
                        description: "Your Microsoft account has been connected.",
                    });
                    // Refresh accounts list
                    queryClient.invalidateQueries({ queryKey: ['emailAccounts'] });
                    queryClient.invalidateQueries({ queryKey: ['userProfile'] });
                    // Clean up URL
                    window.history.replaceState({}, document.title, '/email-accounts');
                })
                .catch((error) => {
                    console.error('Token exchange failed after adding account:', error);
                    toast.success("Account added successfully!", {
                        description: "Your Microsoft account has been connected.",
                    });
                    // Still refresh accounts list even if token exchange fails
                    queryClient.invalidateQueries({ queryKey: ['emailAccounts'] });
                    window.history.replaceState({}, document.title, '/email-accounts');
                });
        } else if (accountAdded === 'success') {
            // Account added but no token (fallback)
            toast.success("Account added successfully!", {
                description: "Your Microsoft account has been connected.",
            });
            queryClient.invalidateQueries({ queryKey: ['emailAccounts'] });
            window.history.replaceState({}, document.title, '/email-accounts');
        } else if (accountAdded === 'error') {
            toast.error("Failed to add account", {
                description: "Please try again.",
            });
            window.history.replaceState({}, document.title, '/email-accounts');
        }
    }, [searchParams, queryClient]);

    if (isLoading) {
        return (
            <div className="space-y-6">
                <div className="flex items-center justify-between">
                    <Skeleton className="h-8 w-48" />
                    <Skeleton className="h-10 w-40" />
                </div>
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                    {[1, 2, 3].map((i) => (
                        <Skeleton key={i} className="h-48" />
                    ))}
                </div>
            </div>
        );
    }

    if (error) {
        console.error("Email accounts error:", error);
        const errorMessage = (error as any)?.message || "Unknown error";
        const isNetworkError = errorMessage.includes('Network Error') || errorMessage.includes('ERR_NETWORK');

        return (
            <div className="flex flex-col items-center justify-center h-[400px] gap-4">
                <AlertCircle className="h-12 w-12 text-destructive" />
                <p className="text-muted-foreground">Failed to load email accounts</p>
                {isNetworkError ? (
                    <div className="text-center space-y-2">
                        <p className="text-sm text-muted-foreground">
                            Cannot connect to the backend server.
                        </p>
                        <p className="text-xs text-muted-foreground">
                            Please ensure the backend is running on port 5000.
                        </p>
                    </div>
                ) : (
                    <p className="text-sm text-muted-foreground">
                        {errorMessage}
                    </p>
                )}
                <div className="flex gap-2">
                    <Button variant="outline" onClick={() => queryClient.invalidateQueries({ queryKey: ['emailAccounts'] })}>
                        Retry
                    </Button>
                    <Button variant="outline" onClick={() => window.location.reload()}>
                        Reload Page
                    </Button>
                </div>
            </div>
        );
    }

    const accounts = data?.accounts || [];

    const handleDisconnect = async (accountId: string) => {
        try {
            await disconnectAccount.mutateAsync(accountId);
            toast.success("Account disconnected successfully");
        } catch (error) {
            toast.error("Failed to disconnect account");
        }
    };

    const handleSetPrimary = async (accountId: string) => {
        try {
            await setPrimaryAccount.mutateAsync(accountId);
            toast.success("Primary account updated");
        } catch (error) {
            toast.error("Failed to set primary account");
        }
    };

    return (
        <div className="space-y-8 max-w-7xl mx-auto">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b pb-6">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight bg-gradient-to-r from-gray-900 to-gray-600 bg-clip-text text-transparent">Linked Mailboxes</h1>
                    <p className="text-muted-foreground mt-1">
                        Connect and manage your email accounts for campaign sending
                    </p>
                </div>
                <Button onClick={() => connectOutlook.mutate()} className="shadow-lg hover:shadow-xl transition-all duration-300 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 border-0">
                    <Plus className="mr-2 h-4 w-4" />
                    Connect Account
                </Button>
            </div>

            {accounts.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-16 px-4 border-2 border-dashed border-yellow-200 rounded-xl bg-yellow-50/50">
                    <div className="h-16 w-16 bg-yellow-100 rounded-full flex items-center justify-center mb-6">
                        <AlertCircle className="h-8 w-8 text-yellow-600" />
                    </div>
                    <h3 className="text-xl font-semibold mb-2 text-gray-900">No email accounts connected</h3>
                    <p className="text-muted-foreground mb-8 text-center max-w-sm">
                        You need to connect at least one Microsoft Outlook account to send emails.
                        Connect your first account to get started.
                    </p>
                    <Button onClick={() => connectOutlook.mutate()} size="lg" className="shadow-md hover:shadow-lg transition-all">
                        <Plus className="mr-2 h-5 w-5" />
                        Connect Outlook Account
                    </Button>
                </div>
            ) : (
                <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
                    {accounts.map((account) => (
                        <Card
                            key={account.id}
                            className={`relative group hover:shadow-xl transition-all duration-300 border-0 shadow-md ${account.is_primary ? 'ring-2 ring-blue-500 ring-offset-2' : 'hover:-translate-y-1'}`}
                        >
                            {account.is_primary && (
                                <div className="absolute top-3 right-3 z-10">
                                    <Badge variant="default" className="bg-blue-600 text-white shadow-sm">
                                        <CheckCircle2 className="mr-1 h-3 w-3" />
                                        Primary
                                    </Badge>
                                </div>
                            )}
                            <CardHeader className="bg-gray-50/50 border-b border-gray-100 pb-4">
                                <div className="flex items-start justify-between">
                                    <div className="flex items-center gap-4">
                                        <div className={`p-3 rounded-xl shadow-sm ${account.is_primary ? 'bg-blue-100 text-blue-600' : 'bg-white text-gray-500 border border-gray-200'}`}>
                                            <Mail className="h-6 w-6" />
                                        </div>
                                        <div>
                                            <CardTitle className="text-lg font-semibold text-gray-900">{account.provider === 'outlook' ? 'Outlook' : 'Gmail'}</CardTitle>
                                            <p className="text-sm text-muted-foreground font-medium">{account.email}</p>
                                        </div>
                                    </div>
                                </div>
                            </CardHeader>
                            <CardContent className="space-y-5 pt-6">
                                <div className="flex items-center justify-between p-2 bg-gray-50 rounded-lg">
                                    <span className="text-sm font-medium text-gray-600">Status</span>
                                    <Badge
                                        variant={account.status === 'active' ? 'default' : 'secondary'}
                                        className={
                                            account.status === 'active'
                                                ? 'bg-green-100 text-green-700 hover:bg-green-200 border-0'
                                                : account.status === 'error'
                                                    ? 'bg-red-100 text-red-700 hover:bg-red-200 border-0'
                                                    : 'bg-gray-100 text-gray-700'
                                        }
                                    >
                                        {account.status === 'active' && <CheckCircle2 className="mr-1 h-3 w-3" />}
                                        {account.status === 'error' && <AlertCircle className="mr-1 h-3 w-3" />}
                                        <span className="capitalize">{account.status}</span>
                                    </Badge>
                                </div>

                                {account.is_primary && (
                                    <div className="flex items-start gap-2 p-3 bg-blue-50 rounded-lg border border-blue-100">
                                        <CheckCircle2 className="h-4 w-4 text-blue-600 mt-0.5" />
                                        <p className="text-xs font-medium text-blue-700">
                                            This account is currently set as your primary sending address.
                                        </p>
                                    </div>
                                )}

                                <div className="flex gap-3 pt-2">
                                    {!account.is_primary && (
                                        <Button
                                            variant="outline"
                                            size="sm"
                                            className="flex-1 hover:bg-blue-50 hover:text-blue-600 hover:border-blue-200 transition-colors"
                                            onClick={() => handleSetPrimary(account.id)}
                                            disabled={setPrimaryAccount.isPending}
                                        >
                                            {setPrimaryAccount.isPending ? (
                                                <Loader2 className="h-4 w-4 animate-spin" />
                                            ) : (
                                                'Set Primary'
                                            )}
                                        </Button>
                                    )}
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        className={`flex-1 hover:bg-red-50 hover:text-red-600 transition-colors ${account.is_primary ? 'w-full' : ''}`}
                                        onClick={() => handleDisconnect(account.id)}
                                        disabled={disconnectAccount.isPending}
                                    >
                                        {disconnectAccount.isPending ? (
                                            <Loader2 className="h-4 w-4 animate-spin" />
                                        ) : (
                                            'Disconnect'
                                        )}
                                    </Button>
                                </div>

                                <div className="text-xs text-center text-muted-foreground border-t pt-3">
                                    Last active: {new Date(account.last_used).toLocaleDateString()}
                                </div>
                            </CardContent>
                        </Card>
                    ))}

                    {/* Add New Account Card */}
                    <Card className="border-2 border-dashed border-gray-200 bg-gray-50/50 hover:bg-gray-50 hover:border-blue-300 transition-all duration-300 cursor-pointer group flex flex-col justify-center items-center min-h-[300px]">
                        <CardContent className="flex flex-col items-center justify-center py-12 w-full">
                            <div className="p-4 bg-white rounded-full mb-4 shadow-sm group-hover:shadow-md group-hover:scale-110 transition-all duration-300">
                                <Plus className="h-8 w-8 text-blue-500" />
                            </div>
                            <h3 className="font-semibold text-lg mb-2 text-gray-900">Connect New Account</h3>
                            <p className="text-sm text-muted-foreground mb-6 text-center max-w-[200px]">
                                Add more mailboxes to increase your daily sending limits
                            </p>
                            <div className="flex flex-col gap-3 w-full max-w-xs">
                                <Button
                                    variant="outline"
                                    className="w-full bg-white hover:bg-blue-50 hover:text-blue-600 hover:border-blue-200 transition-all shadow-sm"
                                    onClick={() => connectOutlook.mutate()}
                                >
                                    <Mail className="mr-2 h-4 w-4" />
                                    Connect Outlook
                                </Button>
                                <Button variant="ghost" className="w-full opacity-50 cursor-not-allowed" disabled>
                                    <Mail className="mr-2 h-4 w-4" />
                                    Gmail (Coming Soon)
                                </Button>
                            </div>
                        </CardContent>
                    </Card>
                </div>
            )}
        </div>
    );
}
