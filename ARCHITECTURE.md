# AI Swim Coach — Architecture

## System Overview

```mermaid
graph TB
    %% Client Layer
    subgraph Client ["Client (Browser)"]
        FE["React SPA<br/>TypeScript · Vite · Recharts"]
    end

    %% AWS Hosting
    subgraph Hosting ["Hosting & Delivery"]
        AMP["AWS Amplify<br/>Static Hosting · CI/CD<br/>main branch auto-deploy"]
    end

    %% API Layer
    subgraph API ["API Layer"]
        APIGW["API Gateway (REST)<br/>Regional Endpoint<br/>29s timeout · CORS · 10MB limit"]
    end

    %% Compute Layer
    subgraph Compute ["Compute"]
        LAM["Lambda (Python 3.12)<br/>ai-swim-coach<br/>256MB · 28s timeout"]
    end

    %% AI Layer
    subgraph AI ["AI / ML"]
        BED["Amazon Bedrock<br/>Claude Haiku 4.5<br/>Tool Use API"]
    end

    %% Storage Layer
    subgraph Storage ["Storage"]
        subgraph DDB ["DynamoDB (6 tables, On-Demand)"]
            T_USERS["ai-swim-coach-users<br/>PK: user_id · GSI: email"]
            T_PROF["ai-swim-coach-user-profiles<br/>PK: user_id"]
            T_SESS["ai-swim-coach-sessions<br/>PK: user_id · SK: session_date<br/>GSI: session_id"]
            T_FRIENDS["ai-swim-coach-friends<br/>PK: pk · SK: sk · GSI: sk-pk"]
            T_NOTES["ai-swim-coach-notes<br/>PK: user_id · SK: note_id"]
            T_RL["ai-swim-coach-rate-limits<br/>PK: rl_key · TTL"]
        end

        subgraph S3 ["S3 Buckets"]
            S3_DATA["ai-swim-coach-data<br/>FIT files · Chat history<br/>(private)"]
            S3_PICS["ai-swim-coach-profile-pictures<br/>Profile photos<br/>(public read)"]
        end
    end

    %% Connections
    FE -->|HTTPS| AMP
    FE -->|REST API calls| APIGW
    APIGW -->|Lambda Proxy| LAM
    LAM -->|InvokeModel| BED
    LAM -->|CRUD| T_USERS
    LAM -->|CRUD| T_PROF
    LAM -->|CRUD| T_SESS
    LAM -->|CRUD| T_FRIENDS
    LAM -->|CRUD| T_NOTES
    LAM -->|Rate check| T_RL
    LAM -->|Get/Put objects| S3_DATA
    LAM -->|Put/Get objects| S3_PICS
```

## Detailed Component Architecture

```mermaid
graph LR
    subgraph Frontend ["Frontend (React SPA)"]
        direction TB
        PAGES["Pages<br/>Dashboard · ActivityDetail<br/>TrainingNotes · Plans<br/>Friends · AI Coach"]
        COMPONENTS["Components<br/>ActivityFeed · AICoachChat<br/>InteractionsPanel · SessionNotes<br/>Navigation · Charts"]
        API_LAYER["API Services<br/>sessionService · notesService<br/>friendsService · interactionsService"]
    end

    subgraph Backend ["Backend (Lambda Handler)"]
        direction TB
        ROUTER["handler.py<br/>Route Dispatch + Auth"]
        
        subgraph Services ["Service Modules"]
            AUTH["auth.py<br/>JWT · bcrypt · Google OAuth"]
            NOTES["notes_service.py<br/>Training Notes CRUD"]
            FRIENDS["friends_service.py<br/>Social Graph"]
            INTERACT["interactions_service.py<br/>Kudos · Comments"]
            HISTORY["chat_history_store.py<br/>S3 Conversation Memory"]
            PROMPT["prompt_assembler.py<br/>Context Builder"]
            BEDROCK["bedrock_client.py<br/>AI Invocation"]
            FIT["fit_parser.py<br/>Garmin .FIT Parsing"]
            SESSIONS["session_history.py<br/>Session Storage"]
            PLANS["plan_generator.py<br/>Training Plan AI"]
        end
    end

    PAGES --> COMPONENTS
    COMPONENTS --> API_LAYER
    API_LAYER -->|HTTP| ROUTER
    ROUTER --> AUTH
    ROUTER --> NOTES
    ROUTER --> FRIENDS
    ROUTER --> INTERACT
    ROUTER --> HISTORY
    ROUTER --> PROMPT
    ROUTER --> BEDROCK
    ROUTER --> FIT
    ROUTER --> SESSIONS
    ROUTER --> PLANS
```

## AI Coach Data Flow

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant Lambda
    participant S3
    participant DynamoDB
    participant Bedrock

    User->>Frontend: Ask AI coach a question
    Frontend->>Lambda: POST /ai/chat {prompt, conversation_history}
    
    Lambda->>S3: Get chat history (best-effort)
    S3-->>Lambda: Previous Q&A entries
    
    Lambda->>DynamoDB: Get training notes (best-effort)
    DynamoDB-->>Lambda: User's notes
    
    Lambda->>DynamoDB: Get sessions (trend data)
    DynamoDB-->>Lambda: Session history
    
    Lambda->>Lambda: prompt_assembler.build_chat_messages()
    Note over Lambda: Assemble system prompt +<br/>notes context + history +<br/>session trends + current prompt
    
    Lambda->>Bedrock: InvokeModel (Claude Haiku 4.5)
    Bedrock-->>Lambda: AI response
    
    Lambda->>S3: Save Q&A entry to history (best-effort)
    Lambda-->>Frontend: {response: "..."}
    Frontend-->>User: Display AI answer
```

## FIT Upload Pipeline

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant Lambda
    participant S3
    participant DynamoDB
    participant Bedrock

    User->>Frontend: Upload .FIT file
    Frontend->>Lambda: POST /upload (multipart/form-data)
    
    Lambda->>Lambda: parse_multipart()
    Lambda->>S3: store_in_s3() (raw FIT file)
    Lambda->>Lambda: parse_fit() (fitparse library)
    Lambda->>Lambda: extract_session_info()
    Note over Lambda: Metrics: pace, SWOLF, stroke rate,<br/>HR zones, splits, stroke breakdown
    
    Lambda->>Bedrock: invoke_bedrock() (structured coaching)
    Bedrock-->>Lambda: {tips[], drill}
    
    Lambda->>DynamoDB: save_session() (full session data)
    Lambda->>DynamoDB: save_to_dynamodb() (coaching audit)
    
    Lambda-->>Frontend: Full response (session + coaching + HR)
    Frontend-->>User: Render session analysis
```

## Infrastructure Summary

| Component | Service | Configuration |
|-----------|---------|---------------|
| Frontend Hosting | AWS Amplify | Auto-deploy from `main`, Vite build |
| API | API Gateway (REST) | Regional, proxy integration, 10MB payload |
| Compute | Lambda | Python 3.12, 256MB, 28s timeout |
| AI Model | Bedrock | Claude Haiku 4.5 (Tool Use API) |
| User Data | DynamoDB | 6 tables, on-demand billing |
| File Storage | S3 | 2 buckets (FIT files + profile pics) |
| Auth | Custom JWT | bcrypt (cost 12), 7-day tokens |
| IaC | Terraform | AWS provider ~> 5.0 |
| CI/CD | Amplify + Manual | Frontend auto-deploy, backend via script |

## Security

- **Auth**: Custom JWT (HS256) with bcrypt password hashing + Google OAuth
- **Rate Limiting**: DynamoDB-backed per-IP throttling (10 req/15min on auth endpoints)
- **Transport**: HTTPS enforced via HSTS headers
- **Headers**: X-Frame-Options: DENY, X-Content-Type-Options: nosniff
- **S3**: FIT uploads fully private; profile pictures public-read
- **CORS**: Restricted to Amplify origin
- **API Gateway**: Custom error responses (413, 4XX, 5XX) with CORS headers

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| Frontend | React 18, TypeScript, Vite, Recharts, react-router-dom v6, CSS (design tokens) |
| Backend | Python 3.12, fitparse, boto3, bcrypt, PyJWT |
| AI | Amazon Bedrock — Claude Haiku 4.5 |
| Testing | Vitest + fast-check (frontend), Pytest + Hypothesis (backend) |
| Infrastructure | Terraform, AWS (Amplify, API GW, Lambda, DynamoDB, S3, Bedrock) |
