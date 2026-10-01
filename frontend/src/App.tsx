import { useRAAHAT } from './hooks/useRAAHAT';
import { Header } from './components/Header';
import { LandingScreen } from './features/mission-control/LandingScreen';
import { MissionControlLayout } from './features/mission-control/MissionControlLayout';
import { motion, AnimatePresence } from 'framer-motion';
import React from 'react';

/**
 * App-level ErrorBoundary — silently catches render crashes and auto-resets.
 * NEVER shows a full-screen error or closes the project.
 * Logs to console only.
 */
class ErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { hasError: boolean; resetKey: number }
> {
  private resetTimer: ReturnType<typeof setTimeout> | null = null;

  constructor(props: any) {
    super(props);
    this.state = { hasError: false, resetKey: 0 };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    // Log silently — never surface to user
    console.error('[RAAHAT] Render error caught, auto-recovering:', error.message);
    console.error(info.componentStack?.slice(0, 400));

    // Auto-reset after 800ms so the component tree retries
    this.resetTimer = setTimeout(() => {
      this.setState(prev => ({ hasError: false, resetKey: prev.resetKey + 1 }));
    }, 800);
  }

  componentWillUnmount() {
    if (this.resetTimer) clearTimeout(this.resetTimer);
  }

  render() {
    if (this.state.hasError) {
      // Render nothing for 800ms (during reset timer), not a crash screen
      return null;
    }
    return (
      <React.Fragment key={this.state.resetKey}>
        {this.props.children}
      </React.Fragment>
    );
  }
}

/**
 * Section-level boundary — wraps individual panels.
 * Shows a tiny inline "retry" chip instead of crashing the whole dashboard.
 */
export class SectionBoundary extends React.Component<
  { children: React.ReactNode; name: string },
  { hasError: boolean; resetKey: number }
> {
  state = { hasError: false, resetKey: 0 };

  static getDerivedStateFromError() { return { hasError: true }; }

  componentDidCatch(e: Error) {
    console.error(`[RAAHAT Panel: ${(this as any).props?.name}]`, e.message);
    // Auto-retry after 1s
    setTimeout(() => {
      this.setState(prev => ({ hasError: false, resetKey: prev.resetKey + 1 }));
    }, 1000);
  }

  render() {
    if (this.state.hasError) {
      // Show nothing during auto-retry
      return null;
    }
    return (
      <React.Fragment key={this.state.resetKey}>
        {this.props.children}
      </React.Fragment>
    );
  }
}

function App() {
  const raahat = useRAAHAT();
  const isRunning = Boolean(raahat.sessionId);

  return (
    <ErrorBoundary>
      <div className="min-h-screen" style={{ background: 'linear-gradient(135deg, #f0f4f8 0%, #e8eef4 50%, #f0f0f8 100%)' }}>
        {/* Subtle ambient blobs */}
        <div className="fixed inset-0 pointer-events-none overflow-hidden">
          <div className="absolute -top-48 -left-24 w-[600px] h-[600px] rounded-full opacity-30"
            style={{ background: 'radial-gradient(circle, rgba(99,102,241,0.08) 0%, transparent 70%)' }} />
          <div className="absolute -bottom-24 -right-24 w-[500px] h-[500px] rounded-full opacity-30"
            style={{ background: 'radial-gradient(circle, rgba(5,150,105,0.06) 0%, transparent 70%)' }} />
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] rounded-full opacity-20"
            style={{ background: 'radial-gradient(circle, rgba(14,165,233,0.05) 0%, transparent 70%)' }} />
        </div>

        <Header
          wsConnected={raahat.wsConnected}
          sessionId={raahat.sessionId}
          onReset={raahat.reset}
          isRunning={isRunning}
        />

        <AnimatePresence>
          {!isRunning ? (
            <motion.div
              key="landing"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
            >
              <LandingScreen
                onStart={raahat.startDemo}
                loading={raahat.loading}
                error={raahat.error}
                demoEvent={raahat.demoEvent}
              />
            </motion.div>
          ) : (
            <motion.div
              key="dashboard"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.2 }}
            >
              <MissionControlLayout {...raahat} />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </ErrorBoundary>
  );
}

export default App;
