import { useState, useEffect } from "react";
import { Dashboard } from "./components/Dashboard";
import { Search } from "./components/Search";
import { CollectItem } from "./components/CollectItem";
import { ExcelJob } from "./components/ExcelJob";
import { ItemsTable } from "./components/ItemsTable";
import { Logs } from "./components/Logs";
import { Templates } from "./components/Templates";
import type { SchemaTemplate } from "./types";
import {
  Database,
  Search as SearchIcon,
  FileSpreadsheet,
  LayoutDashboard,
  DownloadCloud,
  Moon,
  Sun,
  ScrollText,
  LayoutTemplate,
} from "lucide-react";

type View =
  | "dashboard"
  | "collect"
  | "search"
  | "excel"
  | "items"
  | "logs"
  | "templates";

function App() {
  const [currentView, setCurrentView] = useState<View>("dashboard");
  const [pendingTemplate, setPendingTemplate] = useState<
    SchemaTemplate | undefined
  >();
  const [dark, setDark] = useState<boolean>(
    () => localStorage.getItem("theme") === "dark",
  );

  useEffect(() => {
    const root = document.documentElement;
    if (dark) {
      root.classList.add("dark");
    } else {
      root.classList.remove("dark");
    }
    localStorage.setItem("theme", dark ? "dark" : "light");
  }, [dark]);

  const navItems: { id: View; label: string; icon: React.ReactNode }[] = [
    {
      id: "dashboard",
      label: "Dashboard",
      icon: <LayoutDashboard className="w-5 h-5 mr-3" />,
    },
    {
      id: "templates",
      label: "Templates",
      icon: <LayoutTemplate className="w-5 h-5 mr-3" />,
    },
    {
      id: "collect",
      label: "Single Item Collection",
      icon: <DownloadCloud className="w-5 h-5 mr-3" />,
    },
    {
      id: "search",
      label: "Web Search",
      icon: <SearchIcon className="w-5 h-5 mr-3" />,
    },
    {
      id: "excel",
      label: "Excel Job",
      icon: <FileSpreadsheet className="w-5 h-5 mr-3" />,
    },
    {
      id: "items",
      label: "Items Database",
      icon: <Database className="w-5 h-5 mr-3" />,
    },
    {
      id: "logs",
      label: "Logs",
      icon: <ScrollText className="w-5 h-5 mr-3" />,
    },
  ];

  return (
    <div className="flex h-screen bg-neutral-50 dark:bg-neutral-950 font-sans text-neutral-900 dark:text-neutral-100">
      {/* Sidebar */}
      <div className="w-64 bg-white dark:bg-neutral-900 border-r border-neutral-200 dark:border-neutral-700 flex flex-col shadow-sm z-10">
        <div className="h-16 flex items-center px-6 border-b border-neutral-200 dark:border-neutral-700">
          <img
            src="/favicon.svg"
            className="w-8 h-8 mr-2"
            alt="Factoria logo"
          />
          <h1 className="text-xl font-bold text-neutral-800 dark:text-neutral-100 tracking-tight">
            Factoria
          </h1>
        </div>
        <nav className="flex-1 overflow-y-auto py-4">
          <ul className="space-y-1 px-3">
            {navItems.map((item) => (
              <li key={item.id}>
                <button
                  onClick={() => setCurrentView(item.id)}
                  className={`w-full flex items-center px-3 py-2.5 text-sm font-medium rounded-md transition-colors ${
                    currentView === item.id
                      ? "bg-indigo-50 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300"
                      : "text-neutral-600 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-800 hover:text-neutral-900 dark:hover:text-neutral-100"
                  }`}
                >
                  <span
                    className={
                      currentView === item.id
                        ? "text-indigo-600 dark:text-indigo-400"
                        : "text-neutral-400 dark:text-neutral-500"
                    }
                  >
                    {item.icon}
                  </span>
                  {item.label}
                </button>
              </li>
            ))}
          </ul>
        </nav>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <header className="h-16 bg-white dark:bg-neutral-900 border-b border-neutral-200 dark:border-neutral-700 flex items-center justify-between px-8 shadow-sm">
          <h2 className="text-lg font-semibold text-neutral-800 dark:text-neutral-100">
            {navItems.find((i) => i.id === currentView)?.label}
          </h2>
          <button
            onClick={() => setDark((d) => !d)}
            className="p-2 rounded-md text-neutral-500 dark:text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors"
            aria-label={dark ? "Switch to light mode" : "Switch to dark mode"}
          >
            {dark ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
          </button>
        </header>

        <main className="flex-1 overflow-y-auto p-8 bg-[#f9fafb] dark:bg-neutral-950">
          {currentView === "dashboard" && <Dashboard />}
          {currentView === "collect" && <CollectItem />}
          {currentView === "search" && <Search />}
          {currentView === "templates" && (
            <Templates
              onUseTemplate={(t) => {
                setPendingTemplate(t);
                setCurrentView("excel");
              }}
            />
          )}
          {currentView === "excel" && (
            <ExcelJob
              initialTemplate={pendingTemplate}
              onTemplateClear={() => setPendingTemplate(undefined)}
            />
          )}
          {currentView === "items" && <ItemsTable />}
          {currentView === "logs" && <Logs />}
        </main>
      </div>
    </div>
  );
}

export default App;
