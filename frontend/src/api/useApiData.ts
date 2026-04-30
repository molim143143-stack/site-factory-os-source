import { useEffect, useState } from "react";

type State<T> = {
  data: T;
  loading: boolean;
  error: string | null;
  source: "api" | "fallback";
};

export function useApiData<T>(loader: () => Promise<T>, fallback: T, deps: unknown[] = []) {
  const [state, setState] = useState<State<T>>({ data: fallback, loading: true, error: null, source: "fallback" });

  useEffect(() => {
    let cancelled = false;
    setState((prev) => ({ ...prev, loading: true }));
    loader()
      .then((data) => {
        if (!cancelled) setState({ data, loading: false, error: null, source: "api" });
      })
      .catch((error) => {
        if (!cancelled) setState({ data: fallback, loading: false, error: error?.error?.error_code || error?.message || "API_FALLBACK", source: "fallback" });
      });
    return () => {
      cancelled = true;
    };
  }, deps);

  return state;
}
