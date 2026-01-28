"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { CalendarDays, ChevronDown } from "lucide-react";

const presets = [
    { label: "Bugün", value: "today" },
    { label: "Dün", value: "yesterday" },
    { label: "Son 7 Gün", value: "last_7_days" },
    { label: "Son 14 Gün", value: "last_14_days" },
    { label: "Son 30 Gün", value: "last_30_days" },
    { label: "Bu Ay", value: "this_month" },
    { label: "Geçen Ay", value: "last_month" },
];

export function DateRangePicker() {
    const [selected, setSelected] = useState(presets[2]); // Default: Son 7 Gün
    const [isOpen, setIsOpen] = useState(false);

    return (
        <div className="relative">
            <Button
                variant="outline"
                className="border-primary-light hover:bg-cream flex items-center gap-2"
                onClick={() => setIsOpen(!isOpen)}
            >
                <CalendarDays size={16} />
                <span>{selected.label}</span>
                <ChevronDown size={16} />
            </Button>

            {isOpen && (
                <>
                    <div
                        className="fixed inset-0 z-40"
                        onClick={() => setIsOpen(false)}
                    />
                    <div className="absolute right-0 top-full mt-2 z-50 bg-white rounded-lg border border-primary-light shadow-lg py-2 min-w-[180px]">
                        {presets.map((preset) => (
                            <button
                                key={preset.value}
                                className={`w-full px-4 py-2 text-left text-sm hover:bg-cream transition-colors ${selected.value === preset.value
                                        ? "bg-primary text-white hover:bg-primary"
                                        : ""
                                    }`}
                                onClick={() => {
                                    setSelected(preset);
                                    setIsOpen(false);
                                }}
                            >
                                {preset.label}
                            </button>
                        ))}
                    </div>
                </>
            )}
        </div>
    );
}
