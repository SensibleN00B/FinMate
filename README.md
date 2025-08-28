<p align="center">
  <img src="static/img/finmate-mark.svg" alt="FinMate logo" width="500">
</p>


**FinMate** is a personal finance tracking web application built with **Django**.  
It helps you take control of your finances by managing budgets, tracking expenses, and visualizing your spending habits.

## 📸 Screenshots

Some demo screenshots of **FinMate** in action:

| Dashboard | Dashboard p2 |
|---------------------------------------------------|--------------|
| <img src="demo/1.png" alt="Dashboard" width="500"/> | <img src="demo/2.png" alt="Budgets" width="500"/> |

| Accounts   | Transactions |
|-------------------------------------------------------|--------------------------------------------------|
| <img src="demo/3.png" alt="Transactions" width="500"/> | <img src="demo/4.png" alt="Reports" width="500"/> |

| Categories | Tags |
|------------|----------------------------------------------------------|
| <img src="demo/5.png" alt="Categories" width="500"/> | <img src="demo/6.png" alt="Add Transaction" width="500"/> |

| Budgets | Log in  |
|---------------------------------------------------|---------------------------------------------------|
| <img src="demo/7.png" alt="Profile" width="500"/> | <img src="demo/8.png" alt="Settings" width="500"/> |

---

## 🚀 Live demo
https://fin-mate-4a1s.onrender.com

---

## 🔑 Test account

- **Email:** `pullarserbxx.n.ko.18.43@gmail.com`
- **Password:** `1qazcde3`

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
