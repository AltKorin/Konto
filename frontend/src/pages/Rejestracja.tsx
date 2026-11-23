import { useForm } from "@inertiajs/react";
import { Pole } from "@/components/Pole";
import { Blad, Karta } from "@/components/Uklad";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { Bledy } from "@/lib/typy";

type Props = {
  produkty: { kod: string; nazwa: string }[]; produkt: string; wyslano: boolean; bledy: Bledy;
  dane?: { nazwa?: string; imie?: string; email?: string };
};

export default function Rejestracja({ produkty, produkt, wyslano, bledy, dane }: Props) {
  const form = useForm({ nazwa: dane?.nazwa ?? "", imie: dane?.imie ?? "", email: dane?.email ?? "", produkt });
  if (wyslano) {
    return (
      <Karta tytul="Sprawdź skrzynkę" podtytul={form.data.email || undefined}>
        <p className="text-sm">Wysłaliśmy link do potwierdzenia. Kliknij go, ustaw hasło — i firma jest gotowa.</p>
        <p className="text-sm text-muted-foreground">Nie ma maila? Zajrzyj do spamu albo wypełnij formularz jeszcze raz.</p>
      </Karta>
    );
  }
  const wybrany = produkty.find((p) => p.kod === form.data.produkt);
  return (
    <Karta tytul="Załóż konto firmy" podtytul={wybrany ? <>żeby korzystać z: <b className="text-foreground">{wybrany.nazwa}</b></> : "w Koncie sudomie"}>
      <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); form.post("/rejestracja/", { preserveState: true }); }}>
        <Pole etykieta="Nazwa firmy lub lokalu">
          <Input autoFocus required maxLength={200} placeholder="np. Gospoda pod Lipą" value={form.data.nazwa}
            onChange={(e) => form.setData("nazwa", e.target.value)} />
        </Pole>
        <Pole etykieta="Twoje imię">
          <Input autoComplete="given-name" value={form.data.imie} onChange={(e) => form.setData("imie", e.target.value)} />
        </Pole>
        <Pole etykieta="E-mail (będzie loginem)">
          <Input type="email" autoComplete="email" required value={form.data.email} onChange={(e) => form.setData("email", e.target.value)} />
        </Pole>
        {!wybrany && (
          <Pole etykieta="Zaczynasz od aplikacji">
            <select required className="h-11 w-full rounded-md border bg-transparent px-3 text-sm" value={form.data.produkt}
              onChange={(e) => form.setData("produkt", e.target.value)}>
              <option value="">— wybierz —</option>
              {produkty.map((p) => <option key={p.kod} value={p.kod}>{p.nazwa}</option>)}
            </select>
          </Pole>
        )}
        <Blad tekst={bledy.email} />
        <Button className="h-11 w-full font-semibold" disabled={form.processing}>Wyślij link</Button>
        <p className="text-xs text-muted-foreground">
          Zakładając konto akceptujesz zasady opisane w{" "}
          <a className="underline" href="https://sudomie.pl/polityka-prywatnosci.html#konto">polityce prywatności</a>.
          Kolejne aplikacje i pracowników dodasz potem w Koncie.
        </p>
      </form>
      <a href="/logowanie/" className="block text-center text-sm text-muted-foreground underline-offset-4 hover:underline">Masz już konto? Zaloguj się</a>
    </Karta>
  );
}
