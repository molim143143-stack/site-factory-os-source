import { type ReactNode, useEffect, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Z_INDEX } from "../../constants/zIndex";

type Props = {
  open: boolean;
  anchor: HTMLElement | null;
  onClose: () => void;
  children: ReactNode;
  width?: number;
  modal?: boolean;
};

export function PortalMenu({ open, anchor, onClose, children, width = 240, modal = false }: Props) {
  const ref = useRef<HTMLDivElement | null>(null);
  const [position, setPosition] = useState({ top: 72, left: 16 });

  useLayoutEffect(() => {
    if (!open || !anchor) return;
    const rect = anchor.getBoundingClientRect();
    const nextLeft = Math.min(Math.max(12, rect.right - width), window.innerWidth - width - 12);
    setPosition({ top: rect.bottom + 10, left: nextLeft });
  }, [anchor, open, width]);

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose, open]);

  if (!open) return null;

  return createPortal(
    <>
      <button
        aria-label="Close floating layer"
        className="fixed inset-0 cursor-default bg-transparent"
        style={{ zIndex: modal ? Z_INDEX.modalOverlay : Z_INDEX.dropdown - 1 }}
        onClick={onClose}
      />
      <div
        ref={ref}
        className="fixed rounded-2xl border border-neon/25 bg-[#0A0F1C]/95 p-2 text-sm text-textMain shadow-neon backdrop-blur-2xl"
        style={{ top: position.top, left: position.left, width, zIndex: modal ? Z_INDEX.modal : Z_INDEX.dropdown }}
      >
        {children}
      </div>
    </>,
    document.body
  );
}

export function PortalModal({ open, onClose, children }: { open: boolean; onClose: () => void; children: ReactNode }) {
  if (!open) return null;
  return createPortal(
    <>
      <button className="fixed inset-0 bg-black/65 backdrop-blur-sm" style={{ zIndex: Z_INDEX.modalOverlay }} onClick={onClose} aria-label="Close modal" />
      <div className="fixed left-1/2 top-1/2 w-[min(92vw,520px)] -translate-x-1/2 -translate-y-1/2 rounded-3xl border border-neon/30 bg-[#0A0F1C]/95 p-5 shadow-neon backdrop-blur-2xl" style={{ zIndex: Z_INDEX.modal }}>
        {children}
      </div>
    </>,
    document.body
  );
}
