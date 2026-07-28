"""Permanent citation URLs (see docs/archive/data_model_design.md §6)."""

from django.shortcuts import redirect, render

from archive.models import ReferenceAlias, Segment


def _segments_for_cref(cref):
    return (
        Segment.objects.filter(cref=cref)
        .select_related("volume", "kind", "folio")
        .order_by("volume", "order")
    )


def cite(request, token):
    """
    /cite/{token}/

    - token containing ':' → legacy alias (scheme:value) → redirect to canonical
    - otherwise → canonical cref → show all editions carrying this cref
    """
    if ":" in token:
        scheme, _, value = token.partition(":")
        alias = ReferenceAlias.objects.filter(scheme=scheme, value=value).first()
        if alias:
            return redirect("archive:cite", token=alias.cref)
        return render(request, "archive/cite_not_found.html", {"token": token}, status=404)

    segments = _segments_for_cref(token)
    return render(
        request,
        "archive/cite.html",
        {"cref": token, "segments": segments},
    )


def cite_edition(request, collection_code, edition_code, cref):
    """/cite/{collection.code}/{edition.code}/{cref}/ — one edition directly."""
    from website.models import EditionPage, VolumePage

    # edition.code is unique only within its collection, so match the parent too.
    edition = None
    for candidate in EditionPage.objects.filter(code=edition_code):
        parent = candidate.get_parent().specific
        if getattr(parent, "code", None) == collection_code:
            edition = candidate
            break

    if edition is None:
        return render(
            request,
            "archive/cite_not_found.html",
            {"token": f"{collection_code}/{edition_code}/{cref}"},
            status=404,
        )

    volume_ids = list(
        edition.get_descendants().type(VolumePage).values_list("id", flat=True)
    )
    segment = (
        Segment.objects.filter(cref=cref, volume_id__in=volume_ids)
        .select_related("volume", "kind", "folio")
        .first()
    )
    return render(
        request,
        "archive/cite.html",
        {"cref": cref, "edition": edition, "segments": [segment] if segment else []},
    )
