"use client";

import { useState, useRef, useEffect } from "react";
import { Calendar, ChevronLeft, ChevronRight } from "lucide-react";
import { format, startOfMonth, endOfMonth, eachDayOfInterval, isSameMonth, isSameDay, isAfter, isBefore, subDays, subMonths, startOfWeek, endOfWeek, addMonths } from "date-fns";
import { tr } from "date-fns/locale";

interface DateRangePickerProps {
    startDate: Date;
    endDate: Date;
    onChange: (start: Date, end: Date) => void;
}

// Preset options
const PRESETS = [
    { label: "Son 7 Gün", getValue: () => ({ start: subDays(new Date(), 7), end: new Date() }) },
    { label: "Son 14 Gün", getValue: () => ({ start: subDays(new Date(), 14), end: new Date() }) },
    { label: "Son 30 Gün", getValue: () => ({ start: subDays(new Date(), 30), end: new Date() }) },
    { label: "Son 90 Gün", getValue: () => ({ start: subDays(new Date(), 90), end: new Date() }) },
    { label: "Bu Ay", getValue: () => ({ start: startOfMonth(new Date()), end: new Date() }) },
    { label: "Geçen Ay", getValue: () => ({ start: startOfMonth(subMonths(new Date(), 1)), end: endOfMonth(subMonths(new Date(), 1)) }) },
];

export function DateRangePicker({ startDate, endDate, onChange }: DateRangePickerProps) {
    const [isOpen, setIsOpen] = useState(false);
    const [currentMonth, setCurrentMonth] = useState(startOfMonth(endDate));
    const [selecting, setSelecting] = useState<"start" | "end" | null>(null);
    const [tempStart, setTempStart] = useState<Date | null>(startDate);
    const [tempEnd, setTempEnd] = useState<Date | null>(endDate);
    const containerRef = useRef<HTMLDivElement>(null);

    // Close on outside click
    useEffect(() => {
        const handleClickOutside = (e: MouseEvent) => {
            if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
                setIsOpen(false);
            }
        };
        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, []);

    const handleDayClick = (day: Date) => {
        if (!tempStart || (tempStart && tempEnd)) {
            // Start new selection
            setTempStart(day);
            setTempEnd(null);
            setSelecting("end");
        } else {
            // Complete selection
            if (isBefore(day, tempStart)) {
                setTempEnd(tempStart);
                setTempStart(day);
            } else {
                setTempEnd(day);
            }
            setSelecting(null);
        }
    };

    const handleApply = () => {
        if (tempStart && tempEnd) {
            onChange(tempStart, tempEnd);
            setIsOpen(false);
        }
    };

    const handlePresetClick = (preset: typeof PRESETS[0]) => {
        const { start, end } = preset.getValue();
        setTempStart(start);
        setTempEnd(end);
        onChange(start, end);
        setIsOpen(false);
    };

    const renderCalendar = (monthDate: Date) => {
        const monthStart = startOfMonth(monthDate);
        const monthEnd = endOfMonth(monthDate);
        const calendarStart = startOfWeek(monthStart, { weekStartsOn: 1 });
        const calendarEnd = endOfWeek(monthEnd, { weekStartsOn: 1 });
        const days = eachDayOfInterval({ start: calendarStart, end: calendarEnd });

        const dayNames = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"];

        return (
            <div className="p-3">
                <div className="text-center font-medium mb-2 text-sm">
                    {format(monthDate, "MMMM yyyy", { locale: tr })}
                </div>
                <div className="grid grid-cols-7 gap-1 mb-1">
                    {dayNames.map((day) => (
                        <div key={day} className="text-center text-xs text-muted-foreground font-medium py-1">
                            {day}
                        </div>
                    ))}
                </div>
                <div className="grid grid-cols-7 gap-1">
                    {days.map((day, idx) => {
                        const isCurrentMonth = isSameMonth(day, monthDate);
                        const isSelected = (tempStart && isSameDay(day, tempStart)) || (tempEnd && isSameDay(day, tempEnd));
                        const isInRange = tempStart && tempEnd && isAfter(day, tempStart) && isBefore(day, tempEnd);
                        const isToday = isSameDay(day, new Date());
                        const isFuture = isAfter(day, new Date());

                        return (
                            <button
                                key={idx}
                                onClick={() => !isFuture && handleDayClick(day)}
                                disabled={isFuture}
                                className={`
                                    w-8 h-8 text-sm rounded-md transition-colors
                                    ${!isCurrentMonth ? "text-gray-300" : ""}
                                    ${isSelected ? "bg-primary text-white font-medium" : ""}
                                    ${isInRange ? "bg-primary/20" : ""}
                                    ${isToday && !isSelected ? "border border-primary" : ""}
                                    ${isFuture ? "text-gray-300 cursor-not-allowed" : "hover:bg-gray-100"}
                                    ${!isSelected && !isInRange && isCurrentMonth && !isFuture ? "text-foreground" : ""}
                                `}
                            >
                                {format(day, "d")}
                            </button>
                        );
                    })}
                </div>
            </div>
        );
    };

    return (
        <div className="relative" ref={containerRef}>
            {/* Trigger Button */}
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="flex items-center gap-2 bg-white border border-primary-light rounded-lg px-4 py-2 text-sm font-medium min-w-[240px] focus:outline-none focus:ring-2 focus:ring-primary shadow-sm hover:bg-gray-50 transition-colors"
            >
                <Calendar size={16} className="text-muted-foreground" />
                <span>
                    {format(startDate, "d MMM yyyy", { locale: tr })} - {format(endDate, "d MMM yyyy", { locale: tr })}
                </span>
            </button>

            {/* Dropdown */}
            {isOpen && (
                <div className="absolute right-0 top-full mt-2 bg-white border border-gray-200 rounded-xl shadow-lg z-50 flex">
                    {/* Presets */}
                    <div className="border-r border-gray-200 p-2 min-w-[140px]">
                        <div className="text-xs text-muted-foreground font-medium px-2 py-1 mb-1">Hızlı Seçim</div>
                        {PRESETS.map((preset) => (
                            <button
                                key={preset.label}
                                onClick={() => handlePresetClick(preset)}
                                className="w-full text-left px-3 py-2 text-sm rounded-md hover:bg-gray-100 transition-colors"
                            >
                                {preset.label}
                            </button>
                        ))}
                    </div>

                    {/* Calendars */}
                    <div>
                        <div className="flex items-center justify-between px-4 py-2 border-b border-gray-200">
                            <button
                                onClick={() => setCurrentMonth(subMonths(currentMonth, 1))}
                                className="p-1 hover:bg-gray-100 rounded-md transition-colors"
                            >
                                <ChevronLeft size={18} />
                            </button>
                            <span className="text-sm font-medium">Tarih Seçimi</span>
                            <button
                                onClick={() => setCurrentMonth(addMonths(currentMonth, 1))}
                                className="p-1 hover:bg-gray-100 rounded-md transition-colors"
                            >
                                <ChevronRight size={18} />
                            </button>
                        </div>
                        <div className="flex">
                            {renderCalendar(subMonths(currentMonth, 1))}
                            {renderCalendar(currentMonth)}
                        </div>
                        <div className="flex items-center justify-between px-4 py-3 border-t border-gray-200 bg-gray-50 rounded-b-xl">
                            <div className="text-sm text-muted-foreground">
                                {tempStart && tempEnd ? (
                                    <span>
                                        {format(tempStart, "d MMM", { locale: tr })} - {format(tempEnd, "d MMM yyyy", { locale: tr })}
                                    </span>
                                ) : tempStart ? (
                                    <span>Bitiş tarihi seçin</span>
                                ) : (
                                    <span>Başlangıç tarihi seçin</span>
                                )}
                            </div>
                            <div className="flex gap-2">
                                <button
                                    onClick={() => setIsOpen(false)}
                                    className="px-3 py-1.5 text-sm rounded-md hover:bg-gray-200 transition-colors"
                                >
                                    İptal
                                </button>
                                <button
                                    onClick={handleApply}
                                    disabled={!tempStart || !tempEnd}
                                    className="px-3 py-1.5 text-sm bg-primary text-white rounded-md hover:bg-primary-dark transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                                >
                                    Uygula
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
