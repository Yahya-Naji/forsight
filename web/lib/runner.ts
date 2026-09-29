import fs from "fs";
import path from "path";

// Is a runner alive?
//
// /api/generate queues a row; a runner executes it. With no runner the row sits
// at QUEUED indefinitely, which is honest about the pipeline and useless to the
// person watching — "Queued" reads the same whether work is starting in a
// second or will never start at all. The runner touches a file every few
// seconds; if it has gone cold, the console says so and says what to do.

const BEAT = path.join(process.cwd(), "..", "out", ".runner-alive");
const STALE_MS = 20_000;

export function runnerAlive(): boolean {
  try {
    return Date.now() - fs.statSync(BEAT).mtimeMs < STALE_MS;
  } catch {
    return false;                 // never started, or the file was cleaned up
  }
}
