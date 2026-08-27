from flask import g
from flask_login import current_user

def scoped(model):
    """Always use this instead of Model.query for any tenant-owned table."""
    return model.query.filter_by(business_id=g.business_id)
