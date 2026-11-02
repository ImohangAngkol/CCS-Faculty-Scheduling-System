import {useId, useRef, useState} from "react";
import {NavLink} from "react-router-dom";
import "./dashboardLayout.css";

type SidebarItem = {label: string; path: string};
type SidebarProps = {title: string; role: "Admin" | "Faculty"; items: SidebarItem[]};

export default function Sidebar({title, role, items}: SidebarProps) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const panelId = useId();
  const toggle = useRef<HTMLButtonElement>(null);
  function closeNavigation() {
    setMobileOpen(false);
    if (window.matchMedia("(max-width: 767px)").matches) toggle.current?.focus();
  }
  return <aside className="dashboard-sidebar" aria-label={`${role} sidebar`} onKeyDown={event => {
    if (event.key === "Escape" && mobileOpen) {event.preventDefault(); closeNavigation();}
  }}>
    <div className="dashboard-sidebar-brand">
      <div className="dashboard-sidebar-logo" aria-hidden="true">CCS</div>
      <div className="min-w-0">
        <h1 className="dashboard-sidebar-title">{title}</h1>
        <p className="dashboard-sidebar-subtitle">BS Information Technology</p>
        <span className="dashboard-sidebar-portal">{role} Portal</span>
      </div>
      <button ref={toggle} type="button" className="dashboard-navigation-toggle" aria-controls={panelId}
        aria-expanded={mobileOpen} aria-label={mobileOpen ? "Close navigation" : "Open navigation"}
        onClick={() => setMobileOpen(open => !open)}>{mobileOpen ? "Close" : "Menu"}</button>
    </div>
    <div id={panelId} className="dashboard-sidebar-panel" data-open={mobileOpen}>
      <nav aria-label={`${role} navigation`} className="dashboard-navigation">
        {items.map(item => <NavLink key={item.path} to={item.path} end={item.path === "/admin" || item.path === "/faculty"}
          onClick={closeNavigation} className={({isActive}) => `dashboard-navigation-link${isActive ? " dashboard-navigation-active" : ""}`}>
          {item.label}
        </NavLink>)}
      </nav>
      <div className="dashboard-sidebar-footer">
        <div className="flex items-center gap-2" aria-hidden="true"><span className="h-2 w-8 rounded-full bg-[#9D174D]"/><span className="h-2 w-8 rounded-full bg-[#EAB308]"/></div>
        <p className="mt-3 text-xs leading-5 text-teal-200">MSU-IIT<br/>College of Computer Studies</p>
      </div>
    </div>
  </aside>;
}
