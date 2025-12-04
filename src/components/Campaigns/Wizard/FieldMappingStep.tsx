"use client";

import { useEffect } from "react";
import { WizardData } from "@/app/(main)/campaigns/new/page";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { ArrowRight } from "lucide-react";

interface FieldMappingStepProps {
    data: WizardData;
    updateData: (data: Partial<WizardData>) => void;
}

const REQUIRED_FIELDS = [
    { key: "email", label: "Email Address", required: true },
    { key: "firstName", label: "First Name", required: false },
    { key: "lastName", label: "Last Name", required: false },
];

export default function FieldMappingStep({ data, updateData }: FieldMappingStepProps) {
    // Auto-map fields on mount
    useEffect(() => {
        const newMapping = { ...data.mapping };
        let hasChanges = false;

        REQUIRED_FIELDS.forEach((field) => {
            if (!newMapping[field.key]) {
                // Try to find a matching column (case-insensitive)
                const match = data.columns.find(
                    (col) => col.toLowerCase().replace(/[^a-z0-9]/g, "") === field.key.toLowerCase()
                );
                if (match) {
                    newMapping[field.key] = match;
                    hasChanges = true;
                }
            }
        });

        if (hasChanges) {
            updateData({ mapping: newMapping });
        }
    }, [data.columns, data.mapping, updateData]);

    const handleMappingChange = (fieldKey: string, value: string) => {
        updateData({
            mapping: {
                ...data.mapping,
                [fieldKey]: value,
            },
        });
    };

    return (
        <div className="space-y-6 max-w-2xl mx-auto">
            <div className="text-center space-y-2">
                <h2 className="text-2xl font-semibold">Map Fields</h2>
                <p className="text-muted-foreground">
                    Match your CSV columns to the contact fields
                </p>
            </div>

            <div className="bg-white border rounded-lg divide-y">
                {REQUIRED_FIELDS.map((field) => (
                    <div key={field.key} className="p-4 flex items-center gap-4">
                        <div className="w-1/3">
                            <Label className="text-base font-medium">
                                {field.label}
                                {field.required && <span className="text-red-500 ml-1">*</span>}
                            </Label>
                        </div>

                        <ArrowRight className="w-5 h-5 text-muted-foreground" />

                        <div className="flex-1">
                            <Select
                                value={data.mapping[field.key] || ""}
                                onValueChange={(value) => handleMappingChange(field.key, value)}
                            >
                                <SelectTrigger className={!data.mapping[field.key] && field.required ? "border-red-300 bg-red-50" : ""}>
                                    <SelectValue placeholder="Select column..." />
                                </SelectTrigger>
                                <SelectContent>
                                    {data.columns
                                        .filter((col) => col && col.trim() !== "") // Filter out empty columns
                                        .map((col) => (
                                            <SelectItem key={col} value={col}>
                                                {col}
                                            </SelectItem>
                                        ))}
                                </SelectContent>
                            </Select>
                        </div>
                    </div>
                ))}
            </div>

            <div className="bg-blue-50 p-4 rounded-lg text-sm text-blue-800">
                <p className="font-medium mb-1">Tip:</p>
                <p>
                    Mapped fields will be available as variables in your email template.
                    For example, you can use <code>{"{{firstName}}"}</code> to insert the contact's first name.
                </p>
            </div>
        </div>
    );
}
