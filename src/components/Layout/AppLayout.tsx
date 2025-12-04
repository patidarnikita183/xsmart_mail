"use client";

import { Sidebar } from "./Sidebar";
import { TopNav } from "./TopNav";

export function AppLayout({ children }: { children: React.ReactNode }) {
    return (
        <div className="flex min-h-screen bg-background font-sans antialiased">
            <Sidebar />
            <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
                <TopNav />
                <main className="flex-1 overflow-y-auto p-6 bg-muted/10">
                    {children}
                </main>
            </div>
        </div>
    );
}
