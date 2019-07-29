from django.contrib.admin import AdminSite

from .models import Epic, EventHero, EventVillain, Event


class EventAdminSite(AdminSite):
    site_header = "UMSRA Events Admin"
    site_title = "UMSRA Events Admin Portal"
    index_title = "Welcome to UMSRA Researcher Events Portal"


event_admin_site = EventAdminSite(name='event_admin')


event_admin_site.register(Epic)
event_admin_site.register(EventHero)
event_admin_site.register(EventVillain)
event_admin_site.register(Event)
