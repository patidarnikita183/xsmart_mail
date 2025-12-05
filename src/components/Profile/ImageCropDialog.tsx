"use client";

import { useState, useCallback } from "react";
import Cropper from "react-easy-crop";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import { Loader2, ZoomIn } from "lucide-react";

interface ImageCropDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    imageSrc: string;
    onCropComplete: (croppedImageBlob: Blob) => void;
}

interface CroppedArea {
    x: number;
    y: number;
    width: number;
    height: number;
}

export function ImageCropDialog({ open, onOpenChange, imageSrc, onCropComplete }: ImageCropDialogProps) {
    const [crop, setCrop] = useState({ x: 0, y: 0 });
    const [zoom, setZoom] = useState(1);
    const [croppedAreaPixels, setCroppedAreaPixels] = useState<CroppedArea | null>(null);
    const [isProcessing, setIsProcessing] = useState(false);

    const onCropChange = useCallback((crop: { x: number; y: number }) => {
        setCrop(crop);
    }, []);

    const onZoomChange = useCallback((zoom: number) => {
        setZoom(zoom);
    }, []);

    const onCropCompleteCallback = useCallback(
        (croppedArea: any, croppedAreaPixels: CroppedArea) => {
            setCroppedAreaPixels(croppedAreaPixels);
        },
        []
    );

    const createImage = (url: string): Promise<HTMLImageElement> =>
        new Promise((resolve, reject) => {
            const image = new Image();
            image.addEventListener("load", () => resolve(image));
            image.addEventListener("error", (error) => reject(error));
            image.src = url;
        });

    const getCroppedImg = async (
        imageSrc: string,
        pixelCrop: CroppedArea
    ): Promise<Blob> => {
        const image = await createImage(imageSrc);
        const canvas = document.createElement("canvas");
        const ctx = canvas.getContext("2d");

        if (!ctx) {
            throw new Error("No 2d context");
        }

        // Set canvas size to desired output size (400x400 for avatars)
        const outputSize = 400;
        canvas.width = outputSize;
        canvas.height = outputSize;

        // Draw the cropped image
        ctx.drawImage(
            image,
            pixelCrop.x,
            pixelCrop.y,
            pixelCrop.width,
            pixelCrop.height,
            0,
            0,
            outputSize,
            outputSize
        );

        // Convert canvas to blob
        return new Promise((resolve, reject) => {
            canvas.toBlob(
                (blob) => {
                    if (blob) {
                        resolve(blob);
                    } else {
                        reject(new Error("Canvas is empty"));
                    }
                },
                "image/png",
                0.9 // Quality setting
            );
        });
    };

    const handleSave = async () => {
        if (!croppedAreaPixels) return;

        try {
            setIsProcessing(true);
            const croppedImageBlob = await getCroppedImg(imageSrc, croppedAreaPixels);
            onCropComplete(croppedImageBlob);
            onOpenChange(false);
        } catch (error) {
            console.error("Error cropping image:", error);
        } finally {
            setIsProcessing(false);
        }
    };

    const handleCancel = () => {
        onOpenChange(false);
        setCrop({ x: 0, y: 0 });
        setZoom(1);
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-[600px]">
                <DialogHeader>
                    <DialogTitle>Crop Your Profile Picture</DialogTitle>
                </DialogHeader>

                <div className="space-y-4">
                    {/* Crop Area */}
                    <div className="relative h-[400px] bg-gray-100 rounded-lg overflow-hidden">
                        <Cropper
                            image={imageSrc}
                            crop={crop}
                            zoom={zoom}
                            aspect={1}
                            cropShape="round"
                            showGrid={false}
                            onCropChange={onCropChange}
                            onZoomChange={onZoomChange}
                            onCropComplete={onCropCompleteCallback}
                        />
                    </div>

                    {/* Zoom Control */}
                    <div className="space-y-2">
                        <div className="flex items-center justify-between">
                            <label className="text-sm font-medium flex items-center gap-2">
                                <ZoomIn className="h-4 w-4" />
                                Zoom
                            </label>
                            <span className="text-sm text-muted-foreground">{zoom.toFixed(1)}x</span>
                        </div>
                        <Slider
                            value={[zoom]}
                            onValueChange={(value) => setZoom(value[0])}
                            min={1}
                            max={3}
                            step={0.1}
                            className="w-full"
                        />
                    </div>

                    <p className="text-xs text-muted-foreground text-center">
                        Drag to reposition • Scroll or use slider to zoom
                    </p>
                </div>

                <DialogFooter className="gap-2">
                    <Button variant="outline" onClick={handleCancel} disabled={isProcessing}>
                        Cancel
                    </Button>
                    <Button onClick={handleSave} disabled={isProcessing}>
                        {isProcessing ? (
                            <>
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                Processing...
                            </>
                        ) : (
                            "Save & Upload"
                        )}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
