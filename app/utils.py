from flask import g, abort
from flask_login import current_user


def scoped(model):
    """Always use this instead of Model.query for any tenant-owned table."""
    business_id = getattr(g, "business_id", None)
    if business_id is None:
        if getattr(current_user, "is_authenticated", False):
            abort(403)
        abort(401)
    return model.query.filter_by(business_id=business_id)
