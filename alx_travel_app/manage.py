#!/usr/bin/env python

from rest_framework import fields

_old_init = fields.Field.__init__

def patch_init(self, *args, **kwargs):
    kwargs.pop('encoder', None)
    kwargs.pop('decoder', None)
    return _old_init(self, *args, **kwargs)

fields.Field.__init__ = patch_init

"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'alx_travel_app.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
