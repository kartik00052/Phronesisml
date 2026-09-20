import * as React from "react";
import { Outlet, useLocation, useNavigate } from "react-router-dom";

import { Sidebar } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";
import { CommandMenu } from "@/components/layout/command-menu";
import { useCommandMenuState } from "@/hooks/use-command-menu";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Sheet, SheetContent } from "@/components/ui/sheet";
import { useThemeStore, initTheme } from "@/stores/theme";
import { useUiStore } from "@/stores/ui";

export function AppShell() {
  const cmd = useCommandMenuState();
  const location = useLocation();
  const navigate = useNavigate();
  const preference = useThemeStore((s) => s.preference);
  const toggleTheme = useThemeStore((s) => s.toggle);

  const sidebarCollapsed = useUiStore((s) => s.sidebarCollapsed);
  const setSidebarCollapsed = useUiStore((s) => s.setSidebarCollapsed);
  const mobileNavOpen = useUiStore((s) => s.mobileNavOpen);
  const setMobileNavOpen = useUiStore((s) => s.setMobileNavOpen);

  React.useEffect(() => {
    initTheme();
  }, [preference]);

  React.useEffect(() => {
    const onShortcut = (e: KeyboardEvent) => {
      const mod = e.metaKey || e.ctrlKey;
      if (!mod) return;
      const key = e.key.toLowerCase();
      if (key === "n" && !e.shiftKey) {
        e.preventDefault();
        void navigate("/runs/new");
      } else if (key === "l" && e.shiftKey) {
        e.preventDefault();
        toggleTheme();
      }
    };
    window.addEventListener("keydown", onShortcut);
    return () => window.removeEventListener("keydown", onShortcut);
  }, [navigate, toggleTheme]);

  React.useEffect(() => {
    window.scrollTo({ top: 0 });
  }, [location.pathname]);

  const onToggleSidebar = () => {
    if (window.matchMedia("(min-width: 768px)").matches) {
      setSidebarCollapsed(!sidebarCollapsed);
    } else {
      setMobileNavOpen(!mobileNavOpen);
    }
  };

  return (
    <div className="flex h-dvh overflow-hidden bg-background text-foreground">
      <div className="hidden md:block">
        <Sidebar collapsed={sidebarCollapsed} />
      </div>

      <Sheet open={mobileNavOpen} onOpenChange={setMobileNavOpen}>
        <SheetContent side="left" className="w-64 p-0">
          <Sidebar collapsed={false} onNavigate={() => setMobileNavOpen(false)} />
        </SheetContent>
      </Sheet>

      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar onToggleSidebar={onToggleSidebar} onOpenCommand={() => cmd.setOpen(true)} />
        <ScrollArea className="flex-1">
          <main className="mx-auto w-full max-w-[1400px] p-4 sm:p-6">
            <Outlet />
          </main>
        </ScrollArea>
      </div>

      <CommandMenu open={cmd.open} setOpen={cmd.setOpen} />
    </div>
  );
}
