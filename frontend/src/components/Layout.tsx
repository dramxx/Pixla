import { useEffect } from "react";
import { Link, useLocation } from "react-router-dom";
import { Palette, History } from "lucide-react";
import { useSystemStatusStore } from "@/store/status";

interface LayoutProps {
  children: React.ReactNode;
}

export function Layout({ children }: LayoutProps) {
  const location = useLocation();
  const { modelAvailable, llmAvailable, storageWritable, checkStatus } = useSystemStatusStore();

  useEffect(() => {
    checkStatus();
  }, []);

  const isActive = (path: string) => location.pathname === path;
  const isReady = modelAvailable && llmAvailable && storageWritable;

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
          <div className="status-indicator" title={`Model: ${modelAvailable ? 'OK' : 'Missing'} | LLM: ${llmAvailable ? 'OK' : 'Missing'} | Disk: ${storageWritable ? 'OK' : 'Error'}`}>
            <span className={`status-dot ${isReady ? 'success' : 'error'}`}></span>
            <span className="status-label">{isReady ? 'Ready' : 'Not Ready'}</span>
          </div>
        </div>
      </nav>
      <main className="main">{children}</main>
    </div>
  );
}
