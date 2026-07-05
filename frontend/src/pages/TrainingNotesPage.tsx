import { useState, useEffect, FormEvent } from 'react';
import { createNote, getNotes, deleteNote, TrainingNote } from '../api/notesService';
import { formatRelativeTime } from '../utils/relativeTime';
import './TrainingNotesPage.css';

/**
 * Dedicated Training Notes page — accessible from Profile dropdown at /notes.
 * Displays an explanatory section about how notes help the AI coach,
 * plus a form and list of global notes (not tied to any session).
 */
export function TrainingNotesPage() {
  const [notes, setNotes] = useState<TrainingNote[]>([]);
  const [text, setText] = useState('');
  const [loading, setLoading] = useState(false);
  const [fetchLoading, setFetchLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function fetchNotes() {
      try {
        // No sessionId → returns only global notes
        const data = await getNotes();
        if (!cancelled) {
          setNotes(data.slice(0, 50));
          setFetchLoading(false);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load notes.');
          setFetchLoading(false);
        }
      }
    }

    fetchNotes();
    return () => { cancelled = true; };
  }, []);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const trimmed = text.trim();
    if (!trimmed || loading) return;

    setLoading(true);
    setError(null);

    try {
      const newNote = await createNote(trimmed);
      setNotes(prev => [newNote, ...prev].slice(0, 50));
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
    <div className="training-notes-page">
      <header className="training-notes-page__header">
        <h1>Training Notes</h1>
        <p className="training-notes-page__description">
          Record observations about injuries, training group changes, illness, or anything 
          that might affect your swimming. The AI coach reads these notes when answering 
          your questions, helping it understand context behind changes in your performance.
        </p>
        <div className="training-notes-page__info-box">
          <span className="training-notes-page__info-icon" aria-hidden="true">💡</span>
          <p>
            <strong>How it works:</strong> When you ask the AI coach a question, it includes 
            your recent notes as context. This helps the coach explain anomalies — like a 
            sudden drop in pace after an injury, or improved times after switching groups.
          </p>
        </div>
      </header>

      {error && (
        <div className="training-notes-page__error" role="alert">
          {error}
        </div>
      )}

      <form className="training-notes-page__form" onSubmit={handleSubmit}>
        <textarea
          className="training-notes-page__textarea"
          placeholder="Add a training note..."
          value={text}
          onChange={(e) => setText(e.target.value)}
          maxLength={500}
          disabled={loading}
        />
        <div className="training-notes-page__form-footer">
          <span className="training-notes-page__char-count">
            {text.length}/500
          </span>
          <button
            type="submit"
            className="training-notes-page__submit-btn"
            disabled={isSubmitDisabled}
          >
            {loading ? 'Adding...' : 'Add Note'}
          </button>
        </div>
      </form>

      <section className="training-notes-page__list-section">
        <h2>Your Notes</h2>
        {fetchLoading ? (
          <div className="training-notes-page__loading">Loading notes...</div>
        ) : notes.length === 0 ? (
          <p className="training-notes-page__empty">
            No notes yet. Add one above to help your AI coach understand your training context.
          </p>
        ) : (
          <ul className="training-notes-page__list">
            {notes.map(note => (
              <li key={note.note_id} className="training-notes-page__note">
                <p className="training-notes-page__note-text">{note.text}</p>
                <div className="training-notes-page__note-meta">
                  <span className="training-notes-page__note-time">
                    {formatRelativeTime(note.timestamp)}
                  </span>
                  <button
                    className="training-notes-page__note-delete"
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
        )}
      </section>
    </div>
  );
}
