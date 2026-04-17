import { FormEvent, useState } from "react";

interface FragmentInputProps {
  disabled?: boolean;
  onSubmit: (text: string) => Promise<void>;
}

export function FragmentInput({ disabled, onSubmit }: FragmentInputProps) {
  const [value, setValue] = useState("");
  const [pending, setPending] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = value.trim();
    if (!trimmed) {
      return;
    }
    setPending(true);
    try {
      await onSubmit(trimmed);
      setValue("");
    } finally {
      setPending(false);
    }
  }

  return (
    <form className="fragment-form" onSubmit={handleSubmit}>
      <label htmlFor="fragment-input">Visitor fragment</label>
      <div className="fragment-row">
        <textarea
          id="fragment-input"
          value={value}
          onChange={(event) => setValue(event.target.value)}
          placeholder="Offer a phrase, tension, or interruption."
          disabled={disabled || pending}
          rows={3}
        />
        <button type="submit" disabled={disabled || pending || value.trim().length === 0}>
          {pending ? "Sending..." : "Inject fragment"}
        </button>
      </div>
    </form>
  );
}
