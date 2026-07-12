import { useEffect, useState, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { getSessionById, SessionDetail } from '../api/sessionService';
import { uploadFitFile } from '../api/upload';
import { invalidateSessionsCache } from '../api/sessionService';
import { FullResponse } from '../types';
import { SessionSummary } from '../components/SessionSummary';
import { computeBreakdownFromSplits } from '../utils/strokeBreakdown';
import { GroupedSplitsTable } from '../components/GroupedSplitsTable';
import { HRZonesCard } from '../components/HRZonesCard';
import { HRTimeGraph } from '../components/HRTimeGraph';
import { SwolfChart } from '../components/SwolfChart';
import { EfficiencyCurve } from '../components/EfficiencyCurve';
import { StrokeMetricsCharts } from '../components/StrokeMetricsCharts';
import { SessionStatsBlock } from '../components/SessionStatsBlock';
import { SetSummary } from '../components/SetSummary';
import { TrainingLoadChart } from '../components/TrainingLoadChart';
import { AICoachChat } from '../components/AICoachChat';
import { CoachingResult } from '../components/CoachingResult';
import { TrainingPlanResult } from '../components/TrainingPlanResult';
import { FileDropZone } from '../components/FileDropZone';
import { LoadingIndicator } from '../components/LoadingIndicator';
import { ErrorBanner } from '../components/ErrorBanner';
import { InteractionsPanel } from '../components/InteractionsPanel';
import { SessionNotesSection } from '../components/SessionNotesSection';
import { DrillSummary } from '../components/DrillSummary';
import { BulkImportPanel } from '../components/BulkImportPanel';
import './ActivityDetailPage.css';

export interface ActivityDetailPageProps {
  mode?: 'view' | 'upload';
}

/**
 * Activity Detail Page — unified view/upload page.
 *
 * Two modes:
 * 1. View mode (URL has :id param): Fetches session from API and displays all detail components.
 * 2. Upload mode (/activity/new): Shows FileDropZone. After successful upload, displays result.
 *
 * Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5, 12.3, 12.4
 */
export function ActivityDetailPage({ mode }: ActivityDetailPageProps) {
  const { id } = useParams<{ id: string }>();

  // View mode state
  const [sessionDetail, setSessionDetail] = useState<SessionDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Upload mode state
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadResult, setUploadResult] = useState<FullResponse | null>(null);
  const [cssPace, setCssPace] = useState<number | null>(null);
  const [bulkFiles, setBulkFiles] = useState<File[] | null>(null);

  // Fetch user's CSS pace
  useEffect(() => {
    const token = localStorage.getItem('auth_token');
    if (!token) return;
    fetch(`${import.meta.env.VITE_API_ENDPOINT}/profile/css`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(r => r.ok ? r.json() : null)
      .then(data => { if (data?.css_pace_per_100m) setCssPace(data.css_pace_per_100m); })
      .catch(() => {});
  }, []);

  const isUploadMode = mode === 'upload';

  // Determine if current user is the session owner
  const isCurrentUserOwner = useCallback((): boolean => {
    const currentUserId = localStorage.getItem('user_id') || '';
    if (!currentUserId) return true; // Default to owner view if no user_id
    // If session detail has a user_id field, compare; otherwise assume owner
    if (sessionDetail) {
      const sessionUserId = (sessionDetail as unknown as Record<string, unknown>).user_id as string | undefined;
      if (sessionUserId) return sessionUserId === currentUserId;
    }
    return true;
  }, [sessionDetail]);

  const fetchSession = useCallback(async (sessionId: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await getSessionById(sessionId);
      // The backend returns a flat session object — adapt to SessionDetail format
      // If the response already has nested 'session' field, use it directly
      // Otherwise wrap the flat response
      if (data.session) {
        setSessionDetail(data);
      } else {
        // Flat format from GET /sessions/:id — create a compatible shape
        const flat = data as unknown as Record<string, unknown>;
        const adapted: SessionDetail = {
          session: {
            start_time: (flat.session_date as string) || '',
            pool_length_m: (flat.pool_length_meters as number) || 25,
            total_distance_m: (flat.total_distance_meters as number) || 0,
            total_time_seconds: (flat.total_time_seconds as number) || 0,
            num_lengths: Math.round(((flat.total_distance_meters as number) || 0) / ((flat.pool_length_meters as number) || 25)),
            stroke: (flat.stroke_type as string) || 'freestyle',
          },
          splits: (flat.splits as SessionDetail['splits']) || [],
          metrics: {
            pace: (flat.average_pace_per_100m as number) || 0,
            swolf: (flat.swolf_score as number) || 0,
            stroke_rate: (flat.stroke_rate as number) || 0,
          },
          coaching: (flat.coaching as SessionDetail['coaching']) || { tips: [], drill: '' },
          hr_zones: flat.hr_zones as SessionDetail['hr_zones'],
          ability_assessment: flat.ability_assessment as SessionDetail['ability_assessment'],
          session_id: (flat.session_id as string) || sessionId,
          hr_timeseries: flat.hr_timeseries as any,
        };
        setSessionDetail(adapted);
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to load session.';
      setError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!isUploadMode && id) {
      fetchSession(id);
    }
  }, [id, isUploadMode, fetchSession]);

  const handleFileAccepted = useCallback(async (file: File) => {
    setUploading(true);
    setUploadError(null);
    try {
      const result = await uploadFitFile(file);
      setUploadResult(result);
      invalidateSessionsCache();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Upload failed. Please try again.';
      setUploadError(message);
    } finally {
      setUploading(false);
    }
  }, []);

  const handleFilesAccepted = useCallback(async (files: File[]) => {
    // Check if any file is a .zip — extract FIT files from it
    const zipFiles = files.filter(f => f.name.toLowerCase().endsWith('.zip'));
    const fitFiles = files.filter(f => f.name.toLowerCase().endsWith('.fit'));

    if (zipFiles.length > 0) {
      // Unzip all zip files client-side and extract .fit files
      setUploading(true);
      setUploadError(null);
      try {
        const JSZip = (await import('jszip')).default;
        const extractedFiles: File[] = [...fitFiles];

        for (const zipFile of zipFiles) {
          const zip = await JSZip.loadAsync(zipFile);
          const entries = Object.entries(zip.files);
          for (const [path, entry] of entries) {
            if (entry.dir) continue;
            if (!path.toLowerCase().endsWith('.fit')) continue;
            const blob = await entry.async('blob');
            const fileName = path.split('/').pop() || path;
            extractedFiles.push(new File([blob], fileName, { type: 'application/octet-stream' }));
          }
        }

        setUploading(false);

        if (extractedFiles.length === 0) {
          setUploadError('No .fit files found in the zip archive.');
          return;
        }

        if (extractedFiles.length === 1) {
          handleFileAccepted(extractedFiles[0]);
        } else {
          setBulkFiles(extractedFiles);
        }
      } catch (err) {
        setUploading(false);
        setUploadError(err instanceof Error ? err.message : 'Failed to extract zip file.');
      }
      return;
    }

    if (fitFiles.length > 1) {
      // Bulk import mode
      setBulkFiles(fitFiles);
    } else if (fitFiles.length === 1) {
      // Single upload flow
      handleFileAccepted(fitFiles[0]);
    }
  }, [handleFileAccepted]);

  const handleFileRejected = useCallback((reason: string) => {
    setUploadError(reason);
  }, []);

  // Render session detail sections (shared between view mode and post-upload)
  function renderSessionDetail(data: {
    session: SessionDetail['session'] | FullResponse['session'];
    splits: SessionDetail['splits'] | FullResponse['splits'];
    coaching: SessionDetail['coaching'] | FullResponse['coaching'];
    hr_zones?: SessionDetail['hr_zones'] | FullResponse['hr_zones'];
    ability_assessment?: SessionDetail['ability_assessment'] | FullResponse['ability_assessment'];
    training_plan?: SessionDetail['training_plan'];
    hr_timeseries?: { t: number; hr: number }[] | null;
  }) {
    return (
      <div className="activity-detail__sections">
        <SessionSummary
          session={data.session}
          splits={data.splits}
          strokeBreakdown={
            data.splits && data.splits.length > 0
              ? computeBreakdownFromSplits(data.splits)
              : undefined
          }
        />
        {data.splits && data.splits.length > 0 && (
          <DrillSummary splits={data.splits} poolLengthM={data.session.pool_length_m} />
        )}
        <AICoachChat currentSession={{
          total_distance_m: data.session.total_distance_m,
          pace: (data as any).metrics?.pace,
          swolf: (data as any).metrics?.swolf,
          stroke_rate: (data as any).metrics?.stroke_rate,
        }} />
        {data.splits && data.splits.length > 0 && <SetSummary splits={data.splits} poolLengthM={data.session.pool_length_m} />}
        {data.splits && data.splits.length > 0 && <GroupedSplitsTable splits={data.splits} poolLengthM={data.session.pool_length_m} />}
        <HRZonesCard hrZones={data.hr_zones ?? null} />
        <HRTimeGraph
          hrTimeseries={data.hr_timeseries}
          totalDistanceM={data.session.total_distance_m}
          totalTimeSeconds={data.session.total_time_seconds}
        />
        {data.splits && data.splits.length > 0 && <SwolfChart splits={data.splits} poolLengthM={data.session.pool_length_m} />}
        {data.splits && data.splits.length > 0 && <EfficiencyCurve splits={data.splits} poolLengthM={data.session.pool_length_m} />}
        {data.splits && data.splits.length > 0 && <StrokeMetricsCharts splits={data.splits} poolLengthM={data.session.pool_length_m} />}
        {data.splits && data.splits.length > 0 && (
          <SessionStatsBlock
            splits={data.splits}
            poolLengthM={data.session.pool_length_m}
            totalDistanceM={data.session.total_distance_m}
            totalTimeSeconds={data.session.total_time_seconds}
          />
        )}
        {data.splits && data.splits.length > 0 && <TrainingLoadChart splits={data.splits} poolLengthM={data.session.pool_length_m} cssPace={cssPace} />}
        {data.coaching && data.coaching.tips && data.coaching.tips.length > 0 && (
          <CoachingResult tips={data.coaching.tips} drill={data.coaching.drill} />
        )}
        {data.training_plan && <TrainingPlanResult plan={data.training_plan} />}
        {id && isCurrentUserOwner() && (
          <SessionNotesSection sessionId={id} />
        )}
        {id && (
          <InteractionsPanel
            sessionId={id}
            isOwner={isCurrentUserOwner()}
            canInteract={true}
          />
        )}
      </div>
    );
  }

  return (
    <div className="activity-detail">
      <Link to="/" className="activity-detail__back-link">
        ← Back to Dashboard
      </Link>

      {/* View mode: fetch and display existing session */}
      {!isUploadMode && (
        <>
          <h1 className="activity-detail__heading">Activity Details</h1>

          {loading && (
            <div className="activity-detail__loading">
              <LoadingIndicator />
            </div>
          )}

          {error && (
            <div className="activity-detail__error">
              <ErrorBanner message={error} onRetry={id ? () => fetchSession(id) : undefined} />
            </div>
          )}

          {sessionDetail && !loading && !error && renderSessionDetail({
            session: sessionDetail.session,
            splits: sessionDetail.splits,
            coaching: sessionDetail.coaching,
            hr_zones: sessionDetail.hr_zones,
            ability_assessment: sessionDetail.ability_assessment,
            training_plan: sessionDetail.training_plan,
            hr_timeseries: sessionDetail.hr_timeseries,
          })}
        </>
      )}

      {/* Upload mode: show file drop zone or upload result */}
      {isUploadMode && (
        <>
          {bulkFiles && (
            <div className="activity-detail__upload-section">
              <h1 className="activity-detail__heading">Bulk Import</h1>
              <BulkImportPanel files={bulkFiles} onComplete={() => { setBulkFiles(null); invalidateSessionsCache(); }} />
            </div>
          )}

          {!bulkFiles && !uploadResult && (
            <div className="activity-detail__upload-section">
              <h1 className="activity-detail__heading">Upload Activity</h1>
              <FileDropZone
                onFileAccepted={handleFileAccepted}
                onFilesAccepted={handleFilesAccepted}
                onFileRejected={handleFileRejected}
                disabled={uploading}
              />
              {uploading && (
                <div className="activity-detail__loading">
                  <LoadingIndicator />
                </div>
              )}
              {uploadError && (
                <div className="activity-detail__upload-error">
                  <ErrorBanner message={uploadError} />
                </div>
              )}
            </div>
          )}

          {uploadResult && (
            <>
              <h1 className="activity-detail__heading">Activity Details</h1>
              {renderSessionDetail({
                session: uploadResult.session,
                splits: uploadResult.splits,
                coaching: uploadResult.coaching,
                hr_zones: uploadResult.hr_zones,
                ability_assessment: uploadResult.ability_assessment,
                hr_timeseries: uploadResult.hr_timeseries,
              })}
            </>
          )}
        </>
      )}
    </div>
  );
}
