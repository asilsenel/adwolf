import Image from "next/image";
import { cn } from "@/lib/utils";

interface PlatformIconProps {
    platform: "google_ads" | "meta_ads" | "amazon_ads" | "tiktok_ads";
    size?: number;
    className?: string;
}

const platformConfig = {
    google_ads: {
        label: "Google Ads",
        color: "#4285F4",
        initial: "G",
    },
    meta_ads: {
        label: "Meta Ads",
        color: "#0081FB",
        initial: "M",
    },
    amazon_ads: {
        label: "Amazon Ads",
        color: "#FF9900",
        initial: "A",
    },
    tiktok_ads: {
        label: "TikTok Ads",
        color: "#000000",
        initial: "T",
    },
};

export function PlatformIcon({ platform, size = 24, className }: PlatformIconProps) {
    const config = platformConfig[platform];

    return (
        <div
            className={cn(
                "rounded-lg flex items-center justify-center text-white font-bold",
                className
            )}
            style={{
                backgroundColor: config.color,
                width: size,
                height: size,
                fontSize: size * 0.5,
            }}
        >
            {config.initial}
        </div>
    );
}

export function getPlatformLabel(platform: string): string {
    return platformConfig[platform as keyof typeof platformConfig]?.label || platform;
}
