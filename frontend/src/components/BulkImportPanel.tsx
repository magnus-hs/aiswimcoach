import { useEffect, useRef, useState } from 'react';
import { uploadFitFileBulk } from '../api/upload';
import './BulkImportPanel.css';

interface BulkImportPanelProps {
  files: File[];
  onComplete: () => void;
}

/**
 * Bulk Import Panel — uploads multiple FIT files in parallel batches,
 * showing progress and a summary when complete.
 *
 * Uses 5 concurrent uploads for significantly faster throughput.
 *
 * Validates: Requirements 2.1-2.5, 3.1-3.5, 5.1-5.4, 6.1-6.5, 7.1-7.4
 */
export function BulkImportPanel({ files, onComplete }: BulkImportPanelProps) {
  const [successes, setSuccesses] = useState(0);
  const [failures, setFailures] = useState<Array<{ name: string; error: string }>>([]);
  const [cancelled, setCancelled] = useState(false);
  const [done, setDone] = useState(false);
  const [showFailures, setShowFailures] = useState(false);
  const cancelledRef = useRef(false);
  const CONCURRENCY = 5;

  useEffect(() => {
    let active = true;

    async function processFiles() {
      let index = 0;

      async function worker() {
        while (index < files.length) {
          if (cancelledRef.current || !active) return;
          const i = index++;
          if (i >= files.length) return;

          try {
            await uploadFitFileBulk(files[i]);
            if (!active) return;
            setSuccesses(prev => prev + 1);
          } catch (err: unknown) {
            if (!active) return;
            const message = err instanceof Error ? err.message : 'Unknown error';
            setFailures(prev => [...prev, { name: files[i].name, error: message }]);
          }
        }
      }

      // Launch N concurrent workers
      const workers = Array.from({ length: CONCURRENCY }, () => worker());
      await Promise.all(workers);

      if (active) {
        setDone(true);
      }
    }

    processFiles();

    return () => {
      active = false;
    };
  }, [files]);

  const handleCancel = () => {
    cancelledRef.current = true;
    setCancelled(true);
    setDone(true);
  };

  const processed = successes + failures.length;
  const total = files.length;
  const percentage = total > 0 ? ((processed / total) * 100).toFixed(1) : '0.0';
  const notProcessed = total - processed;

  if (done) {
    return (
      <div className="bulk-import-panel" role="region" aria-label="Bulk import summary">
        <h2 className="bulk-import-panel__title">Import Complete</h2>
        {cancelled && (
          <p className="bulk-import-panel__cancelled">
            Import cancelled — {notProcessed} file{notProcessed !== 1 ? 's' : ''} not processed.
          </p>
        )}
        <div className="bulk-import-panel__summary">
          <span className="bulk-import-panel__success">✓ {successes} uploaded</span>
          <span className="bulk-import-panel__failure">✗ {failures.length} failed</span>
        </div>
        {failures.length > 0 && (
          <div className="bulk-import-panel__failures-section">
            <button
              className="bulk-import-panel__toggle-failures"
              onClick={() => setShowFailures(!showFailures)}
              aria-expanded={showFailures}
            >
              {showFailures ? 'Hide' : 'Show'} failed files
            </button>
            {showFailures && (
              <ul className="bulk-import-panel__failures-list">
                {failures.map((f, i) => (
                  <li key={i} className="bulk-import-panel__failure-item">
                    <strong>{f.name}</strong>: {f.error}
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
        <button className="bulk-import-panel__done-btn" onClick={onComplete}>
          Done
        </button>
      </div>
    );
  }

  return (
    <div className="bulk-import-panel" role="region" aria-label="Bulk import progress">
      <h2 className="bulk-import-panel__title">Bulk Import</h2>
      <p className="bulk-import-panel__status">
        Uploading {processed + 1}/{total} — {percentage}%
      </p>
      <div className="bulk-import-panel__progress-bar-container">
        <div
          className="bulk-import-panel__progress-bar"
          style={{ width: `${percentage}%` }}
          role="progressbar"
          aria-valuenow={processed}
          aria-valuemin={0}
          aria-valuemax={total}
          aria-label={`Upload progress: ${percentage}%`}
        />
      </div>
      <p className="bulk-import-panel__counts">
        <span className="bulk-import-panel__success">✓ {successes}</span>
        {failures.length > 0 && (
          <span className="bulk-import-panel__failure"> ✗ {failures.length}</span>
        )}
      </p>
      <button className="bulk-import-panel__cancel-btn" onClick={handleCancel}>
        Cancel
      </button>
    </div>
  );
}
