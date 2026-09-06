# Haritha Connect 🌱



A smart community-focused environmental platform designed to streamline waste collection activities managed by Haritha Karma Sena (HKS) workers across different wards.



## Overview



Haritha Connect integrates essential municipal waste management services into a single, unified online system to simplify and enhance daily activities for residents, Haritha Karma Sena (HKS) workers, and administrators. 



I conceived the product, defined the system architecture and user workflows, and directed the implementation, reviewing progress and functionality throughout development.



## Key Features



- **Resident Portal** — allows residents to view their waste collection status, submit priority "Bin Full" alerts, report offline cash payments with photo proofs, skip monthly collections, and register complaints.
- **Worker Portal** — provides HKS field staff with ward-wise daily route lists, task execution tools with photo proofs, options to clear priority bin alerts, confirm cash payments, and submit field issues or absences.
- **Admin Dashboard** — a central control hub enabling administrators to oversee all data, assign duties to workers via the HKS Ward Assignment matrix, auto-generate 10-day monthly collection schedules, verify payments, and resolve complaints.



## Tech Stack



- **Backend:** Python, Django
- **Database:** SQLite (for development)
- **Frontend:** Django Templates, HTML5, CSS3, JavaScript
- **Other:** REST-style routing and structured data management services



## Project Structure



```text
harithaconnect/
├── requirements.txt
└── haritha_backend      # Django project
    ├── core             # Core app: models, views, logic
    ├── templates        # UI and dashboard templates
    └── static           # CSS, JavaScript, assets

```



## Setup



```bash
git clone [https://github.com/Sr-2525/Haritha-Connect.git](https://github.com/Sr-2525/Haritha-Connect.git)
cd Haritha-Connect/haritha_backend

pip install -r ../requirements.txt

python manage.py migrate

python manage.py runserver

```



## Notes



This project was developed as a dedicated platform to promote digital innovation and sustainable community development, with complete oversight of design, architecture, and feature planning.

```

```
