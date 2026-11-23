import { useForm } from "@inertiajs/react";
import { Pole } from "@/components/Pole";
import { Blad, Karta } from "@/components/Uklad";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function ResetHasla({ wyslano, blad }: { wyslano: boolean; blad: string | null }) {
  const form = useForm({ email: "" });
  if (wyslano) {
    return (
      <Karta tytul="Sprawdź skrzynkę">
        <p className="text-sm text-muted-foreground">
          Jeśli ten adres ma Konto sudomie, wysłaliśmy na niego link do ustawienia nowego hasła (od no-reply@sudomie.pl).
          Nie widzisz maila? Zajrzyj do spamu.
        </p>
        <a href="/logowanie/" className="block text-sm underline">Wróć do logowania</a>
      </Karta>
    );
  }
  return (
    <Karta tytul="Nowe hasło" podtytul="Podaj e-mail, którym się logujesz — wyślemy link.">
      <Blad tekst={blad} />
      <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); form.post("/reset-hasla/", { preserveState: true }); }}>
        <Pole etykieta="E-mail">
          <Input type="email" autoComplete="username" autoFocus required value={form.data.email} onChange={(e) => form.setData("email", e.target.value)} />
        </Pole>
        <Button className="h-11 w-full font-semibold" disabled={form.processing}>Wyślij link</Button>
      </form>
      <a href="/logowanie/" className="block text-center text-sm text-muted-foreground hover:underline">Wróć do logowania</a>
    </Karta>
  );
}
