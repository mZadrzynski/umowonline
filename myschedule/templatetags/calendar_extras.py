from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    Zwraca dictionary[key] lub [] jeśli nie ma
    """
    try:
        return dictionary.get(key, [])
    except Exception:
        return []