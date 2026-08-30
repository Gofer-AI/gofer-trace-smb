import { StrictMode, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { TrueForgeUI } from '@truefoundry/trueforge-ui';

import { ScreenRecorder } from './ScreenRecorder';
import './styles.css';

const server = {
  type: 'trueforge' as const,
  baseUrl: import.meta.env.VITE_TRUEFORGE_BASE_URL || '/',
};

function App() {
  const [error, setError] = useState<string | null>(null);

  return (
    <main className="gofer-shell">
      <ScreenRecorder />
      {error ? (
        <div className="connection-banner" role="alert">
          <strong>TrueForge is not ready.</strong>
          <span>{error}</span>
          <span>Start the runtime and run <code>npm run configure:trueforge</code>.</span>
        </div>
      ) : null}
      <TrueForgeUI
        server={server}
        layout="sidebar"
        agentConfig={{ mode: 'SingleAgent', name: 'gofer-smb' }}
        theme={{
          preset: 'trueforge',
          brand: {
            name: 'Gofer Trace',
            logo: '/gofer-mark.svg',
          },
          tokens: {
            primaryButtonBg: '#18181b',
            primaryButtonHover: '#3f3f46',
            focusRing: '#6366f1',
            radius: '0.55rem',
          },
        }}
        className="h-full"
        onError={(cause) => {
          const message = cause instanceof Error ? cause.message : String(cause);
          setError(message);
          console.error('[gofer-trueforge]', cause);
        }}
      />
    </main>
  );
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
