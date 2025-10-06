from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.conf import settings

from .cart import Cart

from product.models import Product

def add_to_cart(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, pk=product_id)

    # จำนวนที่มีอยู่ในตะกร้า
    current = cart.get_item(product_id)
    current_qty = current['quantity'] if current else 0

    # กันเกินสต็อก: ให้เพิ่มได้ทีละ 1 และไม่เกิน product.quantity
    if current_qty >= product.quantity:
        return render(request, 'cart/partials/menu_cart.html', {'cart': cart})

    cart.add(product_id, 1, update_quantity=True)  # ← เพิ่มทีละ 1 เท่านั้น
    return render(request, 'cart/partials/menu_cart.html', {'cart': cart})

def cart(request):
    return render(request, 'cart/cart.html')

def success(request):
    return render(request, 'cart/success.html')

def update_cart(request, product_id, action):
    cart = Cart(request)
    product = get_object_or_404(Product, pk=product_id)

    item = cart.get_item(product_id)
    current_qty = item['quantity'] if item else 0

    if action == 'increment':
        # กันเกินจำนวนคงเหลือ
        if current_qty < product.quantity:
            cart.add(product_id, 1, update_quantity=True)

    elif action == 'decrement':
        # ถ้าจะเหลือ 0 ให้ลบออกเลย
        new_qty = current_qty - 1
        if new_qty <= 0:
            cart.remove(product_id)
        else:
            cart.add(product_id, -1, update_quantity=True)

    elif action == 'remove':
        cart.remove(product_id)

    # ส่ง partial กลับ (ถ้าถูกลบ item=None จะได้ HTML ว่าง → outerHTML แล้วหาย)
    refreshed = cart.get_item(product_id)
    ctx_item = None
    if refreshed:
        qty = refreshed['quantity']
        ctx_item = {
            'product': product,
            'quantity': qty,
            'total_price': (qty * product.price) / 100,
        }

    response = render(request, 'cart/partials/cart_item.html', {'item': ctx_item})
    response['HX-Trigger'] = 'update-menu-cart'
    return response

@login_required
def checkout(request):
    pub_key = settings.STRIPE_API_KEY_PUBLISHABLE
    return render(request, 'cart/checkout.html', {'pub_key': pub_key})

def hx_menu_cart(request):
    return render(request, 'cart/partials/menu_cart.html')

def hx_cart_total(request):
    return render(request, 'cart/partials/cart_total.html')