import { useForm } from "@inertiajs/react";
import { Pole } from "@/components/Pole";
import { Karta } from "@/components/Uklad";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { Bledy } from "@/lib/typy";

export default function Logowanie({ bledy, next, produkt, rejestracja }: {
  bledy: Bledy; next: string; produkt: string | null; rejestracja?: boolean;
}) {
  const form = useForm({ email: "", haslo: "" });
  const wyslij = (e: React.FormEvent) => {
    e.preventDefault();
    form.post(`/logowanie/?next=${encodeURIComponent(next)}`, { preserveState: true });
  };
  return (
    <Karta tytul="Zaloguj się" podtytul={produkt ? <>żeby przejść do: <b className="text-foreground">{produkt}</b></> : "do Konta sudomie"}>
      <form className="space-y-4" onSubmit={wyslij}>
        <Pole etykieta="E-mail">
          <Input type="email" autoComplete="username" autoFocus required value={form.data.email} onChange={(e) => form.setData("email", e.target.value)} />
        </Pole>
        <Pole etykieta="Hasło" blad={bledy.haslo}>
          <Input type="password" autoComplete="current-password" required value={form.data.haslo} onChange={(e) => form.setData("haslo", e.target.value)} />
        </Pole>
        <Button className="h-11 w-full font-semibold" disabled={form.processing}>Zaloguj</Button>
      </form>
      <a href="/reset-hasla/" className="block text-center text-sm text-muted-foreground underline-offset-4 hover:underline">Nie pamiętasz hasła?</a>
      {rejestracja && (
        <a href="/rejestracja/" className="block text-center text-sm text-muted-foreground underline-offset-4 hover:underline">
          Nie masz konta? Załóż konto firmy
        </a>
      )}
    </Karta>
  );
}
