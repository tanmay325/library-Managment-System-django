from django.db import models
from django.contrib.auth.models import User
from datetime import datetime, timedelta


class Book(models.Model):
    name = models.CharField(max_length=200)
    author = models.CharField(max_length=200)
    isbn = models.PositiveIntegerField(unique=True)
    category = models.CharField(max_length=50)
    quantity = models.PositiveIntegerField(default=1)  # Added field to track available copies

    def __str__(self):
        return str(self.name)


class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    classroom = models.CharField(max_length=10)
    branch = models.CharField(max_length=10)
    roll_no = models.CharField(max_length=3, blank=True)
    phone = models.CharField(max_length=10, blank=True)
    image = models.ImageField(upload_to="", blank=True)

    def __str__(self):
        return str(self.user) + " [" + str(self.branch) + ']' + " [" + str(self.classroom) + ']' + " [" + str(self.roll_no) + ']'


def expiry():
    return datetime.today() + timedelta(days=14)


class IssuedBook(models.Model):
    student_id = models.PositiveIntegerField(blank=True)
    isbn = models.CharField(max_length=13)
    issued_date = models.DateField(auto_now=True)
    expiry_date = models.DateField(default=expiry)
    returned = models.BooleanField(default=False)  # Added field to track book return

    def __str__(self):
        return f"Student ID: {self.student_id} | ISBN: {self.isbn} | Returned: {self.returned}"
