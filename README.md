# Recruitment Pipeline Management System
This document outlines the design, implementation, and usage of the Recruitment Pipeline API, built with Django and Django REST Framework, focusing on transparency, data integrity, and observability.

## Problem Definition
### Business Problem
Recruitment processes are often tracked using fragmented tools (spreadsheets, emails), leading to:

- fragmented visibility into candidate status
- inconsistent workflows and slow hiring decisions
- difficulty auditing actions and understanding process delays

This system standardizes the recruitment pipelineproviding transparency, data integrity, and clear historical tracking.

### Users/Stakeholders
Recruiters/Hiring Managers: Primary users who interact with the system to create job openings, move candidates through the pipeline, log interview feedback, and hire candidates.

### Manual Processes Being Automated
1. Tracking candidate progress across stages
2. Enforcing logical stage transitions
3. Calculating time metrics (time-in-stage and time-to-hire)
4. Maintaining an immutable audit trail for compliance and debugging
5. Centralizing all Candidate, Job, and Application data

### Pain points
1. Lack of Real-time Visibility 
    System Solution: Unified, API-driven status updates and retrieval
2. Inconsistent Processes
    System Solution: Standardized workflow enforced via a single, controlled PATCH /status/ endpoint
3. Manual Calculations 
    System Solution: Automatic computation of days_to_hire.
4. Poor Auditability 
    System Solution: Every status change is recorded in dedicated AuditLog and StageHistory models

## Core Requiements Implementation Plan
### Entities & Relationships
| Entity        |           Description                      |        Relationships            |
|----------------------------------------------------------------------------------------------|
| Job           | Position available for hiring              | One-to-Many with Application    |
| Candidate     | Person applying for roles                  | One-to-Many with Application    |
| Application   | A candidate applying for a job             | Many-to-One (Job, Candidate),   |
|               | Tracks pipeline state                      | One-to-Many with StageHistory   |
| Stage History | Historical log of stage transitions        | Many-to-One with Application    |
| AuditLog      | System-wide, immutable log of user actions | Tracks changes tied to entities |
| User          | Django Auth user performing actions        | Linked in audit logs            |

### Transparency & Observability
- AuditLog model: Records the authenticated Django User (actor), action, timestamp, and metadata (old/new status)
- Stage History Inline: The Django Admin configuration uses TabularInline to display the entire history of stage transitions directly within the Application edit page, providing instant Observability of the workflow
- Health Check: The /healthz/ endpoint provides a readiness check for containerized deployment
- Logging: JSON-structured logs facilitate easier debugging and monitoring in container environments

### Calculated fields & validations
1. Application.current_time_in_stage: Time since last stage transition.
2. Application.days_to_hire: Calculated dynamically via a SerializerMethodField once the status is "hired"
3. Custom Validation: The ApplicationSerializer enforces a Unique Active Application constraint, preventing a candidate from having multiple active applications (status not in 'hired' or 'rejected') for the same job
4. Score Validation: Ensures the score field is within the valid range of 0 to 100
5. Job.open_positions_filled

### Rest Endpoints
1. POST /recruitments/jobs/ - create job
2. GET /recruitments/jobs/?status=open - filter job listings
3. POST /recruitments/applications/ - create application (validation: no duplicate active application)
4. PATCH /recruitments/applications/{id}/status/ - update status & append StageHistory
5. GET /recruitments/applications/{id}/ - retrieve application with logs/history

### Containerized Deployment
- Dockerfile builds the Django application
- docker-compose.yml defines:
    1. services web (Django application), 
    2. db (PostgreSQL database)
- Environment variables control database configuration
- Running docker-compose up launches the full stack

### Testing Strategy
1. Unit Tests
    - Model validations (e.g., score range, unique applications)
    - Business logic: pipeline transitions, time calculations
    - Serializer validation rules
2. Integration Tests
    - Create job → create candidate → create application → update stages → hire
    - Validate API responses, status codes, and history creation
    - Implemented using pytest and pytest-django

## Technical decisions & Trade-offs
### Backend Framework: Django + Django REST Framework
- Django provides an immediate ORM, migrations, admin panel, authentication
- DRF significantly reduces the boilerplate for REST APIs
- Ideal for structured data and predictable workflows

Trade-offs: While DRF adds some overhead, it significantly reduces the boilerplate required for secure, production-ready REST APIs compared to lower-level frameworks.

### Database: PostgreSQL (containerized via Docker)
The Recruitment Pipeline System is inherently a workflow and audit management system. PostgreSQL offers:
- superior transactional reliability (ACID compliance), which is critical for ensuring that status updates (e.g., moving a candidate from Interview to Offer) are never partially recorded. This guarantees the integrity of our core audit trail (Pipeline Step entity), satisfying the core Transparency & Observability requirement.
- JSONB support and indexing useful for metadata
- Containerized with Docker for reproducibility

Trade-offs:
- Slightly more complex setup than SQLite, but necessary for achieving concurrency, data integrity guarantees, and a production-like environment.
- MySQL is less robust than Postgres in strict adherence to standards. Also, eventhough MySQL supports JSON data type, JSONB offers more flexibility for future project extent.

### Authentication: JWT (simplejwt)
Used for securing all workflow endpoints. It is stateless and highly scalable, ideal for microservice architectures.
Endpoints: /auth/token/ (acquire token) and /auth/token/refresh/ (renew token) are provided.

## Setup, Testing & Exploration
### Setup Instructions (Containerized Deployment)
1. Clone repository:
```
git clone <repository_url>
cd <project_directory>
```

2. Build and run containers: (Requires Docker and Docker Compose)
```
docker compose up --build
```

3. Run Migrations and create Superuser: (Execute inside the web container)
```
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

### Testing Instructions
Run the full test suite using the service entrypoint:
```
docker compose exec web pytest
```

### Testing Containers Health
```
docker compose ps
```

### API Exploration & Debugging Guide
using Postman:
/auth/token/ -> method: POST , headers { Content-Type : application/json } , body { "username" : "username" , "password" : "password"}
/recruitments/applications/{id}/status/ -> method: PATCH , headers { Content-Type : application/json, Authorization: Bearer Access Token } , body { "status" : "new_status" , "note" : "note"}

### Authentication Steps:
1. Get Token: Send a POST request to /auth/token/ with your superuser credentials.
2. API Requests: Include the copied Access Token in the header of all protected endpoints: Authorization: Bearer <YOUR_ACCESS_TOKEN>

### Debugging and Observability:
1. Django Admin: Access http://localhost:8000/admin/ to inspect the database state, verify the AuditLog is immutable, and see the StageHistory inline within the Application detail view.
2. Container Logs: Use the following command to view real-time application logs, including the specific AuditLog entries created by the system.
```
docker compose logs web
```