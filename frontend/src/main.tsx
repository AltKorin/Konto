import "./index.css";
import { createInertiaApp } from "@inertiajs/react";
import { createRoot } from "react-dom/client";

createInertiaApp({
  resolve: (nazwa) => {
    const strony = import.meta.glob("./pages/*.tsx", { eager: true });
    return strony[`./pages/${nazwa}.tsx`] as never;
  },
  setup({ el, App, props }) {
    createRoot(el).render(<App {...props} />);
  },
  progress: { color: "#33ff99" },
});
