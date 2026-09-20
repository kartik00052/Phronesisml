import { NavLink, useLocation } from "react-router-dom";
import { Settings } from "lucide-react";

import { cn } from "@/lib/cn";
import { NAV_SECTIONS, type NavItem } from "@/config/navigation";
import { Logo } from "@/components/layout/logo";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

function NavListItem({
  item,
  collapsed,
}: {
  item: NavItem;
  collapsed: boolean;
}) {
  const { pathname } = useLocation();
  const isRoot = item.href === "/";
  const active = isRoot
    ? pathname === "/"
    : item.exact
      ? pathname === item.href
      : pathname.startsWith(item.href) && !(item.exclude ?? []).includes(pathname);

  const link = (
    <NavLink
      to={item.href}
      className={cn(
        "flex items-center gap-2.5 rounded-md px-2.5 py-1.5 text-sm font-medium transition-colors",
        active
          ? "bg-muted/70 text-foreground"
          : "text-muted-foreground hover:bg-muted/40 hover:text-foreground",
        collapsed && "justify-center gap-0 px-0",
      )}
    >
      <item.icon className="size-4 shrink-0" />
      {!collapsed && <span>{item.title}</span>}
    </NavLink>
  );

  if (!collapsed) return link;

  return (
    <Tooltip>
      <TooltipTrigger asChild>{link}</TooltipTrigger>
      <TooltipContent side="right">{item.title}</TooltipContent>
    </Tooltip>
  );
}

export function Sidebar({
  collapsed,
  onNavigate,
}: {
  collapsed: boolean;
  onNavigate?: () => void;
}) {
  return (
    <aside
      className={cn(
        "flex h-full flex-col border-r border-border bg-sidebar transition-[width] duration-200",
        collapsed ? "w-14" : "w-60",
      )}
    >
      <div
        className={cn(
          "flex h-14 items-center border-b border-border px-2",
          collapsed && "justify-center px-0",
        )}
      >
        <Logo compact={collapsed} />
      </div>
      <nav className="flex-1 space-y-5 overflow-y-auto p-2 scrollbar-thin">
        {NAV_SECTIONS.map((section) => (
          <div key={section.label}>
            {!collapsed && (
              <p
                className={cn(
                  "mb-1.5 px-2.5 text-[10px] font-semibold uppercase tracking-[0.14em] text-muted-foreground/70",
                  collapsed && "sr-only",
                )}
              >
                {section.label}
              </p>
            )}
            <div className="space-y-0.5">
              {section.items.map((item) => (
                <NavListItem key={item.href} item={item} collapsed={collapsed} />
              ))}
            </div>
          </div>
        ))}
      </nav>
      <div className="border-t border-border p-2">
        <NavLink
          to="/settings"
          onClick={onNavigate}
          title={collapsed ? "Settings" : undefined}
          className={cn(
            "flex items-center gap-2.5 rounded-md px-2.5 py-1.5 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted/40 hover:text-foreground",
            collapsed && "justify-center gap-0 px-0",
          )}
        >
          <Settings className="size-4 shrink-0" />
          {!collapsed && <span>Settings</span>}
        </NavLink>
      </div>
    </aside>
  );
}