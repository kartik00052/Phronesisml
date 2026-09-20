import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/** Merge conditional class names with tailwind-merge dedup. */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}