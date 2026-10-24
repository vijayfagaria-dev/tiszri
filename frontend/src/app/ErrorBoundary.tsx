import { Component, type ReactNode } from "react";
export class ErrorBoundary extends Component<
  { children: ReactNode },
  { failed: boolean }
> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  render() {
    if (this.state.failed)
      return (
        <main className="error-panel panel">
          <h1>This view couldn’t be displayed.</h1>
          <p>Your URL still contains your selected inputs.</p>
          <button onClick={() => location.reload()}>Reload application</button>
        </main>
      );
    return this.props.children;
  }
}
