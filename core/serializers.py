from rest_framework import serializers
from .models import Scheme, UserProfile

class SchemeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Scheme
        fields = '__all__'
        read_only_fields = ['last_updated', 'scheme_code']

    def validate_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("Name cannot be empty.")
        return value.strip()

    def validate(self, data):
        """Cross-field validation for education ranges and income."""
        edu_min = data.get('education_min')
        edu_max = data.get('education_max')
        
        if edu_min is not None and edu_max is not None:
            if edu_min > edu_max:
                raise serializers.ValidationError({
                    "education_max": "education_max must be greater than or equal to education_min."
                })
        
        min_income = data.get('min_income')
        max_income = data.get('max_income')
        if min_income is not None and max_income is not None:
            if min_income > max_income:
                raise serializers.ValidationError({
                    "max_income": "max_income must be greater than or equal to min_income."
                })
                
        return data

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = '__all__'
        read_only_fields = ['created_at']

class MatchResponseSerializer(serializers.Serializer):
    """Serializer for documentation / OpenAPI response schema."""
    user = serializers.CharField()
    total_matched = serializers.IntegerField()
    total_checked = serializers.IntegerField()
    matches = serializers.ListField(child=serializers.DictField())
    message = serializers.CharField(required=False, allow_blank=True)
