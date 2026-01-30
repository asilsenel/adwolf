"use client"

import * as React from "react"
import { Check, ChevronsUpDown, Filter } from "lucide-react"
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
import { Account } from "@/types/api"

interface AccountSelectorProps {
    accounts: Account[]
    selectedAccountId: string
    onSelect: (accountId: string) => void
}

export function AccountSelector({ accounts, selectedAccountId, onSelect }: AccountSelectorProps) {
    const [open, setOpen] = React.useState(false)

    const selectedAccount = accounts.find((a) => a.id === selectedAccountId)

    // Sort accounts: 1. By name, 2. By ID
    const sortedAccounts = [...accounts].sort((a, b) => {
        const nameA = a.account_name || a.platform_account_name || a.platform_account_id
        const nameB = b.account_name || b.platform_account_name || b.platform_account_id
        return nameA.localeCompare(nameB)
    })

    return (
        <Popover open={open} onOpenChange={setOpen}>
            <PopoverTrigger asChild>
                <Button
                    variant="outline"
                    role="combobox"
                    aria-expanded={open}
                    className="w-[250px] justify-between h-9 px-3"
                >
                    <div className="flex items-center gap-2 truncate">
                        <Filter className="mr-0 h-4 w-4 shrink-0 opacity-50" />
                        {selectedAccountId === "all" ? (
                            "Tüm Hesaplar"
                        ) : (
                            <span className="truncate">
                                {selectedAccount
                                    ? selectedAccount.account_name || selectedAccount.platform_account_name || selectedAccount.platform_account_id
                                    : "Hesap Seçin..."}
                            </span>
                        )}
                    </div>
                    <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                </Button>
            </PopoverTrigger>
            <PopoverContent className="w-[250px] p-0">
                <Command>
                    <CommandInput placeholder="Hesap ara..." />
                    <CommandList>
                        <CommandEmpty>Hesap bulunamadı.</CommandEmpty>
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
                                        selectedAccountId === "all" ? "opacity-100" : "opacity-0"
                                    )}
                                />
                                Tüm Hesaplar
                            </CommandItem>
                            {sortedAccounts.map((account) => (
                                <CommandItem
                                    key={account.id}
                                    value={account.account_name || account.platform_account_name || account.platform_account_id}
                                    onSelect={() => {
                                        onSelect(account.id)
                                        setOpen(false)
                                    }}
                                >
                                    <Check
                                        className={cn(
                                            "mr-2 h-4 w-4",
                                            selectedAccountId === account.id ? "opacity-100" : "opacity-0"
                                        )}
                                    />
                                    <span className="truncate">
                                        {account.account_name || account.platform_account_name || account.platform_account_id}
                                    </span>
                                </CommandItem>
                            ))}
                        </CommandGroup>
                    </CommandList>
                </Command>
            </PopoverContent>
        </Popover>
    )
}
