"""Shared Patidina choice constants (no Django model imports)."""

MOON_PHASE_CHOICES = [
    ("01", "ขึ้น"),
    ("02", "แรม"),
]

DAY_CHOICES = [(f"{i:02d}", f"{i:2d}") for i in range(1, 16)]

MONTH_CHOICES = [
    ("01", "1"),
    ("02", "2"),
    ("03", "3"),
    ("04", "4"),
    ("05", "5"),
    ("06", "6"),
    ("07", "7"),
    ("08", "8"),
    ("09", "88"),
    ("10", "9"),
    ("11", "10"),
    ("12", "11"),
    ("13", "12"),
]

MONTH_DISPLAY_TO_CODE = {display: code for code, display in MONTH_CHOICES}
