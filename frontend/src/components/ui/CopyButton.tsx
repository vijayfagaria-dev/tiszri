import { useState } from "react";
import { Copy } from "lucide-react";

export function CopyButton({
  value,
  label = "Copy link",
}: {
  value: string;
  label?: string;
}) {
  const [message, setMessage] = useState("");
  return (
    <span className="copy-control">
      <button
        className="ghost"
        onClick={async () => {
          try {
            await navigator.clipboard.writeText(value);
            setMessage("Copied");
          } catch {
            setMessage(
              "Clipboard unavailable. Select and copy the text below.",
            );
          }
        }}
      >
        <Copy size={14} />
        {label}
      </button>
      <span role="status" className="copy-feedback">
        {message}
      </span>
      {message.startsWith("Clipboard") && (
        <textarea readOnly aria-label="Text to copy" value={value} />
      )}
    </span>
  );
}
