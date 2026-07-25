from django import template

register = template.Library()


@register.filter
def to_mb(value):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return "0.00 MB"
    return f"{value / 1024 / 1024:.2f} MB"
