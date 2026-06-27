# AI Swim Coach

Upload a Garmin `.fit` file from your swim workout and get personalized coaching feedback powered by AI. The system extracts pace, SWOLF, and stroke rate from your file, sends them to an elite AI swim coach (Claude 3.5 Sonnet via Amazon Bedrock), and returns three actionable tips plus one drill recommendation.

## Architecture

### High-Level Architecture

```mermaid
flowchart TB
    subgraph Client["Client Layer"]
        User[("👤 Swimmer")]
        Browser["🌐 Browser"]
    end

    subgraph Frontend["Frontend (AWS Amplify)"]
        React["React App<br/>(TypeScript + Vite)"]
        FileDropZone["FileDropZone<br/>Component"]
        CoachingResult["CoachingResult<br/>Component"]
        APIClient["API Client<br/>(upload.ts)"]
    end

    subgraph AWS["AWS Cloud Infrastructure"]
        subgraph API["API Layer"]
            APIGW["API Gateway<br/>REST API<br/>POST /upload"]
        end

        subgraph Compute["Compute Layer"]
            Lambda["Lambda Function<br/>Python 3.12<br/>28s timeout"]
            MultipartParser["Multipart<br/>Parser"]
            FitParser["FIT File<br/>Parser<br/>(fitparse)"]
            BedrockClient["Bedrock<br/>Client"]
            DynamoWriter["DynamoDB<br/>Writer"]
        end

        subgraph Storage["Storage Layer"]
            S3["S3 Bucket<br/>uploads/{uuid}.fit"]
            DDB["DynamoDB Table<br/>coaching-sessions"]
        end

        subgraph AI["AI Layer"]
            Bedrock["Amazon Bedrock<br/>Claude 3.5 Sonnet<br/>Tool Use API"]
        end
    end

    User --> Browser
    Browser --> React
    React --> FileDropZone
    FileDropZone --> APIClient
    APIClient -->|"POST<br/>multipart/form-data<br/>.fit file"| APIGW
    APIGW -->|"invoke (sync)"| Lambda
    Lambda --> MultipartParser
    MultipartParser -->|"raw bytes"| FitParser
    Lambda -->|"PutObject"| S3
    FitParser -->|"Metrics<br/>(pace, SWOLF,<br/>stroke rate)"| BedrockClient
    BedrockClient -->|"InvokeModel<br/>with tool schema"| Bedrock
    Bedrock -->|"CoachingResponse<br/>(3 tips + drill)"| BedrockClient
    BedrockClient --> DynamoWriter
    DynamoWriter -->|"PutItem<br/>(best-effort)"| DDB
    Lambda -->|"HTTP 200 JSON<br/>{tips, drill}"| APIGW
    APIGW -->|"response"| APIClient
    APIClient --> CoachingResult
    CoachingResult --> Browser
    Browser --> User

    style User fill:#e1f5ff
    style Browser fill:#e1f5ff
    style React fill:#61dafb
    style Lambda fill:#ff9900
    style S3 fill:#569a31
    style DDB fill:#527fff
    style Bedrock fill:#ff9900
    style APIGW fill:#ff4f8b
```

### Detailed Data Flow

```mermaid
sequenceDiagram
    actor User as 👤 Swimmer
    participant UI as React App
    participant AG as API Gateway
    participant Lambda as Lambda Handler
    participant S3 as S3 Bucket
    participant Parser as FIT Parser
    participant Bedrock as Bedrock (Claude)
    participant DDB as DynamoDB

    User->>UI: 1. Select & drop .fit file
    UI->>UI: 2. Validate (.fit ext, <100MB)
    UI->>AG: 3. POST /upload (multipart/form-data)
    AG->>Lambda: 4. Invoke with base64 body
    
    Lambda->>Lambda: 5. Parse multipart body
    Lambda->>S3: 6. PutObject (uploads/{uuid}.fit)
    S3-->>Lambda: 7. Success
    
    Lambda->>Parser: 8. Parse FIT bytes
    Parser-->>Lambda: 9. Metrics (pace, SWOLF, stroke_rate)
    
    Lambda->>Bedrock: 10. InvokeModel with metrics + tool schema
    Bedrock-->>Lambda: 11. Tool call result (3 tips + drill)
    
    Lambda->>DDB: 12. PutItem (session record)
    Note over Lambda,DDB: Best-effort (doesn't block response)
    
    Lambda-->>AG: 13. HTTP 200 {tips, drill}
    AG-->>UI: 14. JSON response
    UI->>UI: 15. Render CoachingResult
    UI-->>User: 16. Display tips & drill
```

### Error Handling Flow

```mermaid
flowchart TD
    Start([Lambda Invoked]) --> ParseMP[Parse Multipart]
    ParseMP -->|No file part| E400[HTTP 400<br/>No FIT file found]
    ParseMP -->|Success| StoreS3[Store in S3]
    
    StoreS3 -->|boto3 exception| E500[HTTP 500<br/>Failed to store file]
    StoreS3 -->|Success| ParseFIT[Parse FIT File]
    
    ParseFIT -->|Malformed| E422A[HTTP 422<br/>Malformed FIT file]
    ParseFIT -->|Missing metrics| E422B[HTTP 422<br/>Missing metrics: ...]
    ParseFIT -->|Success| InvokeBR[Invoke Bedrock]
    
    InvokeBR -->|Network/HTTP error| E502A[HTTP 502<br/>AI coach unavailable]
    InvokeBR -->|Parse failure| Retry{Retry?}
    Retry -->|First failure| InvokeBR
    Retry -->|Second failure| E502B[HTTP 502<br/>Invalid response]
    InvokeBR -->|Success| WriteDDB[Write to DynamoDB]
    
    WriteDDB -->|Exception| Log[Log Error]
    WriteDDB -->|Success| Return200
    Log --> Return200[HTTP 200<br/>Return CoachingResponse]
    
    style E400 fill:#ffcccc
    style E500 fill:#ffcccc
    style E422A fill:#ffcccc
    style E422B fill:#ffcccc
    style E502A fill:#ffcccc
    style E502B fill:#ffcccc
    style Return200 fill:#ccffcc
```

### Component Relationships

```mermaid
graph TB
    subgraph Frontend["Frontend Components"]
        App[App.tsx]
        Upload[UploadPage.tsx]
        Dropzone[FileDropZone.tsx]
        Result[CoachingResult.tsx]
        Error[ErrorBanner.tsx]
        Loading[LoadingIndicator.tsx]
        API[api/upload.ts]
        Validate[utils/validateFile.ts]
    end

    subgraph Backend["Backend Modules"]
        Handler[handler.py<br/>Pipeline Orchestrator]
        MPParser[multipart_parser.py]
        FParser[fit_parser.py]
        BClient[bedrock_client.py]
        DWriter[dynamo_writer.py]
        S3Store[s3_store.py]
        Models[models.py<br/>Metrics, CoachingResponse]
    end

    subgraph Infrastructure["Infrastructure (Terraform)"]
        TF_API[api_gateway.tf]
        TF_Lambda[lambda.tf]
        TF_S3[s3.tf]
        TF_DDB[dynamodb.tf]
        TF_IAM[iam.tf]
        TF_Amplify[amplify.tf]
    end

    App --> Upload
    Upload --> Dropzone
    Upload --> Result
    Upload --> Error
    Upload --> Loading
    Upload --> API
    Dropzone --> Validate
    API --> Validate

    Handler --> MPParser
    Handler --> FParser
    Handler --> BClient
    Handler --> DWriter
    Handler --> S3Store
    Handler --> Models
    FParser --> Models
    BClient --> Models

    TF_Amplify -.deploys.-> Frontend
    TF_API -.creates.-> APIGW[API Gateway]
    TF_Lambda -.creates.-> LambdaRes[Lambda]
    TF_S3 -.creates.-> S3Res[S3]
    TF_DDB -.creates.-> DDBRes[DynamoDB]
    TF_IAM -.configures.-> LambdaRes
    
    LambdaRes -.runs.-> Backend

    style Frontend fill:#e1f5ff
    style Backend fill:#fff4e1
    style Infrastructure fill:#f0e1ff
```

## Project Structure

```
aiswimcoach/
├── backend/                  # Python Lambda function
│   ├── handler.py            # Lambda entry point (pipeline orchestrator)
│   ├── multipart_parser.py   # Extracts .fit bytes from multipart body
│   ├── fit_parser.py         # Parses FIT files → Metrics (pace, SWOLF, stroke rate)
│   ├── s3_store.py           # Stores raw files in S3
│   ├── bedrock_client.py     # Invokes Claude via Bedrock Tool Use API
│   ├── dynamo_writer.py      # Persists coaching responses to DynamoDB
│   ├── models.py             # Metrics and CoachingResponse dataclasses
│   ├── requirements.txt      # Production dependencies
│   ├── requirements-dev.txt  # Test dependencies (pytest, hypothesis, moto)
│   └── tests/                # Unit and property-based tests
├── frontend/                 # React + TypeScript (Vite)
│   ├── src/
│   │   ├── pages/UploadPage.tsx
│   │   ├── components/       # FileDropZone, CoachingResult, ErrorBanner
│   │   ├── api/upload.ts     # API client with error mapping
│   │   ├── utils/validateFile.ts
│   │   └── types.ts
│   ├── package.json
│   └── vite.config.ts
├── infra/                    # Terraform (AWS infrastructure)
│   ├── main.tf              # Provider configuration
│   ├── api_gateway.tf       # REST API, POST /upload, CORS, binary media
│   ├── lambda.tf            # Lambda function (Python 3.12, 28s timeout)
│   ├── s3.tf                # Uploads bucket (private)
│   ├── dynamodb.tf          # coaching-sessions table
│   ├── iam.tf               # Lambda role + permissions
│   ├── amplify.tf           # Amplify app + branch
│   └── outputs.tf           # API Gateway URL, bucket name, etc.
└── .kiro/specs/             # Requirements, design, and task specs
```

## Getting Started

### Prerequisites

- Python 3.12+
- Node.js 18+
- Terraform 1.5+
- AWS CLI configured with credentials
- A GitHub repository (for Amplify deployments)

### Backend Setup

```bash
cd backend
python -m venv ../.venv
source ../.venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev          # Development server
npm run build        # Production build
```

### Running Tests

```bash
# Backend (44 tests)
PYTHONPATH=. .venv/bin/pytest backend/tests/ -v

# Frontend (18 tests)
cd frontend && npx vitest run
```

## Deployment

### 1. Package the Lambda

```bash
cd backend
pip install -r requirements.txt -t package/
cp -r *.py package/
cd package && zip -r ../../backend.zip . && cd ../..
```

### 2. Deploy Infrastructure

```bash
cd infra
terraform init
terraform plan -var="repository_url=https://github.com/magnus-hs/aiswimcoach"
terraform apply -var="repository_url=https://github.com/magnus-hs/aiswimcoach"
```

### 3. Set Frontend Environment

After `terraform apply`, grab the API Gateway URL from the output:

```bash
terraform output api_gateway_url
```

This is automatically wired into the Amplify build via the `VITE_API_ENDPOINT` environment variable.

## API

### POST /upload

Upload a `.fit` file and receive coaching feedback.

**Request:** `multipart/form-data` with a `file` field containing the `.fit` file (max 10 MB).

**Success Response (200):**
```json
{
  "tips": [
    "Focus on maintaining a high elbow catch to reduce drag.",
    "Breathe bilaterally to balance your stroke.",
    "Increase kick tempo in the final 25m of each rep."
  ],
  "drill": "Single-arm freestyle: 4x50m each arm, focusing on high elbow recovery and hand entry in front of shoulder."
}
```

**Error Responses:**
| Status | Meaning |
|--------|---------|
| 400 | No .fit file found in request |
| 413 | Payload exceeds 10 MB |
| 422 | Malformed file or missing metrics |
| 502 | AI coach unavailable |

## Tech Stack

- **Frontend:** React 18, TypeScript, Vite, react-dropzone
- **Backend:** Python 3.12, fitparse, boto3
- **AI:** Amazon Bedrock (Claude 3.5 Sonnet) with Tool Use API
- **Infrastructure:** API Gateway (REST), Lambda, S3, DynamoDB, Amplify
- **IaC:** Terraform
- **Testing:** pytest + hypothesis (backend), Vitest + fast-check (frontend)

## License

MIT
