"use client";

export const dynamic = 'force-dynamic';

import { useState, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ChevronRight, ChevronLeft, Check } from "lucide-react";
import CsvUploadStep from "@/components/Campaigns/Wizard/CsvUploadStep";
import FieldMappingStep from "@/components/Campaigns/Wizard/FieldMappingStep";
import EmailComposerStep from "@/components/Campaigns/Wizard/EmailComposerStep";
import ScheduleStep from "@/components/Campaigns/Wizard/ScheduleStep";
import ReviewStep from "@/components/Campaigns/Wizard/ReviewStep";
import { useCreateCampaign, useEmailAccounts, useCampaigns } from "@/api/hooks";
import { toast } from "sonner";

export type WizardData = {
    csvFile: File | null;
    parsedData: any[];
    columns: string[];
    mapping: Record<string, string>; // internalField -> csvColumn
    subject: string;
    body: string;
    start_time: string; // ISO datetime string
    duration: number; // Total duration in hours
    send_interval: number; // Minutes between each email send
};

const STEPS = [
    { id: 1, title: "Upload CSV" },
    { id: 2, title: "Map Fields" },
    { id: 3, title: "Compose Email" },
    { id: 4, title: "Schedule" },
    { id: 5, title: "Review & Send" },
];

export default function NewCampaignPage() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const { data: accountsData } = useEmailAccounts();
    const [currentStep, setCurrentStep] = useState(1);
    const [selectedMailboxId, setSelectedMailboxId] = useState<string | null>(null);
    const [data, setData] = useState<WizardData>({
        csvFile: null,
        parsedData: [],
        columns: [],
        mapping: {
            email: "",
            firstName: "",
            lastName: "",
        },
        subject: "",
        body: "",
        start_time: new Date().toISOString().slice(0, 16), // Default to now (datetime-local format)
        duration: 24, // Default 24 hours
        send_interval: 5, // Default 5 minutes between emails
    });

    const createCampaign = useCreateCampaign();
    const { data: campaignsData } = useCampaigns();

    // Get mailbox_id from URL params if present
    useEffect(() => {
        const mailboxId = searchParams.get('mailbox_id');
        if (mailboxId) {
            setSelectedMailboxId(mailboxId);
        } else if (accountsData?.accounts) {
            // Default to primary mailbox if no mailbox_id in URL
            const primaryMailbox = accountsData.accounts.find(acc => acc.is_primary);
            if (primaryMailbox) {
                setSelectedMailboxId(primaryMailbox.id);
            }
        }
    }, [searchParams, accountsData]);

    const handleNext = () => {
        if (currentStep < STEPS.length) {
            setCurrentStep((prev) => prev + 1);
        } else {
            handleFinish();
        }
    };

    const handleBack = () => {
        if (currentStep > 1) {
            setCurrentStep((prev) => prev - 1);
        }
    };

    const handleFinish = async () => {
        try {
            // Check for active campaigns before creating new one
            const activeCampaigns = campaignsData?.campaigns?.filter((campaign: any) => {
                const now = new Date();
                if (campaign.start_time && campaign.duration) {
                    const startTime = new Date(campaign.start_time);
                    const endTime = new Date(startTime.getTime() + campaign.duration * 60 * 60 * 1000);
                    return now >= startTime && now <= endTime;
                }
                return false;
            }) || [];

            if (activeCampaigns.length > 0) {
                const proceed = window.confirm(
                    `You have ${activeCampaigns.length} active campaign(s) running.\n\n` +
                    `Starting a new campaign while others are active may cause:\n` +
                    `- Rate limiting from email providers\n` +
                    `- Overlapping email sends\n` +
                    `- Confusion in tracking\n\n` +
                    `Do you want to proceed anyway?`
                );
                if (!proceed) {
                    return;
                }
            }

            // Transform data for backend
            const recipients = data.parsedData
                .map((row) => {
                    const recipient: any = {};
                    // Map all fields based on user selection - include all mapped fields for template variables
                    Object.entries(data.mapping).forEach(([internalField, csvColumn]) => {
                        if (csvColumn && row[csvColumn]) {
                            // Map email field
                            if (internalField === 'email') {
                                recipient.email = String(row[csvColumn]).trim();
                            }
                            // Map firstName to name (for backward compatibility)
                            else if (internalField === 'firstName') {
                                recipient.name = String(row[csvColumn]).trim();
                                recipient.firstName = String(row[csvColumn]).trim(); // Also add as firstName for template
                            }
                            // Map all other fields directly
                            else {
                                recipient[internalField] = String(row[csvColumn]).trim();
                            }
                        }
                    });
                    // Fallback: if no name, use email prefix
                    if (!recipient.name && recipient.email) {
                        recipient.name = recipient.email.split('@')[0];
                    }
                    return recipient;
                })
                .filter((recipient) => recipient.email); // Filter out recipients without email

            const campaignPayload = {
                subject: data.subject,
                message: data.body,
                recipients: recipients,
                mailbox_id: selectedMailboxId || accountsData?.accounts?.find(acc => acc.is_primary)?.id,
                start_time: data.start_time ? new Date(data.start_time).toISOString() : new Date().toISOString(),
                duration: data.duration || 24, // Total duration in hours
                send_interval: data.send_interval || 5, // Minutes between each email
            };

            const response = await createCampaign.mutateAsync(campaignPayload);

            // Show success message and redirect immediately (campaign runs in background)
            toast.success("Campaign launched successfully! Running in background...", {
                duration: 3000,
            });

            // Redirect immediately - campaign runs in background
            router.push("/campaigns");

            // Show warning if there are active campaigns (after redirect)
            if (response?.warning) {
                setTimeout(() => {
                    toast.warning(response.warning, {
                        description: `You have ${response.active_campaigns?.length || 0} active campaign(s) running.`,
                        duration: 5000,
                    });
                }, 500);
            }
        } catch (error: any) {
            // Extract error message from response
            const errorMessage = error?.response?.data?.error || error?.response?.data?.details || error?.message || "Failed to create campaign";
            toast.error("Failed to create campaign", {
                description: errorMessage,
                duration: 5000,
            });
            console.error("Campaign creation error:", error);
            if (error?.response?.data) {
                console.error("Error details:", error.response.data);
            }
        }
    };

    const updateData = (updates: Partial<WizardData>) => {
        setData((prev) => ({ ...prev, ...updates }));
    };

    return (
        <div className="max-w-5xl mx-auto py-8">
            <div className="mb-10 text-center">
                <h1 className="text-4xl font-bold mb-3 bg-gradient-to-r from-gray-900 to-gray-600 bg-clip-text text-transparent">Create New Campaign</h1>
                <p className="text-muted-foreground text-lg">Follow the steps to launch your email campaign</p>
            </div>

            {/* Progress Steps */}
            <div className="mb-12 relative">
                <div className="absolute top-5 left-0 w-full h-1 bg-gray-100 rounded-full -z-10">
                    <div
                        className="h-full bg-blue-600 rounded-full transition-all duration-500 ease-in-out"
                        style={{ width: `${((currentStep - 1) / (STEPS.length - 1)) * 100}%` }}
                    />
                </div>
                <div className="flex justify-between w-full">
                    {STEPS.map((step) => (
                        <div key={step.id} className="flex flex-col items-center group">
                            <div
                                className={`w-10 h-10 rounded-full flex items-center justify-center border-2 mb-3 transition-all duration-300 shadow-sm ${currentStep >= step.id
                                    ? "border-blue-600 bg-blue-600 text-white scale-110 shadow-blue-200"
                                    : "border-gray-200 bg-white text-gray-400 group-hover:border-gray-300"
                                    }`}
                            >
                                {currentStep > step.id ? <Check className="w-5 h-5" /> : <span className="font-semibold">{step.id}</span>}
                            </div>
                            <span
                                className={`text-sm font-medium transition-colors duration-300 ${currentStep >= step.id ? "text-blue-900" : "text-gray-400"
                                    }`}
                            >
                                {step.title}
                            </span>
                        </div>
                    ))}
                </div>
            </div>

            {/* Step Content */}
            <Card className="min-h-[500px] flex flex-col shadow-lg border-0 bg-white/80 backdrop-blur-sm">
                <CardContent className="flex-1 p-6">
                    {currentStep === 1 && (
                        <CsvUploadStep
                            data={data}
                            updateData={updateData}
                        />
                    )}
                    {currentStep === 2 && (
                        <FieldMappingStep
                            data={data}
                            updateData={updateData}
                        />
                    )}
                    {currentStep === 3 && (
                        <EmailComposerStep
                            data={data}
                            updateData={updateData}
                        />
                    )}
                    {currentStep === 4 && (
                        <ScheduleStep
                            data={data}
                            updateData={updateData}
                        />
                    )}
                    {currentStep === 5 && (
                        <ReviewStep
                            data={data}
                        />
                    )}
                </CardContent>

                {/* Navigation Buttons */}
                <div className="p-6 border-t flex justify-between bg-gray-50/50">
                    <Button
                        variant="outline"
                        onClick={handleBack}
                        disabled={currentStep === 1}
                    >
                        <ChevronLeft className="w-4 h-4 mr-2" />
                        Back
                    </Button>
                    <Button onClick={handleNext} disabled={createCampaign.isPending}>
                        {currentStep === STEPS.length ? (
                            createCampaign.isPending ? "Sending..." : "Launch Campaign"
                        ) : (
                            <>
                                Next
                                <ChevronRight className="w-4 h-4 ml-2" />
                            </>
                        )}
                    </Button>
                </div>
            </Card>
        </div>
    );
}
