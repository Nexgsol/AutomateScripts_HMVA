from rest_framework import serializers
from .models import ScriptRequest

class ScriptRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScriptRequest
        fields = "__all__"
        read_only_fields = ("draft_script","qc_json","final_script","created_at","updated_at")
