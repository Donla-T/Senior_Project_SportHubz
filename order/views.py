import json
import stripe
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import F
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404

from cart.cart import Cart
from product.models import Product
from .models import Order, OrderItem

# Create your views here.

@login_required
def start_order(request):
    """
    1) ตรวจสต็อกรอบสุดท้ายจาก cart
    2) สร้าง Order/OrderItem (ยังไม่ตัดสต็อก และยังไม่ paid)
    3) สร้าง Stripe Checkout Session แล้วคืนค่า session ให้ frontend redirect
    """
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    cart = Cart(request)
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        data = {}

    items_in_cart = list(cart)
    if not items_in_cart:
        return JsonResponse({"error": "Cart is empty"}, status=400)

    # 1) ตรวจสต็อก
    product_ids = [row["product"].id for row in items_in_cart]
    db_products = {p.id: p for p in Product.objects.filter(id__in=product_ids)}
    for row in items_in_cart:
        p = db_products.get(row["product"].id)
        qty = int(row["quantity"])
        if (p is None) or (qty <= 0) or (qty > p.quantity):
            return JsonResponse({"error": f"Insufficient stock for {row['product'].name}"}, status=400)

    # 2) สร้าง Order/OrderItem (ยังไม่ตัดสต็อก)
    order = Order.objects.create(
        user=request.user,
        first_name=data.get("first_name", ""),
        last_name=data.get("last_name", ""),
        email=data.get("email", ""),
        address=data.get("address", ""),
        zipcode=data.get("zipcode", ""),
        place=data.get("place", ""),
        phone=data.get("phone", ""),
        paid=False,
    )

    line_items = []
    total_price = 0  # หน่วย "สตางค์"
    for row in items_in_cart:
        p = db_products[row["product"].id]
        qty = int(row["quantity"])
        unit_amount = int(p.price)            # หน่วย "สตางค์"
        total_price += unit_amount * qty

        # เก็บรายการออเดอร์ (ราคาต่อชิ้น หรือจะเก็บ total ต่อบรรทัดก็ได้
        # ที่โปรเจกต์คุณเคยใช้อยู่คือเก็บ total ต่อบรรทัด — คงเดิมให้สอดคล้อง)
        OrderItem.objects.create(
            order=order,
            product=p,
            price=unit_amount * qty,  # total ต่อบรรทัด (สตางค์)
            quantity=qty,
        )

        line_items.append({
            "price_data": {
                "currency": "thb",
                "unit_amount": unit_amount,  # unit price
                "product_data": {"name": p.name},
            },
            "quantity": qty,
        })

    # เก็บ order id รอคอนเฟิร์มตอน success
    request.session["pending_order_id"] = order.id

    # 3) สร้าง Stripe Session
    stripe.api_key = settings.STRIPE_SECRET_KEY
    session = stripe.checkout.Session.create(
        mode="payment",
        payment_method_types=["card"],
        line_items=line_items,
        success_url="http://127.0.0.1:8000/order/success/?session_id={CHECKOUT_SESSION_ID}",
        cancel_url="http://127.0.0.1:8000/cart/",
        customer_email=request.user.email or None,
    )

    order.payment_intent = session.payment_intent or session.id  # เก็บอ้างอิง
    order.paid_amount = total_price
    order.save(update_fields=["payment_intent", "paid_amount"])

    # อย่า clear cart ที่นี่ — รอหลังจ่ายสำเร็จ
    return JsonResponse({"session": session, "order": order.payment_intent})


@login_required
def success(request):
    """
    กลับจาก Stripe:
    - ตรวจ session_id กับ Stripe ว่า paid แล้ว
    - หักสต็อกแบบ atomic จาก OrderItem → Product.quantity
    - ติ๊ก paid=True, clear cart แล้วแสดงหน้าสำเร็จ
    """
    session_id = request.GET.get("session_id")
    if not session_id:
        # เปิดหน้า success ตรง ๆ ก็ให้ผ่าน (กัน refresh ซ้ำ)
        return render(request, "cart/success.html")

    stripe.api_key = settings.STRIPE_SECRET_KEY
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        if session.get("payment_status") != "paid":
            messages.error(request, "Payment not completed.")
            return redirect("cart")
    except Exception as e:
        messages.error(request, f"Stripe verification failed: {e}")
        return redirect("cart")

    order_id = request.session.pop("pending_order_id", None)
    if not order_id:
        # ป้องกัน refresh หน้า success ซ้ำแล้วสร้างผลข้างเคียง
        return render(request, "cart/success.html")

    order = get_object_or_404(Order, id=order_id, user=request.user)

    # ตัดสต็อกอย่างปลอดภัย
    try:
        with transaction.atomic():
            # ล็อกแถวสินค้าที่เกี่ยวข้อง
            for oi in order.items.select_related("product").select_for_update():
                p = oi.product
                # ตรวจซ้ำกัน race กับแอดมินแก้สต็อก
                # (ที่จริงเราตรวจตั้งแต่ start_order แล้ว แต่อันนี้กันกรณีพิเศษ)
                if oi.quantity > p.quantity:
                    raise ValueError(f"Insufficient stock for {p.name}")
                p.quantity = F("quantity") - oi.quantity
                p.save(update_fields=["quantity"])

            order.paid = True
            order.save(update_fields=["paid"])
    except Exception as e:
        messages.error(request, f"Finalize error: {e}")
        return redirect("cart")

    # เคลียร์ตะกร้า
    Cart(request).clear()

    return render(request, "cart/success.html")