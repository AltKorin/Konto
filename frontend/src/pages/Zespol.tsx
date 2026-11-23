import { router } from "@inertiajs/react";
import { useState } from "react";
import { klasaSelect, Pole } from "@/components/Pole";
import { Potwierdz } from "@/components/Potwierdz";
import { Strona } from "@/components/Uklad";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

type Produkt = { kod: string; nazwa: string; role: string[] };
type Osoba = { id: number; imie: string; email: string; wlasciciel: boolean; aktywne: boolean; dostepy: Record<string, string>; ostatnio: string | null };
type Zapr = { id: number; email: string; imie: string; dostepy: Record<string, string>; wlasciciel: boolean; wazne_do: string; wygaslo: boolean };
type Props = { firma: { id: string; nazwa: string }; produkty: Produkt[]; osoby: Osoba[]; zaproszenia: Zapr[]; ja: number };

const ROLE: Record<string, string> = { dyrektor: "dyrektor", kierownik: "kierownik", pracownik: "pracownik", obsluga: "obsługa", uzytkownik: "użytkownik" };
const nazwaRoli = (r: string) => ROLE[r] ?? r;

function WyborDostepow({ produkty, dostepy, zmien }: { produkty: Produkt[]; dostepy: Record<string, string>; zmien: (d: Record<string, string>) => void }) {
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {produkty.map((p) => (
        <Pole key={p.kod} etykieta={p.nazwa}>
          <select className={klasaSelect + " bg-card"} value={dostepy[p.kod] ?? ""} onChange={(e) => zmien({ ...dostepy, [p.kod]: e.target.value })}>
            <option value="">— bez dostępu —</option>
            {p.role.map((r) => <option key={r} value={r}>{nazwaRoli(r)}</option>)}
          </select>
        </Pole>
      ))}
    </div>
  );
}

export default function Zespol({ firma, produkty, osoby, zaproszenia, ja }: Props) {
  const baza = `/firma/${firma.id}`;
  const [zapros, setZapros] = useState(false);
  const [nowa, setNowa] = useState({ email: "", imie: "", wlasciciel: false, dostepy: {} as Record<string, string> });
  const [edycja, setEdycja] = useState<Osoba | null>(null);
  const [nazwa, setNazwa] = useState<string | null>(null);
  const zachowaj = { preserveScroll: true };

  return (
    <Strona>
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-sm text-muted-foreground">Zespół i dostępy</p>
          {nazwa === null ? (
            <h1 className="flex items-center gap-3 text-3xl">{firma.nazwa}
              <button className="text-sm font-normal text-muted-foreground underline-offset-4 hover:underline" onClick={() => setNazwa(firma.nazwa)}>zmień nazwę</button>
            </h1>
          ) : (
            <form className="mt-1 flex gap-2" onSubmit={(e) => { e.preventDefault(); router.post(`${baza}/nazwa/`, { nazwa }, { ...zachowaj, onSuccess: () => setNazwa(null) }); }}>
              <Input value={nazwa} onChange={(e) => setNazwa(e.target.value)} className="w-72" autoFocus />
              <Button>Zapisz</Button><Button type="button" variant="outline" onClick={() => setNazwa(null)}>Anuluj</Button>
            </form>
          )}
        </div>
        <Button onClick={() => setZapros(true)}>+ Zaproś osobę</Button>
      </div>
      <p className="text-sm text-muted-foreground">
        Jedno konto = jeden login do wszystkich aplikacji. W tabeli ustawiasz, kto ma dostęp do której aplikacji i w jakiej roli.
      </p>

      <div className="overflow-x-auto rounded-lg border bg-card">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Osoba</TableHead>
              {produkty.map((p) => <TableHead key={p.kod}>{p.nazwa}</TableHead>)}
              <TableHead />
            </TableRow>
          </TableHeader>
          <TableBody>
            {osoby.map((o) => (
              <TableRow key={o.id} className={o.aktywne ? "" : "opacity-50"}>
                <TableCell>
                  <div className="font-medium">{o.imie || o.email} {o.wlasciciel && <Badge variant="outline" className="ml-1 border-primary/50 text-primary">właściciel</Badge>}
                    {!o.aktywne && <Badge variant="outline" className="ml-1">wyłączone</Badge>}</div>
                  <div className="text-xs text-muted-foreground">{o.email} · {o.ostatnio ? `logował(a) się ${o.ostatnio}` : "jeszcze się nie logował(a)"}</div>
                </TableCell>
                {produkty.map((p) => <TableCell key={p.kod} className={o.dostepy[p.kod] ? "" : "text-muted-foreground"}>{o.dostepy[p.kod] ? nazwaRoli(o.dostepy[p.kod]) : "—"}</TableCell>)}
                <TableCell className="whitespace-nowrap text-right">
                  <Button size="sm" variant="outline" onClick={() => setEdycja(o)}>Zmień</Button>{" "}
                  {o.id !== ja && (o.aktywne ? (
                    <Potwierdz przycisk={<Button size="sm" variant="outline" className="text-destructive">Wyłącz</Button>}
                      tytul={`Wyłączyć ${o.imie || o.email}?`}
                      skutek="Ta osoba od razu straci dostęp do wszystkich aplikacji tej firmy. Konto i historia zostają; możesz ją włączyć z powrotem."
                      tak="Wyłącz" onTak={() => router.post(`${baza}/osoba/${o.id}/`, { aktywne: false }, zachowaj)} />
                  ) : (
                    <Button size="sm" variant="outline" onClick={() => router.post(`${baza}/osoba/${o.id}/`, { aktywne: true }, zachowaj)}>Włącz</Button>
                  ))}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {zaproszenia.length > 0 && (
        <section className="space-y-2">
          <h2 className="text-lg">Czekają na przyjęcie zaproszenia</h2>
          {zaproszenia.map((z) => (
            <div key={z.id} className="flex flex-wrap items-center gap-3 rounded-lg border bg-card px-4 py-3 text-sm">
              <span className="font-medium">{z.imie || z.email}</span>
              <span className="text-muted-foreground">{z.email}</span>
              <span className="text-muted-foreground">{Object.entries(z.dostepy).map(([k, r]) => `${produkty.find((p) => p.kod === k)?.nazwa ?? k}: ${nazwaRoli(r)}`).join(", ") || "bez aplikacji"}</span>
              <span className={z.wygaslo ? "text-destructive" : "text-muted-foreground"}>{z.wygaslo ? "wygasło" : `ważne do ${z.wazne_do}`}</span>
              <span className="ml-auto flex gap-2">
                <Button size="sm" variant="outline" onClick={() => router.post(`${baza}/zaproszenie/${z.id}/wyslij/`, {}, zachowaj)}>Wyślij ponownie</Button>
                <Potwierdz przycisk={<Button size="sm" variant="outline" className="text-destructive">Anuluj</Button>}
                  tytul={`Anulować zaproszenie dla ${z.email}?`} skutek="Link z maila przestanie działać." tak="Anuluj zaproszenie"
                  onTak={() => router.post(`${baza}/zaproszenie/${z.id}/anuluj/`, {}, zachowaj)} />
              </span>
            </div>
          ))}
        </section>
      )}

      <Dialog open={zapros} onOpenChange={setZapros}>
        <DialogContent className="bg-popover">
          <DialogHeader><DialogTitle>Zaproś osobę do {firma.nazwa}</DialogTitle></DialogHeader>
          <form id="zapros" className="space-y-4" onSubmit={(e) => {
            e.preventDefault();
            router.post(`${baza}/zapros/`, nowa, { ...zachowaj, onSuccess: () => { setZapros(false); setNowa({ email: "", imie: "", wlasciciel: false, dostepy: {} }); } });
          }}>
            <div className="grid gap-3 sm:grid-cols-2">
              <Pole etykieta="E-mail"><Input type="email" required value={nowa.email} onChange={(e) => setNowa({ ...nowa, email: e.target.value })} /></Pole>
              <Pole etykieta="Imię"><Input value={nowa.imie} onChange={(e) => setNowa({ ...nowa, imie: e.target.value })} placeholder="np. Ania" /></Pole>
            </div>
            <WyborDostepow produkty={produkty} dostepy={nowa.dostepy} zmien={(d) => setNowa({ ...nowa, dostepy: d })} />
            <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={nowa.wlasciciel} onChange={(e) => setNowa({ ...nowa, wlasciciel: e.target.checked })} /> Właściciel (może zarządzać zespołem)</label>
            <p className="text-xs text-muted-foreground">Wyślemy maila z no-reply@sudomie.pl z linkiem do ustawienia hasła (ważny 7 dni).</p>
          </form>
          <DialogFooter><Button variant="outline" onClick={() => setZapros(false)}>Anuluj</Button><Button form="zapros">Wyślij zaproszenie</Button></DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={!!edycja} onOpenChange={(o) => !o && setEdycja(null)}>
        <DialogContent className="bg-popover">
          {edycja && (
            <>
              <DialogHeader><DialogTitle>{edycja.imie || edycja.email}</DialogTitle></DialogHeader>
              <WyborDostepow produkty={produkty} dostepy={edycja.dostepy} zmien={(d) => setEdycja({ ...edycja, dostepy: d })} />
              <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={edycja.wlasciciel} onChange={(e) => setEdycja({ ...edycja, wlasciciel: e.target.checked })} /> Właściciel (może zarządzać zespołem)</label>
              <DialogFooter>
                <Button variant="outline" onClick={() => setEdycja(null)}>Anuluj</Button>
                <Button onClick={() => {
                  const dostepy = Object.fromEntries(produkty.map((p) => [p.kod, edycja.dostepy[p.kod] ?? ""]));
                  router.post(`${baza}/osoba/${edycja.id}/`, { dostepy, wlasciciel: edycja.wlasciciel }, { ...zachowaj, onSuccess: () => setEdycja(null) });
                }}>Zapisz</Button>
              </DialogFooter>
            </>
          )}
        </DialogContent>
      </Dialog>
    </Strona>
  );
}
