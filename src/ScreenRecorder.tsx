import { useEffect, useRef, useState } from 'react';
import { TrueForge } from '@truefoundry/trueforge-sdk';

type RecorderState =
  | 'idle'
  | 'selecting'
  | 'requesting'
  | 'recording'
  | 'ready'
  | 'uploading'
  | 'complete'
  | 'error';
type MessageTone = 'info' | 'success' | 'error';
type CaptureSurface = 'monitor' | 'window' | 'browser';

type WorkflowResult = {
  workflow_path: string;
  workflow_name: string;
  steps: number;
  extraction_mode: 'offline_fixture' | 'live';
};

type StagedRecording = {
  upload_id: string;
  status: 'staged' | 'processing' | 'created' | 'failed';
  error?: string;
};

const trueForge = new TrueForge({ baseUrl: window.location.origin });

function preferredMimeType() {
  const candidates = [
    'video/webm;codecs=vp9,opus',
    'video/webm;codecs=vp8,opus',
    'video/webm',
  ];

  return candidates.find((type) => MediaRecorder.isTypeSupported(type));
}

function recordingName() {
  const timestamp = new Date().toISOString().replaceAll(':', '-').replace(/\.\d{3}Z$/, 'Z');
  return `gofer-screen-${timestamp}.webm`;
}

function formatElapsed(seconds: number) {
  const minutes = Math.floor(seconds / 60);
  const remainder = seconds % 60;
  return `${minutes}:${remainder.toString().padStart(2, '0')}`;
}

const captureOptions: Array<{
  surface: CaptureSurface;
  title: string;
  description: string;
}> = [
  { surface: 'monitor', title: 'Entire screen', description: 'Everything visible on one display' },
  { surface: 'window', title: 'App window', description: 'One application window only' },
  { surface: 'browser', title: 'Browser tab', description: 'One tab; best for web workflows' },
];

export function ScreenRecorder() {
  const [state, setState] = useState<RecorderState>('idle');
  const [elapsed, setElapsed] = useState(0);
  const [recordingUrl, setRecordingUrl] = useState<string | null>(null);
  const [recordingBlob, setRecordingBlob] = useState<Blob | null>(null);
  const [fileName, setFileName] = useState('gofer-screen.webm');
  const [message, setMessage] = useState('');
  const [messageTone, setMessageTone] = useState<MessageTone>('info');
  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<number | null>(null);

  const supported =
    typeof navigator !== 'undefined' &&
    Boolean(navigator.mediaDevices?.getDisplayMedia) &&
    typeof MediaRecorder !== 'undefined';

  const clearTimer = () => {
    if (timerRef.current !== null) {
      window.clearInterval(timerRef.current);
      timerRef.current = null;
    }
  };

  const stopTracks = () => {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
  };

  const stopRecording = () => {
    clearTimer();
    const recorder = recorderRef.current;
    if (recorder?.state === 'recording') {
      recorder.stop();
    } else {
      stopTracks();
    }
  };

  const discardRecording = () => {
    if (recordingUrl) {
      URL.revokeObjectURL(recordingUrl);
    }
    setRecordingUrl(null);
    setRecordingBlob(null);
    setElapsed(0);
    setMessage('');
    setMessageTone('info');
    setState('idle');
  };

  const chooseRecordingSource = () => {
    if (!supported) return;
    discardRecording();
    setState('selecting');
  };

  const cancelSourceSelection = () => {
    setState('idle');
    setMessage('');
    setMessageTone('info');
  };

  const startRecording = async (surface: CaptureSurface) => {
    if (!supported || state === 'requesting') return;

    setState('requesting');
    setMessageTone('info');
    const sourceName = captureOptions.find((option) => option.surface === surface)?.title.toLowerCase();
    setMessage(`In the browser dialog, confirm the exact ${sourceName ?? 'source'} you want to record.`);

    try {
      const stream = await navigator.mediaDevices.getDisplayMedia({
        video: {
          displaySurface: surface,
          frameRate: { ideal: 30, max: 30 },
        },
        audio: true,
      });
      const mimeType = preferredMimeType();
      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);

      streamRef.current = stream;
      recorderRef.current = recorder;
      chunksRef.current = [];

      recorder.addEventListener('dataavailable', (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data);
      });
      recorder.addEventListener('stop', () => {
        clearTimer();
        stopTracks();
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || 'video/webm' });
        chunksRef.current = [];
        recorderRef.current = null;
        if (blob.size === 0) {
          setState('error');
          setMessageTone('error');
          setMessage('The browser did not capture any video. Try sharing the screen again.');
          return;
        }
        setFileName(recordingName());
        setRecordingBlob(blob);
        setRecordingUrl(URL.createObjectURL(blob));
        setState('ready');
        setMessageTone('info');
        setMessage('Recording ready. Extract the workflow now, or save a local backup first.');
      });
      stream.getVideoTracks()[0]?.addEventListener('ended', stopRecording, { once: true });

      recorder.start(1_000);
      setElapsed(0);
      setState('recording');
      setMessageTone('info');
      setMessage('Recording your screen. Perform the workflow, then stop when you are done.');
      timerRef.current = window.setInterval(() => setElapsed((value) => value + 1), 1_000);
    } catch (cause) {
      clearTimer();
      stopTracks();
      recorderRef.current = null;
      const denied = cause instanceof DOMException && cause.name === 'NotAllowedError';
      setState(denied ? 'selecting' : 'error');
      setMessageTone(denied ? 'info' : 'error');
      setMessage(
        denied
          ? 'Screen sharing was cancelled. Choose a source to try again, or cancel.'
          : cause instanceof Error
            ? cause.message
            : 'Screen recording could not start.',
      );
    }
  };

  const extractWorkflow = async () => {
    if (!recordingBlob || state !== 'ready') return;
    setState('uploading');
    setMessageTone('info');
    setMessage('Staging the recording and handing extraction to TrueForge…');

    let uploadId: string | null = null;

    try {
      const stageResponse = await fetch('/gofer-api/recordings', {
        method: 'POST',
        headers: {
          'Content-Type': recordingBlob.type || 'video/webm',
          'X-Gofer-Filename': fileName,
        },
        body: recordingBlob,
      });
      const staged = (await stageResponse.json()) as StagedRecording;
      if (!stageResponse.ok) {
        throw new Error(staged.error || `Recording staging failed with HTTP ${stageResponse.status}.`);
      }
      uploadId = staged.upload_id;

      setMessage('TrueForge is invoking the governed recording-extraction tool…');
      const session = await trueForge.sessions.create({ agent: { name: 'gofer-smb' } });
      const events = await trueForge.sessions.createTurnStream(session.data.id, {
        previousTurnId: 'none',
        input: [
          {
            type: 'user.message',
            content:
              `Process the staged screen recording by calling extract_workflow_from_recording exactly once ` +
              `with upload_id ${uploadId}. Do not call any other tool. Return the tool result.`,
          },
        ],
      });
      for await (const _event of events) {
        // Consuming the stream waits for TrueForge and its MCP tool call to finish.
      }

      const statusResponse = await fetch(`/gofer-api/recordings/${encodeURIComponent(uploadId)}`);
      const payload = (await statusResponse.json()) as WorkflowResult & StagedRecording;
      if (!statusResponse.ok || payload.status !== 'created') {
        throw new Error(
          payload.error ||
            (payload.status === 'staged'
              ? 'TrueForge completed without invoking the recording-extraction tool.'
              : 'TrueForge could not complete workflow extraction.'),
        );
      }

      setState('complete');
      setMessageTone('success');
      const summary = `Created ${payload.workflow_path} with ${payload.steps} workflow ${payload.steps === 1 ? 'step' : 'steps'}.`;
      setMessage(
        payload.extraction_mode === 'offline_fixture'
          ? `${summary} Offline mode used the committed demo fixture; enable live extraction to analyze this recording.`
          : summary,
      );
    } catch (cause) {
      if (uploadId) {
        await fetch(`/gofer-api/recordings/${encodeURIComponent(uploadId)}`, { method: 'DELETE' }).catch(() => undefined);
      }
      setState('ready');
      setMessageTone('error');
      setMessage(cause instanceof Error ? cause.message : 'Workflow extraction failed.');
    }
  };

  useEffect(() => {
    return () => {
      clearTimer();
      if (recorderRef.current?.state === 'recording') recorderRef.current.stop();
      stopTracks();
      if (recordingUrl) URL.revokeObjectURL(recordingUrl);
    };
  }, [recordingUrl]);

  return (
    <aside className={`screen-recorder screen-recorder--${state}`} aria-label="Screen recorder">
      <div className="screen-recorder__actions">
        {state === 'recording' ? (
          <button className="record-button record-button--active" type="button" onClick={stopRecording}>
            <span className="record-button__stop" aria-hidden="true" />
            Stop
            <span className="record-button__timer">{formatElapsed(elapsed)}</span>
          </button>
        ) : state === 'uploading' ? (
          <button className="record-button" type="button" disabled>
            <span className="record-button__spinner" aria-hidden="true" />
            Extracting…
          </button>
        ) : state === 'complete' ? (
          <button className="record-button" type="button" onClick={discardRecording}>
            Record another
          </button>
        ) : state === 'selecting' ? (
          <button className="record-button" type="button" disabled>
            <span className="record-button__dot" aria-hidden="true" />
            Choose a source
          </button>
        ) : (
          <button
            className="record-button"
            type="button"
            onClick={chooseRecordingSource}
            disabled={!supported || state === 'requesting'}
            title={supported ? 'Start a screen recording' : 'Screen recording is not supported in this browser'}
          >
            <span className="record-button__dot" aria-hidden="true" />
            {state === 'requesting' ? 'Choose a screen…' : 'Record workflow'}
          </button>
        )}

        {state === 'ready' && recordingUrl && recordingBlob ? (
          <>
            <button className="recording-extract" type="button" onClick={extractWorkflow}>
              Extract workflow
            </button>
            <a className="recording-save" href={recordingUrl} download={fileName}>
              Save backup
            </a>
            <button className="recording-discard" type="button" onClick={discardRecording}>
              Discard
            </button>
          </>
        ) : null}

        {state === 'complete' && recordingUrl ? (
          <a className="recording-save" href={recordingUrl} download={fileName}>
            Save backup
          </a>
        ) : null}
      </div>

      {state === 'selecting' ? (
        <section className="screen-recorder__picker" aria-labelledby="recording-source-title">
          <div className="screen-recorder__picker-heading">
            <div>
              <h2 id="recording-source-title">What would you like to record?</h2>
              <p>Choose one source. Your browser will ask you to confirm the exact screen, window, or tab.</p>
            </div>
            <button
              className="screen-recorder__picker-close"
              type="button"
              onClick={cancelSourceSelection}
              aria-label="Cancel screen recording"
            >
              ×
            </button>
          </div>

          <div className="screen-recorder__source-options">
            {captureOptions.map((option) => (
              <button
                className="screen-recorder__source-option"
                type="button"
                key={option.surface}
                onClick={() => startRecording(option.surface)}
              >
                <span
                  className={`screen-recorder__source-icon screen-recorder__source-icon--${option.surface}`}
                  aria-hidden="true"
                />
                <span className="screen-recorder__source-copy">
                  <strong>{option.title}</strong>
                  <small>{option.description}</small>
                </span>
                <span className="screen-recorder__source-arrow" aria-hidden="true">
                  ›
                </span>
              </button>
            ))}
          </div>

          <p className="screen-recorder__privacy-note">
            Gofer cannot begin capturing until you approve the browser prompt. One source is recorded at a time.
          </p>
        </section>
      ) : null}

      {message ? (
        <p
          className={`screen-recorder__message screen-recorder__message--${messageTone}`}
          role="status"
          aria-live="polite"
        >
          {message}
        </p>
      ) : null}
    </aside>
  );
}
