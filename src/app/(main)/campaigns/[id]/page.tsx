"use client";

import { useParams } from "next/navigation";
import { useCampaign, useCampaignAnalytics, useEmailTracking } from "@/api/hooks";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { AlertCircle, Send, Mail, MousePointerClick, Users, ArrowLeft } from "lucide-react";
import Link from "next/link";
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

    const { data: campaign, isLoading: isLoadingCampaign } = useCampaign(campaignId);
    const { data: analytics, isLoading: isLoadingAnalytics } = useCampaignAnalytics(campaignId);
    const { data: tracking, isLoading: isLoadingTracking } = useEmailTracking(campaignId);

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
                            <Badge variant={campaign.successfully_sent > 0 ? "default" : "secondary"} className={campaign.successfully_sent > 0 ? "bg-green-100 text-green-700 hover:bg-green-200 border-0" : ""}>
                                {campaign.successfully_sent > 0 ? "Active" : "Draft"}
                            </Badge>
                        </div>
                        <p className="text-muted-foreground flex items-center gap-2 text-sm">
                            <span className="font-medium text-gray-900">Created:</span> {new Date(campaign.created_at).toLocaleDateString()}
                            <span className="text-gray-300">•</span>
                            <span className="font-medium text-gray-900">ID:</span> <span className="font-mono text-xs bg-gray-100 px-2 py-0.5 rounded">{campaign.campaign_id.slice(0, 8)}</span>
                        </p>
                    </div>
                </div>
                <div className="flex gap-3 pl-14 md:pl-0">
                    <Button variant="outline" className="shadow-sm hover:shadow transition-all">Edit Campaign</Button>
                    <Button variant="destructive" className="shadow-sm hover:shadow transition-all">Stop Campaign</Button>
                </div>
            </div>

            {/* Metrics Cards */}
            <div className="grid gap-6 md:grid-cols-4">
                <Card className="hover:shadow-lg transition-all duration-300 border-l-4 border-l-transparent hover:border-l-indigo-500 group">
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium text-muted-foreground group-hover:text-indigo-600 transition-colors">Total Sent</CardTitle>
                        <div className="h-8 w-8 rounded-full bg-indigo-50 flex items-center justify-center group-hover:bg-indigo-100 transition-colors">
                            <Send className="h-4 w-4 text-indigo-600" />
                        </div>
                    </CardHeader>
                    <CardContent>
                        <div className="text-3xl font-bold text-gray-900">{campaign.successfully_sent}</div>
                        <p className="text-xs text-muted-foreground mt-1">
                            of <span className="font-medium text-gray-900">{campaign.total_recipients}</span> recipients
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
                        <div className="text-3xl font-bold text-gray-900">{campaign.open_rate}%</div>
                        <p className="text-xs text-muted-foreground mt-1">
                            <span className="font-medium text-gray-900">{campaign.opened}</span> unique opens
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
                            {campaign.successfully_sent > 0
                                ? ((campaign.clicked / campaign.successfully_sent) * 100).toFixed(1)
                                : 0}%
                        </div>
                        <p className="text-xs text-muted-foreground mt-1">
                            <span className="font-medium text-gray-900">{campaign.clicked}</span> unique clicks
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
                        <div className="text-3xl font-bold text-red-600">{campaign.bounce_rate}%</div>
                        <p className="text-xs text-muted-foreground mt-1">
                            <span className="font-medium text-gray-900">{campaign.bounced}</span> emails bounced
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
                                                <TableHead className="font-semibold text-gray-600">Sent At</TableHead>
                                                <TableHead className="font-semibold text-gray-600 text-center">Opens</TableHead>
                                                <TableHead className="font-semibold text-gray-600 text-center">Clicks</TableHead>
                                            </TableRow>
                                        </TableHeader>
                                        <TableBody>
                                            {tracking.map((track) => (
                                                <TableRow key={track.tracking_id} className="hover:bg-gray-50/50 transition-colors border-b border-gray-100">
                                                    <TableCell className="pl-6 py-4">
                                                        <div className="flex flex-col">
                                                            <span className="font-medium text-gray-900">{track.recipient_email}</span>
                                                            <span className="text-xs text-muted-foreground">{track.recipient_name || 'No Name'}</span>
                                                        </div>
                                                    </TableCell>
                                                    <TableCell>
                                                        {track.bounced ? (
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
                                                    <TableCell className="text-gray-500 text-sm">
                                                        {new Date(track.sent_at).toLocaleString()}
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

                <TabsContent value="analytics" className="space-y-4">
                    <Card>
                        <CardHeader>
                            <CardTitle>Performance Over Time</CardTitle>
                        </CardHeader>
                        <CardContent className="h-[300px] flex items-center justify-center text-muted-foreground">
                            Chart visualization coming soon...
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
        </div>
    );
}
