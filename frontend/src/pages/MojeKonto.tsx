import { useForm } from "@inertiajs/react";
import { Pole } from "@/components/Pole";
import { Blad, Strona } from "@/components/Uklad";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { Bledy } from "@/lib/typy";

export default function MojeKonto({ bledy, dane }: { bledy: Bledy; dane: { imie: string; email: string } }) {
  const d = useForm({ co: "dane", imie: dane.imie, email: dane.email, haslo_obecne: "" });
  const h = useForm({ co: "haslo", obecne: "", nowe: "", powtorz: "" });
  const zmianaEmaila = d.data.email.trim().toLowerCase() !== dane.email;
  return (
    <Strona>
      <h1 className="text-3xl">Moje konto</h1>
      <div className="grid gap-5 md:grid-cols-2">
        <form className="space-y-4 rounded-lg border bg-card p-5" onSubmit={(e) => { e.preventDefault(); d.post("/moje-konto/", { preserveScroll: true, onSuccess: () => d.setData("haslo_obecne", "") }); }}>
          <h2 className="text-lg">Dane</h2>
          <Blad tekst={bledy.dane} />
          <Pole etykieta="Imię"><Input value={d.data.imie} onChange={(e) => d.setData("imie", e.target.value)} /></Pole>
          <Pole etykieta="E-mail (login)"><Input type="email" autoComplete="username" value={d.data.email} onChange={(e) => d.setData("email", e.target.value)} /></Pole>
          {zmianaEmaila && (
            <Pole etykieta="Obecne hasło" podpowiedz="Zmieniasz login do wszystkich aplikacji — potwierdź hasłem.">
              <Input type="password" autoComplete="current-password" value={d.data.haslo_obecne} onChange={(e) => d.setData("haslo_obecne", e.target.value)} />
            </Pole>
          )}
          <Button disabled={d.processing}>Zapisz</Button>
        </form>
        <form className="space-y-4 rounded-lg border bg-card p-5" onSubmit={(e) => { e.preventDefault(); h.post("/moje-konto/", { preserveScroll: true, onSuccess: () => h.reset() }); }}>
          <h2 className="text-lg">Hasło</h2>
          <Blad tekst={bledy.haslo} />
          <Pole etykieta="Obecne hasło"><Input type="password" autoComplete="current-password" value={h.data.obecne} onChange={(e) => h.setData("obecne", e.target.value)} /></Pole>
          <Pole etykieta="Nowe hasło" podpowiedz="Minimum 12 znaków. Działa we wszystkich aplikacjach sudomie.">
            <Input type="password" autoComplete="new-password" value={h.data.nowe} onChange={(e) => h.setData("nowe", e.target.value)} />
          </Pole>
          <Pole etykieta="Powtórz nowe hasło"><Input type="password" autoComplete="new-password" value={h.data.powtorz} onChange={(e) => h.setData("powtorz", e.target.value)} /></Pole>
          <Button disabled={h.processing}>Zmień hasło</Button>
        </form>
      </div>
    </Strona>
  );
}
