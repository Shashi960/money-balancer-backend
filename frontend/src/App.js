import "@/App.css";
import { BrowserRouter, Routes, Route, Link, useLocation } from "react-router-dom";
import Dashboard from "@/pages/Dashboard";
import AddExpense from "@/pages/AddExpense";
import Expenses from "@/pages/Expenses";
import Debts from "@/pages/Debts";
import Settings from "@/pages/Settings";
import { Toaster } from "@/components/ui/sonner";
import { Wallet, Plus, Receipt, HandCoins, Settings as SettingsIcon } from "lucide-react";

function Navigation() {
  const location = useLocation();
  
  const navItems = [
    { path: "/", icon: Wallet, label: "Dashboard" },
    { path: "/add-expense", icon: Plus, label: "Add Expense" },
    { path: "/expenses", icon: Receipt, label: "Expenses" },
    { path: "/debts", icon: HandCoins, label: "Debts" },
    { path: "/settings", icon: SettingsIcon, label: "Settings" },
  ];
  
  return (
    <nav className="sidebar">
      <div className="sidebar-header">
        <Wallet className="sidebar-logo" size={32} />
        <h1 className="sidebar-title">Money Balancer</h1>
      </div>
      <div className="nav-links">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = location.pathname === item.path;
          return (
            <Link
              key={item.path}
              to={item.path}
              className={`nav-link ${isActive ? 'active' : ''}`}
              data-testid={`nav-${item.label.toLowerCase().replace(' ', '-')}`}
            >
              <Icon size={20} />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <Navigation />
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/add-expense" element={<AddExpense />} />
            <Route path="/debts" element={<Debts />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </main>
      </BrowserRouter>
      <Toaster />
    </div>
  );
}

export default App;