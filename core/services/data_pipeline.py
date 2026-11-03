import re
from core.models import Scheme
from core.serializers import SchemeSerializer
from core.services.undo_service import record_action

def normalize_scheme_data(data):
    """
    Clean, validate, and auto-correct scheme data.
    Ensures pre/post-matric rules are followed.
    """
    name = str(data.get('name', '')).strip()
    
    # Auto-fix education ranges from name (as per requirement)
    edu_min, edu_max = data.get('education_min'), data.get('education_max')
    
    # Lower-case for matching
    ln = name.lower()
    if re.search(r"pre[\s\-_]*matric", ln):
        edu_min = 0
        edu_max = 0
    elif re.search(r"post[\s\-_]*matric", ln):
        edu_min = 1
        edu_max = 5
    elif re.search(r"fellowship|jrf|srf", ln):
        edu_min = 5
        edu_max = 5
    elif "ug" in ln or "undergraduate" in ln:
        edu_min = 4
        edu_max = 4
    elif "pg" in ln or "postgraduate" in ln:
        edu_min = 5
        edu_max = 5

    normalized = data.copy()
    normalized.update({
        'name': name,
        'education_min': edu_min,
        'education_max': edu_max,
        'category': str(data.get('category', 'all')).lower().strip(),
        'state': str(data.get('state', 'all')).lower().strip(),
    })
    
    # Ensure required_documents is a list for the serializer
    docs = normalized.get('required_documents', [])
    if isinstance(docs, str):
        docs = [d.strip() for d in docs.split(',') if d.strip()]
    normalized['required_documents'] = sorted(list(set(docs)))
    
    return normalized

def create_scheme_safe(data):
    """
    Safe creation using Serializer + UndoLog tracking.
    """
    normalized = normalize_scheme_data(data)
    
    # Use DRF Serializer for validation
    serializer = SchemeSerializer(data=normalized)
    
    if not serializer.is_valid():
        return {'success': False, 'errors': serializer.errors}
    
    # Final duplicate check (by name)
    if Scheme.objects.filter(name=normalized['name']).exists():
        return {'success': False, 'errors': {'name': ['A scheme with this name already exists.']}}
    
    # Save with Undo tracking
    try:
        scheme = serializer.save()
        record_action(scheme, 'create')
        return {'success': True, 'scheme_id': scheme.id}
    except Exception as e:
        return {'success': False, 'errors': {'system': str(e)}}
