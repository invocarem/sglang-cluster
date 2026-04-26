declare module "react" {
  export type ChangeEvent<T = Element> = { target: T };
  export type SetStateAction<S> = S | ((prevState: S) => S);
  export type Dispatch<A> = (value: A) => void;
  export type RefObject<T> = { current: T | null };
  export const StrictMode: any;
  export function useState<S>(initialState: S): [S, Dispatch<SetStateAction<S>>];
  export function useEffect(effect: () => void | (() => void), deps?: readonly unknown[]): void;
  export function useMemo<T>(factory: () => T, deps: readonly unknown[]): T;
  export function useRef<T>(initialValue: T | null): RefObject<T>;
}

declare module "react-dom/client" {
  export function createRoot(container: Element | DocumentFragment): { render: (children: any) => void };
}

declare module "react/jsx-runtime" {
  export const jsx: any;
  export const jsxs: any;
  export const Fragment: any;
}

interface ImportMeta {
  readonly env: Record<string, string | undefined>;
}

declare namespace JSX {
  interface IntrinsicElements {
    [elemName: string]: any;
  }
}
