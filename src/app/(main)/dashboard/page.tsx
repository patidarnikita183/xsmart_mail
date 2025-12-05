"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ArrowUpRight, Mail, MousePointerClick, Send, Users, Inbox, TrendingUp, Calendar, Clock, BarChart3 } from "lucide-react";
import { useDashboardStats, useCampaigns, useEmailAccounts } from "@/api/hooks";
import { Skeleton } from "@/components/ui/skeleton";
import Link from "next/link";
import { useAuth } from "@/contexts/AuthContext";
import AnalyticsChart from "@/components/Dashboard/AnalyticsChart";

export default function DashboardPage() {
    const { user } = useAuth();
    const { data: stats, isLoading: statsLoading } = useDashboardStats();
    const { data: campaignsData } = useCampaigns();
    const { data: accountsData } = useEmailAccounts();

    const campaigns = campaignsData?.campaigns || [];
    const accounts = accountsData?.accounts || [];

    // Calculate active campaigns (campaigns that are currently running based on start_time and duration)
    // IMPORTANT: Exclude stopped campaigns from active count
    const now = new Date();
    const activeCampaigns = campaigns.filter((campaign: any) => {
        // Stopped campaigns should never be counted as active
        if (campaign.status === 'stopped') return false;

        if (!campaign.start_time || !campaign.duration) return false;
        const startTime = new Date(campaign.start_time);
        const endTime = new Date(startTime.getTime() + campaign.duration * 60 * 60 * 1000); // duration in hours
        return now >= startTime && now <= endTime;
    });

    // Calculate unique mailboxes
    const uniqueMailboxes = new Set(accounts.map((acc: any) => acc.email)).size;

    if (statsLoading) {
        return (
            <div className="flex flex-col gap-6">
                <div className="flex items-center justify-between">
                    <Skeleton className="h-8 w-48" />
                    <Skeleton className="h-10 w-40" />
                </div>
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                    {[1, 2, 3, 4].map((i) => (
                        <Skeleton key={i} className="h-32" />
                    ))}
                </div>
            </div>
        );
    }

    const totalCampaigns = campaigns.length;
    const totalSent = stats?.total_sent || 0;
    const openRate = stats?.open_rate || 0;
    const clickRate = stats?.click_rate || 0;
    const bounceRate = stats?.bounce_rate || 0;

    return (
        <div className="flex flex-col gap-8 max-w-7xl mx-auto">
            <div className="flex items-center justify-between border-b pb-6">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight bg-gradient-to-r from-gray-900 to-gray-600 bg-clip-text text-transparent">Dashboard</h1>
                    <p className="text-muted-foreground mt-1">
                        Welcome back, {user?.displayName || 'User'}! Here's what's happening today.
                    </p>
                </div>
                <div className="flex items-center gap-3">
                    <Button variant="outline" asChild className="hidden sm:flex">
                        <Link href="/campaigns">View All Campaigns</Link>
                    </Button>
                    <Button asChild className="shadow-lg hover:shadow-xl transition-all duration-300 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 border-0">
                        <Link href="/campaigns/new">
                            <Send className="mr-2 h-4 w-4" />
                            New Campaign
                        </Link>
                    </Button>
                </div>
            </div>

            {/* Key Metrics */}
            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
                <Card className="hover:shadow-lg transition-all duration-300 border-l-4 border-l-transparent hover:border-l-blue-500 group">
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium text-muted-foreground group-hover:text-blue-600 transition-colors">Total Campaigns</CardTitle>
                        <div className="h-8 w-8 rounded-full bg-blue-50 flex items-center justify-center group-hover:bg-blue-100 transition-colors">
                            <Send className="h-4 w-4 text-blue-600" />
                        </div>
                    </CardHeader>
                    <CardContent>
                        <div className="text-3xl font-bold text-gray-900">{totalCampaigns}</div>
                        <div className="flex items-center justify-between mt-1">
                            <p className="text-xs text-muted-foreground">
                                {activeCampaigns.length} currently active
                            </p>
                            <div className="flex items-center text-green-600 text-xs font-medium bg-green-50 px-2 py-0.5 rounded-full">
                                <TrendingUp className="h-3 w-3 mr-1" />
                                All time
                            </div>
                        </div>
                    </CardContent>
                </Card>

                <Card className="hover:shadow-lg transition-all duration-300 border-l-4 border-l-transparent hover:border-l-purple-500 group">
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium text-muted-foreground group-hover:text-purple-600 transition-colors">Unique Mailboxes</CardTitle>
                        <div className="h-8 w-8 rounded-full bg-purple-50 flex items-center justify-center group-hover:bg-purple-100 transition-colors">
                            <Inbox className="h-4 w-4 text-purple-600" />
                        </div>
                    </CardHeader>
                    <CardContent>
                        <div className="text-3xl font-bold text-gray-900">{uniqueMailboxes}</div>
                        <div className="flex items-center justify-between mt-1">
                            <p className="text-xs text-muted-foreground">
                                {accounts.filter((acc: any) => acc.is_primary).length} primary
                            </p>
                            <Link href="/email-accounts" className="text-xs text-purple-600 hover:underline flex items-center font-medium">
                                Manage
                                <ArrowUpRight className="h-3 w-3 ml-1" />
                            </Link>
                        </div>
                    </CardContent>
                </Card>

                <Card className="hover:shadow-lg transition-all duration-300 border-l-4 border-l-transparent hover:border-l-green-500 group relative overflow-hidden">
                    {activeCampaigns.length > 0 && (
                        <div className="absolute top-0 right-0 w-16 h-16 bg-green-500/10 rounded-bl-full -mr-8 -mt-8" />
                    )}
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium text-muted-foreground group-hover:text-green-600 transition-colors">Active Campaigns</CardTitle>
                        <div className="h-8 w-8 rounded-full bg-green-50 flex items-center justify-center group-hover:bg-green-100 transition-colors">
                            <Calendar className="h-4 w-4 text-green-600" />
                        </div>
                    </CardHeader>
                    <CardContent>
                        <div className="text-3xl font-bold text-gray-900">{activeCampaigns.length}</div>
                        <div className="flex items-center justify-between mt-1">
                            <p className="text-xs text-muted-foreground">
                                Running right now
                            </p>
                            {activeCampaigns.length > 0 && (
                                <div className="flex items-center text-green-600 text-xs font-medium bg-green-50 px-2 py-0.5 rounded-full animate-pulse">
                                    <div className="h-1.5 w-1.5 rounded-full bg-green-500 mr-1.5" />
                                    Live
                                </div>
                            )}
                        </div>
                    </CardContent>
                </Card>

                <Card className="hover:shadow-lg transition-all duration-300 border-l-4 border-l-transparent hover:border-l-indigo-500 group">
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium text-muted-foreground group-hover:text-indigo-600 transition-colors">Total Sent</CardTitle>
                        <div className="h-8 w-8 rounded-full bg-indigo-50 flex items-center justify-center group-hover:bg-indigo-100 transition-colors">
                            <Mail className="h-4 w-4 text-indigo-600" />
                        </div>
                    </CardHeader>
                    <CardContent>
                        <div className="text-3xl font-bold text-gray-900">{totalSent.toLocaleString()}</div>
                        <div className="flex items-center justify-between mt-1">
                            <p className="text-xs text-muted-foreground">
                                Emails delivered
                            </p>
                            <div className="flex items-center text-indigo-600 text-xs font-medium bg-indigo-50 px-2 py-0.5 rounded-full">
                                <TrendingUp className="h-3 w-3 mr-1" />
                                All time
                            </div>
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* Time-Based Analytics */}
            <div className="mt-2">
                <div className="flex items-center gap-2 mb-4">
                    <BarChart3 className="h-5 w-5 text-gray-700" />
                    <h2 className="text-lg font-semibold text-gray-800">Performance Overview</h2>
                </div>
                <div className="grid gap-4 md:grid-cols-3 mb-6">
                    {/* Today's Metrics */}
                    <Card className="border-l-4 border-l-blue-500 hover:shadow-md transition-all">
                        <CardHeader className="pb-3">
                            <div className="flex items-center justify-between">
                                <CardTitle className="text-sm font-medium text-gray-600 flex items-center gap-2">
                                    <Clock className="h-4 w-4" />
                                    Today
                                </CardTitle>
                                <span className="text-xs text-muted-foreground">
                                    {stats?.today?.date || new Date().toLocaleDateString()}
                                </span>
                            </div>
                        </CardHeader>
                        <CardContent className="space-y-2">
                            <div className="flex justify-between items-center">
                                <span className="text-xs text-muted-foreground">Sent</span>
                                <span className="text-lg font-bold text-blue-600">{stats?.today?.sent || 0}</span>
                            </div>
                            <div className="flex justify-between items-center">
                                <span className="text-xs text-muted-foreground">Opened</span>
                                <span className="text-sm font-semibold text-green-600">{stats?.today?.opened || 0}</span>
                            </div>
                            <div className="flex justify-between items-center">
                                <span className="text-xs text-muted-foreground">Clicked</span>
                                <span className="text-sm font-semibold text-purple-600">{stats?.today?.clicked || 0}</span>
                            </div>
                        </CardContent>
                    </Card>

                    {/* Last Week's Metrics */}
                    <Card className="border-l-4 border-l-green-500 hover:shadow-md transition-all">
                        <CardHeader className="pb-3">
                            <div className="flex items-center justify-between">
                                <CardTitle className="text-sm font-medium text-gray-600 flex items-center gap-2">
                                    <Calendar className="h-4 w-4" />
                                    Last 7 Days
                                </CardTitle>
                                <span className="text-xs text-muted-foreground">
                                    {stats?.last_week?.start_date ? new Date(stats.last_week.start_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : ''}
                                </span>
                            </div>
                        </CardHeader>
                        <CardContent className="space-y-2">
                            <div className="flex justify-between items-center">
                                <span className="text-xs text-muted-foreground">Sent</span>
                                <span className="text-lg font-bold text-blue-600">{stats?.last_week?.sent || 0}</span>
                            </div>
                            <div className="flex justify-between items-center">
                                <span className="text-xs text-muted-foreground">Opened</span>
                                <span className="text-sm font-semibold text-green-600">{stats?.last_week?.opened || 0}</span>
                            </div>
                            <div className="flex justify-between items-center">
                                <span className="text-xs text-muted-foreground">Clicked</span>
                                <span className="text-sm font-semibold text-purple-600">{stats?.last_week?.clicked || 0}</span>
                            </div>
                        </CardContent>
                    </Card>

                    {/* Last Month's Metrics */}
                    <Card className="border-l-4 border-l-purple-500 hover:shadow-md transition-all">
                        <CardHeader className="pb-3">
                            <div className="flex items-center justify-between">
                                <CardTitle className="text-sm font-medium text-gray-600 flex items-center gap-2">
                                    <TrendingUp className="h-4 w-4" />
                                    Last 30 Days
                                </CardTitle>
                                <span className="text-xs text-muted-foreground">
                                    {stats?.last_month?.start_date ? new Date(stats.last_month.start_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : ''}
                                </span>
                            </div>
                        </CardHeader>
                        <CardContent className="space-y-2">
                            <div className="flex justify-between items-center">
                                <span className="text-xs text-muted-foreground">Sent</span>
                                <span className="text-lg font-bold text-blue-600">{stats?.last_month?.sent || 0}</span>
                            </div>
                            <div className="flex justify-between items-center">
                                <span className="text-xs text-muted-foreground">Opened</span>
                                <span className="text-sm font-semibold text-green-600">{stats?.last_month?.opened || 0}</span>
                            </div>
                            <div className="flex justify-between items-center">
                                <span className="text-xs text-muted-foreground">Clicked</span>
                                <span className="text-sm font-semibold text-purple-600">{stats?.last_month?.clicked || 0}</span>
                            </div>
                        </CardContent>
                    </Card>
                </div>

                {/* Analytics Chart */}
                {stats?.daily_stats && stats.daily_stats.length > 0 && (
                    <AnalyticsChart data={stats.daily_stats} />
                )}
            </div>

            {/* Performance Metrics */}
            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
                <Card className="hover:shadow-md transition-all duration-300">
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium text-gray-600">Open Rate</CardTitle>
                        <Mail className="h-4 w-4 text-blue-500" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-3xl font-bold text-gray-900">{openRate.toFixed(1)}%</div>
                        <div className="mt-3 w-full bg-gray-100 rounded-full h-1.5 overflow-hidden">
                            <div
                                className="bg-blue-500 h-full rounded-full transition-all duration-1000"
                                style={{ width: `${Math.min(openRate, 100)}%` }}
                            />
                        </div>
                        <p className="text-xs text-muted-foreground mt-2">Target: 40%</p>
                    </CardContent>
                </Card>

                <Card className="hover:shadow-md transition-all duration-300">
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium text-gray-600">Click Rate</CardTitle>
                        <MousePointerClick className="h-4 w-4 text-green-500" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-3xl font-bold text-gray-900">{clickRate.toFixed(1)}%</div>
                        <div className="mt-3 w-full bg-gray-100 rounded-full h-1.5 overflow-hidden">
                            <div
                                className="bg-green-500 h-full rounded-full transition-all duration-1000"
                                style={{ width: `${Math.min(clickRate, 100)}%` }}
                            />
                        </div>
                        <p className="text-xs text-muted-foreground mt-2">Target: 5%</p>
                    </CardContent>
                </Card>

                <Card className="hover:shadow-md transition-all duration-300">
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium text-gray-600">Bounce Rate</CardTitle>
                        <ArrowUpRight className="h-4 w-4 text-red-500" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-3xl font-bold text-gray-900">{bounceRate.toFixed(1)}%</div>
                        <div className="mt-3 w-full bg-gray-100 rounded-full h-1.5 overflow-hidden">
                            <div
                                className="bg-red-500 h-full rounded-full transition-all duration-1000"
                                style={{ width: `${Math.min(bounceRate, 100)}%` }}
                            />
                        </div>
                        <p className="text-xs text-muted-foreground mt-2">Keep below 2%</p>
                    </CardContent>
                </Card>

                <Card className="hover:shadow-md transition-all duration-300">
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium text-gray-600">Reply Rate</CardTitle>
                        <Users className="h-4 w-4 text-purple-500" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-3xl font-bold text-gray-900">{(stats?.reply_rate || 0).toFixed(1)}%</div>
                        <div className="mt-3 w-full bg-gray-100 rounded-full h-1.5 overflow-hidden">
                            <div
                                className="bg-purple-500 h-full rounded-full transition-all duration-1000"
                                style={{ width: `${Math.min(stats?.reply_rate || 0, 100)}%` }}
                            />
                        </div>
                        <p className="text-xs text-muted-foreground mt-2">Target: 10%</p>
                    </CardContent>
                </Card>
            </div>

            {/* Campaign Overview */}
            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-7">
                <Card className="col-span-4 shadow-md border-0">
                    <CardHeader>
                        <CardTitle className="text-xl font-semibold text-gray-800">Recent Campaign Performance</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-4">
                            {campaigns.length === 0 ? (
                                <div className="flex flex-col items-center justify-center py-12 text-center">
                                    <div className="h-12 w-12 bg-gray-100 rounded-full flex items-center justify-center mb-4">
                                        <Send className="h-6 w-6 text-gray-400" />
                                    </div>
                                    <h3 className="text-lg font-medium text-gray-900">No campaigns yet</h3>
                                    <p className="text-sm text-muted-foreground mb-4 max-w-xs">
                                        Create your first campaign to start seeing performance data here.
                                    </p>
                                    <Button asChild variant="outline">
                                        <Link href="/campaigns/new">Create Campaign</Link>
                                    </Button>
                                </div>
                            ) : (
                                <div className="space-y-3">
                                    {campaigns.slice(0, 5).map((campaign: any) => (
                                        <div key={campaign.campaign_id} className="group flex items-center justify-between p-4 border rounded-xl hover:bg-gray-50/80 hover:border-blue-200 transition-all duration-200 cursor-pointer">
                                            <div className="flex-1 min-w-0 mr-4">
                                                <div className="flex items-center gap-2 mb-1">
                                                    <h4 className="font-semibold text-gray-900 truncate">{campaign.subject || 'No Subject'}</h4>
                                                    {campaign.start_time && campaign.duration && (() => {
                                                        const startTime = new Date(campaign.start_time);
                                                        const endTime = new Date(startTime.getTime() + campaign.duration * 60 * 60 * 1000);
                                                        // Stopped campaigns should never show as active
                                                        const isActive = campaign.status !== 'stopped' && now >= startTime && now <= endTime;
                                                        return isActive ? (
                                                            <span className="flex items-center px-2 py-0.5 text-[10px] uppercase tracking-wider font-bold bg-green-100 text-green-700 rounded-full">
                                                                <span className="w-1.5 h-1.5 rounded-full bg-green-500 mr-1 animate-pulse"></span>
                                                                Active
                                                            </span>
                                                        ) : null;
                                                    })()}
                                                </div>
                                                <div className="flex items-center gap-3 text-xs text-muted-foreground">
                                                    <span className="flex items-center">
                                                        <Send className="h-3 w-3 mr-1" />
                                                        {campaign.successfully_sent || 0}
                                                    </span>
                                                    <span className="flex items-center">
                                                        <Mail className="h-3 w-3 mr-1" />
                                                        {campaign.opened || 0}
                                                    </span>
                                                    <span className="flex items-center">
                                                        <MousePointerClick className="h-3 w-3 mr-1" />
                                                        {campaign.clicked || 0}
                                                    </span>
                                                </div>
                                            </div>
                                            <div className="text-right">
                                                <div className="text-lg font-bold text-gray-900">{campaign.open_rate || 0}%</div>
                                                <div className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Open rate</div>
                                            </div>
                                        </div>
                                    ))}
                                    {campaigns.length > 5 && (
                                        <Link href="/campaigns" className="block mt-4">
                                            <Button variant="ghost" className="w-full text-blue-600 hover:text-blue-700 hover:bg-blue-50">
                                                View All Campaigns <ArrowUpRight className="ml-2 h-4 w-4" />
                                            </Button>
                                        </Link>
                                    )}
                                </div>
                            )}
                        </div>
                    </CardContent>
                </Card>

                <Card className="col-span-3 shadow-md border-0 bg-gradient-to-br from-gray-900 to-gray-800 text-white">
                    <CardHeader>
                        <CardTitle className="text-xl font-semibold text-white">Quick Stats Overview</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-6">
                            <div className="flex items-center justify-between p-3 rounded-lg bg-white/5 hover:bg-white/10 transition-colors">
                                <span className="text-sm text-gray-300">Total Recipients</span>
                                <span className="text-lg font-bold text-white">
                                    {campaigns.reduce((sum: number, c: any) => sum + (c.total_recipients || 0), 0).toLocaleString()}
                                </span>
                            </div>
                            <div className="flex items-center justify-between p-3 rounded-lg bg-white/5 hover:bg-white/10 transition-colors">
                                <span className="text-sm text-gray-300">Successful Sends</span>
                                <span className="text-lg font-bold text-green-400">
                                    {campaigns.reduce((sum: number, c: any) => sum + (c.successfully_sent || 0), 0).toLocaleString()}
                                </span>
                            </div>
                            <div className="flex items-center justify-between p-3 rounded-lg bg-white/5 hover:bg-white/10 transition-colors">
                                <span className="text-sm text-gray-300">Total Opens</span>
                                <span className="text-lg font-bold text-blue-400">
                                    {campaigns.reduce((sum: number, c: any) => sum + (c.opened || 0), 0).toLocaleString()}
                                </span>
                            </div>
                            <div className="flex items-center justify-between p-3 rounded-lg bg-white/5 hover:bg-white/10 transition-colors">
                                <span className="text-sm text-gray-300">Total Clicks</span>
                                <span className="text-lg font-bold text-purple-400">
                                    {campaigns.reduce((sum: number, c: any) => sum + (c.clicked || 0), 0).toLocaleString()}
                                </span>
                            </div>

                            <div className="pt-4 mt-2 border-t border-white/10">
                                <Link href="/campaigns/new">
                                    <Button className="w-full bg-white text-gray-900 hover:bg-gray-100 font-semibold shadow-lg transition-all hover:scale-[1.02]">
                                        <Send className="mr-2 h-4 w-4" />
                                        Create New Campaign
                                    </Button>
                                </Link>
                            </div>
                        </div>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
