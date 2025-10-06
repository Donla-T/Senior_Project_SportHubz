from django.conf import settings

from product.models import Product

class Cart(object):
    def __init__(self, request):
        self.session = request.session
        cart = self.session.get(settings.CART_SESSION_ID)

        if not cart:
            cart = self.session[settings.CART_SESSION_ID] = {}
        
        self.cart = cart
    
    def __iter__(self):
        cart_data = self.cart  # dict ใน session: { "1": {"quantity": X, "id": "1"}, ... }
        product_ids = list(cart_data.keys())
        products = Product.objects.filter(pk__in=product_ids)
        products_map = {str(p.id): p for p in products}

        for pid, row in cart_data.items():
            product = products_map.get(str(pid))
            if not product:
                # กันกรณี product ถูกลบไปแล้ว
                continue

            quantity = int(row.get('quantity', 0))
            yield {
                'id': pid,
                'product': product,
                'quantity': quantity,
                'total_price': (product.price * quantity) / 100,
            }
    
    def __len__(self):
        return sum(item['quantity'] for item in self.cart.values())
    
    def save(self):
        self.session[settings.CART_SESSION_ID] = self.cart
        self.session.modified = True
    
    def add(self, product_id, quantity=1, update_quantity=False):
        product_id = str(product_id)

        if product_id not in self.cart:
            self.cart[product_id] = {'quantity': 0, 'id': product_id}
        
        if update_quantity:
            self.cart[product_id]['quantity'] += int(quantity)

            if self.cart[product_id]['quantity'] == 0:
                self.remove(product_id)
            
        self.save()
    
    def remove(self, product_id):
        pid = str(product_id)
        if pid in self.cart:
            del self.cart[pid]
            self.save()

    def clear(self):
        del self.session[settings.CART_SESSION_ID]
        self.session.modified = True
    
    def get_total_cost(self):
        cart_data = self.cart
        product_ids = list(cart_data.keys())
        products = Product.objects.filter(pk__in=product_ids)
        products_map = {str(p.id): p for p in products}

        total_stang = 0  # สตางค์
        for pid, row in cart_data.items():
            product = products_map.get(str(pid))
            if not product:
                continue
            quantity = int(row.get('quantity', 0))
            total_stang += product.price * quantity

        return total_stang / 100
    
    def get_item(self, product_id):
        if str(product_id) in self.cart:
            return self.cart[str(product_id)]
        else:
            return None