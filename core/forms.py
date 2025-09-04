from django import forms
from .models import Brand, Icon, ScriptRequest

class ScriptAvatarForm(forms.Form):
    # LEFT
    brand = forms.ModelChoiceField(queryset=Brand.objects.all(), label="Brand")
    icon  = forms.ModelChoiceField(queryset=Icon.objects.order_by("name"), label="Icon")
    category = forms.CharField(max_length=100, required=False, label="Category (auto)")
    notes = forms.CharField(widget=forms.Textarea(attrs={"rows":4}), required=False, label="Notes")
    duration = forms.ChoiceField(choices=ScriptRequest.DUR, initial="30s", label="Duration")

    # RIGHT
    heygen_avatar_id = forms.CharField(max_length=100, required=False, label="HeyGen Avatar ID")
    heygen_voice_id  = forms.CharField(max_length=100, required=False, label="HeyGen Voice ID")
