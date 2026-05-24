"use client";

import { useState } from "react";
import { SAMPLE_PAPER } from "@/lib/sample";

interface Props {
  onSubmit: (title: string, text: string) => void;
  loading: boolean;
}

export default function UploadBox({ onSubmit, loading }: Props) {
  const [title, setTitle] = useState("");
  const [text, setText] = useState("");

  function handleFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => setText(String(reader.result ?? ""));
    reader.readAsText(file);
  }

  return (
    <div className="panel area-left">
      <h2>Input</h2>
      <p className="muted" style={{ marginTop: 0 }}>
        Paste a paper (.txt / .md) or upload a file. Offline &amp; deterministic.
      </p>
      <input
        type="text"
        placeholder="Optional title"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
      />
      <textarea
        placeholder="Paste paper text here..."
        value={text}
        onChange={(e) => setText(e.target.value)}
      />
      <div className="row">
        <button
          onClick={() => onSubmit(title, text)}
          disabled={loading || text.trim() === ""}
        >
          {loading ? "Reviewing..." : "Review"}
        </button>
        <button
          className="secondary"
          onClick={() => setText(SAMPLE_PAPER)}
          disabled={loading}
        >
          Load sample
        </button>
        <input
          type="file"
          accept=".md,.txt,.markdown,text/plain"
          onChange={handleFile}
          aria-label="Upload paper file"
        />
      </div>
    </div>
  );
}
