"use client";

import { WizardData } from "@/app/(main)/campaigns/new/page";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Calendar, Clock } from "lucide-react";
import DurationWarning from "@/components/Campaigns/DurationWarning";

interface ScheduleStepProps {
    data: WizardData;
    updateData: (updates: Partial<WizardData>) => void;
}

export default function ScheduleStep({ data, updateData }: ScheduleStepProps) {
    const handleStartTimeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        updateData({ start_time: e.target.value });
    };

    const handleDurationChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const duration = parseInt(e.target.value) || 24;
        updateData({ duration });
    };

    const handleSendIntervalChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const send_interval = parseInt(e.target.value) || 5;
        updateData({ send_interval });
    };

    // Calculate end time
    const startTime = data.start_time ? new Date(data.start_time) : new Date();
    const endTime = new Date(startTime.getTime() + (data.duration || 24) * 60 * 60 * 1000);

    return (
        <div className="space-y-6 max-w-3xl mx-auto">
            <div className="text-center space-y-2">
                <h2 className="text-2xl font-semibold">Schedule Campaign</h2>
                <p className="text-muted-foreground">
                    Set when your campaign should start and how long it should run
                </p>
            </div>

            <div className="grid gap-6 md:grid-cols-3">
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <Calendar className="h-5 w-5" />
                            Start Time
                        </CardTitle>
                        <CardDescription>
                            When should the campaign begin?
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="space-y-2">
                            <Label htmlFor="start_time">Campaign Start Date & Time</Label>
                            <Input
                                id="start_time"
                                type="datetime-local"
                                value={data.start_time}
                                onChange={handleStartTimeChange}
                                min={new Date().toISOString().slice(0, 16)}
                            />
                            <p className="text-xs text-muted-foreground">
                                Campaign will start at: {startTime.toLocaleString()}
                            </p>
                        </div>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <Clock className="h-5 w-5" />
                            Campaign Duration
                        </CardTitle>
                        <CardDescription>
                            How long should the campaign run?
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="space-y-2">
                            <Label htmlFor="duration">Total Duration (hours)</Label>
                            <Input
                                id="duration"
                                type="number"
                                min="1"
                                max="720"
                                value={data.duration}
                                onChange={handleDurationChange}
                            />
                            <p className="text-xs text-muted-foreground">
                                Campaign will run for {data.duration} hour{data.duration !== 1 ? 's' : ''}
                            </p>
                        </div>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <Clock className="h-5 w-5" />
                            Send Interval
                        </CardTitle>
                        <CardDescription>
                            How often should emails be sent?
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="space-y-2">
                            <Label htmlFor="send_interval">Interval Between Emails (minutes)</Label>
                            <Input
                                id="send_interval"
                                type="number"
                                min="1"
                                max="1440"
                                value={data.send_interval || 5}
                                onChange={handleSendIntervalChange}
                            />
                            <p className="text-xs text-muted-foreground">
                                Emails will be sent every {data.send_interval || 5} minute{(data.send_interval || 5) !== 1 ? 's' : ''}
                            </p>
                        </div>
                    </CardContent>
                </Card>
            </div>

            <DurationWarning
                totalRecipients={data.parsedData?.length || 0}
                duration={data.duration || 24}
                sendInterval={data.send_interval || 5}
            />

            <Card className="bg-blue-50 dark:bg-blue-900/10 border-blue-200 dark:border-blue-800">
                <CardContent className="pt-6">
                    <div className="space-y-2">
                        <h3 className="font-semibold text-sm">Campaign Timeline</h3>
                        <div className="space-y-1 text-sm">
                            <div className="flex justify-between">
                                <span className="text-muted-foreground">Starts:</span>
                                <span className="font-medium">{startTime.toLocaleString()}</span>
                            </div>
                            <div className="flex justify-between">
                                <span className="text-muted-foreground">Ends:</span>
                                <span className="font-medium">{endTime.toLocaleString()}</span>
                            </div>
                            <div className="flex justify-between pt-2 border-t">
                                <span className="text-muted-foreground">Total Duration:</span>
                                <span className="font-medium">{data.duration} hour{data.duration !== 1 ? 's' : ''}</span>
                            </div>
                            <div className="flex justify-between pt-2 border-t">
                                <span className="text-muted-foreground">Send Interval:</span>
                                <span className="font-medium">Every {data.send_interval || 5} minute{(data.send_interval || 5) !== 1 ? 's' : ''}</span>
                            </div>
                        </div>
                    </div>
                </CardContent>
            </Card>

            <div className="bg-yellow-50 dark:bg-yellow-900/10 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4 text-sm">
                <p className="font-medium mb-1">Note:</p>
                <p className="text-muted-foreground">
                    The campaign will be active during the specified time period. Emails will be sent based on your sending schedule.
                </p>
            </div>
        </div>
    );
}

