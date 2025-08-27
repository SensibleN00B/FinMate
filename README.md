<p align="center">
  <img src="static/img/finmate-mark.svg" alt="FinMate logo" width="500">
</p>


**FinMate** is a personal finance tracking web application built with **Django**.  
It helps you take control of your finances by managing budgets, tracking expenses, and visualizing your spending habits.

---

## ✨ Features

- 📊 **Dashboard with charts** — visualize your income, expenses, and balance trends  
- 💵 **Expense & income tracking** — record all your transactions in one place  
- 🗂 **Categories & budgets** — create category-based monthly budgets  
- 📅 **Period analysis** — filter and analyze data by month or custom date range  
- 🔑 **Authentication** — secure login & registration with **django-allauth**  
- ⚡ **User-friendly interface** — clean design with **Bootstrap 5** and **Chart.js**  

---

## 🛠 Tech Stack

- **Backend:** Python, Django, Django ORM, **django-allauth**  
- **Database:** PostgreSQL (or SQLite for local development)  
- **Frontend:** Bootstrap 5, Chart.js  
- **Tools:** Git, GitHub

---

## 🚀 Getting Started

### 1. Clone the repository
```bash

git clone https://github.com/SensibleN00B/FinMate.git
cd FinMate
```


2. Create & activate virtual environment
```bash

python -m venv venv
source venv/bin/activate  # on Linux/Mac
venv\Scripts\activate     # on Windows
```

3. Install dependencies
```bash

pip install -r requirements.txt
```

4. Configure environment variables. Create a .env file in the root directory with the following variables:
```bash

SECRET_KEY=your-secret-key
DEBUG=True
DATABASE_URL=postgres://user:password@localhost:5432/finmate
```

5. Apply migrations
```bash

python manage.py migrate
```

6. Create superuser
```bash

python manage.py createsuperuser
```

7. Run the development server
```bash

python manage.py runserver
```


Now open http://127.0.0.1:8000/
 in your browser 🎉
