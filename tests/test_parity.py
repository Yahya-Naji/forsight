"""web/lib/verify.ts must agree with pipeline/verify.py.

The TypeScript mirror exists so a reader editing a paragraph in the console
faces the same bar as generated text. A mirror that has drifted is worse than no
mirror: it tells the reader a sentence is fine and the pipeline then withholds
the section. This compiles the TypeScript and runs both over the same corpus.
"""
import json, os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "pipeline"))
sys.path.insert(0, HERE)

import verify                                     # noqa: E402
from test_unsourced import MUST_FAIL, MUST_PASS   # noqa: E402

RUNNER = """
const { checkPassage } = require("./verify.js");
const cases = JSON.parse(require("fs").readFileSync(process.argv[2], "utf8"));
const out = {};
for (const s of cases) out[s] = checkPassage(s, new Set(["EV-001"]), []).unsourced.length > 0;
console.log(JSON.stringify(out));
"""


def test_typescript_mirror_agrees():
    tsc = os.path.join(ROOT, "web", "node_modules", ".bin", "tsc")
    if not os.path.exists(tsc):
        print("skipped: web/node_modules absent (run npm install in web/)")
        return
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run([tsc, os.path.join(ROOT, "web", "lib", "verify.ts"),
                        "--outDir", tmp, "--target", "es2022",
                        "--module", "commonjs", "--lib", "es2022"], check=True)
        runner = os.path.join(tmp, "run.js")
        cases_f = os.path.join(tmp, "cases.json")
        open(runner, "w").write(RUNNER)
        cases = MUST_FAIL + MUST_PASS
        json.dump(cases, open(cases_f, "w"))
        ts = json.loads(subprocess.run(["node", runner, cases_f], check=True,
                                       capture_output=True, text=True).stdout)

    drift = [c for c in cases
             if bool(verify.check_unsourced(verify.sentences_of(c))) != ts[c]]
    assert not drift, "python and typescript disagree on: %s" % drift
    print("✅ %d cases, python and typescript agree" % len(cases))


if __name__ == "__main__":
    test_typescript_mirror_agrees()
