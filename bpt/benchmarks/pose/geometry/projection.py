"""Dataset camera transforms implemented from official reference code."""

from __future__ import annotations

import numpy as np


def fit3d_world_to_camera(points_world: np.ndarray, rotation: np.ndarray, translation: np.ndarray) -> np.ndarray:
    """Fit3D row-vector equivalent of ``(X - T) @ R.T``."""

    points = np.asarray(points_world, dtype=np.float64)
    rotation = np.asarray(rotation, dtype=np.float64).reshape(3, 3)
    translation = np.asarray(translation, dtype=np.float64).reshape(3)
    return (points - translation) @ rotation.T


def athlete_world_to_camera(
    points_world: np.ndarray,
    extrinsic_matrix: np.ndarray,
    camera_position: np.ndarray,
) -> np.ndarray:
    """AthletePose3D's official y/z-row-corrected world-to-camera transform."""

    rotation = np.asarray(extrinsic_matrix, dtype=np.float64).reshape(3, 3).copy()
    rotation[1:, :] *= -1.0
    position = np.asarray(camera_position, dtype=np.float64).reshape(3)
    points = np.asarray(points_world, dtype=np.float64)
    return (rotation @ (points - position).T).T


def project_pinhole(
    points_camera: np.ndarray,
    focal: np.ndarray,
    center: np.ndarray,
) -> np.ndarray:
    points = np.asarray(points_camera, dtype=np.float64)
    focal = np.asarray(focal, dtype=np.float64).reshape(2)
    center = np.asarray(center, dtype=np.float64).reshape(2)
    with np.errstate(divide="ignore", invalid="ignore"):
        normalized = points[..., :2] / points[..., 2:3]
    return normalized * focal + center


def project_fit3d_distorted(
    points_camera: np.ndarray,
    focal: np.ndarray,
    center: np.ndarray,
    radial: np.ndarray,
    tangential: np.ndarray,
) -> np.ndarray:
    """Match the official Fit3D Brown-Conrady projection implementation."""

    points = np.asarray(points_camera, dtype=np.float64)
    focal = np.asarray(focal, dtype=np.float64).reshape(2)
    center = np.asarray(center, dtype=np.float64).reshape(2)
    radial = np.asarray(radial, dtype=np.float64).reshape(3)
    # Official JSON stores p as [p1,p2], while its utility swaps it here.
    p = np.asarray(tangential, dtype=np.float64).reshape(2)[[1, 0]]
    with np.errstate(divide="ignore", invalid="ignore"):
        x = points[..., :2] / points[..., 2:3]
    radius2 = np.sum(x * x, axis=-1)
    radial_factor = 1.0 + radial[0] * radius2 + radial[1] * radius2**2 + radial[2] * radius2**3
    tangent_dot = x @ p
    distorted = x * (tangent_dot + radial_factor)[..., None] + radius2[..., None] * p
    return distorted * focal + center


def fit3d_project_world(points_world: np.ndarray, camera: dict, distorted: bool = True) -> np.ndarray:
    camera_points = fit3d_world_to_camera(
        points_world,
        camera["extrinsics"]["R"],
        camera["extrinsics"]["T"],
    )
    key = "intrinsics_w_distortion" if distorted else "intrinsics_wo_distortion"
    intrinsics = camera[key]
    if distorted:
        return project_fit3d_distorted(
            camera_points,
            intrinsics["f"],
            intrinsics["c"],
            intrinsics["k"],
            intrinsics["p"],
        )
    return project_pinhole(camera_points, intrinsics["f"], intrinsics["c"])


def athlete_project_world(points_world: np.ndarray, camera: dict) -> tuple[np.ndarray, np.ndarray]:
    """Return official pinhole image points and metric camera-frame joints."""

    camera_points = athlete_world_to_camera(
        points_world,
        camera["extrinsic_matrix"],
        camera["xyz"],
    )
    matrix = np.asarray(camera["affine_intrinsics_matrix"], dtype=np.float64)
    pixels = project_pinhole(camera_points, [matrix[0, 0], matrix[1, 1]], [matrix[0, 2], matrix[1, 2]])
    return pixels, camera_points
