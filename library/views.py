from library.forms import IssueBookForm
from django.shortcuts import get_object_or_404, redirect, render,HttpResponse
from .models import *
from django.contrib.auth import authenticate, login, logout
from . import forms, models
from datetime import date
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from .models import IssuedBook, Student, Book
from django.conf import settings
from django.core.paginator import Paginator
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from .models import Student  # Ensure you import the Student model
from django.contrib import messages

def index(request):
    return render(request, "index.html")

@login_required(login_url='/admin_login')
def add_book(request):
    if request.method == "POST":
        # Extract form data
        name = request.POST['name']
        author = request.POST['author']
        isbn = request.POST['isbn']
        category = request.POST['category']
        quantity = request.POST.get('quantity', 0)  # Default to 0 if not provided

        try:
            quantity = int(quantity)
            if quantity < 0:
                raise ValueError
        except ValueError:
            return render(request, "add_book.html", {'invalid_quantity': True})

        if Book.objects.filter(isbn=isbn).exists():
            duplicate_alert = True
            return render(request, "add_book.html", {'duplicate_alert': duplicate_alert})
        else:
            book = Book.objects.create(name=name, author=author, isbn=isbn, category=category, quantity=quantity)
            book.save()
            success_alert = True
            return render(request, "add_book.html", {'success_alert': success_alert})

    return render(request, "add_book.html")

@login_required(login_url = '/admin_login')
def view_books(request):
    query = request.GET.get('q', '')  # Get the search query from the URL parameters
    books = Book.objects.all()

    if query:
        # Filter books by name, author, or ISBN
        books = books.filter(
            Q(name__icontains=query) | 
            Q(author__icontains=query) | 
            Q(isbn__icontains=query)
        )

    # Pagination: 10 books per page
    paginator = Paginator(books, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, "view_books.html", {'books': page_obj, 'query': query})


@login_required(login_url='/admin_login')
def view_students(request):
    query = request.GET.get('q', '')  # Get the search query from the URL parameters
    students = Student.objects.all()
    
    if query:
        # Filter students by name or roll number
        students = students.filter(
            Q(user__first_name__icontains=query) | 
            Q(user__last_name__icontains=query) | 
            Q(roll_no__icontains=query)
        )
    
    # Pagination: Show only 10 students per page
    paginator = Paginator(students, 10)  # 10 students per page
    page_number = request.GET.get('page')  # Get the page number from the request
    page_obj = paginator.get_page(page_number)  # Get the students for the current page
    
    return render(request, "view_students.html", {'students': page_obj, 'query': query})

#new function
@login_required(login_url='/admin_login')
@login_required(login_url='/admin_login')
def issue_book(request):
    students = Student.objects.all()
    books = Book.objects.all()
    form = forms.IssueBookForm()

    student_query = request.GET.get('student_q', '')
    book_query = request.GET.get('book_q', '')

    if student_query:
        students = students.filter(
            Q(user__first_name__icontains=student_query) |
            Q(user__last_name__icontains=student_query) |
            Q(roll_no__icontains=student_query)
        )
    if book_query:
        books = books.filter(
            Q(name__icontains=book_query) |
            Q(author__icontains=book_query) |
            Q(isbn__icontains=book_query)
        )

    if request.method == "POST":
        student_id = request.POST.get('student_id')
        isbn = request.POST.get('book_isbn')

        if not Student.objects.filter(user_id=student_id).exists():
            messages.error(request, "Student not found.")
            return redirect('issue_book')

        try:
            book = Book.objects.get(isbn=isbn)
        except Book.DoesNotExist:
            messages.error(request, "Book not available.")
            return redirect('issue_book')

        if book.quantity <= 0:
            messages.error(request, "Book out of stock.")
            return redirect('issue_book')

        issued_book = IssuedBook(student_id=student_id, isbn=isbn, returned=False)
        issued_book.save()

        book.quantity -= 1
        book.save()

        messages.success(request, "Book issued successfully!")
        return redirect('issue_book')

    return render(request, "issue_book.html", {
        'form': form,
        'students': students,
        'books': books
    })

@login_required(login_url='/admin_login')
def view_issued_book(request):
    issuedBooks = IssuedBook.objects.filter(returned=False)
    details = []
    
    for i in issuedBooks:
        days = (date.today() - i.issued_date).days
        fine = max(0, (days - 14) * 5) if days > 14 else 0
        
        book = Book.objects.filter(isbn=i.isbn).first()
        student = Student.objects.filter(user=i.student_id).first()

        if book and student:
            t = (
                student.user, 
                student.user_id, 
                book.name, 
                book.isbn, 
                i.issued_date, 
                i.expiry_date, 
                fine
            )
            details.append(t)

    paginator = Paginator(details, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, "view_issued_book.html", {'details': page_obj})



@login_required(login_url='/admin_login')
def return_book(request, student_id, isbn):
    try:
        issued_book = IssuedBook.objects.get(student_id=student_id, isbn=isbn, returned=False)
        issued_book.returned = True
        issued_book.save()

        # ✅ Increase book quantity after return
        book = Book.objects.get(isbn=isbn)
        book.quantity += 1
        book.save()

        messages.success(request, "Book returned successfully!")
    except IssuedBook.DoesNotExist:
        messages.error(request, "Issued book not found.")
    except Book.DoesNotExist:
        messages.error(request, "Book not found.")

    return redirect('view_issued_book')



@login_required(login_url='/student_login')
def student_issued_books(request):
    student = Student.objects.filter(user_id=request.user.id).first()  # Ensure single student object
    if not student:
        return redirect('/student_login')  # Redirect if student is not found

    issuedBooks = IssuedBook.objects.filter(student_id=student.user_id)
    issued_details = []

    for issued_book in issuedBooks:
        book = Book.objects.filter(isbn=issued_book.isbn).first()
        if book:
            days_issued = (date.today() - issued_book.issued_date).days
            fine = max(0, (days_issued - 14) * 5) if days_issued > 14 else 0
            
            issued_details.append({
                'user_id': request.user.id,
                'full_name': request.user.get_full_name(),
                'book_name': book.name,
                'book_author': book.author,
                'issued_date': issued_book.issued_date,
                'expiry_date': issued_book.expiry_date,
                'fine': fine
            })

    return render(request, 'student_issued_books.html', {'issued_details': issued_details})


@login_required(login_url = '/student_login')
def profile(request):
    return render(request, "profile.html")

@login_required(login_url = '/student_login')
def edit_profile(request):
    student = Student.objects.get(user=request.user)
    if request.method == "POST":
        student.user.email = request.POST['email']
        student.phone = request.POST['phone']
        student.branch = request.POST['branch']
        student.classroom = request.POST['classroom']
        student.roll_no = request.POST['roll_no']
        student.user.save()
        student.save()
        alert = True
        return render(request, "edit_profile.html", {'alert':alert})
    return render(request, "edit_profile.html")

def delete_book(request, myid):
    books = Book.objects.filter(id=myid)
    books.delete()
    return redirect("/view_books")

def delete_student(request, myid):
    students = Student.objects.filter(id=myid)
    students.delete()
    return redirect("/view_students")

def delete_issue(request, myid, isbn):
    
    try:
        issue = IssuedBook.objects.get(student_id=myid, isbn=isbn)
    except IssuedBook.DoesNotExist:
        return redirect('view_issued_book')
    
    issue.delete()
   
    return redirect('view_issued_book')

def change_password(request):
    if request.method == "POST":
        current_password = request.POST['current_password']
        new_password = request.POST['new_password']
        try:
            u = User.objects.get(id=request.user.id)
            if u.check_password(current_password):
                u.set_password(new_password)
                u.save()
                alert = True
                return render(request, "change_password.html", {'alert':alert})
            else:
                currpasswrong = True
                return render(request, "change_password.html", {'currpasswrong':currpasswrong})
        except:
            pass
    return render(request, "change_password.html")

def student_registration(request):
    if request.method == "POST":
        Username=request.POST['username']
        password=request.POST['password']
        phone=request.POST['phone']
        confirm_password = request.POST['confirm_password']
        if password != confirm_password:
            passnotmatch = True
            return render(request, "student_registration.html", {'passnotmatch':passnotmatch})

        if User.objects.filter(username=Username).exists():
            return render(request, "student_registration.html", {'username_exists': True})
        
        image = request.FILES['image']
        if image.size > 1024*1024*5:  # 5MB
            return render(request, "student_registration.html",{'image_size':True})
        if not image.name.endswith(('.jpg', '.jpeg', '.png')):
            return render(request, "student_registration.html",{'image_format':True})
       
        user = User.objects.create_user(username=Username, email=request.POST['email'], password=password,first_name=request.POST['first_name'], last_name=request.POST['last_name'])
        student = Student.objects.create(user=user, phone=phone, branch=request.POST['branch'], classroom=request.POST['classroom'],roll_no=request.POST['roll_no'], image=image)
        user.save()
        student.save()
        alert = True
        return render(request, "student_registration.html", {'alert':alert})
    return render(request, "student_registration.html")


def student_login(request):
    if request.method == "POST":
        user = authenticate(username=request.POST['username'], password=request.POST['password'])

        if user is not None:
            login(request, user)
            if request.user.is_superuser:
                return HttpResponse("You are not a student!!")
            else:
                return redirect("/profile")
        else:
            alert = True
            return render(request, "student_login.html", {'alert':alert})
    return render(request, "student_login.html")

def admin_login(request):
    if request.method == "POST":
        user = authenticate(username=request.POST['username'], password=request.POST['password'])

        if user is not None:
            login(request, user)
            if request.user.is_superuser:
                return redirect("/add_book")
            else:
                return HttpResponse("You are not an admin.")
        else:
            alert = True
            return render(request, "admin_login.html", {'alert':alert})
    return render(request, "admin_login.html")

def Logout(request):
    logout(request)
    return redirect ("/")