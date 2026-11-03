import json
from django.core import serializers
from django.db import transaction
from core.models import Scheme, UndoLog

def record_action(obj, action):
    """
    Record an action in the UndoLog.
    action: 'create', 'update', or 'delete'
    """
    previous_data = None
    if action in ('update', 'delete'):
        # For update/delete, store the current state (as previous data)
        previous_data = json.loads(serializers.serialize('json', [obj]))[0]['fields']

    UndoLog.objects.create(
        action=action,
        object_id=obj.id,
        model_name=obj._meta.model_name,
        previous_data=previous_data
    )

def undo_last_action():
    """
    Reverse the most recent entry in UndoLog.
    Returns: (success: bool, message: str)
    """
    log = UndoLog.objects.all().first()
    if not log:
        return False, "No actions to undo."

    try:
        with transaction.atomic():
            if log.action == 'create':
                # Reverse creation by deleting the object
                try:
                    obj = Scheme.objects.get(id=log.object_id)
                    obj.delete()
                except Scheme.DoesNotExist:
                    pass # Already gone
                
            elif log.action == 'update':
                # Restore previous state
                try:
                    obj = Scheme.objects.get(id=log.object_id)
                    for key, value in log.previous_data.items():
                        setattr(obj, key, value)
                    obj.save()
                except Scheme.DoesNotExist:
                    return False, f"Cannot undo update: Object {log.object_id} no longer exists."

            elif log.action == 'delete':
                # Re-create the object from previous_data
                Scheme.objects.create(id=log.object_id, **log.previous_data)

            # Once reversed, delete the log entry
            log.delete()
            return True, f"Successfully reversed {log.action} on {log.model_name}:{log.object_id}"

    except Exception as e:
        return False, f"Undo failed: {str(e)}"
