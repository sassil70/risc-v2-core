/**
 * Lightweight utility for merging class names.
 * Replacing clsx/tailwind-merge since they are not installed.
 */
export function cn(...classes: (string | undefined | null | false)[]) {
    return classes.filter(Boolean).join(" ");
}
