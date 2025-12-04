import { useCampaignStatus } from "@/api/hooks";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Send, Mail, MousePointerClick, Users, AlertCircle, CheckCircle2, Calendar, Loader2 } from "lucide-react";
import Link from "next/link";

interface CampaignCardProps {
    campaign: any;
}

export default function CampaignCard({ campaign }: CampaignCardProps) {
    // Determine initial active state to decide if we should poll
    const now = new Date();
    let shouldPoll = false;

    if (campaign.status === 'active' || campaign.status === 'scheduled') {
        shouldPoll = true;
    } else if (campaign.start_time && campaign.duration) {
        const startTime = new Date(campaign.start_time);
        const endTime = new Date(startTime.getTime() + (campaign.duration || 24) * 60 * 60 * 1000);
        if (now >= startTime && now <= endTime) {
            shouldPoll = true;
        } else if (now < startTime) {
            shouldPoll = true; // Scheduled
        }
    }

    // Poll status if active/scheduled
    const { data: statusData } = useCampaignStatus(
        campaign.campaign_id,
        shouldPoll
    );

    // Use polled data if available, otherwise fallback to prop data
    const currentStatus = statusData?.status || campaign.status;
    const sentCount = statusData?.sent_count ?? campaign.successfully_sent;
    const failedCount = statusData?.failed_count ?? campaign.bounced; // Mapping failed to bounced for now as simplified view

    // Calculate derived state
    const isActive = currentStatus === 'active';
    const isScheduled = currentStatus === 'scheduled';
    const isCompleted = currentStatus === 'completed';

    // Calculate progress percentage
    const totalRecipients = campaign.total_recipients || 0;
    const progress = totalRecipients > 0 ? (sentCount / totalRecipients) * 100 : 0;

    return (
        <Link href={`/campaigns/${campaign.campaign_id}`}>
            <Card className="group hover:shadow-lg transition-all duration-300 cursor-pointer relative overflow-hidden border-l-4 border-l-transparent hover:border-l-primary">
                {isActive && (
                    <div className="absolute top-0 left-0 w-1 h-full bg-green-500 animate-pulse" />
                )}
                <CardHeader className="pb-3">
                    <div className="flex items-start justify-between">
                        <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1.5 flex-wrap">
                                <h3 className="text-lg font-semibold truncate pr-2 leading-none">
                                    {campaign.subject || 'Untitled Campaign'}
                                </h3>
                                {isActive && (
                                    <Badge variant="default" className="gap-1.5 bg-green-500/15 text-green-600 hover:bg-green-500/25 border-green-200 shadow-none">
                                        <span className="relative flex h-2 w-2">
                                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                                            <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
                                        </span>
                                        Active
                                    </Badge>
                                )}
                                {isScheduled && (
                                    <Badge variant="secondary" className="gap-1.5 bg-blue-50 text-blue-700 hover:bg-blue-100 border-blue-200">
                                        <Calendar className="h-3 w-3" />
                                        Scheduled
                                    </Badge>
                                )}
                                {isCompleted && (
                                    <Badge variant="outline" className="gap-1.5 text-muted-foreground">
                                        <CheckCircle2 className="h-3 w-3" />
                                        Completed
                                    </Badge>
                                )}
                                {failedCount > 0 && (
                                    <Badge variant="destructive" className="gap-1.5">
                                        <AlertCircle className="h-3 w-3" />
                                        {failedCount} issues
                                    </Badge>
                                )}
                            </div>

                            <div className="flex items-center gap-3 text-sm text-muted-foreground">
                                <span className="flex items-center gap-1">
                                    <Badge variant="outline" className="font-mono text-[10px] h-5 px-1.5 text-muted-foreground/70">
                                        ID: {campaign.campaign_id.slice(0, 8)}
                                    </Badge>
                                </span>
                                <span className="text-xs">
                                    Created {new Date(campaign.created_at).toLocaleDateString()}
                                </span>
                                {campaign.start_time && (
                                    <span className="text-xs flex items-center gap-1">
                                        • Starts {new Date(campaign.start_time).toLocaleString(undefined, {
                                            month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit'
                                        })}
                                    </span>
                                )}
                            </div>

                            {isActive && (
                                <div className="mt-3 max-w-md">
                                    <div className="flex items-center justify-between text-xs mb-1.5">
                                        <span className="font-medium text-green-600">Sending in progress...</span>
                                        <span className="text-muted-foreground">{Math.round(progress)}%</span>
                                    </div>
                                    <div className="h-1.5 w-full bg-gray-100 rounded-full overflow-hidden">
                                        <div
                                            className="h-full bg-green-500 transition-all duration-1000 ease-out rounded-full"
                                            style={{ width: `${progress}%` }}
                                        />
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                </CardHeader>
                <CardContent>
                    <div className="grid grid-cols-2 sm:grid-cols-5 gap-4 pt-2">
                        <div className="flex flex-col p-2 rounded-lg bg-gray-50/50 group-hover:bg-gray-50 transition-colors">
                            <div className="flex items-center gap-2 text-muted-foreground mb-1">
                                <Send className="h-3.5 w-3.5" />
                                <span className="text-xs font-medium">Sent</span>
                            </div>
                            <div className="text-xl font-bold text-gray-900">{sentCount}</div>
                            <div className="text-[10px] text-muted-foreground">
                                of {totalRecipients}
                            </div>
                        </div>

                        <div className="flex flex-col p-2 rounded-lg bg-blue-50/30 group-hover:bg-blue-50/50 transition-colors">
                            <div className="flex items-center gap-2 text-blue-600/70 mb-1">
                                <Mail className="h-3.5 w-3.5" />
                                <span className="text-xs font-medium">Opened</span>
                            </div>
                            <div className="text-xl font-bold text-blue-700">{campaign.opened}</div>
                            <div className="text-[10px] text-blue-600/70 font-medium">
                                {campaign.open_rate}% rate
                            </div>
                        </div>

                        <div className="flex flex-col p-2 rounded-lg bg-purple-50/30 group-hover:bg-purple-50/50 transition-colors">
                            <div className="flex items-center gap-2 text-purple-600/70 mb-1">
                                <MousePointerClick className="h-3.5 w-3.5" />
                                <span className="text-xs font-medium">Clicked</span>
                            </div>
                            <div className="text-xl font-bold text-purple-700">{campaign.clicked}</div>
                            <div className="text-[10px] text-purple-600/70 font-medium">
                                {sentCount > 0
                                    ? ((campaign.clicked / sentCount) * 100).toFixed(1)
                                    : 0}% rate
                            </div>
                        </div>

                        <div className="flex flex-col p-2 rounded-lg bg-gray-50/50 group-hover:bg-gray-50 transition-colors">
                            <div className="flex items-center gap-2 text-muted-foreground mb-1">
                                <Users className="h-3.5 w-3.5" />
                                <span className="text-xs font-medium">Replied</span>
                            </div>
                            <div className="text-xl font-bold text-gray-900">0</div>
                            <div className="text-[10px] text-muted-foreground">0% rate</div>
                        </div>

                        <div className="flex flex-col p-2 rounded-lg bg-red-50/30 group-hover:bg-red-50/50 transition-colors">
                            <div className="flex items-center gap-2 text-red-600/70 mb-1">
                                <AlertCircle className="h-3.5 w-3.5" />
                                <span className="text-xs font-medium">Bounced</span>
                            </div>
                            <div className="text-xl font-bold text-red-700">
                                {campaign.bounced}
                            </div>
                            <div className="text-[10px] text-red-600/70 font-medium">
                                {campaign.bounce_rate}% rate
                            </div>
                        </div>
                    </div>
                </CardContent>
            </Card>
        </Link>
    );
}
