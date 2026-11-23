import { useState, type ReactNode } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger,
} from "@/components/ui/dialog";

/** Usuwanie zawsze z potwierdzeniem i opisem skutku (CLAUDE.md). */
export function Potwierdz({ przycisk, tytul, skutek, tak, onTak }: {
  przycisk: ReactNode; tytul: string; skutek: string; tak: string; onTak: () => void;
}) {
  const [otwarte, setOtwarte] = useState(false);
  return (
    <Dialog open={otwarte} onOpenChange={setOtwarte}>
      <DialogTrigger asChild>{przycisk}</DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{tytul}</DialogTitle>
          <DialogDescription>{skutek}</DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="outline" onClick={() => setOtwarte(false)}>Anuluj</Button>
          <Button variant="destructive" onClick={() => { setOtwarte(false); onTak(); }}>{tak}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
