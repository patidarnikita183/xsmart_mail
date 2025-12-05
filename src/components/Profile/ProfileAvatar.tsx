"use client";

import { useState } from "react";
import { useUser } from "@clerk/nextjs";
import { Camera, Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { toast } from "@/components/ui/use-toast";
import { ImageCropDialog } from "./ImageCropDialog";

const PREDEFINED_AVATARS = [
    "/avatars/avatar-1.png",
    "/avatars/avatar-2.png",
    "/avatars/avatar-3.png",
    "/avatars/avatar-4.png",
    "/avatars/avatar-5.png",
    "/avatars/avatar-6.png",
];

export function ProfileAvatar() {
    const { user } = useUser();
    const [selectedAvatar, setSelectedAvatar] = useState<string | null>(null);
    const [isUploading, setIsUploading] = useState(false);
    const [open, setOpen] = useState(false);

    // Crop dialog state
    const [cropDialogOpen, setCropDialogOpen] = useState(false);
    const [imageToCrop, setImageToCrop] = useState<string | null>(null);

    const currentAvatar = user?.imageUrl || "";
    const userInitials = user?.firstName?.[0] + (user?.lastName?.[0] || "");

    const handleAvatarSelect = async (avatarUrl: string) => {
        setSelectedAvatar(avatarUrl);
    };

    const handleConfirmSelection = async () => {
        if (!selectedAvatar || !user) return;

        try {
            setIsUploading(true);
            // Fetch the avatar image and convert to blob
            const response = await fetch(selectedAvatar);
            const blob = await response.blob();
            const file = new File([blob], "avatar.png", { type: "image/png" });

            await user.setProfileImage({ file });
            await user.reload(); // Refresh user data to update avatar everywhere

            toast({
                title: "Success",
                description: "Avatar updated successfully!",
            });
            setOpen(false);
            setSelectedAvatar(null);
        } catch (error) {
            console.error("Error updating avatar:", error);
            toast({
                title: "Error",
                description: "Failed to update avatar. Please try again.",
                variant: "destructive",
            });
        } finally {
            setIsUploading(false);
        }
    };

    const handleFileSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        if (!file) return;

        // Validate file size (max 10MB before cropping)
        if (file.size > 10 * 1024 * 1024) {
            toast({
                title: "Error",
                description: "Image size must be less than 10MB",
                variant: "destructive",
            });
            return;
        }

        // Validate file type
        if (!file.type.startsWith("image/")) {
            toast({
                title: "Error",
                description: "Please upload an image file",
                variant: "destructive",
            });
            return;
        }

        // Read file as data URL for cropping
        const reader = new FileReader();
        reader.onload = () => {
            setImageToCrop(reader.result as string);
            setCropDialogOpen(true);
        };
        reader.readAsDataURL(file);

        // Reset input
        event.target.value = "";
    };

    const handleCropComplete = async (croppedImageBlob: Blob) => {
        if (!user) return;

        try {
            setIsUploading(true);
            const file = new File([croppedImageBlob], "avatar.png", { type: "image/png" });

            await user.setProfileImage({ file });
            await user.reload(); // Refresh user data to update avatar everywhere

            toast({
                title: "Success",
                description: "Avatar uploaded successfully!",
            });
        } catch (error) {
            console.error("Error uploading avatar:", error);
            toast({
                title: "Error",
                description: "Failed to upload avatar. Please try again.",
                variant: "destructive",
            });
        } finally {
            setIsUploading(false);
            setImageToCrop(null);
        }
    };

    return (
        <div className="flex flex-col items-center gap-4">
            <div className="relative group">
                <Avatar className="h-32 w-32 border-4 border-white shadow-xl">
                    <AvatarImage src={currentAvatar} alt={user?.fullName || "User"} />
                    <AvatarFallback className="text-3xl font-semibold bg-gradient-to-br from-blue-500 to-purple-600 text-white">
                        {userInitials}
                    </AvatarFallback>
                </Avatar>
                <label
                    htmlFor="avatar-upload"
                    className="absolute bottom-0 right-0 p-2 bg-white rounded-full shadow-lg cursor-pointer hover:bg-gray-50 transition-colors border-2 border-gray-200"
                >
                    <Camera className="h-5 w-5 text-gray-600" />
                    <input
                        id="avatar-upload"
                        type="file"
                        accept="image/*"
                        className="hidden"
                        onChange={handleFileSelect}
                        disabled={isUploading}
                    />
                </label>
            </div>

            <Dialog open={open} onOpenChange={setOpen}>
                <DialogTrigger asChild>
                    <Button variant="outline" disabled={isUploading}>
                        Choose from Gallery
                    </Button>
                </DialogTrigger>
                <DialogContent className="sm:max-w-md">
                    <DialogHeader>
                        <DialogTitle>Choose an Avatar</DialogTitle>
                    </DialogHeader>
                    <div className="grid grid-cols-3 gap-4 py-4">
                        {PREDEFINED_AVATARS.map((avatar, index) => (
                            <button
                                key={index}
                                onClick={() => handleAvatarSelect(avatar)}
                                className={`relative rounded-full overflow-hidden border-4 transition-all hover:scale-105 ${selectedAvatar === avatar
                                        ? "border-blue-500 shadow-lg"
                                        : "border-gray-200 hover:border-gray-300"
                                    }`}
                            >
                                <img
                                    src={avatar}
                                    alt={`Avatar ${index + 1}`}
                                    className="w-full h-full object-cover"
                                />
                                {selectedAvatar === avatar && (
                                    <div className="absolute inset-0 bg-blue-500/20 flex items-center justify-center">
                                        <Check className="h-8 w-8 text-blue-600" />
                                    </div>
                                )}
                            </button>
                        ))}
                    </div>
                    <div className="flex justify-end gap-2">
                        <Button variant="outline" onClick={() => setOpen(false)}>
                            Cancel
                        </Button>
                        <Button
                            onClick={handleConfirmSelection}
                            disabled={!selectedAvatar || isUploading}
                        >
                            {isUploading ? "Updating..." : "Confirm"}
                        </Button>
                    </div>
                </DialogContent>
            </Dialog>

            {/* Image Crop Dialog */}
            {imageToCrop && (
                <ImageCropDialog
                    open={cropDialogOpen}
                    onOpenChange={setCropDialogOpen}
                    imageSrc={imageToCrop}
                    onCropComplete={handleCropComplete}
                />
            )}

            {isUploading && (
                <p className="text-sm text-muted-foreground">Updating avatar...</p>
            )}
        </div>
    );
}
