import { useState, useEffect, FormEvent } from 'react';
import { createNote, getNotes, deleteNote, TrainingNote } from '../api/notesService';
import { formatRelativeTime } from '../utils/relativeTime';
import './SessionNotesSection.css';

interface SessionNotesSectionProps {
  sessionId: string;
}

/**
 * SessionNotesSection — per-swim notes displayed on the Activity Detail page.
 * Shows notes tied to a specific session, positioned above the InteractionsPanel.
 */
export function SessionNotesSection({ sessionId }: SessionNotesSectionProps) {
  const [notes, setNotes] = useState<TrainingNote[]>([]);
  const [text, setText] = useState('');
  const [loading, setLoading] = useState(false);
  const [fetchLoading, setFetchLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function fetchSessionNotes() {
      try {
        const data = await getNotes(sessionId);
        if (!cancelled) {
          setNotes(data);
          setFetchLoading(false);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load session notes.');
          setFetchLoading(false);
        }
      }
    }

    fetchSessionNotes();
    return () => { cancelled = true; };
  }, [sessionId]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const trimmed = text.trim();
    if (!trimmed || loading) return;

    setLoading(true);
    setError(null);

    try {
      const newNote = await createNote(trimmed, sessionId);
      setNotes(prev => [newNote, ...prev]);
      setText('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add note. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (noteId: string) => {
    const noteIndex = notes.findIndex(n => n.note_id === noteId);
    if (noteIndex === -1) return;

    const removedNote = notes[noteIndex];
    setNotes(prev => prev.filter(n => n.note_id !== noteId));
    setError(null);

    try {
      await deleteNote(noteId);
    } catch (err) {
      setNotes(prev => {
        const restored = [...prev];
        restored.splice(noteIndex, 0, removedNote);
        return restored;
      });
      setError(err instanceof Error ? err.message : 'Failed to delete note. Please try again.');
    }
  };

  const isSubmitDisabled = !text.trim() || loading;

  return (
    <section className="session-notes" aria-label="Session Notes">
      <h3 className="session-notes__heading">Session Notes</h3>

      {error && (
        <div className="session-notes__error" role="alert">
          {error}
        </div>
      )}

      <form className="session-notes__form" onSubmit={handleSubmit}>
        <textarea
          className="session-notes__textarea"
          placeholder="Add a note about this session..."
          value={text}
          onChange={(e) => setText(e.target.value)}
          maxLength={500}
          disabled={loading}
        />
        <div className="session-notes__form-footer">
          <span className="session-notes__char-count">{text.length}/500</span>
          <button
            type="submit"
            className="session-notes__submit-btn"
            disabled={isSubmitDisabled}
          >
            {loading ? 'Adding...' : 'Add Note'}
          </button>
        </div>
      </form>

      {fetchLoading ? (
        <div className="session-notes__loading">Loading notes...</div>
      ) : notes.length > 0 ? (
        <ul className="session-notes__list">
          {notes.map(note => (
            <li key={note.note_id} className="session-notes__note">
              <p className="session-notes__note-text">{note.text}</p>
              <div className="session-notes__note-meta">
                <span className="session-notes__note-time">
                  {formatRelativeTime(note.timestamp)}
                </span>
                <button
                  className="session-notes__note-delete"
                  onClick={() => handleDelete(note.note_id)}
                  aria-label="Delete note"
                  title="Delete note"
                >
                  ×
                </button>
              </div>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}
