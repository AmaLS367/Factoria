import { useState } from 'react';
import { Dashboard } from './components/Dashboard';
import { Search } from './components/Search';
import { CollectItem } from './components/CollectItem';
import { ExcelJob } from './components/ExcelJob';
import { ItemsTable } from './components/ItemsTable';
import { Database, Search as SearchIcon, FileSpreadsheet, LayoutDashboard, DownloadCloud } from 'lucide-react';

type View = 'dashboard' | 'collect' | 'search' | 'excel' | 'items';

function App() {
  const [currentView, setCurrentView] = useState<View>('dashboard');

  const navItems: { id: View; label: string; icon: React.ReactNode }[] = [
    { id: 'dashboard', label: 'Dashboard', icon: <LayoutDashboard className="w-5 h-5 mr-3" /> },
    { id: 'collect', label: 'Single Item Collection', icon: <DownloadCloud className="w-5 h-5 mr-3" /> },
    { id: 'search', label: 'Web Search', icon: <SearchIcon className="w-5 h-5 mr-3" /> },
    { id: 'excel', label: 'Excel Job', icon: <FileSpreadsheet className="w-5 h-5 mr-3" /> },
    { id: 'items', label: 'Items Database', icon: <Database className="w-5 h-5 mr-3" /> },
  ];

  return (
    <div className="flex h-screen bg-neutral-50 font-sans text-neutral-900">
      {/* Sidebar */}
      <div className="w-64 bg-white border-r border-neutral-200 flex flex-col shadow-sm z-10">
        <div className="h-16 flex items-center px-6 border-b border-neutral-200">
          <Database className="w-6 h-6 text-indigo-600 mr-2" />
          <h1 className="text-xl font-bold text-neutral-800 tracking-tight">Factoria</h1>
        </div>
        <nav className="flex-1 overflow-y-auto py-4">
          <ul className="space-y-1 px-3">
            {navItems.map((item) => (
              <li key={item.id}>
                <button
                  onClick={() => setCurrentView(item.id)}
                  className={`w-full flex items-center px-3 py-2.5 text-sm font-medium rounded-md transition-colors ${
                    currentView === item.id
                      ? 'bg-indigo-50 text-indigo-700'
                      : 'text-neutral-600 hover:bg-neutral-100 hover:text-neutral-900'
                  }`}
                >
                  <span className={currentView === item.id ? 'text-indigo-600' : 'text-neutral-400'}>
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
        <header className="h-16 bg-white border-b border-neutral-200 flex items-center px-8 shadow-sm">
          <h2 className="text-lg font-semibold text-neutral-800">
            {navItems.find((i) => i.id === currentView)?.label}
          </h2>
        </header>

        <main className="flex-1 overflow-y-auto p-8 bg-[#f9fafb]">
          {currentView === 'dashboard' && <Dashboard />}
          {currentView === 'collect' && <CollectItem />}
          {currentView === 'search' && <Search />}
          {currentView === 'excel' && <ExcelJob />}
          {currentView === 'items' && <ItemsTable />}
        </main>
      </div>
    </div>
  );
}

export default App;
