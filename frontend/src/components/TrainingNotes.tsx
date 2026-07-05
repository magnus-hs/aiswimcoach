import { useState, useEffect, FormEvent } from 'react';
import { createNote, getNotes, deleteNote, TrainingNote } from '../api/notesService';
import { formatRelativeTime } from '../utils/relativeTime';
import './TrainingNotes.css';

/**
 * TrainingNotes — allows swimmers to add, view, and delete personal training notes.
 * Notes are displayed in reverse chronological order (most recent first).
 */
export function TrainingNotes() {
  const [notes, setNotes] = useState<TrainingNote[]>([]);
  const [text, setText] = useState('');
  const [loading, setLoading] = useState(false);
  const [fetchLoading, setFetchLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function fetchNotes() {
      try {
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

    // Optimistic removal
    setNotes(prev => prev.filter(n => n.note_id !== noteId));
    setError(null);

    try {
      await deleteNote(noteId);
    } catch (err) {
      // Rollback on failure
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
    <section className="training-notes" aria-label="Training Notes">
      <h2 className="training-notes__heading">Training Notes</h2>
      <p className="training-notes__subtitle">
        Record observations about injuries, group changes, or anything the coach should know
      </p>

      {error && (
        <div className="training-notes__error" role="alert">
          {error}
        </div>
      )}

      <form className="training-notes__input-section" onSubmit={handleSubmit}>
        <textarea
          className="training-notes__textarea"
          placeholder="Add a training note..."
          value={text}
          onChange={(e) => setText(e.target.value)}
          maxLength={500}
          disabled={loading}
        />
        <div className="training-notes__input-footer">
          <span className="training-notes__char-count">
            {text.length}/500
          </span>
          <button
            type="submit"
            className="training-notes__submit-btn"
            disabled={isSubmitDisabled}
          >
            {loading ? 'Adding...' : 'Add Note'}
          </button>
        </div>
      </form>

      {fetchLoading ? (
        <div className="training-notes__loading">Loading notes...</div>
      ) : notes.length === 0 ? (
        <p className="training-notes__empty">No notes yet. Add one above to get started.</p>
      ) : (
        <ul className="training-notes__list">
          {notes.map(note => (
            <li key={note.note_id} className="training-notes__note">
              <p className="training-notes__note-text">{note.text}</p>
              <span className="training-notes__note-time">
                {formatRelativeTime(note.timestamp)}
              </span>
              <button
                className="training-notes__note-delete"
                onClick={() => handleDelete(note.note_id)}
                aria-label="Delete note"
                title="Delete note"
              >
                ×
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
