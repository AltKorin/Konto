import { useForm } from "@inertiajs/react";
import { Pole } from "@/components/Pole";
import { Karta } from "@/components/Uklad";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { Bledy } from "@/lib/typy";

export default function NoweHaslo({ wazny, bledy, email }: { wazny: boolean; bledy: Bledy; email?: string }) {
  const form = useForm({ haslo: "", powtorz: "" });
  if (!wazny) {
    return (
      <Karta tytul="Link nieważny">
        <p className="text-sm text-muted-foreground">Ten link już został użyty albo wygasł. Poproś o nowy.</p>
        <a href="/reset-hasla/" className="block text-sm underline">Wyślij nowy link</a>
      </Karta>
    );
  }
  return (
    <Karta tytul="Ustaw nowe hasło" podtytul={email}>
      <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); form.post(window.location.pathname, { preserveState: true }); }}>
        <input type="email" autoComplete="username" value={email} readOnly hidden />
        <Pole etykieta="Nowe hasło" blad={bledy.haslo} podpowiedz="Minimum 12 znaków. Najlepiej kilka słów.">
          <Input type="password" autoComplete="new-password" autoFocus required value={form.data.haslo} onChange={(e) => form.setData("haslo", e.target.value)} />
        </Pole>
        <Pole etykieta="Powtórz hasło" blad={bledy.powtorz}>
          <Input type="password" autoComplete="new-password" required value={form.data.powtorz} onChange={(e) => form.setData("powtorz", e.target.value)} />
        </Pole>
        <Button className="h-11 w-full font-semibold" disabled={form.processing}>Zapisz hasło</Button>
      </form>
    </Karta>
  );
}
