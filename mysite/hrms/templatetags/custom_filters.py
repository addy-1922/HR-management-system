from django import template

register = template.Library()


@register.filter
def startswith(value, arg):
    """Return True if the string value starts with the given argument."""
    return str(value).startswith(str(arg))
