"use client"

import * as React from "react"
import { Check, ChevronsUpDown, Target } from "lucide-react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import {
    Command,
    CommandEmpty,
    CommandGroup,
    CommandInput,
    CommandItem,
    CommandList,
} from "@/components/ui/command"
import {
    Popover,
    PopoverContent,
    PopoverTrigger,
} from "@/components/ui/popover"

interface Campaign {
    id: string;
    platform_campaign_id: string;
    name: string;
    status: string;
    campaign_type?: string;
}

interface CampaignSelectorProps {
    campaigns: Campaign[]
    selectedCampaignId: string
    onSelect: (campaignId: string) => void
}

export function CampaignSelector({ campaigns, selectedCampaignId, onSelect }: CampaignSelectorProps) {
    const [open, setOpen] = React.useState(false)

    const selectedCampaign = campaigns.find((c) => c.id === selectedCampaignId)

    // Sort campaigns by name
    const sortedCampaigns = [...campaigns].sort((a, b) => {
        return a.name.localeCompare(b.name)
    })

    return (
        <Popover open={open} onOpenChange={setOpen}>
            <PopoverTrigger asChild>
                <Button
                    variant="outline"
                    role="combobox"
                    aria-expanded={open}
                    className="w-[280px] justify-between h-9 px-3"
                >
                    <div className="flex items-center gap-2 truncate">
                        <Target className="mr-0 h-4 w-4 shrink-0 opacity-50" />
                        {selectedCampaignId === "all" ? (
                            "Tüm Kampanyalar"
                        ) : (
                            <span className="truncate">
                                {selectedCampaign?.name || "Kampanya Seçin..."}
                            </span>
                        )}
                    </div>
                    <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                </Button>
            </PopoverTrigger>
            <PopoverContent className="w-[280px] p-0">
                <Command>
                    <CommandInput placeholder="Kampanya ara..." />
                    <CommandList>
                        <CommandEmpty>Kampanya bulunamadı.</CommandEmpty>
                        <CommandGroup>
                            <CommandItem
                                value="all"
                                onSelect={() => {
                                    onSelect("all")
                                    setOpen(false)
                                }}
                            >
                                <Check
                                    className={cn(
                                        "mr-2 h-4 w-4",
                                        selectedCampaignId === "all" ? "opacity-100" : "opacity-0"
                                    )}
                                />
                                Tüm Kampanyalar
                            </CommandItem>
                            {sortedCampaigns.map((campaign) => (
                                <CommandItem
                                    key={campaign.id}
                                    value={campaign.name}
                                    onSelect={() => {
                                        onSelect(campaign.id)
                                        setOpen(false)
                                    }}
                                >
                                    <Check
                                        className={cn(
                                            "mr-2 h-4 w-4",
                                            selectedCampaignId === campaign.id ? "opacity-100" : "opacity-0"
                                        )}
                                    />
                                    <span className="truncate">{campaign.name}</span>
                                </CommandItem>
                            ))}
                        </CommandGroup>
                    </CommandList>
                </Command>
            </PopoverContent>
        </Popover>
    )
}
