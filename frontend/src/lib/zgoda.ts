// GA4 z Consent Mode v2, tylko strony publiczne (start, regulamin) — ten sam kontrakt co agenda i fc.sudomie.pl:
// wszystko odrzucone do „Akceptuję”, wybór w localStorage "cc". Brak identyfikatora = brak tagu.
declare global {
  interface Window {
    dataLayer: unknown[];
    gtag: (...args: unknown[]) => void;
  }
}

export type Wybor = "accepted" | "declined" | null;

export function wybor(): Wybor {
  try {
    const v = localStorage.getItem("cc");
    return v === "accepted" || v === "declined" ? v : null;
  } catch {
    return null;
  }
}

let uruchomione = "";

export function uruchomAnalityke(id: string) {
  if (!id || uruchomione) return;
  uruchomione = id;
  window.dataLayer = window.dataLayer || [];
  window.gtag = function () {
    // gtag.js czyta obiekt arguments, nie kopię tablicy
    // eslint-disable-next-line prefer-rest-params
    window.dataLayer.push(arguments);
  };
  window.gtag("consent", "default", { analytics_storage: "denied", ad_storage: "denied", ad_user_data: "denied", ad_personalization: "denied" });
  if (wybor() === "accepted") window.gtag("consent", "update", { analytics_storage: "granted" });
  window.gtag("js", new Date());
  window.gtag("config", id);
  const s = document.createElement("script");
  s.async = true;
  s.src = `https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(id)}`;
  document.head.append(s);
}

export function wybierz(w: Exclude<Wybor, null>) {
  try {
    localStorage.setItem("cc", w);
  } catch {
    /* tryb prywatny: baner wróci przy następnej wizycie */
  }
  window.gtag?.("consent", "update", { analytics_storage: w === "accepted" ? "granted" : "denied" });
  if (w === "declined") {
    // wycofanie tak łatwe jak zgoda (art. 7 ust. 3 RODO): kasujemy ciasteczka, które GA już zapisał
    const rodzic = location.hostname.split(".").slice(-2).join(".");
    for (const n of document.cookie.split("; ").map((c) => c.split("=")[0]).filter((n) => n.startsWith("_ga"))) {
      for (const d of ["", `; domain=.${rodzic}`]) document.cookie = `${n}=; Max-Age=0; path=/${d}`;
    }
  }
}
