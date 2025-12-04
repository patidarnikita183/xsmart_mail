"use client";

import { WizardData } from "@/app/(main)/campaigns/new/page";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Plus } from "lucide-react";

interface EmailComposerStepProps {
    data: WizardData;
    updateData: (data: Partial<WizardData>) => void;
}

export default function EmailComposerStep({ data, updateData }: EmailComposerStepProps) {
    const handleInsertVariable = (variable: string) => {
        const textArea = document.getElementById("email-body") as HTMLTextAreaElement;
        if (textArea) {
            const start = textArea.selectionStart;
            const end = textArea.selectionEnd;
            const text = data.body;
            const newText = text.substring(0, start) + `{{${variable}}}` + text.substring(end);
            updateData({ body: newText });

            // Restore focus and cursor position (next tick)
            setTimeout(() => {
                textArea.focus();
                textArea.setSelectionRange(start + variable.length + 4, start + variable.length + 4);
            }, 0);
        } else {
            updateData({ body: data.body + `{{${variable}}}` });
        }
    };

    const availableVariables = Object.entries(data.mapping)
        .filter(([_, col]) => col) // Only show mapped fields
        .map(([key]) => key);

    return (
        <div className="space-y-6 max-w-3xl mx-auto">
            <div className="text-center space-y-2">
                <h2 className="text-2xl font-semibold">Compose Email</h2>
                <p className="text-muted-foreground">
                    Create your email template using variables
                </p>
            </div>

            <div className="space-y-4">
                <div className="space-y-2">
                    <Label htmlFor="subject">Subject Line</Label>
                    <Input
                        id="subject"
                        placeholder="Enter email subject..."
                        value={data.subject}
                        onChange={(e) => updateData({ subject: e.target.value })}
                    />
                </div>

                <div className="space-y-2">
                    <div className="flex justify-between items-center">
                        <Label htmlFor="email-body">Email Body</Label>
                        <div className="flex gap-2">
                            {availableVariables.map((variable) => (
                                <Button
                                    key={variable}
                                    variant="outline"
                                    size="sm"
                                    onClick={() => handleInsertVariable(variable)}
                                    className="h-7 text-xs"
                                >
                                    <Plus className="w-3 h-3 mr-1" />
                                    {variable}
                                </Button>
                            ))}
                        </div>
                    </div>
                    <Textarea
                        id="email-body"
                        placeholder="Hi {{firstName}}, ..."
                        className="min-h-[300px] font-mono text-sm"
                        value={data.body}
                        onChange={(e) => updateData({ body: e.target.value })}
                    />
                </div>
            </div>

            <div className="bg-gray-50 p-4 rounded-lg border">
                <h4 className="text-sm font-medium mb-2 text-gray-700">Preview (First Recipient)</h4>
                <div className="bg-white p-4 rounded border shadow-sm space-y-3">
                    <div className="border-b pb-2">
                        <span className="text-gray-500 text-sm">Subject:</span>{" "}
                        <span className="font-medium">
                            {data.subject || "(No subject)"}
                        </span>
                    </div>
                    <div className="whitespace-pre-wrap text-sm text-gray-800">
                        {data.body
                            ? data.body.replace(/{{(\w+)}}/g, (match, key) => {
                                const colName = data.mapping[key];
                                if (colName && data.parsedData.length > 0) {
                                    return data.parsedData[0][colName] || match;
                                }
                                return match;
                            })
                            : "(No content)"}
                    </div>
                </div>
            </div>
        </div>
    );
}
