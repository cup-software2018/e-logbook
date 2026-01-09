# E-Logbook System

A web-based digital logbook system designed for research laboratories and experimental groups. This system facilitates recording experimental data, sharing logs within teams based on User Groups, and exporting daily records to PDF format. Built with Django and Bootstrap 5.

## 🚀 Key Features

### 1. Log Management
* **Markdown Support**: Write logs using rich text formatting, tables, and code blocks.
* **Image Uploads**: Attach multiple images to log entries (drag & drop supported).
* **CRUD Operations**: Create, Read, Update, and Delete logs easily.
* **Comments**: Collaborative feedback on specific log entries.

### 2. Access Control & Permissions
* **Private**: Accessible only by the owner.
* **Shared**: Accessible by members of specific **User Groups** (e.g., 'AMoRE Team', 'KIMS Group').
* **Public**: Accessible by all registered users.

### 3. User & Group Management
* **Custom Sign-up**: Register with Email, Name, and **Group Affiliation**.
* **Group Selection**: Integrated `Select2` widget for easy multi-group selection during sign-up.

### 4. Export & Reporting
* **PDF Export**: Generate official daily log sheets using **WeasyPrint**.
* **High-Fidelity Output**: PDF includes proper formatting, images, and timestamps.

### 5. Dashboard
* **Smart Filtering**: Separates 'My Logbooks' from 'Shared & Public Logbooks'.
* **Search**: Full-text search capability for logs and logbooks.

---

## 🛠️ Tech Stack

* **Backend**: Python 3.11, Django 5.x
* **Database**: SQLite (Default)
* **Frontend**: HTML5, CSS3, Bootstrap 5, jQuery
* **Libraries**:
    * `markdown`: For rendering log content.
    * `weasyprint`: For HTML to PDF conversion.
    * `Pillow`: For image processing.
    * `django-widget-tweaks`: For form rendering.

---

## 📦 Installation

Follow these steps to set up the project locally.

### 1. Clone the repository

    git clone https://github.com/YOUR_GITHUB_ID/e-logbook-system.git
    cd e-logbook-system

### 2. Create and activate a virtual environment

**Linux / macOS:**

    python3 -m venv .venv
    source .venv/bin/activate

**Windows:**

    python -m venv .venv
    .venv\Scripts\activate

### 3. Install dependencies

    pip install -r requirements.txt

> **Note:** If you encounter errors installing `WeasyPrint` on Windows or Linux, you may need to install GTK+ libraries separately.

### 4. Apply database migrations

    python manage.py makemigrations
    python manage.py migrate

### 5. Create a Superuser (Admin)
Create an account to manage users and groups.

    python manage.py createsuperuser

### 6. Run the server

    python manage.py runserver

Access the application at: `http://127.0.0.1:8000/`

---

## 📝 Usage Guide

### 1. Setting up Groups (Admin)
Before users sign up, the administrator should create groups.
1. Go to `http://127.0.0.1:8000/admin/` and login.
2. Click **Groups** -> **Add Group**.
3. Create teams (e.g., `Physics Team`, `Analysis Group`). *No specific permissions are required.*

### 2. User Sign Up
1. Go to the **Sign Up** page.
2. Fill in your details and select your **Team (Group)** from the dropdown.
3. Upon registration, you will be automatically logged in.

### 3. Creating a Logbook
1. Click **New Logbook** on the dashboard.
2. Choose the **Access Level**:
    * **Shared**: Select which groups can see this logbook.
    * **Private**: Only you can see it.

### 4. Exporting to PDF
1. Navigate to a specific date in your logbook.
2. Click the **Export PDF** button at the top right.
3. A formatted PDF of that day's logs will be downloaded.

---

## 📂 Project Structure

    e-logbook/
    ├── config/             # Django project settings
    ├── elog/               # Main application app
    │   ├── models.py       # DB Schema
    │   ├── views.py        # Business logic & PDF generation
    │   ├── forms.py        # Custom forms (SignUp, Logbook)
    │   ├── templates/      # HTML Templates
    │   └── urls.py         # URL routing
    ├── media/              # User uploaded images
    ├── static/             # CSS, JS, and static assets
    ├── manage.py
    └── requirements.txt

## 📄 License

This project is licensed under the MIT License.