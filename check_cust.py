from app import create_app
from app.models import Invoice, db
import warnings
warnings.filterwarnings('ignore')

app = create_app()
with app.app_context():
    inv = Invoice.query.first()
    print(f'Invoice {inv.id}: customer_id={inv.customer_id}, customer={inv.customer}')
    # Check if customer relationship is loaded
    print(f'Customer query: {inv.customer}')
PYEOF