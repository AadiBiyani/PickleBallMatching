"""
contact.py -- pick one ground-contact pixel from the two heels.

This file is pure arithmetic.  It does not open video, load a model, or know
about the court.  track_video.py feeds it heel locations and then maps the
returned pixel into court feet with the existing homography.

classify_contact also records how that pixel was chosen.  both_heels is the
midpoint.  single_heel is the one heel still visible in the image.  no_contact
means both heels are inside the frame but neither is usable.  out_of_frame
means both heels lie outside the image.
"""

from __future__ import annotations

from dataclasses import dataclass

# MediaPipe Pose Landmarker landmark indices.
# https://developers.google.com/edge/mediapipe/solutions/vision/pose_landmarker
LEFT_HEEL = 29
RIGHT_HEEL = 30

DEFAULT_MIN_VISIBILITY = 0.5

BOTH_HEELS = "both_heels"
SINGLE_HEEL = "single_heel"
NO_CONTACT = "no_contact"
OUT_OF_FRAME = "out_of_frame"


@dataclass(frozen=True)
class ContactSample:
    """The ground-contact pixel for one frame, and why it was chosen.

    pixel is (x, y) in image pixels, or None when the frame has no ground
    position.  status is both_heels, single_heel, no_contact, or out_of_frame.
    """

    pixel: tuple[float, float] | None
    status: str


def _usable(heel, min_visibility):
    """Return (x, y) when a heel observation is usable, else None.

    A heel is (x, y), (x, y, visibility), or None.  Missing visibility means
    the caller already decided the point is real.
    """
    if heel is None:
        return None
    if len(heel) >= 3 and heel[2] is not None and float(heel[2]) < min_visibility:
        return None
    return (float(heel[0]), float(heel[1]))


def contact_pixel(left_heel, right_heel, min_visibility=DEFAULT_MIN_VISIBILITY):
    """Return the ground-contact pixel, or None when neither heel is usable.

    Both heels usable: the midpoint, the same spot as a click between the feet.
    One heel usable: that heel.  Neither: None, and the frame is left blank.
    This does not know the image size, so it cannot tell an obstructed heel
    from one that left the frame.  Use classify_contact for that.
    """
    left = _usable(left_heel, min_visibility)
    right = _usable(right_heel, min_visibility)
    if left is not None and right is not None:
        return ((left[0] + right[0]) / 2.0, (left[1] + right[1]) / 2.0)
    if left is not None:
        return left
    return right


def _in_frame(pixel, width, height):
    x, y = pixel
    return 0.0 <= x < float(width) and 0.0 <= y < float(height)


def _observe(heel, width, height, min_visibility):
    """Return (state, pixel) for one heel.

    state is visible, obstructed, out_of_frame, or missing.  A heel outside
    the image is out_of_frame even when its visibility is high.  Missing
    visibility means the caller already decided the point is real.
    """
    if heel is None:
        return "missing", None
    pixel = (float(heel[0]), float(heel[1]))
    if not _in_frame(pixel, width, height):
        return "out_of_frame", pixel
    if len(heel) >= 3 and heel[2] is not None and float(heel[2]) < min_visibility:
        return "obstructed", pixel
    return "visible", pixel


def classify_contact(left_heel, right_heel, width, height, min_visibility=DEFAULT_MIN_VISIBILITY):
    """Choose the ground-contact pixel and name the case.

    Both heels visible inside the image: their midpoint, status both_heels.
    One heel visible inside the image: that heel, status single_heel.  The
    other heel may be obstructed or outside the image.
    Both heels outside the image: no pixel, status out_of_frame.
    Otherwise no pixel, status no_contact.  That covers two obstructed heels
    and a heel that is missing rather than outside the image.
    """
    left_state, left_px = _observe(left_heel, width, height, min_visibility)
    right_state, right_px = _observe(right_heel, width, height, min_visibility)
    if left_state == "visible" and right_state == "visible":
        return ContactSample(contact_pixel(left_px, right_px), BOTH_HEELS)
    if left_state == "visible":
        return ContactSample(left_px, SINGLE_HEEL)
    if right_state == "visible":
        return ContactSample(right_px, SINGLE_HEEL)
    if left_state == "out_of_frame" and right_state == "out_of_frame":
        return ContactSample(None, OUT_OF_FRAME)
    return ContactSample(None, NO_CONTACT)


def landmark_pixel(landmark, width, height):
    """Convert one normalized pose landmark to an image-pixel heel sample.

    Returns (x, y, visibility) or None.  x and y on a landmark are fractions
    of the frame width and height.  Visibility is omitted from the sample when
    the model did not provide it.
    """
    if landmark is None:
        return None
    x = float(landmark.x) * float(width)
    y = float(landmark.y) * float(height)
    visibility = getattr(landmark, "visibility", None)
    if visibility is None:
        return (x, y)
    return (x, y, float(visibility))


def classify_from_landmarks(landmarks, width, height, min_visibility=DEFAULT_MIN_VISIBILITY):
    """ContactSample from one pose's landmark list.

    A list with no heel landmarks is no_contact.  A missing pose, before any
    landmarks exist, is out_of_frame and is decided by the caller.
    """
    if not landmarks or len(landmarks) <= RIGHT_HEEL:
        return ContactSample(None, NO_CONTACT)
    left = landmark_pixel(landmarks[LEFT_HEEL], width, height)
    right = landmark_pixel(landmarks[RIGHT_HEEL], width, height)
    return classify_contact(left, right, width, height, min_visibility)


def contact_from_landmarks(landmarks, width, height, min_visibility=DEFAULT_MIN_VISIBILITY):
    """Contact pixel from one pose's landmark list, or None if the heels are missing."""
    return classify_from_landmarks(landmarks, width, height, min_visibility).pixel
