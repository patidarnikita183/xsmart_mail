"use client";

import { useParams } from "next/navigation";
import { useCampaign, useCampaignAnalytics, useEmailTracking } from "@/api/hooks";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { AlertCircle, Send, Mail, MousePointerClick, Users, ArrowLeft, Clock, Calendar, Timer, Eye, ExternalLink, BarChart3 } from "lucide-react";
import Link from "next/link";
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from "recharts";
import { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";

export default function CampaignDetailPage() {
    const params = useParams();
    const campaignId = params.id as string;
    const [selectedEmail, setSelectedEmail] = useState<any>(null);
    const [emailAnalytics, setEmailAnalytics] = useState<any>(null);
    const [loadingEmailAnalytics, setLoadingEmailAnalytics] = useState(false);

    const { data: campaign, isLoading: isLoadingCampaign } = useCampaign(campaignId);
    const { data: analytics, isLoading: isLoadingAnalytics } = useCampaignAnalytics(campaignId);
    const { data: tracking, isLoading: isLoadingTracking } = useEmailTracking(campaignId);

    const fetchEmailAnalytics = async (trackingId: string) => {
        setLoadingEmailAnalytics(true);
        try {
            const API_URL = process.env.NEXT_PUBLIC_API_URL;
            const response = await fetch(`${API_URL}/api/campaign/${campaignId}/email/${trackingId}`);
            const data = await response.json();
            setEmailAnalytics(data);
        } catch (error) {
            console.error("Failed to fetch email analytics:", error);
        } finally {
            setLoadingEmailAnalytics(false);
        }
    };

    const handleEmailClick = (track: any) => {
        setSelectedEmail(track);
        if (track.tracking_id) {
            fetchEmailAnalytics(track.tracking_id);
        }
    };

    const handleStopCampaign = async () => {
        if (!confirm("Are you sure you want to stop this campaign? This action cannot be undone.")) return;

        try {
            const API_URL = process.env.NEXT_PUBLIC_API_URL;
            const response = await fetch(`${API_URL}/api/campaigns/${campaignId}/stop`, {
                method: 'POST',
            });

            if (response.ok) {
                alert("Campaign stopped successfully");
                window.location.reload();
            } else {
                alert("Failed to stop campaign");
            }
        } catch (error) {
            console.error("Error stopping campaign:", error);
            alert("An error occurred while stopping the campaign");
        }
    };

    if (isLoadingCampaign || isLoadingAnalytics) {
        return (
            <div className="space-y-6">
                <div className="flex items-center gap-4">
                    <Skeleton className="h-10 w-10 rounded-full" />
                    <div className="space-y-2">
                        <Skeleton className="h-8 w-64" />
                        <Skeleton className="h-4 w-32" />
                    </div>
                </div>
                <div className="grid grid-cols-4 gap-4">
                    {[1, 2, 3, 4].map((i) => (
                        <Skeleton key={i} className="h-32" />
                    ))}
                </div>
            </div>
        );
    }

    if (!campaign) {
        return (
            <div className="flex flex-col items-center justify-center h-[400px] gap-4">
                <AlertCircle className="h-12 w-12 text-destructive" />
                <h2 className="text-xl font-semibold">Campaign not found</h2>
                <Link href="/campaigns">
                    <Button variant="outline">
                        <ArrowLeft className="mr-2 h-4 w-4" />
                        Back to Campaigns
                    </Button>
                </Link>
            </div>
        );
    }

    return (
        <div className="space-y-8 max-w-7xl mx-auto">
            {/* Header */}
            <div className="flex flex-col gap-6 md:flex-row md:items-center md:justify-between border-b pb-6">
                <div className="flex items-start gap-4">
                    <Link href="/campaigns">
                        <Button variant="ghost" size="icon" className="mt-1 hover:bg-gray-100 rounded-full">
                            <ArrowLeft className="h-5 w-5 text-gray-600" />
                        </Button>
                    </Link>
                    <div>
                        <div className="flex items-center gap-3 mb-2">
                            <h1 className="text-3xl font-bold tracking-tight bg-gradient-to-r from-gray-900 to-gray-600 bg-clip-text text-transparent">{campaign.subject}</h1>
                            {analytics?.status === 'stopped' || campaign.status === 'stopped' ? (
                                <Badge variant="destructive" className="bg-red-100 text-red-700 hover:bg-red-200 border-0">
                                    <span className="relative flex h-2 w-2 mr-1.5">
                                        <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500"></span>
                                    </span>
                                    Stopped
                                </Badge>
                            ) : analytics?.is_active ? (
                                <Badge className="bg-green-100 text-green-700 hover:bg-green-200 border-0">
                                    <span className="relative flex h-2 w-2 mr-1.5">
                                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                                        <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
                                    </span>
                                    Active
                                </Badge>
                            ) : (
                                <Badge variant="outline" className="text-muted-foreground">
                                    Closed
                                </Badge>
                            )}
                        </div>
                        <p className="text-muted-foreground flex items-center gap-2 text-sm">
                            <span className="font-medium text-gray-900">Created:</span> {new Date(campaign.created_at).toLocaleDateString()}
                            <span className="text-gray-300">•</span>
                            <span className="font-medium text-gray-900">ID:</span> <span className="font-mono text-xs bg-gray-100 px-2 py-0.5 rounded">{campaign.campaign_id.slice(0, 8)}</span>
                        </p>
                    </div>
                </div>
                <div className="flex gap-3 pl-14 md:pl-0">
                    <Button
                        variant="destructive"
                        className="shadow-sm hover:shadow transition-all"
                        onClick={handleStopCampaign}
                        disabled={!analytics?.is_active}
                    >
                        Stop Campaign
                    </Button>
                </div>
            </div>

            {/* Metrics Cards */}
            <div className="grid gap-6 md:grid-cols-6">
                <Card className="hover:shadow-lg transition-all duration-300 border-l-4 border-l-transparent hover:border-l-indigo-500 group">
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium text-muted-foreground group-hover:text-indigo-600 transition-colors">Total Sent</CardTitle>
                        <div className="h-8 w-8 rounded-full bg-indigo-50 flex items-center justify-center group-hover:bg-indigo-100 transition-colors">
                            <Send className="h-4 w-4 text-indigo-600" />
                        </div>
                    </CardHeader>
                    <CardContent>
                        <div className="text-3xl font-bold text-gray-900">{campaign.sent_count || campaign.successfully_sent || campaign.total_sent || 0}</div>
                        <p className="text-xs text-muted-foreground mt-1">
                            of <span className="font-medium text-gray-900">{campaign.total_recipients || 0}</span> recipients
                        </p>
                    </CardContent>
                </Card>
                <Card className="hover:shadow-lg transition-all duration-300 border-l-4 border-l-transparent hover:border-l-orange-500 group">
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium text-muted-foreground group-hover:text-orange-600 transition-colors">Not Delivered</CardTitle>
                        <div className="h-8 w-8 rounded-full bg-orange-50 flex items-center justify-center group-hover:bg-orange-100 transition-colors">
                            <AlertCircle className="h-4 w-4 text-orange-600" />
                        </div>
                    </CardHeader>
                    <CardContent>
                        <div className="text-3xl font-bold text-orange-600">{campaign.not_delivered_count || analytics?.not_delivered_count || 0}</div>
                        <p className="text-xs text-muted-foreground mt-1">
                            Pending delivery
                        </p>
                    </CardContent>
                </Card>
                <Card className="hover:shadow-lg transition-all duration-300 border-l-4 border-l-transparent hover:border-l-blue-500 group">
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium text-muted-foreground group-hover:text-blue-600 transition-colors">Open Rate</CardTitle>
                        <div className="h-8 w-8 rounded-full bg-blue-50 flex items-center justify-center group-hover:bg-blue-100 transition-colors">
                            <Mail className="h-4 w-4 text-blue-600" />
                        </div>
                    </CardHeader>
                    <CardContent>
                        <div className="text-3xl font-bold text-gray-900">{campaign.open_rate || analytics?.open_rate || 0}%</div>
                        <p className="text-xs text-muted-foreground mt-1">
                            <span className="font-medium text-gray-900">{campaign.opened || analytics?.unique_opens || 0}</span> unique opens
                        </p>
                    </CardContent>
                </Card>
                <Card className="hover:shadow-lg transition-all duration-300 border-l-4 border-l-transparent hover:border-l-green-500 group">
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium text-muted-foreground group-hover:text-green-600 transition-colors">Click Rate</CardTitle>
                        <div className="h-8 w-8 rounded-full bg-green-50 flex items-center justify-center group-hover:bg-green-100 transition-colors">
                            <MousePointerClick className="h-4 w-4 text-green-600" />
                        </div>
                    </CardHeader>
                    <CardContent>
                        <div className="text-3xl font-bold text-gray-900">
                            {(campaign.successfully_sent || campaign.total_sent || analytics?.successfully_sent || 0) > 0
                                ? (((campaign.clicked || analytics?.unique_clicks || 0) / (campaign.successfully_sent || campaign.total_sent || analytics?.successfully_sent || 1)) * 100).toFixed(1)
                                : 0}%
                        </div>
                        <p className="text-xs text-muted-foreground mt-1">
                            <span className="font-medium text-gray-900">{campaign.clicked || analytics?.unique_clicks || 0}</span> unique clicks
                        </p>
                    </CardContent>
                </Card>
                <Card className="hover:shadow-lg transition-all duration-300 border-l-4 border-l-transparent hover:border-l-amber-500 group">
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium text-muted-foreground group-hover:text-amber-600 transition-colors">Reply Rate</CardTitle>
                        <div className="h-8 w-8 rounded-full bg-amber-50 flex items-center justify-center group-hover:bg-amber-100 transition-colors">
                            <Users className="h-4 w-4 text-amber-600" />
                        </div>
                    </CardHeader>
                    <CardContent>
                        <div className="text-3xl font-bold text-amber-600">{analytics?.reply_rate || campaign.reply_rate || 0}%</div>
                        <p className="text-xs text-muted-foreground mt-1">
                            <span className="font-medium text-gray-900">{analytics?.reply_count || campaign.reply_count || 0}</span> replies received
                        </p>
                    </CardContent>
                </Card>
                <Card className="hover:shadow-lg transition-all duration-300 border-l-4 border-l-transparent hover:border-l-red-500 group">
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium text-muted-foreground group-hover:text-red-600 transition-colors">Bounce Rate</CardTitle>
                        <div className="h-8 w-8 rounded-full bg-red-50 flex items-center justify-center group-hover:bg-red-100 transition-colors">
                            <AlertCircle className="h-4 w-4 text-red-600" />
                        </div>
                    </CardHeader>
                    <CardContent>
                        <div className="text-3xl font-bold text-red-600">{campaign.bounce_rate || analytics?.bounce_rate || 0}%</div>
                        <p className="text-xs text-muted-foreground mt-1">
                            <span className="font-medium text-gray-900">{campaign.bounced || analytics?.bounce_count || 0}</span> emails bounced
                        </p>
                    </CardContent>
                </Card>
            </div>

            {/* Tabs */}
            <Tabs defaultValue="leads" className="space-y-4">
                <TabsList>
                    <TabsTrigger value="leads">Lead List</TabsTrigger>
                    <TabsTrigger value="analytics">Analytics</TabsTrigger>
                    <TabsTrigger value="settings">Settings</TabsTrigger>
                </TabsList>

                <TabsContent value="leads" className="space-y-4">
                    <Card className="shadow-md border-0">
                        <CardHeader className="border-b bg-gray-50/50">
                            <CardTitle className="text-lg font-semibold text-gray-800">Recipients & Activity</CardTitle>
                        </CardHeader>
                        <CardContent className="p-0">
                            {isLoadingTracking ? (
                                <div className="space-y-4 p-6">
                                    {[1, 2, 3, 4, 5].map((i) => (
                                        <Skeleton key={i} className="h-12 w-full" />
                                    ))}
                                </div>
                            ) : tracking && tracking.length > 0 ? (
                                <div className="rounded-md">
                                    <Table>
                                        <TableHeader className="bg-gray-50/50">
                                            <TableRow className="hover:bg-transparent border-b border-gray-100">
                                                <TableHead className="font-semibold text-gray-600 pl-6">Recipient</TableHead>
                                                <TableHead className="font-semibold text-gray-600">Status</TableHead>
                                                <TableHead className="font-semibold text-gray-600">Delivered</TableHead>
                                                <TableHead className="font-semibold text-gray-600">Sent At</TableHead>
                                                <TableHead className="font-semibold text-gray-600 text-center">Opens</TableHead>
                                                <TableHead className="font-semibold text-gray-600 text-center">Clicks</TableHead>
                                                <TableHead className="font-semibold text-gray-600 text-center">Actions</TableHead>
                                            </TableRow>
                                        </TableHeader>
                                        <TableBody>
                                            {tracking.map((track) => (
                                                <TableRow
                                                    key={track.tracking_id}
                                                    className="hover:bg-gray-50/50 transition-colors border-b border-gray-100 cursor-pointer"
                                                    onClick={() => handleEmailClick(track)}
                                                >
                                                    <TableCell className="pl-6 py-4">
                                                        <div className="flex flex-col">
                                                            <span className="font-medium text-gray-900">{track.recipient_email || 'N/A'}</span>
                                                            <span className="text-xs text-muted-foreground">{track.recipient_name || 'No Name'}</span>
                                                        </div>
                                                    </TableCell>
                                                    <TableCell>
                                                        {track.application_error ? (
                                                            <Badge className="bg-orange-100 text-orange-700 hover:bg-orange-200 border-0 shadow-none">App Error</Badge>
                                                        ) : track.bounced ? (
                                                            <Badge variant="destructive" className="bg-red-100 text-red-700 hover:bg-red-200 border-0 shadow-none">Bounced</Badge>
                                                        ) : track.replies > 0 ? (
                                                            <Badge className="bg-purple-100 text-purple-700 hover:bg-purple-200 border-0 shadow-none">Replied</Badge>
                                                        ) : track.clicks > 0 ? (
                                                            <Badge className="bg-green-100 text-green-700 hover:bg-green-200 border-0 shadow-none">Clicked</Badge>
                                                        ) : track.opens > 0 ? (
                                                            <Badge className="bg-blue-100 text-blue-700 hover:bg-blue-200 border-0 shadow-none">Opened</Badge>
                                                        ) : (
                                                            <Badge variant="secondary" className="bg-gray-100 text-gray-600 hover:bg-gray-200 border-0 shadow-none">Sent</Badge>
                                                        )}
                                                    </TableCell>
                                                    <TableCell>
                                                        {track.application_error || track.bounced ? (
                                                            <Badge variant="destructive" className="bg-red-100 text-red-700">No</Badge>
                                                        ) : (
                                                            <Badge className="bg-green-100 text-green-700">Yes</Badge>
                                                        )}
                                                    </TableCell>
                                                    <TableCell className="text-gray-500 text-sm">
                                                        {track.sent_at ? new Date(track.sent_at).toLocaleString() : 'N/A'}
                                                    </TableCell>
                                                    <TableCell className="text-center">
                                                        {track.opens > 0 ? (
                                                            <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-blue-50 text-blue-600 text-xs font-bold">
                                                                {track.opens}
                                                            </span>
                                                        ) : (
                                                            <span className="text-gray-300">-</span>
                                                        )}
                                                    </TableCell>
                                                    <TableCell className="text-center">
                                                        {track.clicks > 0 ? (
                                                            <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-green-50 text-green-600 text-xs font-bold">
                                                                {track.clicks}
                                                            </span>
                                                        ) : (
                                                            <span className="text-gray-300">-</span>
                                                        )}
                                                    </TableCell>
                                                    <TableCell className="text-center">
                                                        <Button
                                                            variant="ghost"
                                                            size="sm"
                                                            onClick={(e) => {
                                                                e.stopPropagation();
                                                                handleEmailClick(track);
                                                            }}
                                                        >
                                                            <Eye className="h-4 w-4" />
                                                        </Button>
                                                    </TableCell>
                                                </TableRow>
                                            ))}
                                        </TableBody>
                                    </Table>
                                </div>
                            ) : (
                                <div className="flex flex-col items-center justify-center py-16 text-center">
                                    <div className="h-12 w-12 bg-gray-100 rounded-full flex items-center justify-center mb-4">
                                        <Mail className="h-6 w-6 text-gray-400" />
                                    </div>
                                    <h3 className="text-lg font-medium text-gray-900">No activity recorded yet</h3>
                                    <p className="text-sm text-muted-foreground max-w-xs">
                                        Once your campaign starts sending, recipient activity will appear here.
                                    </p>
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="analytics" className="space-y-6">
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        {/* Left Column: Success Pie Chart */}
                        <Card className="h-full border-0 shadow-lg bg-gradient-to-br from-white to-gray-50 dark:from-gray-900 dark:to-gray-800 overflow-hidden relative">
                            <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-blue-500 via-purple-500 to-pink-500"></div>
                            <CardHeader>
                                <CardTitle className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-600 to-purple-600">
                                    Campaign Success Rate
                                </CardTitle>
                            </CardHeader>
                            <CardContent className="flex flex-col items-center justify-center p-6">
                                {analytics ? (
                                    <div className="h-[350px] w-full relative">
                                        <ResponsiveContainer width="100%" height="100%">
                                            <PieChart>
                                                <Pie
                                                    data={[
                                                        { name: 'Sent', value: analytics.successfully_sent || 0, color: '#3b82f6' },
                                                        { name: 'Opened', value: analytics.unique_opens || 0, color: '#10b981' },
                                                        { name: 'Clicked', value: analytics.unique_clicks || 0, color: '#8b5cf6' },
                                                        { name: 'Replied', value: analytics.reply_count || 0, color: '#f59e0b' },
                                                        { name: 'Bounced', value: analytics.bounce_count || 0, color: '#ef4444' }
                                                    ].filter(i => i.value > 0)}
                                                    cx="50%"
                                                    cy="50%"
                                                    innerRadius={80}
                                                    outerRadius={120}
                                                    paddingAngle={5}
                                                    dataKey="value"
                                                >
                                                    {[
                                                        { name: 'Sent', value: analytics.successfully_sent || 0, color: '#3b82f6' },
                                                        { name: 'Opened', value: analytics.unique_opens || 0, color: '#10b981' },
                                                        { name: 'Clicked', value: analytics.unique_clicks || 0, color: '#8b5cf6' },
                                                        { name: 'Replied', value: analytics.reply_count || 0, color: '#f59e0b' },
                                                        { name: 'Bounced', value: analytics.bounce_count || 0, color: '#ef4444' }
                                                    ].filter(i => i.value > 0).map((entry, index) => (
                                                        <Cell key={`cell-${index}`} fill={entry.color} strokeWidth={0} />
                                                    ))}
                                                </Pie>
                                                <Tooltip
                                                    contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)' }}
                                                    itemStyle={{ fontWeight: '600' }}
                                                />
                                                <Legend verticalAlign="bottom" height={36} iconType="circle" />
                                            </PieChart>
                                        </ResponsiveContainer>
                                        {/* Center Text */}
                                        <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 text-center">
                                            <div className="text-3xl font-bold text-gray-900">{analytics.successfully_sent || 0}</div>
                                            <div className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">Total Sent</div>
                                        </div>
                                    </div>
                                ) : (
                                    <div className="h-[300px] flex items-center justify-center text-muted-foreground">
                                        No data available
                                    </div>
                                )}
                            </CardContent>
                        </Card>

                        {/* Right Column: Detailed Metrics */}
                        <div className="space-y-6">
                            {/* Engagement Metrics */}
                            <Card className="border-0 shadow-lg overflow-hidden">
                                <CardHeader className="pb-2">
                                    <CardTitle className="text-lg font-semibold flex items-center gap-2">
                                        <div className="p-2 rounded-lg bg-indigo-100 text-indigo-600">
                                            <BarChart3 className="h-5 w-5" />
                                        </div>
                                        Engagement Metrics
                                    </CardTitle>
                                </CardHeader>
                                <CardContent className="space-y-6 pt-4">
                                    {/* Open Rate */}
                                    <div className="space-y-2">
                                        <div className="flex justify-between items-end">
                                            <span className="text-sm font-medium text-gray-600">Open Rate</span>
                                            <div className="text-right">
                                                <span className="text-xl font-bold text-gray-900">{analytics?.open_rate || 0}%</span>
                                                <span className="text-xs text-muted-foreground ml-1">({analytics?.unique_opens || 0} opens)</span>
                                            </div>
                                        </div>
                                        <div className="h-3 w-full bg-gray-100 rounded-full overflow-hidden">
                                            <div
                                                className="h-full bg-gradient-to-r from-blue-400 to-blue-600 rounded-full transition-all duration-1000 ease-out"
                                                style={{ width: `${Math.min(100, analytics?.open_rate || 0)}%` }}
                                            ></div>
                                        </div>
                                    </div>

                                    {/* Click Rate */}
                                    <div className="space-y-2">
                                        <div className="flex justify-between items-end">
                                            <span className="text-sm font-medium text-gray-600">Click Rate</span>
                                            <div className="text-right">
                                                <span className="text-xl font-bold text-gray-900">
                                                    {(analytics?.successfully_sent > 0 && analytics?.unique_clicks > 0)
                                                        ? ((analytics.unique_clicks / analytics.successfully_sent) * 100).toFixed(1)
                                                        : 0}%
                                                </span>
                                                <span className="text-xs text-muted-foreground ml-1">({analytics?.unique_clicks || 0} clicks)</span>
                                            </div>
                                        </div>
                                        <div className="h-3 w-full bg-gray-100 rounded-full overflow-hidden">
                                            <div
                                                className="h-full bg-gradient-to-r from-purple-400 to-purple-600 rounded-full transition-all duration-1000 ease-out"
                                                style={{ width: `${(analytics?.successfully_sent > 0 && analytics?.unique_clicks > 0) ? ((analytics.unique_clicks / analytics.successfully_sent) * 100) : 0}%` }}
                                            ></div>
                                        </div>
                                    </div>

                                    {/* Reply Rate */}
                                    <div className="space-y-2">
                                        <div className="flex justify-between items-end">
                                            <span className="text-sm font-medium text-gray-600">Reply Rate</span>
                                            <div className="text-right">
                                                <span className="text-xl font-bold text-gray-900">{analytics?.reply_rate || 0}%</span>
                                                <span className="text-xs text-muted-foreground ml-1">({analytics?.reply_count || 0} replies)</span>
                                            </div>
                                        </div>
                                        <div className="h-3 w-full bg-gray-100 rounded-full overflow-hidden">
                                            <div
                                                className="h-full bg-gradient-to-r from-amber-400 to-amber-600 rounded-full transition-all duration-1000 ease-out"
                                                style={{ width: `${Math.min(100, analytics?.reply_rate || 0)}%` }}
                                            ></div>
                                        </div>
                                    </div>
                                </CardContent>
                            </Card>

                            {/* Timeline Card */}
                            <Card className="border-0 shadow-lg">
                                <CardHeader className="pb-2">
                                    <CardTitle className="text-lg font-semibold flex items-center gap-2">
                                        <div className="p-2 rounded-lg bg-emerald-100 text-emerald-600">
                                            <Clock className="h-5 w-5" />
                                        </div>
                                        Campaign Timeline
                                    </CardTitle>
                                </CardHeader>
                                <CardContent className="pt-4">
                                    <div className="grid grid-cols-2 gap-4">
                                        <div className="p-3 bg-gray-50 rounded-xl border border-gray-100">
                                            <div className="text-xs text-muted-foreground mb-1">Started</div>
                                            <div className="font-semibold text-gray-900">
                                                {analytics?.start_time ? new Date(analytics.start_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '-'}
                                            </div>
                                            <div className="text-xs text-gray-500">
                                                {analytics?.start_time ? new Date(analytics.start_time).toLocaleDateString() : ''}
                                            </div>
                                        </div>
                                        <div className="p-3 bg-gray-50 rounded-xl border border-gray-100">
                                            <div className="text-xs text-muted-foreground mb-1">Duration</div>
                                            <div className="font-semibold text-gray-900">
                                                {analytics?.duration || 24} Hours
                                            </div>
                                            <div className="text-xs text-gray-500">
                                                {analytics?.time_per_email_minutes ? `${analytics.time_per_email_minutes}m interval` : 'Auto interval'}
                                            </div>
                                        </div>
                                    </div>
                                </CardContent>
                            </Card>
                        </div>
                    </div>

                    {/* Recipient Table (Full Width) */}
                    <Card className="border-0 shadow-lg mt-6">
                        <CardHeader className="border-b bg-gray-50/50">
                            <CardTitle className="flex items-center justify-between">
                                <span>Recipient Activity</span>
                                <Badge variant="outline" className="font-normal">
                                    {analytics?.recipients?.length || 0} Total Recipients
                                </Badge>
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="p-0">
                            {analytics && analytics.recipients && analytics.recipients.length > 0 ? (
                                <div className="rounded-md">
                                    <Table>
                                        <TableHeader>
                                            <TableRow className="hover:bg-transparent">
                                                <TableHead>Recipient</TableHead>
                                                <TableHead>Status</TableHead>
                                                <TableHead className="text-center">Opens</TableHead>
                                                <TableHead className="text-center">Clicks</TableHead>
                                                <TableHead className="text-center">Replied</TableHead>
                                                <TableHead>Sent At</TableHead>
                                            </TableRow>
                                        </TableHeader>
                                        <TableBody>
                                            {analytics.recipients.slice(0, 10).map((recipient: any) => (
                                                <TableRow key={recipient.tracking_id || recipient.email} className="hover:bg-gray-50/50">
                                                    <TableCell>
                                                        <div className="flex flex-col">
                                                            <span className="font-medium text-gray-900">{recipient.email}</span>
                                                            <span className="text-xs text-muted-foreground">{recipient.name || 'No Name'}</span>
                                                        </div>
                                                    </TableCell>
                                                    <TableCell>
                                                        {recipient.application_error ? (
                                                            <Badge className="bg-orange-100 text-orange-700 border-0">App Error</Badge>
                                                        ) : recipient.bounced ? (
                                                            <Badge variant="destructive" className="bg-red-100 text-red-700 border-0">Bounced</Badge>
                                                        ) : recipient.replies > 0 ? (
                                                            <Badge className="bg-amber-100 text-amber-700 border-0">Replied</Badge>
                                                        ) : recipient.clicks > 0 ? (
                                                            <Badge className="bg-purple-100 text-purple-700 border-0">Clicked</Badge>
                                                        ) : recipient.opens > 0 ? (
                                                            <Badge className="bg-green-100 text-green-700 border-0">Opened</Badge>
                                                        ) : (
                                                            <Badge variant="secondary" className="bg-gray-100 text-gray-600 border-0">Delivered</Badge>
                                                        )}
                                                    </TableCell>
                                                    <TableCell className="text-center">
                                                        {recipient.opens > 0 ? (
                                                            <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-green-100 text-green-700 text-xs font-bold">
                                                                {recipient.opens}
                                                            </span>
                                                        ) : <span className="text-gray-300">-</span>}
                                                    </TableCell>
                                                    <TableCell className="text-center">
                                                        {recipient.clicks > 0 ? (
                                                            <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-purple-100 text-purple-700 text-xs font-bold">
                                                                {recipient.clicks}
                                                            </span>
                                                        ) : <span className="text-gray-300">-</span>}
                                                    </TableCell>
                                                    <TableCell className="text-center">
                                                        {recipient.replies > 0 ? (
                                                            <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-amber-100 text-amber-700 text-xs font-bold">
                                                                {recipient.replies}
                                                            </span>
                                                        ) : <span className="text-gray-300">-</span>}
                                                    </TableCell>
                                                    <TableCell className="text-sm text-muted-foreground">
                                                        {recipient.sent_at ? new Date(recipient.sent_at).toLocaleString() : '-'}
                                                    </TableCell>
                                                </TableRow>
                                            ))}
                                        </TableBody>
                                    </Table>
                                </div>
                            ) : (
                                <div className="p-8 text-center text-muted-foreground">
                                    No recipient activity to display yet.
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="settings" className="space-y-4">
                    <Card>
                        <CardHeader>
                            <CardTitle>Campaign Settings</CardTitle>
                        </CardHeader>
                        <CardContent>
                            <p className="text-sm text-muted-foreground">
                                Settings configuration will be available here.
                            </p>
                        </CardContent>
                    </Card>
                </TabsContent>
            </Tabs>

            {/* Email Analytics Dialog */}
            <Dialog open={!!selectedEmail} onOpenChange={(open) => !open && setSelectedEmail(null)}>
                <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
                    <DialogHeader>
                        <DialogTitle>Email Analytics</DialogTitle>
                        <DialogDescription>
                            Detailed analytics for {selectedEmail?.recipient_email || selectedEmail?.email || 'this email'}
                        </DialogDescription>
                    </DialogHeader>
                    {loadingEmailAnalytics ? (
                        <div className="flex items-center justify-center py-8">
                            <div className="text-muted-foreground">Loading analytics...</div>
                        </div>
                    ) : emailAnalytics ? (
                        <div className="space-y-6">
                            <div className="grid grid-cols-2 gap-4">
                                <div className="p-4 border rounded-lg">
                                    <div className="text-sm text-muted-foreground mb-1">Recipient</div>
                                    <div className="font-semibold">{emailAnalytics.recipient_email}</div>
                                    <div className="text-xs text-muted-foreground mt-1">{emailAnalytics.recipient_name || 'No Name'}</div>
                                </div>
                                <div className="p-4 border rounded-lg">
                                    <div className="text-sm text-muted-foreground mb-1">Status</div>
                                    <div>
                                        {emailAnalytics.bounced ? (
                                            <Badge variant="destructive">Bounced</Badge>
                                        ) : (
                                            <Badge className="bg-green-100 text-green-700">Delivered</Badge>
                                        )}
                                    </div>
                                    {emailAnalytics.bounce_reason && (
                                        <div className="text-xs text-red-600 mt-1">{emailAnalytics.bounce_reason}</div>
                                    )}
                                </div>
                            </div>

                            <div className="grid grid-cols-4 gap-4">
                                <div className="p-4 border rounded-lg text-center">
                                    <div className="text-2xl font-bold text-blue-600">{emailAnalytics.opens || 0}</div>
                                    <div className="text-xs text-muted-foreground mt-1">Opens</div>
                                    {emailAnalytics.first_open && (
                                        <div className="text-xs text-muted-foreground mt-1">
                                            First: {new Date(emailAnalytics.first_open).toLocaleString()}
                                        </div>
                                    )}
                                </div>
                                <div className="p-4 border rounded-lg text-center">
                                    <div className="text-2xl font-bold text-green-600">{emailAnalytics.clicks || 0}</div>
                                    <div className="text-xs text-muted-foreground mt-1">Clicks</div>
                                    {emailAnalytics.first_click && (
                                        <div className="text-xs text-muted-foreground mt-1">
                                            First: {new Date(emailAnalytics.first_click).toLocaleString()}
                                        </div>
                                    )}
                                </div>
                                <div className="p-4 border rounded-lg text-center">
                                    <div className="text-2xl font-bold text-purple-600">{emailAnalytics.replies || 0}</div>
                                    <div className="text-xs text-muted-foreground mt-1">Replies</div>
                                    {emailAnalytics.reply_date && (
                                        <div className="text-xs text-muted-foreground mt-1">
                                            {new Date(emailAnalytics.reply_date).toLocaleString()}
                                        </div>
                                    )}
                                </div>
                                <div className="p-4 border rounded-lg text-center">
                                    <div className="text-2xl font-bold text-red-600">{emailAnalytics.bounced ? 1 : 0}</div>
                                    <div className="text-xs text-muted-foreground mt-1">Bounced</div>
                                    {emailAnalytics.bounce_date && (
                                        <div className="text-xs text-muted-foreground mt-1">
                                            {new Date(emailAnalytics.bounce_date).toLocaleString()}
                                        </div>
                                    )}
                                </div>
                            </div>

                            <div className="p-4 border rounded-lg">
                                <div className="text-sm text-muted-foreground mb-2">Timeline</div>
                                <div className="space-y-2 text-sm">
                                    {emailAnalytics.sent_at && (
                                        <div className="flex justify-between">
                                            <span>Sent:</span>
                                            <span className="font-medium">{new Date(emailAnalytics.sent_at).toLocaleString()}</span>
                                        </div>
                                    )}
                                    {emailAnalytics.first_open && (
                                        <div className="flex justify-between">
                                            <span>First Opened:</span>
                                            <span className="font-medium text-blue-600">{new Date(emailAnalytics.first_open).toLocaleString()}</span>
                                        </div>
                                    )}
                                    {emailAnalytics.first_click && (
                                        <div className="flex justify-between">
                                            <span>First Clicked:</span>
                                            <span className="font-medium text-green-600">{new Date(emailAnalytics.first_click).toLocaleString()}</span>
                                        </div>
                                    )}
                                    {emailAnalytics.unsubscribed && emailAnalytics.unsubscribe_date && (
                                        <div className="flex justify-between">
                                            <span>Unsubscribed:</span>
                                            <span className="font-medium text-orange-600">{new Date(emailAnalytics.unsubscribe_date).toLocaleString()}</span>
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>
                    ) : (
                        <div className="text-center py-8 text-muted-foreground">
                            No analytics data available
                        </div>
                    )}
                </DialogContent>
            </Dialog>
        </div>
    );
}
