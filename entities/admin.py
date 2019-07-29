import csv

from django.contrib import admin
from django.contrib.auth.models import Group
from django.db.models import Count
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import path

from .models import Category, Origin, Entity, Hero, Villain


admin.site.site_header = 'UMSRA Admin'
admin.site.site_title = 'UMSRA Admin Portal'
admin.site.index_title = 'Welcome to UMSRA Researcher Portal'


class OriginAdmin(admin.ModelAdmin):
    list_display = ("name", "hero_count", "villain_count")

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(
            _hero_count=Count("hero", distinct=True),
            _villain_count=Count("villain", distinct=True),
        )
        return queryset

    def hero_count(self, obj):
        return obj._hero_count

    def villain_count(self, obj):
        return obj._villain_count
    
    # enable sorting on calculated fields
    hero_count.admin_order_field = '_hero_count'
    villain_count.admin_order_field = '_villain_count'


# enable filtering on calculated fields
class IsVeryBenevolentFilter(admin.SimpleListFilter):
    title = 'is_very_benevolent'
    parameter_name = 'is_very_benevolent'

    def lookups(self, request, model_admin):
        return (
            ('Yes', 'Yes'),
            ('No', 'No'),
        )
    
    def queryset(self, request, queryset):
        value = self.value()
        if value == 'Yes':
            return queryset.filter(benevolence_factor__gt=75)
        elif value == 'No':
            return queryset.exclude(benevolence_factor__gt=75)
        return queryset


# export CSV
class ExportCsvMixin:
    def export_as_csv(self, request, queryset):
        meta = self.model._meta
        field_names = [field.name for field in meta.field]
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename={}.csv'.format(meta)
        writer = csv.writer(response)

        writer.writerow(field_names)
        for obj in queryset:
            row = writer.writerow([getattr(obj, field) for field in field_names])
        
        return response
    
    export_as_csv.short_description = "Export Selected"


class HeroAdmin(admin.ModelAdmin, ExportCsvMixin):
    list_display = ("name", "is_immortal", "category", "origin", "is_very_benevolent")
    list_filter = ("is_immortal", "category", "origin", IsVeryBenevolentFilter)
    # add additional actions
    actions = ["mark_immortal", "export_as_csv"]

    # add Custom Action Buttons (not actions)
    change_list_template = "entities/heroes_changelist.html"

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('immortal/', self.set_immortal),
            path('mortal/', self.set_mortal),
        ]
        
        return my_urls + urls
    
    def set_immortal(self, request):
        self.model.objects.all().update(is_immortal=True)
        self.message_user(request, "All heroes are now immortal")
        return HttpResponseRedirect("../")
    

    def set_mortal(self, request):
        self.model.objects.all().update(is_immortal=False)
        self.message_user(request, "All heroes are now mortal")
        return HttpResponseRedirect("../")

    def mark_immortal(self, request, queryset):
        queryset.update(is_immortal=True)

    def is_very_benevolent(self, obj):
        return obj.benevolence_factor > 75
    
    # remove the delete selected action
    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions
    
    # show “on” or “off” icons for calculated boolean fields
    is_very_benevolent.boolean = True


class VillainAdmin(admin.ModelAdmin, ExportCsvMixin):
    list_display = ("name", "category", "origin")
    actions = ["export_as_csv"]


admin.site.register(Category)
# admin.site.register(Origin)
admin.site.register(Origin, OriginAdmin)
admin.site.register(Hero, HeroAdmin)
admin.site.register(Villain, VillainAdmin)

admin.site.unregister(Group)
