import { NavLink, Outlet } from "react-router-dom";

export default function App() {
  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-border bg-surface/70 backdrop-blur sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-baseline gap-2">
            <span className="text-xl font-extrabold tracking-tight text-ink">
              kms
            </span>
            <span className="text-[11px] text-muted uppercase tracking-[0.2em]">
              dashboard
            </span>
          </div>
          <nav className="flex items-center gap-1">
            <NavItem to="/" end>
              Dashboard
            </NavItem>
            <NavItem to="/prompts">Prompts</NavItem>
          </nav>
        </div>
      </header>
      <main className="flex-1">
        <div className="max-w-4xl mx-auto px-6 py-10">
          <Outlet />
        </div>
      </main>
      <footer className="border-t border-border py-6 text-center text-xs text-subtle">
        local · 127.0.0.1
      </footer>
    </div>
  );
}

function NavItem({
  to,
  end,
  children,
}: {
  to: string;
  end?: boolean;
  children: React.ReactNode;
}) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        [
          "px-3 py-1.5 rounded-full text-sm transition",
          isActive
            ? "bg-accent-soft text-accent"
            : "text-muted hover:text-ink hover:bg-bg",
        ].join(" ")
      }
    >
      {children}
    </NavLink>
  );
}
