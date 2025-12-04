"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { SignIn } from "@clerk/nextjs";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Mail, Send, BarChart3, Shield, Zap, CheckCircle2, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { useLogin, useRegister } from "@/api/hooks";
import { useQueryClient } from "@tanstack/react-query";
import apiClient from "@/api/axios";
import { useUser } from "@clerk/nextjs";

export default function Home() {
    const router = useRouter();
    const { user, isLoading, isAuthenticated } = useAuth();
    const { user: clerkUser, isLoaded: clerkLoaded } = useUser();
    const queryClient = useQueryClient();
    const [isLoginMode, setIsLoginMode] = useState(true);
    const [showClerkSignIn, setShowClerkSignIn] = useState(false);
    const [formData, setFormData] = useState({
        username: '',
        password: '',
        email: '',
        display_name: ''
    });
    
    const loginMutation = useLogin();
    const registerMutation = useRegister();
    
    // Redirect if Clerk user is signed in
    useEffect(() => {
        if (clerkLoaded && clerkUser) {
            router.push('/dashboard');
        }
    }, [clerkUser, clerkLoaded, router]);

    // Handle OAuth callback from URL
    useEffect(() => {
        const urlParams = new URLSearchParams(window.location.search);
        const authStatus = urlParams.get('auth');

        if (authStatus === 'success') {
            // Get the temporary token from URL
            const tempToken = urlParams.get('token');

            if (tempToken) {
                console.log('Exchanging OAuth token for session...', tempToken.substring(0, 20));

                // Use Next.js API route as proxy to avoid CORS issues
                fetch('/api/exchange-token', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    credentials: 'include', // Important for cookies
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
                        console.log('Session established:', data);

                        if (data.success && data.user) {
                            // Set user data directly in query cache to avoid extra request
                            queryClient.setQueryData(['userProfile'], {
                                displayName: data.user.displayName,
                                email: data.user.email,
                                id: data.user.id,
                                userType: data.user.userType
                            });
                        }

                        // Show success message
                        toast.success("Authentication successful! Welcome to xSmart Mail Sender", {
                            description: "Your account has been connected successfully.",
                        });
                        // Clean up URL
                        window.history.replaceState({}, document.title, '/');

                        // Redirect to dashboard after a short delay
                        setTimeout(() => {
                            router.push('/dashboard');
                        }, 500);
                    })
                    .catch((error) => {
                        console.error('Token exchange failed:', error);
                        console.error('Error details:', error);

                        // More specific error message
                        let errorMsg = "Failed to establish session";
                        if (error.message.includes('Failed to fetch') || error.message.includes('Network')) {
                            errorMsg = "Cannot connect to server. Please ensure the backend is running on port 5000.";
                        } else if (error.message) {
                            errorMsg = error.message;
                        }

                        toast.error("Authentication failed", {
                            description: errorMsg,
                        });
                        window.history.replaceState({}, document.title, '/');
                    });
            } else {
                // No token - try to verify existing session
                console.log('No token in URL, trying to verify existing session...');
                toast.success("Authentication successful! Welcome to xSmart Mail Sender", {
                    description: "Your account has been connected successfully.",
                });
                window.history.replaceState({}, document.title, '/');
                queryClient.invalidateQueries({ queryKey: ['userProfile'] });
            }
        } else if (authStatus === 'error') {
            // Show error message and stay on home page (don't redirect)
            toast.error("Authentication failed", {
                description: "Please try signing in again.",
            });
            window.history.replaceState({}, document.title, '/');
        }
    }, [queryClient]);

    // Redirect to dashboard when user becomes authenticated
    useEffect(() => {
        // Only redirect if user is authenticated and not loading
        // This will trigger automatically when OAuth success refetches the user profile
        if (!isLoading && isAuthenticated && user) {
            router.push('/dashboard');
        }
    }, [isAuthenticated, user, isLoading, router]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        if (isLoginMode) {
            // Login
            if (!formData.username || !formData.password) {
                toast.error("Please fill in all fields");
                return;
            }

            try {
                const result = await loginMutation.mutateAsync({
                    username: formData.username,
                    password: formData.password
                });

                if (result.success) {
                    toast.success("Login successful!", {
                        description: `Welcome back, ${result.user.display_name || result.user.username}!`,
                    });
                    // Invalidate and refetch user profile
                    queryClient.invalidateQueries({ queryKey: ['userProfile'] });
                    // Wait for profile to load, then redirect to dashboard
                    setTimeout(() => {
                        router.push('/dashboard');
                    }, 800);
                } else {
                    // Login failed - stay on home page
                    toast.error("Login failed", {
                        description: result.error || "Invalid username or password",
                    });
                }
            } catch (error: any) {
                // Login failed - stay on home page
                toast.error("Login failed", {
                    description: error.response?.data?.error || "Invalid username or password",
                });
            }
        } else {
            // Register
            if (!formData.username || !formData.password || !formData.email) {
                toast.error("Please fill in all required fields");
                return;
            }

            if (formData.password.length < 6) {
                toast.error("Password must be at least 6 characters");
                return;
            }

            try {
                const result = await registerMutation.mutateAsync({
                    username: formData.username,
                    password: formData.password,
                    email: formData.email,
                    display_name: formData.display_name || formData.username
                });

                if (result.success) {
                    toast.success("Registration successful!", {
                        description: `Welcome, ${result.user.display_name || result.user.username}!`,
                    });
                    // Invalidate and refetch user profile
                    queryClient.invalidateQueries({ queryKey: ['userProfile'] });
                    // Wait for profile to load, then redirect to dashboard
                    setTimeout(() => {
                        router.push('/dashboard');
                    }, 800);
                } else {
                    // Registration failed - stay on home page
                    toast.error("Registration failed", {
                        description: result.error || "Failed to create account",
                    });
                }
            } catch (error: any) {
                // Registration failed - stay on home page
                toast.error("Registration failed", {
                    description: error.response?.data?.error || "Failed to create account",
                });
            }
        }
    };

    const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        setFormData(prev => ({
            ...prev,
            [e.target.name]: e.target.value
        }));
    };

    // Show loading state while checking authentication
    if (isLoading) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800">
                <div className="text-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
                    <p className="text-muted-foreground">Loading...</p>
                </div>
            </div>
        );
    }

    // Don't render home page if user is authenticated (will redirect)
    if (isAuthenticated && user) {
        return null;
    }

    return (
        <div className="min-h-screen bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900">
            {/* Hero Section */}
            <div className="container mx-auto px-4 py-16">
                <div className="text-center mb-16">
                    <div className="flex justify-center mb-6">
                        <div className="h-16 w-16 rounded-2xl bg-primary flex items-center justify-center shadow-lg">
                            <Mail className="h-8 w-8 text-primary-foreground" />
                        </div>
                    </div>
                    <h1 className="text-5xl md:text-6xl font-bold tracking-tight mb-4 bg-gradient-to-r from-blue-600 to-indigo-600 dark:from-blue-400 dark:to-indigo-400 bg-clip-text text-transparent">
                        xSmart Mail Sender
                    </h1>
                    <p className="text-xl md:text-2xl text-muted-foreground mb-2">
                        AI-Powered Email Outreach Platform
                    </p>
                    <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
                        Streamline your email campaigns, track engagement, and grow your business with intelligent email automation
                    </p>
                </div>

                {/* Login/Sign Up Card */}
                <div className="max-w-md mx-auto mb-16">
                    <Card className="shadow-2xl border-2">
                        <CardHeader className="space-y-1 text-center pb-4">
                            <CardTitle className="text-2xl font-bold">
                                {isLoginMode ? 'Welcome Back' : 'Create Account'}
                            </CardTitle>
                            <CardDescription className="text-base">
                                {isLoginMode
                                    ? 'Login to your account to continue'
                                    : 'Sign up to get started with xSmart Mail Sender'}
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            {/* Clerk Sign In Button */}
                            <div className="space-y-3 mb-6">
                                <Button
                                    onClick={() => setShowClerkSignIn(true)}
                                    className="w-full h-12 text-base font-semibold"
                                    size="lg"
                                    variant="default"
                                >
                                    <svg className="mr-3 h-5 w-5" viewBox="0 0 21 21" fill="none">
                                        <rect x="1" y="1" width="9" height="9" fill="#f25022" />
                                        <rect x="1" y="11" width="9" height="9" fill="#00a4ef" />
                                        <rect x="11" y="1" width="9" height="9" fill="#7fba00" />
                                        <rect x="11" y="11" width="9" height="9" fill="#ffb900" />
                                    </svg>
                                    {isLoginMode ? 'Sign In with Clerk' : 'Sign Up with Clerk'}
                                </Button>

                                <div className="relative">
                                    <div className="absolute inset-0 flex items-center">
                                        <span className="w-full border-t" />
                                    </div>
                                    <div className="relative flex justify-center text-xs uppercase">
                                        <span className="bg-card px-2 text-muted-foreground">Or</span>
                                    </div>
                                </div>
                            </div>
                            
                            {/* Clerk Sign In Modal */}
                            {showClerkSignIn && (
                                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
                                    <div className="relative bg-background rounded-lg p-6 max-w-md w-full mx-4">
                                        <Button
                                            variant="ghost"
                                            size="icon"
                                            className="absolute right-2 top-2"
                                            onClick={() => setShowClerkSignIn(false)}
                                        >
                                            ×
                                        </Button>
                                        <SignIn 
                                            routing="hash"
                                            afterSignInUrl="/dashboard"
                                        />
                                    </div>
                                </div>
                            )}

                            {/* Username/Password Form */}
                            <form onSubmit={handleSubmit} className="space-y-4">
                                {!isLoginMode && (
                                    <div className="space-y-2">
                                        <Label htmlFor="email">Email *</Label>
                                        <Input
                                            id="email"
                                            name="email"
                                            type="email"
                                            placeholder="your.email@example.com"
                                            value={formData.email}
                                            onChange={handleInputChange}
                                            required
                                        />
                                    </div>
                                )}

                                <div className="space-y-2">
                                    <Label htmlFor="username">Username *</Label>
                                    <Input
                                        id="username"
                                        name="username"
                                        type="text"
                                        placeholder="Enter your username"
                                        value={formData.username}
                                        onChange={handleInputChange}
                                        required
                                    />
                                </div>

                                <div className="space-y-2">
                                    <Label htmlFor="password">Password *</Label>
                                    <Input
                                        id="password"
                                        name="password"
                                        type="password"
                                        placeholder={isLoginMode ? "Enter your password" : "At least 6 characters"}
                                        value={formData.password}
                                        onChange={handleInputChange}
                                        required
                                    />
                                </div>

                                {!isLoginMode && (
                                    <div className="space-y-2">
                                        <Label htmlFor="display_name">Display Name (Optional)</Label>
                                        <Input
                                            id="display_name"
                                            name="display_name"
                                            type="text"
                                            placeholder="Your display name"
                                            value={formData.display_name}
                                            onChange={handleInputChange}
                                        />
                                    </div>
                                )}

                                <Button
                                    type="submit"
                                    className="w-full h-12 text-base font-semibold"
                                    size="lg"
                                    variant="outline"
                                    disabled={loginMutation.isPending || registerMutation.isPending}
                                >
                                    {(loginMutation.isPending || registerMutation.isPending) ? (
                                        <>
                                            <Loader2 className="mr-3 h-5 w-5 animate-spin" />
                                            {isLoginMode ? 'Logging in...' : 'Creating account...'}
                                        </>
                                    ) : (
                                        isLoginMode ? 'Login with Username' : 'Sign Up with Username'
                                    )}
                                </Button>
                            </form>

                            <div className="mt-4 text-center">
                                <button
                                    type="button"
                                    onClick={() => {
                                        setIsLoginMode(!isLoginMode);
                                        setFormData({ username: '', password: '', email: '', display_name: '' });
                                    }}
                                    className="text-sm text-primary hover:underline"
                                >
                                    {isLoginMode
                                        ? "Don't have an account? Sign up"
                                        : "Already have an account? Login"}
                                </button>
                            </div>

                            <p className="text-xs text-center text-muted-foreground pt-4">
                                By continuing, you agree to our Terms of Service and Privacy Policy
                            </p>
                        </CardContent>
                    </Card>
                </div>

                {/* Features Section */}
                <div className="grid md:grid-cols-3 gap-6 max-w-5xl mx-auto">
                    <Card className="border-2 hover:shadow-lg transition-shadow">
                        <CardHeader>
                            <div className="h-12 w-12 rounded-lg bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center mb-4">
                                <Send className="h-6 w-6 text-blue-600 dark:text-blue-400" />
                            </div>
                            <CardTitle>Smart Campaigns</CardTitle>
                            <CardDescription>
                                Create and manage email campaigns with advanced targeting and personalization
                            </CardDescription>
                        </CardHeader>
                    </Card>

                    <Card className="border-2 hover:shadow-lg transition-shadow">
                        <CardHeader>
                            <div className="h-12 w-12 rounded-lg bg-indigo-100 dark:bg-indigo-900/30 flex items-center justify-center mb-4">
                                <BarChart3 className="h-6 w-6 text-indigo-600 dark:text-indigo-400" />
                            </div>
                            <CardTitle>Real-time Analytics</CardTitle>
                            <CardDescription>
                                Track opens, clicks, replies, and bounces with detailed analytics and insights
                            </CardDescription>
                        </CardHeader>
                    </Card>

                    <Card className="border-2 hover:shadow-lg transition-shadow">
                        <CardHeader>
                            <div className="h-12 w-12 rounded-lg bg-purple-100 dark:bg-purple-900/30 flex items-center justify-center mb-4">
                                <Zap className="h-6 w-6 text-purple-600 dark:text-purple-400" />
                            </div>
                            <CardTitle>Automated Workflows</CardTitle>
                            <CardDescription>
                                Set up automated email sequences and follow-ups to nurture your leads
                            </CardDescription>
                        </CardHeader>
                    </Card>
                </div>

                {/* Benefits Section */}
                <div className="mt-16 max-w-3xl mx-auto">
                    <h2 className="text-3xl font-bold text-center mb-8">Why Choose xSmart Mail Sender?</h2>
                    <div className="grid md:grid-cols-2 gap-4">
                        {[
                            "Secure Microsoft OAuth integration",
                            "Real-time email tracking",
                            "Advanced campaign analytics",
                            "Automated email sequences",
                            "Bounce and delivery monitoring",
                            "User-friendly dashboard"
                        ].map((benefit, index) => (
                            <div key={index} className="flex items-center gap-3">
                                <CheckCircle2 className="h-5 w-5 text-green-600 dark:text-green-400 flex-shrink-0" />
                                <span className="text-muted-foreground">{benefit}</span>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
}
