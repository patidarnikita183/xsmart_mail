"use client";

import { useState, useCallback } from "react";
// Fix: Removed unused react-dropzone import
import Papa from "papaparse";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Upload, FileSpreadsheet, AlertCircle } from "lucide-react";
import { WizardData } from "@/app/(main)/campaigns/new/page";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

interface CsvUploadStepProps {
    data: WizardData;
    updateData: (data: Partial<WizardData>) => void;
}

export default function CsvUploadStep({ data, updateData }: CsvUploadStepProps) {
    const [error, setError] = useState<string | null>(null);
    const [isDragging, setIsDragging] = useState(false);

    const handleFileUpload = (file: File) => {
        if (file.type !== "text/csv" && !file.name.endsWith(".csv")) {
            setError("Please upload a valid CSV file");
            return;
        }

        setError(null);
        Papa.parse(file, {
            header: true,
            skipEmptyLines: true,
            complete: (results) => {
                if (results.data.length === 0) {
                    setError("The CSV file is empty");
                    return;
                }

                // Filter out empty column names
                const columns = (results.meta.fields || []).filter((col) => col && col.trim() !== "");
                updateData({
                    csvFile: file,
                    parsedData: results.data,
                    columns: columns,
                });
            },
            error: (err) => {
                setError(`Error parsing CSV: ${err.message}`);
            },
        });
    };

    const onDragOver = (e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(true);
    };

    const onDragLeave = () => {
        setIsDragging(false);
    };

    const onDrop = (e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(false);
        const file = e.dataTransfer.files[0];
        if (file) handleFileUpload(file);
    };

    return (
        <div className="space-y-6">
            <div className="text-center space-y-2">
                <h2 className="text-2xl font-semibold">Import Contacts</h2>
                <p className="text-muted-foreground">Upload a CSV file containing your leads</p>
            </div>

            <div
                className={`border-2 border-dashed rounded-lg p-12 text-center transition-colors ${isDragging ? "border-primary bg-primary/5" : "border-gray-200 hover:border-primary/50"
                    }`}
                onDragOver={onDragOver}
                onDragLeave={onDragLeave}
                onDrop={onDrop}
            >
                <div className="flex flex-col items-center gap-4">
                    <div className="p-4 bg-primary/10 rounded-full">
                        <Upload className="w-8 h-8 text-primary" />
                    </div>
                    <div>
                        <p className="text-lg font-medium">Click to upload or drag and drop</p>
                        <p className="text-sm text-muted-foreground mt-1">CSV files only (max 5MB)</p>
                    </div>
                    <input
                        type="file"
                        accept=".csv"
                        className="hidden"
                        id="csv-upload"
                        onChange={(e) => {
                            const file = e.target.files?.[0];
                            if (file) handleFileUpload(file);
                        }}
                    />
                    <Button variant="outline" onClick={() => document.getElementById("csv-upload")?.click()}>
                        Select File
                    </Button>
                </div>
            </div>

            {error && (
                <Alert variant="destructive">
                    <AlertCircle className="h-4 w-4" />
                    <AlertTitle>Error</AlertTitle>
                    <AlertDescription>{error}</AlertDescription>
                </Alert>
            )}

            {data.csvFile && !error && (
                <div className="space-y-4">
                    <div className="flex items-center gap-3 p-4 border rounded-lg bg-green-50 border-green-100">
                        <FileSpreadsheet className="w-6 h-6 text-green-600" />
                        <div className="flex-1">
                            <p className="font-medium text-green-900">{data.csvFile.name}</p>
                            <p className="text-sm text-green-700">
                                {data.parsedData.length} contacts found • {data.columns.length} columns
                            </p>
                        </div>
                        <Button
                            variant="ghost"
                            size="sm"
                            className="text-green-700 hover:text-green-800 hover:bg-green-100"
                            onClick={() => updateData({ csvFile: null, parsedData: [], columns: [] })}
                        >
                            Remove
                        </Button>
                    </div>

                    <div className="border rounded-lg overflow-hidden">
                        <div className="bg-gray-50 px-4 py-2 border-b text-sm font-medium text-gray-500">
                            Preview (First 5 rows)
                        </div>
                        <div className="overflow-x-auto">
                            <table className="w-full text-sm text-left">
                                <thead className="bg-gray-50 text-gray-700">
                                    <tr>
                                        {data.columns.map((col) => (
                                            <th key={col} className="px-4 py-2 font-medium whitespace-nowrap">
                                                {col}
                                            </th>
                                        ))}
                                    </tr>
                                </thead>
                                <tbody className="divide-y">
                                    {data.parsedData.slice(0, 5).map((row, i) => (
                                        <tr key={i} className="bg-white">
                                            {data.columns.map((col) => (
                                                <td key={col} className="px-4 py-2 whitespace-nowrap text-gray-600">
                                                    {row[col]}
                                                </td>
                                            ))}
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
