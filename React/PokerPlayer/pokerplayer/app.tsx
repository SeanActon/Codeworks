import { createRoot } from "react-dom/client";
import CardTable from "./components/CardTable";
import "./style.css";

const rootElement = document.getElementById("root");

if (!rootElement) {
  throw new Error('Root element "#root" was not found.');
}

createRoot(rootElement).render(<CardTable />);
