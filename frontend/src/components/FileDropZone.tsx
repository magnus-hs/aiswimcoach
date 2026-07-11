import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { validateFile } from '../utils/validateFile';

export interface FileDropZoneProps {
  onFileAccepted: (file: File) => void;
  onFilesAccepted?: (files: File[]) => void;
  onFileRejected: (reason: string) => void;
  disabled?: boolean;
  multiple?: boolean;
}

/**
 * Accessible drag-and-drop file upload zone for .fit files.
 *
 * Uses react-dropzone for keyboard navigation and drag/drop support.
 * Includes ARIA label and a live region for screen reader announcements.
 *
 * Validates: Requirements 1.1, 1.2, 1.3, 8.3
 */
export function FileDropZone({
  onFileAccepted,
  onFilesAccepted,
  onFileRejected,
  disabled = false,
  multiple = true,
}: FileDropZoneProps) {
  const [announcement, setAnnouncement] = useState('');

  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      if (acceptedFiles.length === 0) {
        return;
      }

      // Validate all files
      const validFiles: File[] = [];
      for (const file of acceptedFiles) {
        const result = validateFile(file);
        if (result.valid) {
          validFiles.push(file);
        } else {
          setAnnouncement(`File rejected: ${result.reason}`);
          onFileRejected(result.reason);
          return;
        }
      }

      if (validFiles.length > 1 && onFilesAccepted) {
        setAnnouncement(`${validFiles.length} files accepted. Upload starting.`);
        onFilesAccepted(validFiles);
      } else if (validFiles.length >= 1) {
        setAnnouncement(`File ${validFiles[0].name} accepted. Upload starting.`);
        if (onFilesAccepted && validFiles.length > 0) {
          onFilesAccepted(validFiles);
        } else {
          onFileAccepted(validFiles[0]);
        }
      }
    },
    [onFileAccepted, onFilesAccepted, onFileRejected],
  );

  const onDropRejected = useCallback(() => {
    const reason = 'Only .fit files are accepted.';
    setAnnouncement(`File rejected: ${reason}`);
    onFileRejected(reason);
  }, [onFileRejected]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    onDropRejected,
    accept: { 'application/octet-stream': ['.fit'], 'application/zip': ['.zip'], 'application/x-zip-compressed': ['.zip'] },
    disabled,
    multiple,
  });

  return (
    <div>
      <div
        {...getRootProps()}
        aria-label="File upload drop zone. Accepts .fit files."
        className={`dropzone${isDragActive ? ' dropzone--active' : ''}${disabled ? ' dropzone--disabled' : ''}`}
      >
        <input {...getInputProps()} />
        {disabled ? (
          <p>Upload in progress…</p>
        ) : isDragActive ? (
          <p>Drop your .fit or .zip file(s) here…</p>
        ) : (
          <p>Drop your .fit or .zip file(s) here, or click to select</p>
        )}
      </div>
      <div aria-live="polite" aria-atomic="true" className="sr-only">
        {announcement}
      </div>
    </div>
  );
}
