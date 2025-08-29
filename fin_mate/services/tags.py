from fin_mate.models import TransactionTag


def replace_transaction_tags(tx, selected_tags, added_by):
    selected_ids = set(getattr(t, "pk", t) for t in (selected_tags or []))
    current_ids = set(tx.tags.values_list("pk", flat=True))

    to_add = selected_ids - current_ids
    to_remove = current_ids - selected_ids

    if to_remove:
        TransactionTag.objects.filter(transaction=tx, tag_id__in=to_remove).delete()
    if to_add:
        TransactionTag.objects.bulk_create([
            TransactionTag(transaction=tx, tag_id=tid, added_by=added_by)
            for tid in to_add
        ])
