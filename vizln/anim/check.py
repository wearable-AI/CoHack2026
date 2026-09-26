"""Check a clip's layout without rendering it or looking at it.

    anim/check.sh clip.py [Scene]

Runs the scene with the file writer switched off and the audit hooks on, sampling
the mobject tree about eight times a second of clip time. Reports five faults:

  off-frame      a text runs past the frame edge
  overlap        two different strings cover each other by more than a tenth
  too-small      a text is set below the size 12 floor
  ink-over-text  a stroke is drawn through a word
  dot-collision  two dots cover each other

It cannot judge taste. It catches the faults that used to cost a render, a frame
extraction and a look, which were nearly all of them.
"""
import importlib.util
import os
import sys

os.environ["VANIM_AUDIT"] = "1"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from manim import config, tempconfig  # noqa: E402

import vanim  # noqa: E402


def load(path):
    spec = importlib.util.spec_from_file_location("clip_under_test", path)
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, os.path.dirname(os.path.abspath(path)))
    spec.loader.exec_module(mod)
    return mod


def main():
    if len(sys.argv) < 2:
        print("usage: check.py clip.py [Scene]", file=sys.stderr)
        return 2
    mod = load(sys.argv[1])
    name = sys.argv[2] if len(sys.argv) > 2 else None
    scenes = [v for v in vars(mod).values()
              if isinstance(v, type) and issubclass(v, vanim.Clip) and v is not vanim.Clip]
    if name:
        scenes = [s for s in scenes if s.__name__ == name]
    if not scenes:
        print("no Clip subclass found", file=sys.stderr)
        return 2

    cls = scenes[0]
    with tempconfig({"dry_run": True, "quality": "low_quality",
                     "disable_caching": True, "verbosity": "ERROR", "progress_bar": "none"}):
        cls().render()

    hits = vanim.AUDIT_HITS
    if not hits:
        print(f"{cls.__name__}: clean")
        return 0
    order = {"off-frame": 0, "overlap": 1, "ink-over-text": 2,
             "dot-collision": 3, "too-small": 4}
    hits.sort(key=lambda h: order.get(h[0], 9))
    print(f"{cls.__name__}: {len(hits)} finding(s)")
    for kind, detail in hits:
        print(f"  {kind:<14} {detail}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
