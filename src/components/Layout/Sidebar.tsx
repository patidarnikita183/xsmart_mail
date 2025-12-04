"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  Users,
  Mail,
  Send,
  GitBranch,
  BarChart3,
  FileText,
  Flame,
  Settings,
  Menu,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import { useState } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { useUser } from "@clerk/nextjs";

const sidebarItems = [
  { href: "/dashboard", icon: LayoutDashboard, label: "Dashboard" },
  { href: "/leads", icon: Users, label: "Lead Manager" },
  { href: "/email-accounts", icon: Mail, label: "Email Accounts" },
  { href: "/campaigns", icon: Send, label: "Campaigns" },
  { href: "/sequences", icon: GitBranch, label: "Sequences" },
  { href: "/analytics", icon: BarChart3, label: "Analytics" },
  { href: "/emails/logs", icon: FileText, label: "Activity Log" },
  { href: "/warmup", icon: Flame, label: "Warmup" },
  { href: "/settings", icon: Settings, label: "Settings" },
];

interface SidebarProps extends React.HTMLAttributes<HTMLDivElement> { }

export function Sidebar({ className }: SidebarProps) {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  return (
    <>
      <Sheet open={open} onOpenChange={setOpen}>
        <SheetTrigger asChild>
          <Button variant="ghost" className="md:hidden fixed left-4 top-4 z-40">
            <Menu className="h-5 w-5" />
          </Button>
        </SheetTrigger>
        <SheetContent side="left" className="p-0 w-64 bg-sidebar text-sidebar-foreground border-r border-sidebar-border">
          <SidebarContent pathname={pathname} setOpen={setOpen} />
        </SheetContent>
      </Sheet>

      <div className={cn("hidden md:flex flex-col w-64 bg-sidebar text-sidebar-foreground border-r border-sidebar-border h-screen sticky top-0", className)}>
        <SidebarContent pathname={pathname} />
      </div>
    </>
  );
}

function SidebarContent({ pathname, setOpen }: { pathname: string; setOpen?: (open: boolean) => void }) {
  const { user } = useAuth();
  const { user: clerkUser } = useUser();

  // Generate user initials from display name
  const getInitials = (name: string | undefined): string => {
    if (!name) return "U";
    const parts = name.trim().split(/\s+/);
    if (parts.length >= 2) {
      // First letter of first name + first letter of last name
      return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
    } else if (parts.length === 1) {
      // First 2 letters if single name
      return parts[0].substring(0, 2).toUpperCase();
    }
    return "U";
  };

  // Prioritize Clerk user data, then fallback to backend user data
  const displayName = clerkUser?.fullName ||
    clerkUser?.firstName ||
    clerkUser?.emailAddresses[0]?.emailAddress?.split('@')[0] ||
    user?.displayName ||
    "User";

  const userEmail = clerkUser?.emailAddresses[0]?.emailAddress || user?.email || "";
  const userInitials = getInitials(displayName);
  const userType = user?.userType ? user.userType.charAt(0).toUpperCase() + user.userType.slice(1) : "User";

  return (
    <div className="flex flex-col h-full bg-slate-900 text-slate-300">
      <div className="p-6 border-b border-slate-800">
        <h1 className="text-xl font-bold tracking-tight flex items-center gap-2 text-white">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600 shadow-lg shadow-blue-500/20">
            <span className="text-white">⚡</span>
          </span>
          xSmart Mail
        </h1>
      </div>
      <ScrollArea className="flex-1 px-4 py-4">
        <nav className="flex flex-col gap-1.5">
          {sidebarItems.map((item) => {
            const isActive = pathname === item.href || pathname.startsWith(`${item.href}/`);
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setOpen?.(false)}
                className={cn(
                  "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 group relative overflow-hidden",
                  isActive
                    ? "bg-blue-600 text-white shadow-md shadow-blue-900/20"
                    : "text-slate-400 hover:bg-slate-800 hover:text-white"
                )}
              >
                {isActive && (
                  <div className="absolute inset-0 bg-gradient-to-r from-blue-600 to-indigo-600 opacity-100 -z-10" />
                )}
                <item.icon className={cn("h-4 w-4 transition-transform group-hover:scale-110", isActive ? "text-white" : "text-slate-400 group-hover:text-white")} />
                {item.label}
              </Link>
            );
          })}
        </nav>
      </ScrollArea>
      <div className="p-4 border-t border-slate-800 bg-slate-950/30">
        <div className="flex items-center gap-3 px-2 py-2 rounded-lg hover:bg-slate-800/50 transition-colors cursor-pointer">
          <div className="h-9 w-9 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-inner border border-white/10">
            <span className="text-xs font-bold text-white">{userInitials}</span>
          </div>
          <div className="flex flex-col min-w-0">
            <span className="text-sm font-medium text-white truncate">{displayName}</span>
            <span className="text-xs text-slate-500 truncate">{userEmail}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
