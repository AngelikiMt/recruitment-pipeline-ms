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
### Entities & Relationships

| Entity | Description | Relationships |
|:---|:---|:---|
| **Job** | Position available for hiring | One-to-Many with Application |
| **Candidate** | Person applying for roles | One-to-Many with Application |
| **Application** | A candidate applying for a job, Tracks pipeline state | Many-to-One (Job, Candidate), One-to-Many with StageHistory |
| **Stage History** | Historical log of stage transitions | Many-to-One with Application |
| **AuditLog** | System-wide, immutable log of user actions | Tracks changes tied to entities |
| **User** | Django Auth user performing actions | Linked in audit logs |

### Transparency & Observability
- AuditLog model: Records the authenticated Django User (actor), action, timestamp, and metadata (old/new status)
- Stage History Inline: The Django Admin configuration uses TabularInline to display the entire history of stage transitions directly within the Application edit page, providing instant Observability of the workflow
- Health Check: The /healthz/ endpoint provides a readiness check for containerized deployment
- Logging: JSON-structured logs facilitate easier debugging and monitoring in container environments

### Pipeline Transition Rules
The system enforces strict, predefined status changes to maintain process consistency. Any attempt to skip steps (e.g., applied directly to offer) will be rejected by the API with a 400 Bad Request.

| Current Status | Allowed Next Statuses |
|:---|:---|
| applied | phone_screen, rejected |
| phone_screen | onsite, rejected |
| onsite | offer, rejected |
| offer | hired, rejected |
| hired, rejected | (Final states - no further transitions allowed) |

### Reject Reason Validation
When an application is moved to the rejected status, the system requires a specific rejection reason (reject_reason field) to be provided. This ensures data completeness for future analytics and auditability.

Valid reasons include: culture_fit, technical_skills, experience, salary, position_closed.

### Calculated fields & validations
1. Application.current_time_in_stage: Time since last stage transition.
2. Application.days_to_hire: Calculated dynamically via a SerializerMethodField once the status is "hired"
3. Custom Validation: The ApplicationSerializer enforces a Unique Active Application constraint, preventing a candidate from having multiple active applications (status not in 'hired' or 'rejected') for the same job
4. Score Validation: Ensures the score field is within the valid range of 0 to 100

### Rest Endpoints
1. POST /recruitments/jobs/ - create job
2. GET /recruitments/jobs/?status=open - filter job listings
3. POST /recruitments/applications/ - create application (validation: no duplicate active application)
4. PATCH /recruitments/applications/{id}/status/ - update status & append StageHistory (Validation: transition rules & reject reason)
5. GET /recruitments/applications/{id}/ - retrieve application with logs/history

### Containerized Deployment
1. Dockerfile builds the Django application
2. docker-compose.yml defines:
    - services web (Django application), 
    - db (PostgreSQL database)
3. Environment variables control database configuration
4. Running docker compose up launches the full stack

### Testing
1. Unit Tests
    - Model validations (e.g., score range, unique applications)
    - Service Layer Logic: pipeline transitions and reject reason validation
    - Business logic: pipeline transitions, time calculations
    - Serializer validation rules
2. Integration Tests
    - Create job -> create candidate -> create application -> update stages -> hire
    - Validate API responses, status codes, and history creation
    - Implemented using pytest and pytest-django

## Technical decisions & Trade-offs
### Backend Framework: Django + Django REST Framework
- Django provides an immediate ORM, migrations, admin panel, authentication
- DRF significantly reduces the boilerplate for REST APIs
- Ideal for structured data and predictable workflows

Trade-offs: While DRF adds some overhead, it significantly reduces the boilerplate required for secure, production-ready REST APIs compared to lower-level frameworks.

### Frontend Strategy & Architectural Choice
The Pure API + Django Admin approach is the most strategic choice for this phase of the project. It delivers the core business value, a reliable, auditable workflow, with the minimum time investment and lowest architectural complexity.

| Strategy | Description | Development Time | Complexity | Justification |
|:---|:---|:---|:---|:---|
| Pure API + Django Admin | Django REST Framework (DRF) with the built-in Django Admin Interface used for all management/CRUD tasks | Low | Low | Allows immediate focus on crucial back-end validation, auditing, and business logic. Provides instant, authenticated workflow management |
| Simple Forms / MPA | Traditional Django Templates, Forms, and minimal JavaScript/jQuery | Medium | Medium | Requires developing and maintaining templates, forms, and views for every screen. Offers little advantage over the Django Admin for internal management tasks but significantly increases development overhead |
| Single Page Application (SPA) | Dedicated frontend framework (e.g., React, Vue, Angular) consuming the API separately | High | High | Introduces complexities like CORS, separate build processes, and client-side JWT/State Management. The high initial time and complexity cost is not justified when the primary goal is a robust API back end |

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
1. Install Docker Desktop
2. Docker Login
3. Clone repository:

```
git clone <repository_url>
cd <project_directory>
```

4. Build and run containers: (Requires Docker and Docker Compose)

```
docker compose up --build
```

5. Run Migrations and create Superuser: (Execute inside the web container)

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
1. Authentication
Get an Access Token via Postman for interaction with the protected operations

| Field | Value |
|:---|:---|
| **Endpoint** | /auth/token/ |
| **Method** | POST |
| **Headers** | Content-Type : application/json |
| **Body** | (JSON) |

```
{ 
    "username": "your_superuser_username",
    "password": "your_password"
}
```

2. Pipeline Transition (status update)
Update the application status via Postman for create the StageHistory anf the AuditLog. 
Requires reject_reason if status is "rejected".

| Field | Value |
|:---|:---|
| **Endpoint** | /recruitments/applications/{id}/status/ |
| **Method** | PATCH |
| **Headers** | Content-Type : application/json , Authorization: Bearer your_access_token |
| **Body** | (JSON) |

```
{ 
    "status" : "new_status" , 
    "note" : "your_note"
}
```

```
{ 
    "status" : "rejected", 
    "note" : "Insufficient experience on modern frameworks",
    "reject_reason": "technical_skills"
}
```

### Authentication Steps:
1. Get Token: Send a POST request to /auth/token/ with your superuser credentials.
2. API Requests: Include the copied Access Token in the header of all protected endpoints: Authorization: Bearer <YOUR_ACCESS_TOKEN>

### Debugging and Observability:
1. Django Admin: Access http://localhost:8000/admin/ to inspect the database state, verify the AuditLog is immutable, and see the StageHistory inline within the Application detail view.
2. Container Logs: Use the following command to view real-time application logs, including the specific AuditLog entries created by the system.
```
docker compose logs web
```