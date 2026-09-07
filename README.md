# 🎬 BookMySeat

BookMySeat is a full-featured Movie Ticket Booking System built with Django. It allows users to browse movies, view show schedules, select seats, make bookings, complete payments, generate QR-based tickets, manage wishlists, and submit reviews and ratings.

## 🚀 Features

### 👤 User Features
- User Registration & Login
- Profile Management
- Browse Movies
- View Movie Details
- Search & Filter Movies
- Seat Selection System
- Ticket Booking
- Booking History
- Wishlist Management
- Movie Ratings & Reviews

### 🎟️ Ticket Management
- QR Code Generation
- PDF Ticket Generation
- Booking Confirmation
- Booking Cancellation

### 💳 Payment Integration
- Razorpay Payment Gateway
- Payment Tracking
- Refund Status Management

### 🎬 Movie Management
- Movie Posters
- Genres & Languages
- Cast Members
- Show Scheduling
- Theater Management

### 🛠️ Admin Features
- Manage Movies
- Manage Theaters
- Manage Show Schedules
- Manage Users
- Manage Bookings
- Dashboard Analytics

### ⚡ Advanced Features
- Celery Background Tasks
- Django Signals
- Optimized Database Indexes
- Secure Authentication
- Responsive UI

---

## 🏗️ Tech Stack

### Backend
- Django
- Python

### Database
- SQLite (Development)
- MySQL (Production Ready)

### Frontend
- HTML5
- CSS3
- Bootstrap

### Additional Libraries
- Razorpay
- Celery
- Redis
- ReportLab
- QRCode

---

## 📂 Project Structure

```text
bookmyseat/
│
├── bookmyseat/
│   ├── settings.py
│   ├── urls.py
│   ├── celery.py
│   └── wsgi.py
│
├── users/
│   ├── models.py
│   ├── views.py
│   ├── forms.py
│   ├── signals.py
│   ├── tasks.py
│   ├── urls.py
│   ├── templates/
│   └── static/
│
├── media/
├── manage.py
└── requirements.txt
```

---

## ⚙️ Installation

### Clone Repository

```bash
git clone https://github.com/LeelaPrasath008/bookmyseat.git
cd bookmyseat
```

### Create Virtual Environment

```bash
python -m venv venv
```

### Activate Virtual Environment

Windows:

```bash
venv\Scripts\activate
```

Linux/Mac:

```bash
source venv/bin/activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Run Migrations

```bash
python manage.py migrate
```

### Create Superuser

```bash
python manage.py createsuperuser
```

### Start Server

```bash
python manage.py runserver
```

Visit:

```
http://127.0.0.1:8000/
```

## 🔮 Future Enhancements

- Email Notifications
- SMS Alerts
- AI Movie Recommendations
- Multi-City Support
- Real-Time Seat Locking
- Coupon & Offers System
- Advanced Analytics Dashboard

---

## 👨‍💻 Author

**Leelaprasath V**

- B.E. Computer Science & Engineering
- University College of Engineering, Kancheepuram

GitHub:
https://github.com/LeelaPrasath008

---

## ⭐ Support

If you like this project, consider giving it a ⭐ on GitHub.
