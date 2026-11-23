import { Strona } from "@/components/Uklad";

type Firma = { id: string; nazwa: string; wlasciciel: boolean; produkty: { kod: string; nazwa: string; adres: string; rola: string }[] };

export default function Start({ firmy }: { firmy: Firma[] }) {
  return (
    <Strona>
      <h1 className="text-3xl">Twoje aplikacje</h1>
      {firmy.length === 0 && (
        <p className="text-muted-foreground">Nie należysz jeszcze do żadnej firmy. Poproś szefa o zaproszenie.</p>
      )}
      {firmy.map((f) => (
        <section key={f.id} className="space-y-3">
          <div className="flex flex-wrap items-center gap-3">
            <h2 className="text-lg text-muted-foreground">{f.nazwa}{f.wlasciciel && " · właściciel"}</h2>
            {f.wlasciciel && <a href={`/firma/${f.id}/zespol/`} className="rounded-md border px-3 py-1 text-sm hover:border-primary">Zespół i dostępy</a>}
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {f.produkty.map((p) => (
              <a key={p.kod} href={p.adres} className="rounded-lg border bg-card p-5 transition hover:border-primary">
                <div className="text-lg font-semibold">{p.nazwa}</div>
                <div className="text-sm text-muted-foreground">{p.rola}</div>
                <div className="mt-3 text-sm text-primary">Otwórz →</div>
              </a>
            ))}
            {f.produkty.length === 0 && <p className="text-sm text-muted-foreground">Brak dostępu do aplikacji w tej firmie.</p>}
          </div>
        </section>
      ))}
    </Strona>
  );
}
