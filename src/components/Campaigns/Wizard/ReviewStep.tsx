"use client";

import { WizardData } from "@/app/(main)/campaigns/new/page";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Users, Mail, CheckCircle2, Calendar, Clock } from "lucide-react";

interface ReviewStepProps {
    data: WizardData;
}

export default function ReviewStep({ data }: ReviewStepProps) {
    const recipientCount = data.parsedData.length;
    const mappedFieldsCount = Object.values(data.mapping).filter(Boolean).length;

    return (
        <div className="space-y-6 max-w-3xl mx-auto">
            <div className="text-center space-y-2">
                <h2 className="text-2xl font-semibold">Review Campaign</h2>
                <p className="text-muted-foreground">
                    Double check everything before launching
                </p>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Total Recipients</CardTitle>
                        <Users className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{recipientCount}</div>
                        <p className="text-xs text-muted-foreground">
                            Contacts from CSV
                        </p>
                    </CardContent>
                </Card>
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Mapped Fields</CardTitle>
                        <CheckCircle2 className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{mappedFieldsCount}</div>
                        <p className="text-xs text-muted-foreground">
                            Columns mapped successfully
                        </p>
                    </CardContent>
                </Card>
            </div>

            <div className="bg-white border rounded-lg overflow-hidden">
                <div className="bg-gray-50 px-4 py-3 border-b flex items-center gap-2">
                    <Mail className="w-4 h-4 text-gray-500" />
                    <span className="font-medium text-sm text-gray-700">Email Preview</span>
                </div>
                <div className="p-6 space-y-4">
                    <div>
                        <span className="text-sm font-medium text-gray-500 block mb-1">Subject</span>
                        <div className="text-lg font-medium">{data.subject || "(No subject)"}</div>
                    </div>
                    <div className="border-t pt-4">
                        <span className="text-sm font-medium text-gray-500 block mb-2">Body</span>
                        <div className="whitespace-pre-wrap text-gray-800 font-mono text-sm">
                            {data.body || "(No content)"}
                        </div>
                    </div>
                </div>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Start Time</CardTitle>
                        <Calendar className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-lg font-bold">
                            {data.start_time ? new Date(data.start_time).toLocaleString() : 'Immediately'}
                        </div>
                        <p className="text-xs text-muted-foreground">
                            Campaign start date & time
                        </p>
                    </CardContent>
                </Card>
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Duration</CardTitle>
                        <Clock className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-lg font-bold">{data.duration || 24} hours</div>
                        <p className="text-xs text-muted-foreground">
                            {data.start_time && (() => {
                                const startTime = new Date(data.start_time);
                                const endTime = new Date(startTime.getTime() + (data.duration || 24) * 60 * 60 * 1000);
                                return `Ends: ${endTime.toLocaleString()}`;
                            })()}
                        </p>
                    </CardContent>
                </Card>
            </div>

            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 text-sm text-yellow-800">
                <p className="font-medium mb-1">Ready to launch?</p>
                <p>
                    Clicking "Launch Campaign" will schedule emails for all {recipientCount} recipients.
                    {data.start_time && new Date(data.start_time) > new Date() && (
                        <span className="block mt-1">
                            Campaign will start on {new Date(data.start_time).toLocaleString()}.
                        </span>
                    )}
                    Make sure your email account limits are sufficient.
                </p>
            </div>
        </div>
    );
}
