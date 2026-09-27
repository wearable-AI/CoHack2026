import argparse
import os
import sys
import time
import re
import subprocess

def get_scene_class(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    match = re.search(r'^class\s+([A-Za-z_][A-Za-z0-9_]*)\(Clip\):', content, re.MULTILINE)
    if match:
        return match.group(1)
    return None

def main():
    parser = argparse.ArgumentParser(description="Demo Runner")
    parser.add_argument("--scenario", required=True, help="Scenario name (e.g., schematic, heartbeat, smoke, demo_login)")
    parser.add_argument("--cached", action="store_true", help="Use cached MP4 in vizln/demo/")
    args = parser.parse_args()

    # Determine script path
    script_candidates = [
        os.path.join("vizln", "anim", "examples", f"{args.scenario}.py"),
        os.path.join("vizln", "anim", f"{args.scenario}.py"),
    ]

    script_path = None
    for cand in script_candidates:
        if os.path.exists(cand):
            script_path = cand
            break
            
    if not script_path:
        print(f"Error: Could not find scenario script for '{args.scenario}'")
        sys.exit(1)
        
    scene_name = get_scene_class(script_path)
    if not scene_name:
        print(f"Error: Could not find a Clip subclass in {script_path}")
        sys.exit(1)

    print(f"--- Running Scenario: {args.scenario} ---")
    
    # Simulate harness intercept logs
    print("[sandbox] Loading target environment...")
    time.sleep(0.4)
    print("[sandbox] Environment active.")
    time.sleep(0.3)
    print(f"[harness] Attaching to {args.scenario} scenario...")
    time.sleep(0.5)
    print("[harness] Intercepting runtime events...")
    time.sleep(0.6)
    print("[harness] Event stream captured.")
    time.sleep(0.4)
    print("[harness] Transforming trace to visual model...")
    time.sleep(0.4)

    video_path = None

    if args.cached:
        # Pre-rendered MP4 in vizln/demo/
        cached_path = os.path.join("vizln", "demo", f"{scene_name}.mp4")
        if os.path.exists(cached_path):
            print(f"[runner] Using cached render: {cached_path}")
            video_path = cached_path
        else:
            print(f"[runner] Cached file {cached_path} not found. Falling back to rendering.")

    if not video_path:
        print(f"[runner] Rendering scene {scene_name} from {script_path} in low quality (-ql)...")
        
        # Manim rendering
        env = os.environ.copy()
        anim_dir = os.path.abspath(os.path.join("vizln", "anim"))
        if "PYTHONPATH" in env:
            env["PYTHONPATH"] = f"{anim_dir}{os.pathsep}{env['PYTHONPATH']}"
        else:
            env["PYTHONPATH"] = anim_dir
            
        cmd = [sys.executable, "-m", "manim", "-ql", script_path, scene_name]
        try:
            subprocess.run(cmd, env=env, check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error: Manim render failed with code {e.returncode}")
            sys.exit(1)
            
        script_basename = os.path.splitext(os.path.basename(script_path))[0]
        video_path = os.path.join("media", "videos", script_basename, "480p15", f"{scene_name}.mp4")

    if video_path and os.path.exists(video_path):
        print(f"[runner] Opening video: {video_path}")
        if os.name == 'nt':
            os.startfile(video_path)
        elif sys.platform == 'darwin':
            subprocess.call(['open', video_path])
        else:
            subprocess.call(['xdg-open', video_path])
    else:
        print(f"Error: Video file {video_path} not found.")

if __name__ == '__main__':
    main()
