import { useState, useEffect, FormEvent } from 'react';
import './AICoachChat.css';

interface AICoachChatProps {
  /** Optional current session context to send with prompts */
  currentSession?: {
    total_distance_m?: number;
    pace?: number;
    swolf?: number;
    stroke_rate?: number;
  } | null;
  /** Externally set prompt (from parent clicking an example) */
  externalPrompt?: string;
}

interface Message {
  role: 'user' | 'assistant';
  text: string;
}

/**
 * AI coaching chat — interactive analysis of current session and historical trends.
 * Clicking a suggestion populates the input box for the user to edit or send.
 */
export function AICoachChat({ currentSession, externalPrompt }: AICoachChatProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);

  // When an external prompt is set (from clicking an example), populate the input
  useEffect(() => {
    if (externalPrompt) {
      setInput(externalPrompt);
    }
  }, [externalPrompt]);

  const sendMessage = async (prompt: string) => {
    if (!prompt.trim() || loading) return;

    const userMsg: Message = { role: 'user', text: prompt };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const token = localStorage.getItem('auth_token');
      const response = await fetch(`${import.meta.env.VITE_API_ENDPOINT}/ai/chat`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          prompt,
          current_session: currentSession || undefined,
        }),
      });

      if (!response.ok) {
        throw new Error('AI unavailable');
      }

      const data = await response.json();
      const aiMsg: Message = { role: 'assistant', text: data.response };
      setMessages(prev => [...prev, aiMsg]);
    } catch {
      const errMsg: Message = { role: 'assistant', text: 'Sorry, I couldn\'t analyse that right now. Please try again.' };
      setMessages(prev => [...prev, errMsg]);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    sendMessage(input);
  };

  return (
    <section className="ai-chat" aria-label="AI Coach Analysis">
      <h2 className="ai-chat__heading">AI Coach</h2>
      <p className="ai-chat__subtitle">
        Ask about your performance, trends, or how you compare to others in your age group
      </p>

      <form className="ai-chat__form" onSubmit={handleSubmit}>
        <input
          className="ai-chat__input"
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask your AI coach..."
          disabled={loading}
        />
        <button className="ai-chat__send" type="submit" disabled={loading || !input.trim()}>
          Send
        </button>
      </form>

      {messages.length > 0 && (
        <div className="ai-chat__messages">
          {messages.map((msg, i) => (
            <div key={i} className={`ai-chat__message ai-chat__message--${msg.role}`}>
              <span className="ai-chat__message-label">
                {msg.role === 'user' ? 'You' : 'Coach'}
              </span>
              <p className="ai-chat__message-text">{msg.text}</p>
            </div>
          ))}
          {loading && (
            <div className="ai-chat__message ai-chat__message--assistant">
              <span className="ai-chat__message-label">Coach</span>
              <p className="ai-chat__message-text ai-chat__message-text--loading">Analysing...</p>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
