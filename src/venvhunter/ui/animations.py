from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import (
    QEasingCurve,
    QPoint,
    QParallelAnimationGroup,
    QPropertyAnimation,
    QSequentialAnimationGroup,
    QVariantAnimation,
)
from PySide6.QtWidgets import QGraphicsOpacityEffect, QLabel, QWidget


def fade_in(
    widget: QWidget,
    enabled: bool,
    duration_ms: int = 180,
    delay_ms: int = 0,
    finished: Callable[[], None] | None = None,
) -> QSequentialAnimationGroup | None:
    if not enabled:
        if finished:
            finished()
        return None

    effect = QGraphicsOpacityEffect(widget)
    widget.setGraphicsEffect(effect)

    fade = QPropertyAnimation(effect, b"opacity", widget)
    fade.setDuration(duration_ms)
    fade.setStartValue(0.0)
    fade.setEndValue(1.0)
    fade.setEasingCurve(QEasingCurve.Type.OutCubic)

    group = QSequentialAnimationGroup(widget)
    if delay_ms:
        group.addPause(delay_ms)
    group.addAnimation(fade)

    def cleanup() -> None:
        widget.setGraphicsEffect(None)
        if finished:
            finished()

    group.finished.connect(cleanup)
    group.start()
    return group


def fade_slide_in(
    widget: QWidget,
    enabled: bool,
    offset: QPoint | None = None,
    duration_ms: int = 190,
    delay_ms: int = 0,
    finished: Callable[[], None] | None = None,
) -> QSequentialAnimationGroup | None:
    if not enabled:
        if finished:
            finished()
        return None

    slide_offset = offset if offset is not None else QPoint(0, 10)
    original_position = widget.pos()
    widget.move(original_position + slide_offset)

    effect = QGraphicsOpacityEffect(widget)
    widget.setGraphicsEffect(effect)

    fade = QPropertyAnimation(effect, b"opacity", widget)
    fade.setDuration(duration_ms)
    fade.setStartValue(0.0)
    fade.setEndValue(1.0)
    fade.setEasingCurve(QEasingCurve.Type.OutCubic)

    slide = QPropertyAnimation(widget, b"pos", widget)
    slide.setDuration(duration_ms)
    slide.setStartValue(original_position + slide_offset)
    slide.setEndValue(original_position)
    slide.setEasingCurve(QEasingCurve.Type.OutCubic)

    parallel = QParallelAnimationGroup(widget)
    parallel.addAnimation(fade)
    parallel.addAnimation(slide)

    group = QSequentialAnimationGroup(widget)
    if delay_ms:
        group.addPause(delay_ms)
    group.addAnimation(parallel)

    def cleanup() -> None:
        widget.move(original_position)
        widget.setGraphicsEffect(None)
        if finished:
            finished()

    group.finished.connect(cleanup)
    group.start()
    return group


def animate_number(
    label: QLabel,
    start: int,
    end: int,
    formatter: Callable[[int], str],
    enabled: bool,
    duration_ms: int = 260,
) -> QVariantAnimation | None:
    if not enabled or start == end:
        label.setText(formatter(end))
        return None

    animation = QVariantAnimation(label)
    animation.setDuration(duration_ms)
    animation.setStartValue(start)
    animation.setEndValue(end)
    animation.setEasingCurve(QEasingCurve.Type.OutCubic)
    animation.valueChanged.connect(lambda value: label.setText(formatter(int(value))))
    animation.finished.connect(lambda: label.setText(formatter(end)))
    animation.start()
    return animation
