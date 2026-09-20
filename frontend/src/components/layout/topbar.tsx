import { PanelLeft, Moon, Sun } from "lucide-react";

import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { CommandMenuTrigger } from "@/components/layout/command-menu";
import { ConnectionStatus } from "@/components/layout/connection-status";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useThemeStore } from "@/stores/theme";
import { isDemoMode } from "@/mocks";

export function Topbar({
  onToggleSidebar,
  onOpenCommand,
}: {
  onToggleSidebar: () => void;
  onOpenCommand: () => void;
}) {
  const { preference, setPreference } = useThemeStore();

  return (
    <header className="flex h-14 shrink-0 items-center gap-3 border-b border-border bg-card px-3 sm:px-4">
      <Button
        variant="ghost"
        size="icon"
        onClick={onToggleSidebar}
        aria-label="Toggle sidebar"
        className="text-muted-foreground"
      >
        <PanelLeft className="size-4" />
      </Button>

      <Breadcrumbs className="hidden min-w-0 sm:flex" />

      <div className="ml-auto flex items-center gap-2">
        {isDemoMode() && (
          <span className="hidden rounded-md border border-warning/30 bg-warning/10 px-2 py-1 text-xs font-medium text-warning sm:inline-flex">
            Demo mode
          </span>
        )}
        <ConnectionStatus />
        <div className="hidden lg:block">
          <CommandMenuTrigger onClick={onOpenCommand} />
        </div>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" aria-label="Toggle theme" className="text-muted-foreground">
              <Sun className="size-4 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
              <Moon className="absolute size-4 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuLabel>Theme</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={() => setPreference("light")}>
              Light {preference === "light" && "✓"}
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => setPreference("dark")}>
              Dark {preference === "dark" && "✓"}
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => setPreference("system")}>
              System {preference === "system" && "✓"}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      <div className="lg:hidden">
        <CommandMenuTrigger onClick={onOpenCommand} className="w-auto gap-1.5 px-2 [&>span]:hidden" />
      </div>
    </header>
  );
}