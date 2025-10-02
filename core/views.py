from django.shortcuts import render, redirect
from product.models import Product, Category
from django.db.models import Q
from .forms import SignUpForm
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required

# Create your views here.

def frontpage(request):
    products = Product.objects.all()[0:8]

    return render(request, "core/frontpage.html", {'products':products})

def signup(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)

        if form.is_valid():
            user = form.save()

            login(request, user)

            return redirect('/')
    else:
        form = SignUpForm()

    return render(request, 'core/signup.html', {'form': form})

@login_required
def myaccount(request):
    return render(request, 'core/myaccount.html')

@login_required
def edit_myaccount(request):
    if request.method == 'POST':
        user = request.user
        user.first_name = request.POST.get('first_name')
        user.last_name = request.POST.get('last_name')
        user.email = request.POST.get('email')
        user.username = request.POST.get('username')
        user.save()

        return redirect('myaccount')
    return render(request, 'core/edit_myaccount.html')

def shop(request):
    categories = Category.objects.filter(parent__isnull=True)
    products = Product.objects.all()

    active_category = request.GET.get('category', '')

    if active_category:
        try:
            #หา category object ที่มี slug ตรงกับที่ส่งมา
            category = Category.objects.get(slug=active_category)

            #หากลุ่มของ slug ที่จะใช้ฟิลเตอร โดยเริ่มจาก slug ของตัวเอง และรวม slug ของ subcategories ทั้งหมดเข้าไปด้วย
            subcategories = category.subcategories.all()
            slugs_to_filter = [category.slug] + [sub.slug for sub in subcategories]
            
            #ใช้ __in เพื่อฟิลเตอร์สินค้าจาก slug ทั้งหมดใน list
            products = products.filter(category__slug__in=slugs_to_filter)
        except Category.DoesNotExist:
            #ในกรณีที่ใส่ slug มามั่วๆ ใน URL ก็ให้ไม่เจอสินค้าเลย
            products = Product.objects.none()

    query = request.GET.get('query', '')

    if query:
        products = products.filter(Q(name__icontains=query))

    context = {
        'categories': categories,
        'products': products,
        'active_category': active_category
    }

    return render(request, "core/shop.html", context)

def about(request):
    return render(request, 'core/about.html')