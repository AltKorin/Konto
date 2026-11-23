export type Wspolne = {
  osoba: { imie: string; email: string } | null;
  komunikaty: { tekst: string; poziom: string }[];
  ga: string;
};
export type Bledy = Record<string, string>;
