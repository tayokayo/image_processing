from flask import Blueprint
from app.models import ComponentStatus

def init_filters(app):
    @app.template_filter('status_color_class')
    def status_color_class(status):
        """Return Tailwind CSS classes for component status colors"""
        return {
            ComponentStatus.PENDING: 'bg-yellow-100 text-yellow-800',
            ComponentStatus.ACCEPTED: 'bg-green-100 text-green-800',
            ComponentStatus.REJECTED: 'bg-red-100 text-red-800'
        }.get(status, 'bg-gray-100 text-gray-800')