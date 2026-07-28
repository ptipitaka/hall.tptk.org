"""Moon phase SVG rendering (ported from original patidina utils)."""

from __future__ import annotations

import math
from datetime import date

import ephem
from svgwrite import Drawing


def draw_moon_phase_as_svg(phase: float, texture_path: str = "/static/patidina/img/moon.png") -> str:
    radius = 100
    svg = Drawing(size=(2 * radius, 2 * radius))
    center = radius

    pattern = svg.pattern(size=(2 * radius, 2 * radius), patternUnits="userSpaceOnUse")
    pattern.add(svg.image(href=texture_path, size=(2 * radius, 2 * radius)))
    svg.defs.add(pattern)

    moon = svg.circle(center=(center, center), r=radius, fill=pattern.get_funciri())
    svg.add(moon)

    if phase < 0:
        phase = abs(phase)
        for y in range(-radius, radius):
            x = math.sqrt(radius**2 - y**2)
            shade_width = 2 * x * phase
            x0 = center - x + shade_width
            x1 = center + x
            y0 = center + y
            svg.add(
                svg.line(
                    start=(x0, y0),
                    end=(x1, y0),
                    stroke="#f9c23c",
                    stroke_opacity=0.6,
                    stroke_width=2,
                )
            )
    elif phase > 0:
        for y in range(-radius, radius):
            x = math.sqrt(radius**2 - y**2)
            shade_width = 2 * x * phase
            x0 = center - x
            x1 = center + x - shade_width
            y0 = center + y
            svg.add(
                svg.line(
                    start=(x0, y0),
                    end=(x1, y0),
                    stroke="#f9c23c",
                    stroke_opacity=0.6,
                    stroke_width=2,
                )
            )

    return svg.tostring()


def moon_phase_svg(ini_solar_date: date | None = None) -> str:
    if ini_solar_date is None:
        ini_solar_date = date.today()
    observer = ephem.Observer()
    observer.date = ini_solar_date
    m = ephem.Moon(observer)
    m.compute(observer)
    phase = 1 - m.moon_phase
    if m.elong > 0:
        phase = -phase
    return draw_moon_phase_as_svg(phase)
