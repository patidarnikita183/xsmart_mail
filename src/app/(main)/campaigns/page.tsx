"use client";

import { useCampaigns } from "@/api/hooks";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Plus, Send, Mail, MousePointerClick, Users, AlertCircle, CheckCircle2, Calendar } from "lucide-react";
import Link from "next/link";
import { Skeleton } from "@/components/ui/skeleton";

import CampaignCard from "@/components/Campaigns/CampaignCard";

export default function CampaignsPage() {
    const { data, isLoading, error } = useCampaigns();

    if (isLoading) {
        return (
            <div className="flex flex-col gap-6">
                <div className="flex items-center justify-between">
                    <Skeleton className="h-8 w-48" />
                    <Skeleton className="h-10 w-40" />
                </div>
                <div className="space-y-4">
                    {[1, 2, 3].map((i) => (
                        <Skeleton key={i} className="h-32 w-full" />
                    ))}
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="flex flex-col items-center justify-center h-[400px] gap-4">
                <AlertCircle className="h-12 w-12 text-destructive" />
                <p className="text-muted-foreground">Failed to load campaigns</p>
                <Button variant="outline" onClick={() => window.location.reload()}>
                    Retry
                </Button>
            </div>
        );
    }

    const campaigns = data?.campaigns || [];
    const totalCampaigns = data?.total_campaigns || 0;

    return (
        <div className="flex flex-col gap-8 max-w-7xl mx-auto">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b pb-6">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight bg-gradient-to-r from-gray-900 to-gray-600 bg-clip-text text-transparent">Campaigns</h1>
                    <p className="text-muted-foreground mt-1">
                        Manage and track your email outreach campaigns
                    </p>
                </div>
                <div className="flex items-center gap-3">
                    <div className="hidden md:flex items-center gap-2 px-3 py-1 bg-gray-100 rounded-full text-xs font-medium text-gray-600">
                        <span className="w-2 h-2 rounded-full bg-green-500"></span>
                        {totalCampaigns} Total
                    </div>
                    <Link href="/campaigns/new">
                        <Button className="shadow-lg hover:shadow-xl transition-all duration-300 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 border-0">
                            <Plus className="mr-2 h-4 w-4" />
                            New Campaign
                        </Button>
                    </Link>
                </div>
            </div>

            {campaigns.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-16 px-4 border-2 border-dashed border-gray-200 rounded-xl bg-gray-50/50">
                    <div className="h-16 w-16 bg-blue-100/50 rounded-full flex items-center justify-center mb-6">
                        <Send className="h-8 w-8 text-blue-600" />
                    </div>
                    <h3 className="text-xl font-semibold mb-2 text-gray-900">No campaigns yet</h3>
                    <p className="text-muted-foreground mb-8 text-center max-w-sm">
                        Get started by creating your first email campaign. Track opens, clicks, and engagement in real-time.
                    </p>
                    <Link href="/campaigns/new">
                        <Button size="lg" className="shadow-lg hover:shadow-xl transition-all duration-300 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 border-0">
                            <Plus className="mr-2 h-5 w-5" />
                            Create First Campaign
                        </Button>
                    </Link>
                </div>
            ) : (
                <div className="grid gap-6">
                    {campaigns.map((campaign: any) => (
                        <CampaignCard key={campaign.campaign_id} campaign={campaign} />
                    ))}
                </div>
            )}
        </div>
    );
}
