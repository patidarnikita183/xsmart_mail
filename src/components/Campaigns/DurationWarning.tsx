import React from 'react';
import { AlertTriangle, Clock } from 'lucide-react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';

interface DurationWarningProps {
    totalRecipients: number;
    duration: number; // in hours
    sendInterval: number; // in minutes
}

export default function DurationWarning({ totalRecipients, duration, sendInterval }: DurationWarningProps) {
    // Calculate time needed
    // (recipients - 1) * interval because the first email is sent at 0
    const minutesNeeded = (totalRecipients - 1) * sendInterval;
    const hoursNeeded = minutesNeeded / 60;

    // Add a small buffer (e.g., 5 minutes) for processing time
    const isInsufficient = hoursNeeded > duration;

    if (!isInsufficient) return null;

    return (
        <Alert variant="destructive" className="mt-4">
            <AlertTriangle className="h-4 w-4" />
            <AlertTitle>Duration Warning</AlertTitle>
            <AlertDescription>
                <div className="space-y-2">
                    <p>
                        The selected duration is too short for {totalRecipients} recipients with a {sendInterval}-minute interval.
                    </p>
                    <div className="flex items-center gap-2 text-sm font-medium">
                        <Clock className="h-4 w-4" />
                        <span>
                            Minimum required duration: {Math.ceil(hoursNeeded * 10) / 10} hours
                        </span>
                    </div>
                    <p className="text-xs opacity-90">
                        Emails scheduled after the {duration}-hour mark will not be sent.
                    </p>
                </div>
            </AlertDescription>
        </Alert>
    );
}
