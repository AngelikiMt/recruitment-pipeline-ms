from django.contrib import admin
from .models import Job, Candidate, Application, StageHistory, AuditLog


class StageHistoryInline(admin.TabularInline):
    model = StageHistory
    extra = 0
    readonly_fields = ("stage", "entered_at", "note")


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "department", "location", "is_open", "created_at")
    list_filter = ("is_open", "department", "location")
    search_fields = ("title", "department", "location")
    ordering = ("-created_at",)


@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = ("id", "full_name", "email", "created_at")
    search_fields = ("full_name", "email")
    ordering = ("-created_at",)


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ("id", "candidate", "job", "status", "score", "applied_at", "hired_at")
    list_filter = ("status", "job")
    search_fields = ("candidate__full_name", "candidate__email", "job__title")
    readonly_fields = ("applied_at", "hired_at")
    inlines = [StageHistoryInline]
    ordering = ("-applied_at",)


@admin.register(StageHistory)
class StageHistoryAdmin(admin.ModelAdmin):
    list_display = ("id", "application", "stage", "entered_at")
    list_filter = ("stage",)
    search_fields = ("application__candidate__full_name",)
    ordering = ("-entered_at",)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "verb", "target_type", "target_id", "actor")
    list_filter = ("verb", "target_type")
    search_fields = ("target_id", "verb")
    readonly_fields = ("actor", "verb", "target_type", "target_id", "timestamp", "data")
    ordering = ("-timestamp",)