# animate_trajectory Blit Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate the per-frame raster redraw in `_save_animation` so frame render time stays constant regardless of trajectory length.

**Architecture:** Cache the matplotlib background (raster + empty axes) once before the save loop using `fig.canvas.copy_from_bbox`. Each frame restores that background and draws only the dirty trajectory artists via `ax.draw_artist`, then blits. The growing `set_data` slice is unchanged — only the canvas redraw strategy changes.

**Tech Stack:** matplotlib (Agg backend), imageio, numpy

---

### Task 1: Add test for imageio blit path

**Files:**
- Modify: `tests/test_trajectory.py`

- [ ] **Step 1: Add the failing test**

Add at the bottom of `tests/test_trajectory.py`:

```python
def test_animate_trajectory_saves_gif_imageio(tmp_path, monkeypatch):
    """Blit path via imageio produces a valid multi-frame GIF."""
    import types
    from mapgod.trajectory import animate_trajectory

    # Build a minimal imageio stub so the imageio path is taken
    frames_captured = []

    class _FakeWriter:
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def append_data(self, frame): frames_captured.append(frame)

    fake_imageio = types.ModuleType("imageio")
    fake_imageio.get_writer = lambda *a, **kw: _FakeWriter()

    import importlib.util as _ilu
    real_find_spec = _ilu.find_spec

    def _patched_find_spec(name):
        if name == "imageio_ffmpeg":
            # Return a truthy spec so the imageio branch is taken
            return object()
        return real_find_spec(name)

    monkeypatch.setattr(_ilu, "find_spec", _patched_find_spec)
    monkeypatch.setitem(__import__("sys").modules, "imageio", fake_imageio)

    raster = _write_raster(tmp_path)
    traj = _make_trajectory()
    output = tmp_path / "blit_test.mp4"
    animate_trajectory(raster, traj, output=output, fps=5)

    # 3 points in trajectory → 3 frames
    assert len(frames_captured) == 3
    h, w, c = frames_captured[0].shape
    assert c == 3
    assert h > 0 and w > 0
```

- [ ] **Step 2: Run the test to confirm it fails**

```
pytest tests/test_trajectory.py::test_animate_trajectory_saves_gif_imageio -v
```

Expected: FAIL (currently the blit path doesn't exist — frames_captured will have wrong shape or the test errors because `ax` isn't passed to `_save_animation`).

---

### Task 2: Implement the blit fix

**Files:**
- Modify: `src/mapgod/trajectory.py:64-93` (`_save_animation`) and line ~249 (callsite)

- [ ] **Step 3: Update `_save_animation` signature and body**

Replace the entire `_save_animation` function:

```python
def _save_animation(fig, ax, update_fn, anim, n_frames: int, output: Path, *, fps: int, dpi: int) -> None:
    """Save animation using imageio-ffmpeg when available, falling back to Pillow."""
    try:
        import importlib.util

        import imageio

        if importlib.util.find_spec("imageio_ffmpeg") is None:
            raise ImportError("imageio_ffmpeg not installed")

        fig.canvas.draw()
        bg = fig.canvas.copy_from_bbox(fig.bbox)

        with imageio.get_writer(str(output), fps=fps, macro_block_size=1) as writer:
            for i in range(n_frames):
                artists = update_fn(i)
                fig.canvas.restore_region(bg)
                for artist in artists:
                    ax.draw_artist(artist)
                fig.canvas.blit(fig.bbox)
                w, h = fig.canvas.get_width_height()
                buf = np.frombuffer(fig.canvas.buffer_rgba(), dtype=np.uint8).reshape(h, w, 4)
                writer.append_data(buf[..., :3].copy())
                print(f"\r  Rendering frame {i + 1}/{n_frames}", end="", flush=True)
        print()

    except ImportError:
        print("  imageio-ffmpeg not found — falling back to Pillow (slow). Install with: pip install imageio-ffmpeg")

        def _progress(current_frame: int, total_frames: int) -> None:
            print(f"\r  Frame {current_frame + 1}/{total_frames}", end="", flush=True)

        if output.suffix == ".gif":
            anim.save(output, writer="pillow", fps=fps, dpi=dpi, progress_callback=_progress)
        else:
            anim.save(output, fps=fps, dpi=dpi, progress_callback=_progress)
```

- [ ] **Step 4: Update the callsite in `animate_trajectory`**

Find the line (around line 249):
```python
_save_animation(fig, _update, None, n_frames, output, fps=fps, dpi=dpi)
```

Replace with:
```python
_save_animation(fig, ax, _update, None, n_frames, output, fps=fps, dpi=dpi)
```

- [ ] **Step 5: Run the new test**

```
pytest tests/test_trajectory.py::test_animate_trajectory_saves_gif_imageio -v
```

Expected: PASS

- [ ] **Step 6: Run the full test suite**

```
pytest tests/test_trajectory.py -v
```

Expected: all tests PASS (especially `test_animate_trajectory_saves_gif` which exercises the Pillow fallback path — unchanged).

- [ ] **Step 7: Commit**

```bash
git add src/mapgod/trajectory.py tests/test_trajectory.py
git commit -m "perf: cache background in _save_animation to avoid per-frame raster redraw"
```
