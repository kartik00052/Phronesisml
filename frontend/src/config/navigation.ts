import {
  Archive,
  BrainCircuit,
  Database,
  FileText,
  GitBranch,
  LayoutDashboard,
  PieChart,
  PlayCircle,
  Settings,
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  title: string;
  href: string;
  icon: LucideIcon;
  /** Short matching hint used by the command palette. */
  keywords?: string[];
  /** Match the route exactly instead of by prefix. */
  exact?: boolean;
  /** Paths that must never mark this item active (e.g. exclude /runs/new). */
  exclude?: string[];
}

export interface NavSection {
  label: string;
  items: NavItem[];
}

export const NAV_SECTIONS: NavSection[] = [
  {
    label: "Overview",
    items: [{ title: "Dashboard", href: "/", icon: LayoutDashboard, keywords: ["home", "overview", "stats"] }],
  },
  {
    label: "Workflows",
    items: [
      { title: "New Run", href: "/runs/new", icon: PlayCircle, exact: true, keywords: ["create", "new run", "wizard", "start"] },
      { title: "Runs", href: "/runs", icon: GitBranch, exclude: ["/runs/new"], keywords: ["experiments", "history", "pipeline", "jobs"] },
    ],
  },
  {
    label: "Data & Models",
    items: [
      { title: "Datasets", href: "/datasets", icon: Database, keywords: ["data", "files", "csv"] },
      { title: "Models", href: "/models", icon: BrainCircuit, keywords: ["leaderboard", "best model", "ml"] },
      { title: "Explainability", href: "/explainability", icon: PieChart, keywords: ["shap", "features", "importance"] },
      { title: "Reports", href: "/reports", icon: FileText, keywords: ["markdown", "summary", "docs"] },
      { title: "Artifacts", href: "/artifacts", icon: Archive, keywords: ["files", "output", "saved models"] },
    ],
  },
  {
    label: "System",
    items: [{ title: "Settings", href: "/settings", icon: Settings, keywords: ["config", "preferences", "theme"] }],
  },
];

export const FLAT_NAV = NAV_SECTIONS.flatMap((s) => s.items);