# animate_trajectory Blit Fix

## Problem

`_save_animation` calls `fig.canvas.draw()` every frame. This redraws the full figure — raster imshow included — so render time grows linearly with frame count. Frames get progressively slower.

## Fix: Manual Blit in Save Path

Cache the background (raster + empty axes) once before the loop. Each frame: restore background, draw only the dirty trajectory artists, blit canvas. Raster is never redrawn after frame 0.

## Changes

**File:** `src/mapgod/trajectory.py`

### `_save_animation` signature

Add `ax` parameter:

```python
def _save_animation(fig, ax, update_fn, anim, n_frames, output, *, fps, dpi):
```

### imageio path — before loop

```python
fig.canvas.draw()
bg = fig.canvas.copy_from_bbox(fig.bbox)
```

### imageio path — per frame (replaces current body)

```python
artists = update_fn(i)
fig.canvas.restore_region(bg)
for artist in artists:
    ax.draw_artist(artist)
fig.canvas.blit(fig.bbox)
w, h = fig.canvas.get_width_height()
buf = np.frombuffer(fig.canvas.buffer_rgba(), dtype=np.uint8).reshape(h, w, 4)
writer.append_data(buf[..., :3].copy())
```

### callsite in `animate_trajectory`

```python
_save_animation(fig, ax, _update, None, n_frames, output, fps=fps, dpi=dpi)
```

## Non-goals

- Interactive FuncAnimation path is unchanged (blit=True already handles it).
- Pillow fallback path is unchanged.
- `_update` / `xs[:n]` slice logic is unchanged.
