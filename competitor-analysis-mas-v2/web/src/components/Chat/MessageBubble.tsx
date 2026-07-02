// web/src/components/Chat/MessageBubble.tsx

import type { Message } from "../../types/events";

interface Props {
  message: Message;
}

export function MessageBubble({ message }: Props) {
  if (message.role === "system") {
    return (
      <div className="message-row system">
        <div className="message-bubble system">{message.content}</div>
      </div>
    );
  }

  return (
    <div className={`message-row ${message.role}`}>
      <div className={`message-bubble ${message.role}`}>
        {message.content}
      </div>
    </div>
  );
}
