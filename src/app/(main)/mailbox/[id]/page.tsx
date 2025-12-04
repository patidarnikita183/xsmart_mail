"use client";

import { useParams, useRouter } from "next/navigation";
import { useEmailAccount, useMailboxCampaigns } from "@/api/hooks";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Mail, ArrowLeft, Send, CheckCircle2, AlertCircle, Loader2 } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

export default function MailboxPage() {
    const params = useParams();
    const router = useRouter();
    const accountId = params.id as string;
    
    const { data: account, isLoading: accountLoading } = useEmailAccount(accountId);
    const { data: campaigns, isLoading: campaignsLoading } = useMailboxCampaigns(accountId);
    
    if (accountLoading) {
        return (
            <div className="space-y-6">
                <Skeleton className="h-8 w-48" />
                <Skeleton className="h-64" />
            </div>
        );
    }
    
    if (!account) {
        return (
            <div className="flex flex-col items-center justify-center h-[400px] gap-4">
                <AlertCircle className="h-12 w-12 text-destructive" />
                <p className="text-muted-foreground">Mailbox not found</p>
                <Button variant="outline" onClick={() => router.push('/email-accounts')}>
                    <ArrowLeft className="mr-2 h-4 w-4" />
                    Back to Mailboxes
                </Button>
            </div>
        );
    }
    
    return (
        <div className="space-y-6">
            <div className="flex items-center gap-4">
                <Button variant="ghost" onClick={() => router.push('/email-accounts')}>
                    <ArrowLeft className="h-4 w-4 mr-2" />
                    Back to Mailboxes
                </Button>
                <div>
                    <h1 className="text-2xl font-bold">{account.email}</h1>
                    <p className="text-muted-foreground">Mailbox Details & Campaigns</p>
                </div>
            </div>
            
            <Card>
                <CardHeader>
                    <CardTitle>Mailbox Information</CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="space-y-4">
                        <div className="flex items-center justify-between">
                            <div className="flex items-center gap-3">
                                <div className={`p-2 rounded-lg ${account.is_primary ? 'bg-blue-100 dark:bg-blue-900/30' : 'bg-primary/10'}`}>
                                    <Mail className={`h-5 w-5 ${account.is_primary ? 'text-blue-600 dark:text-blue-400' : 'text-primary'}`} />
                                </div>
                                <div>
                                    <p className="font-medium">{account.provider === 'outlook' ? 'Outlook' : 'Gmail'}</p>
                                    <p className="text-sm text-muted-foreground">{account.email}</p>
                                </div>
                            </div>
                            <div className="flex items-center gap-2">
                                <Badge
                                    variant={account.status === 'active' ? 'default' : 'secondary'}
                                    className={
                                        account.status === 'active'
                                            ? 'bg-green-500'
                                            : account.status === 'error'
                                                ? 'bg-red-500'
                                                : ''
                                    }
                                >
                                    {account.status === 'active' && <CheckCircle2 className="mr-1 h-3 w-3" />}
                                    {account.status === 'error' && <AlertCircle className="mr-1 h-3 w-3" />}
                                    {account.status}
                                </Badge>
                                {account.is_primary && (
                                    <Badge variant="default" className="bg-blue-600 text-white">
                                        <CheckCircle2 className="mr-1 h-3 w-3" />
                                        Primary
                                    </Badge>
                                )}
                            </div>
                        </div>
                        
                        {account.is_primary && (
                            <div className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-md border border-blue-200 dark:border-blue-800">
                                <p className="text-sm font-medium text-blue-700 dark:text-blue-300">
                                    ✓ This is your primary mailbox. Campaigns will be sent from this account by default.
                                </p>
                            </div>
                        )}
                        
                        <div className="text-sm text-muted-foreground">
                            <p>Last used: {new Date(account.last_used).toLocaleDateString()}</p>
                            <p>Connected: {new Date(account.created_at).toLocaleDateString()}</p>
                        </div>
                    </div>
                </CardContent>
            </Card>
            
            <Card>
                <CardHeader>
                    <div className="flex items-center justify-between">
                        <CardTitle>Campaigns from this Mailbox</CardTitle>
                        <Button onClick={() => router.push(`/campaigns/new?mailbox_id=${accountId}`)}>
                            <Send className="h-4 w-4 mr-2" />
                            Send Campaign
                        </Button>
                    </div>
                </CardHeader>
                <CardContent>
                    {campaignsLoading ? (
                        <div className="space-y-2">
                            <Skeleton className="h-12 w-full" />
                            <Skeleton className="h-12 w-full" />
                            <Skeleton className="h-12 w-full" />
                        </div>
                    ) : campaigns && campaigns.length > 0 ? (
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead>Subject</TableHead>
                                    <TableHead>Sent</TableHead>
                                    <TableHead>Opened</TableHead>
                                    <TableHead>Clicked</TableHead>
                                    <TableHead>Bounced</TableHead>
                                    <TableHead>Date</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {campaigns.map((campaign: any) => (
                                    <TableRow 
                                        key={campaign.campaign_id}
                                        className="cursor-pointer"
                                        onClick={() => router.push(`/campaigns/${campaign.campaign_id}`)}
                                    >
                                        <TableCell className="font-medium">{campaign.subject || 'No Subject'}</TableCell>
                                        <TableCell>{campaign.successfully_sent || 0}</TableCell>
                                        <TableCell>{campaign.opened || 0}</TableCell>
                                        <TableCell>{campaign.clicked || 0}</TableCell>
                                        <TableCell>
                                            <Badge variant={campaign.bounced > 0 ? 'destructive' : 'secondary'}>
                                                {campaign.bounced || 0}
                                            </Badge>
                                        </TableCell>
                                        <TableCell>
                                            {new Date(campaign.created_at).toLocaleDateString()}
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    ) : (
                        <div className="flex flex-col items-center justify-center py-12">
                            <Mail className="h-12 w-12 text-muted-foreground mb-4" />
                            <p className="text-muted-foreground mb-4">No campaigns sent from this mailbox yet</p>
                            <Button onClick={() => router.push(`/campaigns/new?mailbox_id=${accountId}`)}>
                                <Send className="h-4 w-4 mr-2" />
                                Send Your First Campaign
                            </Button>
                        </div>
                    )}
                </CardContent>
            </Card>
        </div>
    );
}

