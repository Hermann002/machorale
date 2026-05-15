from django import template

register = template.Library()

# Mapping centralisé : event_type → (icône Material Symbols, classe text, classe bg)
# Toute modification d'icône ou de couleur se fait ici, une seule fois.
_ACTIVITY_ICONS = {
    'payment':       ('payments',      'text-green-600',  'bg-green-50 dark:bg-green-900/30'),
    'person_add':    ('person_add',    'text-blue-600',   'bg-blue-50 dark:bg-blue-900/30'),
    'person_remove': ('person_remove', 'text-red-600',    'bg-red-50 dark:bg-red-900/30'),
    'warning':       ('warning',       'text-yellow-600', 'bg-yellow-50 dark:bg-yellow-900/30'),
    'upload_file':   ('description',   'text-purple-600', 'bg-purple-50 dark:bg-purple-900/30'),
    'other':         ('event_note',    'text-slate-600',  'bg-slate-50 dark:bg-slate-900/30'),
}

_DEFAULT = _ACTIVITY_ICONS['other']


@register.filter
def activity_icon(event_type):
    """Retourne le nom de l'icône Material Symbols pour un type d'activité."""
    return _ACTIVITY_ICONS.get(event_type, _DEFAULT)[0]


@register.filter
def activity_icon_color(event_type):
    """Retourne les classes Tailwind bg + text pour le conteneur d'icône."""
    data = _ACTIVITY_ICONS.get(event_type, _DEFAULT)
    return f"{data[2]} {data[1]}"
