import { useEffect, useRef, type ReactNode } from "react";

type DrawerProps = {
  open: boolean;
  onClose: () => void;
  title: string;
  side?: "left" | "right";
  width?: string;
  showBackdrop?: boolean;
  children: ReactNode;
};

export function Drawer({ open, onClose, title, side = "right", width = "380px", showBackdrop = true, children }: DrawerProps) {
  const panelRef = useRef<HTMLElement>(null);

  useEffect(() => {
    if (open) {
      panelRef.current?.focus();
    }
  }, [open]);

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape" && open) {
        onClose();
      }
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [open, onClose]);

  return (
    <>
      {open && showBackdrop ? (
        <div
          className="drawer-backdrop"
          onClick={onClose}
          aria-hidden="true"
        />
      ) : null}
      <aside
        ref={panelRef}
        className={`drawer drawer-${side} ${open ? "drawer-open" : ""}`}
        style={{ width }}
        role="dialog"
        aria-modal={open}
        aria-label={title}
        aria-hidden={!open}
        tabIndex={-1}
      >
        <header className="drawer-header">
          <h2 className="drawer-title">{title}</h2>
          <button
            className="drawer-close"
            onClick={(e) => {
              e.stopPropagation();
              onClose();
            }}
            aria-label="Fechar painel"
            type="button"
          >
            ✕
          </button>
        </header>
        <div className="drawer-body">
          {children}
        </div>
      </aside>
    </>
  );
}
