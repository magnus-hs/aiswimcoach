import { useState, useEffect, useCallback } from 'react';
import {
  getInteractions,
  addComment,
  deleteComment,
  toggleKudos,
  Comment,
} from '../api/interactionsService';
import { KudosIcon } from './KudosIcon';
import './InteractionsPanel.css';

export interface InteractionsPanelProps {
  sessionId: string;
  isOwner: boolean;
  canInteract: boolean;
}

/**
 * Format a timestamp into a relative time string.
 */
function relativeTime(isoString: string): string {
  const now = Date.now();
  const then = new Date(isoString).getTime();
  const diffMs = now - then;

  if (diffMs < 0 || diffMs < 60_000) return 'just now';

  const minutes = Math.floor(diffMs / 60_000);
  if (minutes < 60) return `${minutes} min ago`;

  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} hour${hours > 1 ? 's' : ''} ago`;

  const days = Math.floor(hours / 24);
  return `${days} day${days > 1 ? 's' : ''} ago`;
}

/**
 * InteractionsPanel — displays kudos + comments for a swim session.
 * Handles optimistic kudos toggle, comment submission, and deletion with confirmation.
 */
export function InteractionsPanel({ sessionId, isOwner, canInteract }: InteractionsPanelProps) {
  const [comments, setComments] = useState<Comment[]>([]);
  const [kudosCount, setKudosCount] = useState(0);
  const [userHasKudos, setUserHasKudos] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Comment input state
  const [commentText, setCommentText] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);

  // Current user id from localStorage
  const currentUserId = localStorage.getItem('user_id') || '';

  const fetchInteractions = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getInteractions(sessionId);
      setComments(data.comments);
      setKudosCount(data.kudos_count);
      setUserHasKudos(data.user_has_kudos);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load interactions.');
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    fetchInteractions();
  }, [fetchInteractions]);

  // --- Kudos toggle (optimistic) ---
  const handleKudosToggle = async () => {
    const prevHasKudos = userHasKudos;
    const prevCount = kudosCount;

    // Optimistic update
    setUserHasKudos(!prevHasKudos);
    setKudosCount(prevHasKudos ? prevCount - 1 : prevCount + 1);

    try {
      const result = await toggleKudos(sessionId);
      setKudosCount(result.kudos_count);
      setUserHasKudos(result.action === 'added');
    } catch {
      // Revert on failure
      setUserHasKudos(prevHasKudos);
      setKudosCount(prevCount);
    }
  };

  // --- Comment submission ---
  const handleSubmitComment = async () => {
    const trimmed = commentText.trim();
    if (trimmed.length === 0) {
      setValidationError('Comment cannot be empty.');
      return;
    }
    if (trimmed.length > 500) {
      setValidationError('Comment must be 500 characters or fewer.');
      return;
    }

    setValidationError(null);
    setSubmitting(true);
    try {
      const newComment = await addComment(sessionId, trimmed);
      setComments((prev) => [...prev, newComment]);
      setCommentText('');
    } catch (err: unknown) {
      setValidationError(err instanceof Error ? err.message : 'Failed to post comment.');
    } finally {
      setSubmitting(false);
    }
  };

  // --- Comment deletion ---
  const handleDeleteComment = async (commentId: string) => {
    const confirmed = window.confirm('Delete this comment?');
    if (!confirmed) return;

    try {
      await deleteComment(sessionId, commentId);
      setComments((prev) => prev.filter((c) => c.comment_id !== commentId));
    } catch (err: unknown) {
      // Show error but keep comment visible
      setError(err instanceof Error ? err.message : 'Failed to delete comment.');
    }
  };

  // --- Loading state ---
  if (loading) {
    return (
      <div className="interactions-panel">
        <div className="interactions-panel__loading">Loading interactions…</div>
      </div>
    );
  }

  // --- Error state ---
  if (error && comments.length === 0) {
    return (
      <div className="interactions-panel">
        <div className="interactions-panel__error">
          <span>{error}</span>
          <button
            type="button"
            className="interactions-panel__error-retry"
            onClick={fetchInteractions}
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  const canGiveKudos = canInteract || isOwner;
  const canComment = isOwner || canInteract;

  return (
    <div className="interactions-panel">
      {/* Kudos Section */}
      <div className="interactions-panel__kudos">
        <KudosIcon
          active={userHasKudos}
          size={24}
          onClick={canGiveKudos ? handleKudosToggle : undefined}
        />
        {kudosCount > 0 && (
          <span className="interactions-panel__kudos-count">{kudosCount}</span>
        )}
      </div>

      {/* Error banner (non-blocking) */}
      {error && (
        <div className="interactions-panel__error" style={{ marginBottom: 'var(--space-3)' }}>
          <span>{error}</span>
          <button
            type="button"
            className="interactions-panel__error-retry"
            onClick={() => setError(null)}
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Comments Section */}
      <h3 className="interactions-panel__comments-heading">Comments</h3>

      {comments.length === 0 ? (
        <p className="interactions-panel__empty">No comments yet. Be the first to add one.</p>
      ) : (
        <ul className="interactions-panel__comment-list">
          {comments.map((comment) => (
            <li key={comment.comment_id} className="interactions-panel__comment">
              <div className="interactions-panel__comment-header">
                <span className="interactions-panel__comment-author">
                  {comment.display_name}
                </span>
                <span className="interactions-panel__comment-time">
                  {relativeTime(comment.created_at)}
                </span>
              </div>
              <p className="interactions-panel__comment-text">{comment.text}</p>
              {comment.user_id === currentUserId && (
                <button
                  type="button"
                  className="interactions-panel__comment-delete"
                  onClick={() => handleDeleteComment(comment.comment_id)}
                >
                  Delete
                </button>
              )}
            </li>
          ))}
        </ul>
      )}

      {/* Comment Input */}
      {canComment && (
        <div className="interactions-panel__input-section">
          <textarea
            className="interactions-panel__textarea"
            placeholder="Add a comment…"
            value={commentText}
            onChange={(e) => {
              setCommentText(e.target.value);
              setValidationError(null);
            }}
            maxLength={500}
          />
          <div className="interactions-panel__input-footer">
            <span
              className={`interactions-panel__char-count${
                commentText.length > 500 ? ' interactions-panel__char-count--over' : ''
              }`}
            >
              {commentText.length}/500
            </span>
            <button
              type="button"
              className="interactions-panel__submit-btn"
              disabled={submitting || commentText.trim().length === 0}
              onClick={handleSubmitComment}
            >
              {submitting ? 'Posting…' : 'Post'}
            </button>
          </div>
          {validationError && (
            <p className="interactions-panel__validation-error">{validationError}</p>
          )}
        </div>
      )}
    </div>
  );
}
