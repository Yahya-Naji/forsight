import { Meter } from "@/components/ui/meter";

// Signal strength is an ordinal the corroboration rule computed from distinct
// publishers — four discrete steps, never a continuous bar, because a bar
// invites the reader to interpolate a precision that is not there.
const LEVELS: Record<string, number> = { WEAK: 1, EMERGING: 2, STRONG_EMERGING: 3, STRONG: 4 };

export default function SignalMeter({ strength }: { strength?: string | null }) {
  return <Meter filled={LEVELS[strength ?? ""] ?? 0} />;
}
