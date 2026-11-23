import { router, usePage } from "@inertiajs/react";
import { type ReactNode, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import type { Wspolne } from "@/lib/typy";
import { cn } from "@/lib/utils";
import { uruchomAnalityke, wybierz, wybor } from "@/lib/zgoda";

export const POLITYKA = "https://sudomie.pl/polityka-prywatnosci.html#konto";

/** Wąska karta na środku — logowanie, reset, zaproszenie. */
export function Karta({ tytul, podtytul, children }: { tytul: string; podtytul?: ReactNode; children: ReactNode }) {
  const { komunikaty, ga } = usePage<Wspolne>().props;
  return (
    <div className="flex min-h-screen flex-col items-center justify-center px-4 py-10">
      <img src="/static/sudomie-logo.svg" alt="sudomie" className="mb-8 h-9 w-auto" />
      <div className="w-full max-w-sm rounded-lg border bg-card p-6">
        <h1 className="text-2xl">{tytul}</h1>
        {podtytul && <p className="mt-1 text-sm text-muted-foreground">{podtytul}</p>}
        <div className="mt-5 space-y-4">
          <Komunikaty lista={komunikaty} />
          {children}
        </div>
      </div>
      <p className="mt-6 max-w-sm text-center text-xs text-muted-foreground">
        Konto sudomie — jeden login do Grafiku, Kalendarza przyjęć i innych aplikacji sudomie.
      </p>
      <p className="mt-2 flex max-w-sm flex-wrap justify-center gap-x-3 text-xs text-muted-foreground">
        <a className="underline" href={POLITYKA}>Polityka prywatności</a>
        {ga && <button type="button" className="underline" onClick={() => window.dispatchEvent(new Event("cc:open"))}>Ustawienia cookies</button>}
      </p>
      <BanerZgody ga={ga} />
    </div>
  );
}

export function Komunikaty({ lista }: { lista: Wspolne["komunikaty"] }) {
  return (
    <>
      {lista.map((k, i) => (
        <p key={i} role="status" className={cn("rounded-md border p-3 text-sm",
          k.poziom === "error" ? "border-destructive/50 text-destructive" : "border-primary/40 text-primary")}>{k.tekst}</p>
      ))}
    </>
  );
}

export function Blad({ tekst }: { tekst?: string | null }) {
  return tekst ? <p role="alert" className="rounded-md border border-destructive/50 p-3 text-sm text-destructive">{tekst}</p> : null;
}

/** Szeroki układ po zalogowaniu (Moje konto, Zespół). */
export function Strona({ children }: { children: ReactNode }) {
  const { osoba, komunikaty } = usePage<Wspolne>().props;
  return (
    <div className="min-h-screen">
      <header className="border-b bg-card">
        <div className="mx-auto flex max-w-5xl items-center gap-4 px-4 py-3">
          <a href="/" className="flex items-center gap-3">
            <img src="/static/sudomie-logo.svg" alt="sudomie" className="h-7 w-auto" />
            <span className="text-sm text-muted-foreground">Konto</span>
          </a>
          {osoba && (
            <div className="ml-auto flex items-center gap-3 text-sm text-muted-foreground">
              <a href="/moje-konto/" className="hover:text-foreground hover:underline">{osoba.imie || osoba.email}</a>
              <Button variant="outline" size="sm" onClick={() => router.post("/wyloguj/")}>Wyloguj</Button>
            </div>
          )}
        </div>
      </header>
      <main className="mx-auto max-w-5xl space-y-4 px-4 py-8">
        <Komunikaty lista={komunikaty} />
        {children}
      </main>
    </div>
  );
}

/** Baner zgody na statystyki — te same ekrany co tag (publiczne). Kontrakt „cc” jak agenda/fc/Kalendarz. */
function BanerZgody({ ga }: { ga: string }) {
  const [otwarty, setOtwarty] = useState(false);
  useEffect(() => {
    if (!ga) return;
    uruchomAnalityke(ga);
    setOtwarty(wybor() === null);
    const otworz = () => setOtwarty(true);
    window.addEventListener("cc:open", otworz);
    return () => window.removeEventListener("cc:open", otworz);
  }, [ga]);
  if (!otwarty) return null;
  const wybrano = (w: "accepted" | "declined") => { wybierz(w); setOtwarty(false); };
  return (
    <div role="region" aria-label="Zgoda na statystyki"
      className="fixed inset-x-0 bottom-0 z-50 border-t bg-card p-4 shadow-lg">
      <div className="mx-auto flex max-w-5xl flex-wrap items-center gap-3">
        <p className="flex-1 text-sm">
          Używamy Google Analytics, żeby wiedzieć, jak korzystasz z tej strony. Bez zgody nie zapisujemy cookies
          statystycznych. <a className="underline" href={POLITYKA}>Polityka prywatności</a>
        </p>
        <Button onClick={() => wybrano("accepted")}>Akceptuję</Button>
        <Button variant="outline" onClick={() => wybrano("declined")}>Odrzucam</Button>
      </div>
    </div>
  );
}
