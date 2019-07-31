import csv
import sys

from django.contrib import admin
from django.contrib.auth.models import Group
from django.db.models import Count
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import path, reverse
from django.forms import forms, models
from django.shortcuts import render, redirect
from django.utils.safestring import mark_safe

from .models import Category, Origin, Entity, Hero, Villain, HeroAcquaintance, HeroProxy


admin.site.site_header = 'UMSRA Admin'
admin.site.site_title = 'UMSRA Admin Portal'
admin.site.index_title = 'Welcome to UMSRA Researcher Portal'


class CategoryChoiceField(models.ModelChoiceField):
    def label_from_instance(self, obj):
        return "Category: {}".format(obj.name)


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


class CsvImportForm(forms.Form):
    csv_file = forms.FileField()


class HeroAcquaintanceInline(admin.TabularInline):
    model = HeroAcquaintance


class HeroAdmin(admin.ModelAdmin, ExportCsvMixin):
    list_display = ("name", "is_immortal", "category", "origin", "is_very_benevolent", 'children_display',)
    list_filter = ("is_immortal", "category", "origin", IsVeryBenevolentFilter)
    # mark a field as readonly
    # readonly_fields = ["headshot_image", "father", "mother", "spouse"]

    # show an uneditable field.
    readonly_fields = ["headshot_image", "added_on"]
    # add additional actions
    actions = ["mark_immortal", "export_as_csv"]
    
    # hide the 'added_by' field to not show up on the change form
    exclude = ['added_by',]

    # add Custom Action Buttons (not actions)
    change_list_template = "entities/heroes_changelist.html"
    inlines = [HeroAcquaintanceInline]
    # show larger number of rows on listview page
    # list_per_page = 25

    # disable django admin pagination
    list_per_page = sys.maxsize

    # date based filtering
    date_hierarchy = 'added_on'

    raw_id_fields = ["category"]

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.added_by = request.user
        super().save_model(request, obj, form, change)
    
    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('immortal/', self.set_immortal),
            path('mortal/', self.set_mortal),
            path('import-csv/', self.import_csv),
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
    
    # import CSV
    def import_csv(self, request):
        if request.method == "POST":
            csv_file = request.FILES("csv_file")
            reader = csv.reader(csv_file)
            # Create Hero objects from passed in data
            # ...
            self.message_user(request, "Your csv file has been imported")
            return redirect("..")
        form = CsvImportForm()
        payload = {"form": form}
        return render(
            request, "admin/csv_form.html", payload
        )

    def mark_immortal(self, request, queryset):
        queryset.update(is_immortal=True)

    def is_very_benevolent(self, obj):
        return obj.benevolence_factor > 75
    
    # show “on” or “off” icons for calculated boolean fields
    is_very_benevolent.boolean = True
    
    # remove the delete selected action
    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions
    
    def children_display(self, obj):
        display_text = ", ".join(["<a href={}>{}</a>".format(
                    reverse('admin:{}_{}_change'.format(obj._meta.app_label, obj._meta.model_name),
                    args=(child.pk,)),
                child.name)
             for child in obj.children.all()
        ])
        if display_text:
            return mark_safe(display_text)
        return "-"
    
    children_display.short_description = 'Children'

    def headshot_image(self, obj):
        return mark_safe('<img src="{url}" width="{width}" height={height} />'.format(
            url = obj.headshot.url,
            width=obj.headshot.width,
            height=obj.headshot.height,
            )
        )
    
    # make a field editable while creating, but read only in existing objects
    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ["name"]
        else:
            return []
    
    #  filter FK dropdown values in django admin
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'category':
            # kwargs["queryset"] = Category.objects.filter(name__in=["God", "Demi God"])
            return CategoryChoiceField(queryset=Category.objects.all())
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class HeroProxyAdmin(admin.ModelAdmin, ExportCsvMixin):
    list_display = ("name", "is_immortal", "category", "origin",)


class VillainInline(admin.StackedInline):
    model = Villain


class VillainAdmin(admin.ModelAdmin, ExportCsvMixin):
    list_display = ("name", "category", "origin")
    actions = ["export_as_csv"]

    date_hierarchy = 'added_on'

    change_form_template = "entities/villain_changeform.html"

    def response_change(self, request, obj):
        if "_make-unique" in request.POST:
            matching_names_except_this = self.get_queryset(request).filter(name=obj.name).exclude(pk=obj.id)
            matching_names_except_this.delete()
            obj.is_unique = True
            obj.save()
            self.message_user(request, "This villain is now unique")
            return HttpResponseRedirect(".")
        return super().response_change(request, obj)


class CategoryAdmin(admin.ModelAdmin):
    inlines = [VillainInline]
    # remove the ‘Add’/’Delete’ button
    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(Category, CategoryAdmin)
# admin.site.register(Origin)
admin.site.register(Origin, OriginAdmin)
admin.site.register(Hero, HeroAdmin)
admin.site.register(HeroProxy, HeroProxyAdmin)
admin.site.register(Villain, VillainAdmin)

admin.site.unregister(Group)
