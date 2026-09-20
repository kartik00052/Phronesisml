import { FLAT_NAV } from "@/config/navigation";

export interface Crumb {
  label: string;
  to?: string;
}

/** Build breadcrumb segments for a given pathname. */
export function buildCrumbs(pathname: string): Crumb[] {
  const segments = pathname.split("/").filter(Boolean);
  const crumbs: Crumb[] = [];

  let acc = "";
  for (const seg of segments) {
    acc += `/${seg}`;
    const match = FLAT_NAV.find((n) => n.href === acc);
    const label = match?.title ?? decodeURIComponent(seg);
    crumbs.push({ label, to: match ? acc : undefined });
  }

  return crumbs;
}