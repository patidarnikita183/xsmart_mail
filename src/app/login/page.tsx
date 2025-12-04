"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { SignIn } from "@clerk/nextjs";
import { useUser } from "@clerk/nextjs";
import { Loader2 } from "lucide-react";

export default function LoginPage() {
    const router = useRouter();
    const { user, isLoaded } = useUser();

    // Redirect to dashboard if already authenticated
    useEffect(() => {
        if (isLoaded && user) {
            router.replace('/dashboard');
        }
    }, [user, isLoaded, router]);

    // Show loading state while checking authentication
    if (!isLoaded) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
                <div className="text-center">
                    <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4 text-white" />
                    <p className="text-white">Loading...</p>
                </div>
            </div>
        );
    }

    // Don't render if redirecting to dashboard
    if (user) {
        return null;
    }

    return (
        <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
            <div className="w-full max-w-md p-8">
                <div className="text-center mb-8">
                    <h1 className="text-4xl font-bold text-white mb-2">xSmart Mail Sender</h1>
                    <p className="text-slate-300">Professional Email Outreach Platform</p>
                </div>
                <SignIn 
                    appearance={{
                        elements: {
                            rootBox: "mx-auto",
                            card: "bg-white shadow-2xl"
                        }
                    }}
                />
            </div>
        </div>
    );
}
