import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export function Pole({ etykieta, blad, podpowiedz, children, className }: {
  etykieta: string; blad?: string; podpowiedz?: string; children: ReactNode; className?: string;
}) {
  return (
    <div className={cn("space-y-1.5", className)}>
      {/* <label> obejmuje pole: etykieta jest jego nazwą dla czytników ekranu i klik w nią ustawia kursor */}
      <label className="block space-y-1.5">
        <span className="flex items-center gap-2 text-sm leading-none font-medium select-none">{etykieta}</span>
        {children}
      </label>
      {blad ? <p className="text-sm text-destructive">{blad}</p>
        : podpowiedz && <p className="text-xs text-muted-foreground">{podpowiedz}</p>}
    </div>
  );
}

export const klasaSelect =
  "h-9 w-full rounded-md border border-input bg-transparent px-3 text-sm shadow-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring";
