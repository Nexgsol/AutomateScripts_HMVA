from django.contrib import admin
from .models import Brand, AvatarProfile, Icon, Template, PublishTarget, ScriptRequest

@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ("name","timezone","post_windows")

@admin.register(AvatarProfile)
class AvatarAdmin(admin.ModelAdmin):
    list_display = ("brand","avatar_name","voice_name")

@admin.register(Template)
class TemplateAdmin(admin.ModelAdmin):
    list_display = ("brand","template_id","engine","duration_sec")

@admin.register(PublishTarget)
class PublishTargetAdmin(admin.ModelAdmin):
    list_display = ("brand","platform","enabled")

@admin.register(ScriptRequest)
class ScriptRequestAdmin(admin.ModelAdmin):
    list_display = ("id","brand","icon_or_topic","duration","status","created_at")
    list_filter = ("brand","status","duration")
    search_fields = ("icon_or_topic","draft_script","final_script")

@admin.register(Icon)
class IconAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "short_cues_preview")
    search_fields = ("name", "category", "short_cues")
    list_filter = ("category",)
    ordering = ("name",)

    def short_cues_preview(self, obj):
        text = (obj.short_cues or "").strip()
        return (text[:80] + "…") if len(text) > 80 else text
    short_cues_preview.short_description = "Notes"