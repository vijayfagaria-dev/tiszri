import { useEffect, useRef } from "react";
import { ScanLine, X } from "lucide-react";
import type { DayAnalysis, Interval } from "../../api/schemas";
import { Inspector } from "./Inspector";

export function ResponsiveInspector({
  interval,
  data,
}: {
  interval: Interval;
  data: DayAnalysis;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const desktop = matchMedia("(min-width: 801px)");
    const closeOnDesktop = () => {
      if (desktop.matches) dialog.current?.close();
    };
    desktop.addEventListener("change", closeOnDesktop);
    return () => desktop.removeEventListener("change", closeOnDesktop);
  }, []);
  return (
    <div className="inspector-host">
      <Inspector interval={interval} data={data} />
      <button
        className="mobile-inspector-trigger"
        onClick={() => dialog.current?.showModal()}
      >
        <ScanLine size={17} />
        Inspect interval {interval.settlementPeriod}
      </button>
      <dialog
        className="evidence-dialog"
        ref={dialog}
        aria-label="Selected interval evidence"
      >
        <button
          className="dialog-close"
          aria-label="Close interval evidence"
          onClick={() => dialog.current?.close()}
        >
          <X size={18} />
          Close
        </button>
        <Inspector
          interval={interval}
          data={data}
          id="mobile-interval-inspector"
        />
      </dialog>
    </div>
  );
}
