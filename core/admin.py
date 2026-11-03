from django.contrib import admin
from .models import Scheme, UserProfile


from .services.data_pipeline import normalize_scheme_data
from .services.undo_service import record_action

@admin.register(Scheme)
class SchemeAdmin(admin.ModelAdmin):
    list_display  = [
        'name', 'opportunity_type', 'provider',
        'education_min', 'education_max',
        'max_income', 'category', 'state', 'deadline',
    ]
    list_filter   = ['opportunity_type', 'provider', 'category', 'state', 'requires_disability']
    search_fields = ['name', 'description', 'state']
    ordering      = ['name']

    def save_model(self, request, obj, form, change):
        # Normalize fields before saving
        data = {
            'name': obj.name,
            'opportunity_type': obj.opportunity_type,
            'education_min': obj.education_min,
            'education_max': obj.education_max,
            'required_documents': obj.required_documents,
            'category': obj.category,
            'state': obj.state,
        }
        normalized = normalize_scheme_data(data)
        
        obj.name = normalized['name']
        obj.opportunity_type = normalized['opportunity_type']
        obj.education_min = normalized['education_min']
        obj.education_max = normalized['education_max']
        
        # Ensure documents are handled correctly
        obj.required_documents = normalized['required_documents']
        obj.category = normalized['category']
        obj.state = normalized['state']
        
        # Track for Undo (if changing existing or creating new)
        # record_action handles 'update' by taking current state as 'previous'
        if change:
            # We must fetch the OLD state from DB for a true 'update' record
            old_obj = Scheme.objects.get(id=obj.id)
            record_action(old_obj, 'update')
        
        super().save_model(request, obj, form, change)
        
        if not change:
            # For creation, record AFTER save so we have the ID
            record_action(obj, 'create')


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display  = ['name', 'education_level', 'income', 'category', 'state', 'marks', 'created_at']
    list_filter   = ['education_level', 'category', 'state']
    search_fields = ['name', 'state']
    readonly_fields = ['created_at']
    ordering      = ['-created_at']
