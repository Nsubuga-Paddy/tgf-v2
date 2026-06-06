from __future__ import annotations

from django.db.models import QuerySet

from .models import Project, ProjectAccessRequest, UserProfile


def get_member_project_access_requests(profile: UserProfile) -> QuerySet:
    return profile.project_access_requests.select_related("project").order_by("-created_at")


def get_requestable_projects(profile: UserProfile) -> QuerySet:
    """Projects the member may still request (no access, no pending request)."""
    pending_ids = profile.project_access_requests.filter(
        status=ProjectAccessRequest.STATUS_PENDING,
    ).values_list("project_id", flat=True)
    granted_ids = profile.projects.values_list("pk", flat=True)
    return Project.objects.exclude(pk__in=granted_ids).exclude(pk__in=pending_ids).order_by(
        "name"
    )


def submit_project_access_requests(
    profile: UserProfile,
    project_ids: list,
    member_notes: str = "",
) -> dict:
    """
    Create pending access requests. Skips duplicates (pending) and already-granted projects.
    Returns counts and labels for user feedback.
    """
    notes = (member_notes or "").strip()
    created: list[ProjectAccessRequest] = []
    skipped_duplicate: list[str] = []
    skipped_granted: list[str] = []
    invalid: list[str] = []

    seen: set[int] = set()
    for raw_id in project_ids:
        try:
            project_id = int(raw_id)
        except (TypeError, ValueError):
            continue
        if project_id in seen:
            continue
        seen.add(project_id)

        try:
            project = Project.objects.get(pk=project_id)
        except Project.DoesNotExist:
            invalid.append(str(raw_id))
            continue

        if profile.projects.filter(pk=project.pk).exists():
            skipped_granted.append(project.name)
            continue

        if profile.project_access_requests.filter(
            project=project,
            status=ProjectAccessRequest.STATUS_PENDING,
        ).exists():
            skipped_duplicate.append(project.name)
            continue

        created.append(
            ProjectAccessRequest.objects.create(
                user_profile=profile,
                project=project,
                member_notes=notes,
                status=ProjectAccessRequest.STATUS_PENDING,
            )
        )

    return {
        "created": created,
        "skipped_duplicate": skipped_duplicate,
        "skipped_granted": skipped_granted,
        "invalid": invalid,
    }


def build_submission_messages(result: dict) -> list[tuple[str, str]]:
    """Return (django message level, text) pairs for flash messages."""
    messages_out: list[tuple[str, str]] = []
    created = result["created"]
    if created:
        names = ", ".join(r.project.name for r in created)
        messages_out.append(
            (
                "success",
                f"Submitted access request{'s' if len(created) != 1 else ''} for: {names}.",
            )
        )
    if result["skipped_duplicate"]:
        messages_out.append(
            (
                "info",
                "Already pending (not duplicated): "
                + ", ".join(result["skipped_duplicate"])
                + ".",
            )
        )
    if result["skipped_granted"]:
        messages_out.append(
            (
                "info",
                "You already have access to: "
                + ", ".join(result["skipped_granted"])
                + ".",
            )
        )
    if not created and not result["skipped_duplicate"] and not result["skipped_granted"]:
        messages_out.append(("warning", "No new project requests were submitted."))
    return messages_out
