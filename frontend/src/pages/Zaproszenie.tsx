import { router, useForm } from "@inertiajs/react";
import { Pole } from "@/components/Pole";
import { Blad, Karta } from "@/components/Uklad";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { Bledy } from "@/lib/typy";

type Props = {
  blad: string | null; bledy?: Bledy; firma?: string; email?: string; imie?: string;
  produkty?: { nazwa: string; rola: string }[]; konto_istnieje?: boolean; zalogowany_jako?: string | null;
};

export default function Zaproszenie(p: Props) {
  const form = useForm({ haslo: "", powtorz: "" });
  if (p.blad) {
    return <Karta tytul="Zaproszenie nieważne"><Blad tekst={p.blad} /></Karta>;
  }
  const tutaj = window.location.pathname;
  return (
    <Karta tytul={`Dołącz do: ${p.firma}`} podtytul={p.email}>
      <ul className="space-y-1 rounded-md bg-secondary p-3 text-sm">
        {p.produkty!.map((x) => <li key={x.nazwa}>{x.nazwa} <span className="text-muted-foreground">— {x.rola}</span></li>)}
      </ul>
      <Blad tekst={p.bledy?.haslo} />
      {p.zalogowany_jako ? (
        <>
          <p className="text-sm text-muted-foreground">Jesteś zalogowany jako <b className="text-foreground">{p.zalogowany_jako}</b>.</p>
          <Button className="h-11 w-full font-semibold" onClick={() => router.post(tutaj)}>Dołącz tym kontem</Button>
        </>
      ) : p.konto_istnieje ? (
        <>
          <p className="text-sm text-muted-foreground">Masz już Konto sudomie z tym adresem. Zaloguj się — wrócisz tutaj.</p>
          <Button asChild className="h-11 w-full font-semibold"><a href={`/logowanie/?next=${encodeURIComponent(tutaj)}`}>Zaloguj się</a></Button>
        </>
      ) : (
        <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); form.post(tutaj, { preserveState: true }); }}>
          <input type="email" autoComplete="username" value={p.email} readOnly hidden />
          <Pole etykieta="Ustaw hasło" podpowiedz="Minimum 12 znaków. Tym hasłem zalogujesz się do wszystkich aplikacji sudomie.">
            <Input type="password" autoComplete="new-password" autoFocus required value={form.data.haslo} onChange={(e) => form.setData("haslo", e.target.value)} />
          </Pole>
          <Pole etykieta="Powtórz hasło">
            <Input type="password" autoComplete="new-password" required value={form.data.powtorz} onChange={(e) => form.setData("powtorz", e.target.value)} />
          </Pole>
          <Button className="h-11 w-full font-semibold" disabled={form.processing}>Dołącz</Button>
        </form>
      )}
    </Karta>
  );
}
