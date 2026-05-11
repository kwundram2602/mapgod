"""Trajectory plotting and animation over GeoTIFF rasters."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import matplotlib.pyplot as plt
import numpy as np
import rasterio
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from rasterio.enums import Resampling

if TYPE_CHECKING:
    from vecraspy.vector import Trajectory


def _load_raster(
    path: Path | str,
    band: int,
    *,
    max_dim: int | None = None,
    dtype: np.dtype | str | None = np.float32,
) -> tuple[np.ndarray, list[float], Any]:
    """Return (data_2d, extent, raster_crs) from a GeoTIFF."""
    with rasterio.open(path) as src:
        read_kwargs: dict[str, Any] = {}
        if max_dim is not None:
            scale = min(max_dim / src.width, max_dim / src.height, 1.0)
            if scale < 1.0:
                out_height = max(1, int(src.height * scale))
                out_width = max(1, int(src.width * scale))
                read_kwargs["out_shape"] = (out_height, out_width)
                read_kwargs["resampling"] = Resampling.bilinear
        if dtype is not None:
            read_kwargs["out_dtype"] = np.dtype(dtype)
        raw = src.read(band, **read_kwargs)
        nodata = src.nodata
        bounds = src.bounds
        crs = src.crs
    if nodata is not None:
        if not np.issubdtype(raw.dtype, np.floating):
            raw = raw.astype(np.float32)
        raw = np.where(raw == nodata, np.nan, raw)
    extent = [bounds.left, bounds.right, bounds.bottom, bounds.top]
    return raw, extent, crs


def _reproject_points(
    traj: Trajectory, raster_crs: Any
) -> tuple[list[float], list[float]]:
    """Return (xs, ys) of trajectory points reprojected to raster CRS."""
    epsg = raster_crs.to_epsg()
    target = f"EPSG:{epsg}" if epsg else raster_crs.to_wkt()
    pts = traj.points.to_crs(target) if traj.points.crs else traj.points
    return [g.x for g in pts.geometry], [g.y for g in pts.geometry]


def _color_cycle() -> list[str]:
    return [p["color"] for p in plt.rcParams["axes.prop_cycle"]]


def _save_animation(fig, update_fn, anim, n_frames: int, output: Path, *, fps: int, dpi: int) -> None:
    """Save animation using imageio-ffmpeg when available, falling back to Pillow."""
    try:
        import importlib.util

        import imageio

        if importlib.util.find_spec("imageio_ffmpeg") is None:
            raise ImportError("imageio_ffmpeg not installed")

        with imageio.get_writer(str(output), fps=fps) as writer:
            for i in range(n_frames):
                update_fn(i)
                fig.canvas.draw()
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


def plot_trajectory(
    raster: Path | str,
    trajectories: Trajectory | list[Trajectory],
    *,
    band: int = 1,
    cmap: str = "gray",
    raster_max_dim: int | None = 4096,
    raster_dtype: np.dtype | str | None = np.float32,
    point_style: dict | None = None,
    line_style: dict | None = None,
    ax: Axes | None = None,
    title: str | None = None,
    figsize: tuple[float, float] = (10, 8),
) -> tuple[Figure, Axes]:
    """Plot one or more trajectories over a GeoTIFF raster (static)."""
    from vecraspy.vector import Trajectory as _Trajectory

    if isinstance(trajectories, _Trajectory):
        trajectories = [trajectories]

    data, extent, raster_crs = _load_raster(
        raster,
        band,
        max_dim=raster_max_dim,
        dtype=raster_dtype,
    )

    if ax is None:
        fig, ax = plt.subplots(figsize=figsize)
    else:
        fig = ax.get_figure()

    valid = data[np.isfinite(data)]
    vmin = float(np.nanpercentile(valid, 2)) if valid.size > 0 else None
    vmax = float(np.nanpercentile(valid, 98)) if valid.size > 0 else None
    ax.imshow(data, cmap=cmap, extent=extent, origin="upper", vmin=vmin, vmax=vmax)

    ls: dict = {"linewidth": 1.5, "alpha": 0.8}
    ps: dict = {"markersize": 6, "zorder": 5}
    if line_style:
        ls.update(line_style)
    if point_style:
        ps.update(point_style)

    colors = _color_cycle()
    for i, traj in enumerate(trajectories):
        color = colors[i % len(colors)]
        xs, ys = _reproject_points(traj, raster_crs)
        if len(xs) > 1:
            ax.plot(xs, ys, color=color, **ls)
        ax.plot(xs[-1], ys[-1], "o", color=color, **ps)

    if title:
        ax.set_title(title)
    ax.set_xlabel("Easting")
    ax.set_ylabel("Northing")
    return fig, ax


def animate_trajectory(
    raster: Path | str,
    trajectories: Trajectory | list[Trajectory],
    *,
    band: int = 1,
    cmap: str = "gray",
    raster_max_dim: int | None = 1024,
    raster_dtype: np.dtype | str | None = np.float32,
    point_style: dict | None = None,
    line_style: dict | None = None,
    interval: int = 100,
    output: Path | str | None = None,
    figsize: tuple[float, float] = (8, 6),
    title: str | None = None,
    fps: int = 10,
    dpi: int = 72,
    nth_frame: int = 1,
):
    """Animate one or more trajectories building up over a GeoTIFF raster.

    Each frame reveals one more point. Multiple trajectories run in parallel;
    shorter ones freeze at their last point. Returns a FuncAnimation object.
    Saves to .gif (pillow) or .mp4 (ffmpeg) when output is provided.
    """
    from matplotlib.animation import FuncAnimation
    from vecraspy.vector import Trajectory as _Trajectory

    if isinstance(trajectories, _Trajectory):
        trajectories = [trajectories]

    print(f"Loading raster: {raster}")
    data, extent, raster_crs = _load_raster(
        raster,
        band,
        max_dim=raster_max_dim,
        dtype=raster_dtype,
    )
    print(f"Raster loaded: shape={data.shape}, CRS={raster_crs}")

    fig, ax = plt.subplots(figsize=figsize)

    valid = data[np.isfinite(data)]
    vmin = float(np.nanpercentile(valid, 2)) if valid.size > 0 else None
    vmax = float(np.nanpercentile(valid, 98)) if valid.size > 0 else None
    ax.imshow(data, cmap=cmap, extent=extent, origin="upper", vmin=vmin, vmax=vmax)

    if title:
        ax.set_title(title)
    ax.set_xlabel("Easting")
    ax.set_ylabel("Northing")

    ls: dict = {"linewidth": 1.5, "alpha": 0.8}
    ps: dict = {"markersize": 6, "zorder": 5}
    if line_style:
        ls.update(line_style)
    if point_style:
        ps.update(point_style)

    colors = _color_cycle()
    all_coords: list[tuple[list[float], list[float]]] = []
    print(f"Reprojecting {len(trajectories)} trajectory/trajectories to raster CRS...")
    for traj in trajectories:
        xs, ys = _reproject_points(traj, raster_crs)
        all_coords.append((xs, ys))

    n_frames_full = max(len(c[0]) for c in all_coords)
    frame_indices = list(range(0, n_frames_full, nth_frame))
    n_frames = len(frame_indices)
    print(f"Animation: {len(all_coords)} trajectory/trajectories, {n_frames} frames total (nth_frame={nth_frame})")

    artist_groups = []
    for i, (xs, ys) in enumerate(all_coords):
        print(f"  Trajectory {i}: {len(xs)} points")
        color = colors[i % len(colors)]
        (line,) = ax.plot([], [], color=color, **ls)
        (marker,) = ax.plot([], [], "o", color=color, **ps)
        artist_groups.append((line, marker, xs, ys))

    def _update(frame: int):
        updated = []
        actual_frame = frame_indices[frame]
        for line, marker, xs, ys in artist_groups:
            n = min(actual_frame + 1, len(xs))
            if n >= 2:
                line.set_data(xs[:n], ys[:n])
            else:
                line.set_data([], [])
            marker.set_data([xs[n - 1]], [ys[n - 1]])
            updated.extend([line, marker])
        return updated

    if output is not None:
        output = Path(output)
        print(f"Saving animation to {output} (fps={fps}, dpi={dpi}, {n_frames} frames)...")
        _save_animation(fig, _update, None, n_frames, output, fps=fps, dpi=dpi)
        print(f"\nSaved: {output}")

    anim = FuncAnimation(fig, _update, frames=n_frames, interval=interval, blit=True)
    return anim
