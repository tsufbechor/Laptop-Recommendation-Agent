import { useCallback, useState } from "react";
import { SendHorizontal } from "lucide-react";

import { Button } from "../ui/button";
import { Textarea } from "../ui/textarea";

interface InputBoxProps {
  onSend: (message: string) => void;
  disabled?: boolean;
}

const MAX_CHARACTERS = 600;

const InputBox: React.FC<InputBoxProps> = ({ onSend, disabled = false }) => {
  const [message, setMessage] = useState("");

  const handleSubmit = useCallback(() => {
    if (!message.trim()) {
      return;
    }
    onSend(message.trim());
    setMessage("");
  }, [message, onSend]);

  const handleKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-3">
      <Textarea
        value={message}
        onChange={(event) => setMessage(event.target.value.slice(0, MAX_CHARACTERS))}
        onKeyDown={handleKeyDown}
        placeholder="Describe how you'll use your laptop, budget, GPU needs, etc."
        disabled={disabled}
      />
      <div className="mt-2 flex items-center justify-between text-xs text-slate-500">
        <span>{message.length}/{MAX_CHARACTERS}</span>
        <Button onClick={handleSubmit} disabled={!message.trim() || disabled} className="gap-2" size="sm">
          Send
          <SendHorizontal className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
};

export default InputBox;
