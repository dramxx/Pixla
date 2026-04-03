import React from "react";
import { Link, useLocation } from "react-router-dom";
import { Palette, History, Sun, Moon } from "lucide-react";
import { useThemeStore } from "@/store/theme";

interface LayoutProps {
  children: React.ReactNode;
}

export function Layout({ children }: LayoutProps) {
  const { isDark, toggle } = useThemeStore();
  const location = useLocation();

  const isActive = (path: string) => location.pathname === path;

  return (
    <div className="min-h-screen bg-primary">
      <nav className="nav">
        <div className="nav-container">
          <div className="flex items-center gap-6">
            <Link to="/" className="nav-logo">
              🖌️ Pixla
            </Link>
            <div className="nav-links">
              <Link
                to="/"
                className={`nav-link ${isActive("/") ? "active" : ""}`}
              >
                Generate
              </Link>
              <Link
                to="/palettes"
                className={`nav-link ${isActive("/palettes") ? "active" : ""}`}
              >
                <Palette size={16} />
                Palettes
              </Link>
              <Link
                to="/history"
                className={`nav-link ${isActive("/history") ? "active" : ""}`}
              >
                <History size={16} />
                History
              </Link>
            </div>
          </div>
          <button
            onClick={toggle}
            className="theme-toggle"
            aria-label="Toggle theme"
          >
            {isDark ? <Sun size={18} /> : <Moon size={18} />}
          </button>
        </div>
      </nav>
      <main className="main">{children}</main>
    </div>
  );
}
